"""Student/session/upload endpoint callables."""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from common.helper_scope import issue_scope_token
from config.localization import localization_from_request

from ..forms import SubmissionUploadForm
from ..http.headers import apply_no_store
from ..models import (
    Class,
    Material,
    StudentEvent,
    StudentIdentity,
    StudentMaterialResponse,
    Submission,
)
from ..services.export_service import build_student_portfolio_export_response
from ..services.helper_widget import build_helper_prompt_sets_json
from ..services.helper_control import clear_actor_conversations as clear_helper_actor_conversations
from ..services.lesson_handouts import resolve_reading_level
from ..services.ip_privacy import minimize_student_event_ip
from ..services.join_flow_service import clear_device_hint_cookie
from ..services.peer_feedback import resolve_peer_feedback_starters
from ..services.student_home import (
    build_class_landing_context,
    build_image_asset_preview_map,
    build_material_access_map,
    build_material_checklist_items_map,
    build_material_feedback_starters_map,
    build_gallery_entries_map,
    build_material_rubric_specs_map,
    build_material_response_map,
    build_submissions_by_material,
    helper_backend_label,
    privacy_meta_context,
    student_self_delete_mode,
)
from ..services.submission_service import (
    parse_extensions,
    process_material_upload_form,
    resolve_remix_source_submission,
    resolve_upload_release_state,
    scan_uploaded_file,
    validate_upload_content,
)
from ..services.submission_quota import invalidate_classroom_submission_quota_cache
from ..services.telemetry_events import delete_student_event_history, write_student_event
from ..services.ui_density import resolve_ui_density_mode_for_modules
from .student_downloads import submission_download
from .student_micro_checks import latest_micro_check_state

logger = logging.getLogger(__name__)

def _helper_scope_signing_key() -> str:
    return str(getattr(settings, "HELPER_SCOPE_SIGNING_KEY", "") or "")


def _json_no_store_response(payload: dict, *, status: int = 200, private: bool = False) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    apply_no_store(response, private=private, pragma=True)
    return response


def _emit_student_event(
    *,
    event_type: str,
    classroom: Class | None,
    student: StudentIdentity | None,
    source: str,
    details: dict,
    ip_address: str = "",
) -> None:
    try:
        write_student_event(
            event_type=event_type,
            source=source,
            details=details or {},
            classroom=classroom,
            student=student,
            ip_address=(minimize_student_event_ip(ip_address) or None),
            write_source="student_view",
        )
    except Exception:
        logger.exception("student_event_write_failed type=%s", event_type)


def _end_student_session_response(request):
    request.session.flush()
    response = redirect("/")
    clear_device_hint_cookie(response)
    return response
def _student_home_helper_widget(*, request, classroom: Class, ui_density_mode: str, privacy_meta: dict) -> str:
    localization = localization_from_request(request)
    helper_description = _("This helper can coach you through the next step. It may not know every class resource yet.")
    if ui_density_mode == "compact":
        helper_description = _("Need help? Ask for one small next step at a time.")
    elif ui_density_mode == "expanded":
        helper_description = _("Use studio mode: ask for strategy, code-reading checks, and release-quality feedback.")

    helper_context = f"Classroom summary: {classroom.name}"
    return render_to_string(
        "includes/helper_widget.html",
        {
            "helper_title": _("Class helper"),
            "helper_description": helper_description,
            "helper_context": helper_context,
            "helper_topics": "Classroom overview",
            "helper_reference": "",
            "helper_allowed_topics": "",
            "helper_backend_label": helper_backend_label(),
            "helper_delete_url": "/student/my-data",
            "helper_language_code": localization.helper_code,
            "helper_prompt_sets_json": build_helper_prompt_sets_json(),
            **privacy_meta,
            "helper_scope_token": issue_scope_token(
                context=helper_context,
                topics=["Classroom overview"],
                allowed_topics=[],
                reference="",
                signing_key=_helper_scope_signing_key(),
            ),
        },
        request=request,
    )


def student_home(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    request.student.last_seen_at = timezone.now()
    request.student.save(update_fields=["last_seen_at"])

    localization = localization_from_request(request)
    classroom = request.classroom
    modules = list(classroom.modules.prefetch_related("materials").all())
    ui_density_mode = resolve_ui_density_mode_for_modules(modules=modules, program_profile=getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary"))
    material_ids, material_access = build_material_access_map(request, classroom=classroom, modules=modules)
    class_landing = build_class_landing_context(classroom=classroom, modules=modules, material_access=material_access)
    submissions_by_material = build_submissions_by_material(student=request.student, material_ids=material_ids)
    material_checklist_items = build_material_checklist_items_map(modules=modules); material_rubric_specs = build_material_rubric_specs_map(modules=modules)
    material_responses = build_material_response_map(student=request.student, material_ids=material_ids)
    material_feedback_starters = build_material_feedback_starters_map(modules=modules, language_code=localization.code)
    gallery_entries_by_material = build_gallery_entries_map(classroom=classroom, viewer_student=request.student, material_ids=material_ids)
    image_assets_by_material = build_image_asset_preview_map(modules=modules)
    privacy_meta = privacy_meta_context(classroom=classroom)
    helper_widget = _student_home_helper_widget(request=request, classroom=classroom, ui_density_mode=ui_density_mode, privacy_meta=privacy_meta)
    micro_check_state = latest_micro_check_state(classroom=classroom, student=request.student, modules=modules)
    checkin_notice = (request.GET.get("checkin_notice") or "").strip()
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    get_token(request)
    response = render(
        request,
        "student_class.html",
        {
            "student": request.student,
            "classroom": classroom,
            "modules": modules,
            "submissions_by_material": submissions_by_material,
            "material_checklist_items": material_checklist_items,
            "material_rubric_specs": material_rubric_specs,
            "material_responses": material_responses,
            "material_feedback_starters": material_feedback_starters,
            "gallery_entries_by_material": gallery_entries_by_material,
            "image_assets_by_material": image_assets_by_material,
            "material_access": material_access,
            "class_landing": class_landing,
            "helper_widget": helper_widget,
            "ui_density_mode": ui_density_mode,
            "micro_check_state": micro_check_state,
            "checkin_notice": checkin_notice,
            "selected_reading_level": selected_reading_level,
            **privacy_meta,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@require_GET
def student_return_code(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")
    return _json_no_store_response(
        {"return_code": request.student.return_code},
        private=True,
    )


def student_portfolio_export(request):
    """Download this student's submissions as an offline portfolio ZIP."""
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")
    filename_mode = str(getattr(settings, "CLASSHUB_PORTFOLIO_FILENAME_MODE", "generic") or "generic").strip().lower()
    return build_student_portfolio_export_response(
        student=request.student,
        classroom=request.classroom,
        filename_mode=filename_mode,
    )


def student_my_data(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    submissions = (
        Submission.objects.filter(student=request.student, material__module__classroom=request.classroom)
        .select_related("material__module")
        .order_by("-uploaded_at", "-id")
    )
    notice = (request.GET.get("notice") or "").strip()
    response = render(
        request,
        "student_my_data.html",
        {
            "student": request.student,
            "classroom": request.classroom,
            "submissions": submissions,
            "notice": notice,
            "selected_reading_level": resolve_reading_level(request.GET.get("reading_level")),
            **privacy_meta_context(classroom=request.classroom),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@require_POST
def student_delete_work(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    if student_self_delete_mode() == "request":
        _emit_student_event(
            event_type=StudentEvent.EVENT_STUDENT_DELETE_WORK_REQUEST,
            classroom=request.classroom,
            student=request.student,
            source="classhub.student_my_data",
            details={"delete_mode": "request"},
        )
        notice = _("Deletion request sent to your teacher.")
        return redirect("/student/my-data?" + urlencode({"notice": notice}))

    helper_clear = clear_helper_actor_conversations(
        class_id=request.classroom.id,
        student_id=request.student.id,
        endpoint_url=getattr(settings, "HELPER_INTERNAL_ACTOR_CLEAR_URL", ""),
        internal_token=getattr(settings, "HELPER_INTERNAL_API_TOKEN", ""),
        timeout_seconds=getattr(settings, "HELPER_INTERNAL_RESET_TIMEOUT_SECONDS", 2.0),
    )
    if not helper_clear.ok:
        notice = _(
            "Nothing was deleted because the helper service could not confirm its context clear. Please try again."
        )
        return redirect("/student/my-data?" + urlencode({"notice": notice}))

    deleted_history = delete_student_event_history(
        classroom_id=request.classroom.id,
        student_id=request.student.id,
    )
    if not deleted_history.ok:
        notice = _(
            "Nothing else was deleted because the activity-history store could not confirm deletion. Please try again."
        )
        return redirect("/student/my-data?" + urlencode({"notice": notice}))

    submissions_qs = Submission.objects.filter(
        student=request.student,
        material__module__classroom=request.classroom,
    )
    deleted_submissions = submissions_qs.count()
    submissions_qs.delete()
    invalidate_classroom_submission_quota_cache(classroom_id=request.classroom.id)
    StudentMaterialResponse.objects.filter(
        student=request.student,
        material__module__classroom=request.classroom,
    ).delete()

    notice = _(
        "Deleted %(submissions)s submission(s), %(events)s class event record(s), %(outcomes)s outcome record(s), and transient helper context."
    ) % {
        "submissions": deleted_submissions,
        "events": deleted_history.core_events_deleted + deleted_history.telemetry_events_deleted,
        "outcomes": deleted_history.core_outcomes_deleted + deleted_history.telemetry_outcomes_deleted,
    }
    return redirect("/student/my-data?" + urlencode({"notice": notice}))


@require_POST
def student_end_session(request):
    return _end_student_session_response(request)


def _material_upload_post_state(
    *,
    request,
    material: Material,
    form: SubmissionUploadForm,
    allowed_exts: list[str],
    max_bytes: int,
):
    response_status = 200
    error = ""
    remix_source = None
    if form.is_valid():
        share_with_class = bool(request.POST.get("share_with_class")) if material.type == Material.TYPE_GALLERY else False
        remix_source = resolve_remix_source_submission(
            request=request,
            material=material,
            remix_of_submission_id=form.cleaned_data.get("remix_of_submission_id"),
        )
        upload_result = process_material_upload_form(
            request=request,
            material=material,
            form=form,
            allowed_exts=allowed_exts,
            max_bytes=max_bytes,
            validate_upload_content_fn=validate_upload_content,
            scan_uploaded_file_fn=scan_uploaded_file,
            emit_student_event_fn=_emit_student_event,
            logger=logger,
            share_with_class=share_with_class,
            remix_of_submission=remix_source,
        )
        return upload_result.redirect_url, upload_result.error, upload_result.response_status, remix_source

    first_error = next((str(values[0]).strip() for values in form.errors.values() if values), "")
    error = first_error or "Please check your upload form and try again."
    response_status = 400
    return "", error, response_status, remix_source


def material_upload(request, material_id: int):
    """Student upload page for a Material of type=upload or type=gallery."""
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")
    localization = localization_from_request(request)

    material = Material.objects.select_related("module__classroom").filter(id=material_id).first()
    if not material or material.module.classroom_id != request.classroom.id:
        return HttpResponse("Not found", status=404)
    if material.type not in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
        return HttpResponse("Not an upload material", status=404)

    release_state = resolve_upload_release_state(request, material=material)

    allowed_exts = parse_extensions(material.accepted_extensions) or [".sb3"]
    max_bytes = int(material.max_upload_mb) * 1024 * 1024

    error = ""
    response_status = 200
    form = SubmissionUploadForm()
    notice = (request.GET.get("notice") or "").strip()
    process_note_starters = resolve_peer_feedback_starters(language_code=localization.code, course_manifest={})
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    remix_source = resolve_remix_source_submission(
        request=request,
        material=material,
        remix_of_submission_id=request.GET.get("remix_of"),
    )
    if remix_source is not None:
        form = SubmissionUploadForm(initial={"remix_of_submission_id": remix_source.id})

    if release_state.get("is_locked"):
        available_on = release_state.get("available_on")
        error = f"Submissions for this lesson open on {available_on.isoformat()}." if available_on else "Submissions for this lesson are not open yet."
        if request.method == "POST":
            response_status = 403
    elif request.method == "POST":
        form = SubmissionUploadForm(request.POST, request.FILES)
        redirect_url, error, response_status, remix_source = _material_upload_post_state(
            request=request,
            material=material,
            form=form,
            allowed_exts=allowed_exts,
            max_bytes=max_bytes,
        )
        if redirect_url:
            return redirect(redirect_url)
    submissions = Submission.objects.filter(material=material, student=request.student).all()

    response = render(
        request,
        "material_upload.html",
        {
            "student": request.student,
            "classroom": request.classroom,
            "material": material,
            "allowed_exts": allowed_exts,
            "form": form,
            "error": error,
            "notice": notice,
            "submissions": submissions,
            "is_gallery_material": material.type == Material.TYPE_GALLERY,
            "gallery_enabled": bool(getattr(material.module, "gallery_enabled", True)),
            "process_note_starters": process_note_starters,
            "upload_locked": bool(release_state.get("is_locked")),
            "upload_available_on": release_state.get("available_on"),
            "remix_source": remix_source,
            "selected_reading_level": selected_reading_level,
            **privacy_meta_context(classroom=request.classroom),
        },
        status=response_status,
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def student_logout(request):
    return _end_student_session_response(request)


__all__ = [
    "student_home",
    "student_return_code",
    "student_portfolio_export",
    "student_my_data",
    "student_delete_work",
    "student_end_session",
    "material_upload",
    "submission_download",
    "student_logout",
]
