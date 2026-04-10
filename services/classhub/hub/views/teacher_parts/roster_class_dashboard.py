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
from ...services.helper_control import (
    HelperRemoteComputeEvidenceResult,
    HelperRemoteComputeStatusResult,
    fetch_remote_compute_evidence,
    fetch_remote_compute_status,
)
from ...services.teacher_roster_class import build_dashboard_context
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


def _remote_compute_status_context(*, can_manage_remote_compute: bool, classroom) -> dict:
    if can_manage_remote_compute:
        status_result = fetch_remote_compute_status(
            class_id=classroom.id,
            endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_STATUS_URL", "") or "").strip(),
            internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
            timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
        )
        evidence_result = fetch_remote_compute_evidence(
            class_id=classroom.id,
            endpoint_url=str(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_EVIDENCE_URL", "") or "").strip(),
            internal_token=str(getattr(settings, "HELPER_INTERNAL_API_TOKEN", "") or "").strip(),
            timeout_seconds=float(getattr(settings, "HELPER_INTERNAL_REMOTE_COMPUTE_TIMEOUT_SECONDS", 2.0) or 2.0),
        )
    else:
        status_result = HelperRemoteComputeStatusResult(ok=False, error_code="not_visible")
        evidence_result = HelperRemoteComputeEvidenceResult(ok=False, error_code="not_visible")
    return {
        "helper_remote_compute": status_result,
        "helper_remote_compute_evidence": evidence_result,
        "helper_remote_compute_cost_risk": _remote_compute_cost_risk(
            status_result=status_result,
            evidence_result=evidence_result,
        ),
        "helper_remote_compute_duration_choices": [30, 60, 90, 120],
    }


def _remote_compute_cost_risk(*, status_result, evidence_result) -> dict:
    if not bool(getattr(status_result, "ok", False)):
        return {
            "level": "unavailable",
            "summary": "Staff evidence unavailable",
            "detail": "The helper evidence path did not return a usable remote-compute status snapshot.",
        }
    if not bool(getattr(status_result, "active", False)):
        return {
            "level": "low",
            "summary": "No active lease",
            "detail": "Remote helper compute is off, so there is no current leased-cost exposure.",
        }
    if str(getattr(status_result, "state", "") or "").strip() == "degraded":
        return {
            "level": "degraded_active",
            "summary": "Lease active while degraded",
            "detail": "The lease is still active but helper traffic is falling back locally; stop it if the class no longer needs remote capacity.",
        }
    if int(getattr(status_result, "remaining_minutes", 0) or 0) <= 10:
        return {
            "level": "expiring",
            "summary": "Lease nearing expiry",
            "detail": "The remote window is close to ending; extend it only if the class is actively using the remote path right now.",
        }
    remote_routes = int(getattr(status_result, "remote_route_count", 0) or 0)
    if bool(getattr(evidence_result, "ok", False)):
        recent_sessions = list(getattr(evidence_result, "recent_sessions", []) or [])
        if recent_sessions:
            remote_routes = int(recent_sessions[0].get("remote_route_count") or remote_routes)
    if remote_routes <= 0:
        return {
            "level": "unused_active",
            "summary": "Lease active but unused",
            "detail": "The current lease is running but the helper has not recorded remote-routed chats yet.",
        }
    return {
        "level": "bounded",
        "summary": "Bounded active lease",
        "detail": "Remote helper compute is active within a class-scoped window and has recorded live remote usage.",
    }


@staff_member_required
@require_POST
def teach_create_class(request):
    if not staff_can_create_classes(request.user):
        return HttpResponse("Forbidden", status=403)

    name = _clean_class_seed_value(request.POST.get("name"), limit=200)
    if not name:
        return redirect("/teach")

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
    if first_module_title:
        created_module = classroom.modules.create(title=first_module_title, order_index=0)
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
        },
    )
    if _should_open_class_workspace(request):
        notice = "Class workspace created."
        if created_module:
            notice += " First session added."
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
            **_remote_compute_status_context(
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
