"""Teacher class dashboard/create/join-card endpoints."""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_no_store
from ...models import Class, ClassInviteLink, ClassStaffAssignment
from ...services.coursepack_import import CoursepackImportError, import_content_upload_to_class
from ...services.teacher_roster_class import build_dashboard_context
from .roster_class_remote_compute import remote_compute_status_context
from .shared_auth import (
    staff_can_create_classes,
    staff_can_manage_policy,
    staff_classroom_or_none,
    staff_default_organization,
    staff_member_required,
)
from .shared_ordering import _next_unique_class_join_code, _normalize_order
from .shared_routing import _audit, _teach_class_path, _with_notice


def _class_assignment_panel_context(*, request, classroom):
    if not request.user.is_superuser:
        return {"class_staff_assignments": [], "class_assignment_staff_users": []}
    User = get_user_model()
    staff_users = list(
        User.objects.filter(is_staff=True, is_active=True, is_superuser=False)
        .order_by("username", "id")
        .only("id", "username")
    )
    assignments = list(
        ClassStaffAssignment.objects.select_related("user")
        .filter(classroom=classroom)
        .order_by("-is_active", "user__username", "id")
    )
    return {
        "class_staff_assignments": assignments,
        "class_assignment_staff_users": staff_users,
    }


def _clean_class_seed_value(raw: str | None, *, limit: int) -> str:
    return (raw or "").strip()[:limit]


def _should_open_class_workspace(request) -> bool:
    raw = (request.POST.get("open_after_create") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _class_content_import_upload(request):
    return request.FILES.get("class_content_import")


def _class_content_import_requested(request) -> bool:
    raw = (request.POST.get("class_content_import_intent") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    return _class_content_import_upload(request) is not None


def _class_content_import_options(request) -> dict:
    return {
        "course_slug": _clean_class_seed_value(request.POST.get("import_course_slug"), limit=120).lower(),
        "course_title": _clean_class_seed_value(request.POST.get("import_course_title"), limit=200),
        "default_ui_level": _clean_class_seed_value(request.POST.get("import_default_ui_level"), limit=20) or "secondary",
        "session_parse_mode": _clean_class_seed_value(request.POST.get("import_session_parse_mode"), limit=20) or "auto",
        "overwrite_content": (request.POST.get("import_overwrite_content") or "").strip().lower()
        in {"1", "true", "yes", "on"},
    }


@staff_member_required
@require_POST
def teach_create_class(request):
    if not staff_can_create_classes(request.user):
        return HttpResponse("Forbidden", status=403)
    source_upload = _class_content_import_upload(request)
    import_requested = _class_content_import_requested(request)
    if import_requested and not request.user.is_superuser:
        return HttpResponse("Forbidden", status=403)

    name = _clean_class_seed_value(request.POST.get("name"), limit=200)
    if not name:
        return redirect("/teach")
    if import_requested and source_upload is None:
        return redirect(
            _with_notice(
                "/teach",
                error=(
                    "Class content import was requested, but no file reached the server. "
                    "Reopen the import section, choose the file again, and submit once the filename is visible."
                ),
            )
        )

    landing_title = _clean_class_seed_value(request.POST.get("student_landing_title"), limit=200)
    landing_message = _clean_class_seed_value(request.POST.get("student_landing_message"), limit=4000)
    first_module_title = _clean_class_seed_value(request.POST.get("first_module_title"), limit=200)
    join_code = _next_unique_class_join_code()
    organization = staff_default_organization(request.user)
    classroom = Class.objects.create(
        organization=organization,
        name=name,
        join_code=join_code,
        student_landing_title=landing_title,
        student_landing_message=landing_message,
    )
    created_module = None
    import_result = None
    if first_module_title and source_upload is None:
        created_module = classroom.modules.create(title=first_module_title, order_index=0)
    if source_upload is not None:
        try:
            import_result = import_content_upload_to_class(
                source_upload=source_upload,
                classroom=classroom,
                replace=True,
                **_class_content_import_options(request),
            )
        except CoursepackImportError as exc:
            classroom.delete()
            return redirect(_with_notice("/teach", error=f"Class content import failed: {exc}"))
    if not request.user.is_superuser:
        ClassStaffAssignment.objects.update_or_create(
            classroom=classroom,
            user=request.user,
            defaults={"is_active": True},
        )
    _audit(
        request,
        action="class.create",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Created class {classroom.name}",
        metadata={
            "join_code": classroom.join_code,
            "organization_id": classroom.organization_id,
            "has_student_landing_title": bool(landing_title),
            "has_student_landing_message": bool(landing_message),
            "created_first_module": bool(created_module),
            "first_module_id": created_module.id if created_module else None,
            "imported_course_slug": import_result.course_slug if import_result else "",
            "imported_course_title": import_result.course_title if import_result else "",
            "import_source_kind": import_result.source_kind if import_result else "",
        },
    )
    if import_result:
        _audit(
            request,
            action="class.content_import",
            classroom=classroom,
            target_type="Coursepack",
            target_id=import_result.course_slug,
            summary=f"Imported course content into {classroom.name}",
            metadata={
                "course_slug": import_result.course_slug,
                "course_title": import_result.course_title,
                "source_kind": import_result.source_kind,
                "source_files": list(import_result.source_files),
                "created_modules": import_result.created_modules,
                "created_materials": import_result.created_materials,
                "created_assets": import_result.created_assets,
                "course_dir": str(import_result.course_dir),
                "writes_live_content": True,
            },
        )
    if _should_open_class_workspace(request):
        notice = "Class workspace created."
        if created_module:
            notice += " First session added."
        if import_result:
            notice += f" Imported {import_result.course_slug}."
        return redirect(_with_notice(_teach_class_path(classroom.id), notice=notice))
    return redirect("/teach")


@staff_member_required
def teach_class_dashboard(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)

    context = build_dashboard_context(
        request=request,
        classroom=classroom,
        normalize_order_fn=_normalize_order,
    )
    invite_links = list(
        ClassInviteLink.objects.filter(classroom=classroom)
        .select_related("created_by")
        .order_by("-created_at", "-id")
    )
    now = timezone.now()
    for invite in invite_links:
        invite.invite_url = request.build_absolute_uri(f"/invite/{invite.token}")
        invite.is_expired_now = invite.is_expired(at=now)
        invite.seats_remaining_value = invite.seats_remaining()

    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()
    class_assignment_panel = _class_assignment_panel_context(request=request, classroom=classroom)
    can_manage_remote_compute = bool(staff_can_manage_policy(request.user, classroom))
    get_token(request)

    response = render(
        request,
        "teach_class.html",
        {
            "classroom": classroom,
            **context,
            "invite_links": invite_links,
            "notice": notice,
            "error": error,
            "can_manage_helper_remote_compute": can_manage_remote_compute,
            **remote_compute_status_context(
                can_manage_remote_compute=can_manage_remote_compute,
                classroom=classroom,
            ),
            **class_assignment_panel,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
def teach_class_join_card(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)

    query = urlencode({"class_code": classroom.join_code})
    response = render(
        request,
        "teach_join_card.html",
        {
            "classroom": classroom,
            "join_url": request.build_absolute_uri("/"),
            "prefilled_join_url": request.build_absolute_uri(f"/?{query}"),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
]
