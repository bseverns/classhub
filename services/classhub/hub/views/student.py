"""Student/session/upload endpoint callables."""

import logging
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from common.helper_scope import issue_scope_token

from ..forms import SubmissionUploadForm
from ..http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ..models import Class, Material, StudentEvent, StudentIdentity, StudentMaterialResponse, Submission
from ..services.export_service import build_student_portfolio_export_response
from ..services.ip_privacy import minimize_student_event_ip
from ..services.join_flow_service import clear_device_hint_cookie
from ..services.student_home import (
    build_class_landing_context,
    build_material_access_map,
    build_material_checklist_items_map,
    build_gallery_entries_map,
    build_material_rubric_specs_map,
    build_material_response_map,
    build_submissions_by_material,
    helper_backend_label,
    privacy_meta_context,
)
from ..services.submission_service import (
    parse_extensions,
    process_material_upload_form,
    resolve_upload_release_state,
    scan_uploaded_file,
    validate_upload_content,
)
from ..services.ui_density import resolve_ui_density_mode_for_modules

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
        StudentEvent.objects.create(
            classroom=classroom,
            student=student,
            event_type=event_type,
            source=source,
            details=details or {},
            ip_address=(minimize_student_event_ip(ip_address) or None),
        )
    except Exception:
        logger.exception("student_event_write_failed type=%s", event_type)


def _end_student_session_response(request):
    request.session.flush()
    response = redirect("/")
    clear_device_hint_cookie(response)
    return response


def healthz(request):
    # Used by Caddy/ops checks to confirm the app process is alive.
    return HttpResponse("ok", content_type="text/plain")


def student_home(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    request.student.last_seen_at = timezone.now()
    request.student.save(update_fields=["last_seen_at"])

    classroom = request.classroom
    modules = list(classroom.modules.prefetch_related("materials").all())
    ui_density_mode = resolve_ui_density_mode_for_modules(modules=modules, program_profile=getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary"))
    material_ids, material_access = build_material_access_map(request, classroom=classroom, modules=modules)
    class_landing = build_class_landing_context(classroom=classroom, modules=modules, material_access=material_access)
    submissions_by_material = build_submissions_by_material(student=request.student, material_ids=material_ids)
    material_checklist_items = build_material_checklist_items_map(modules=modules); material_rubric_specs = build_material_rubric_specs_map(modules=modules)
    material_responses = build_material_response_map(student=request.student, material_ids=material_ids)
    gallery_entries_by_material = build_gallery_entries_map(classroom=classroom, viewer_student=request.student, material_ids=material_ids)
    privacy_meta = privacy_meta_context()
    helper_widget = render_to_string(
        "includes/helper_widget.html",
        {
            "helper_title": "Class helper",
            "helper_description": "This is a Day-1 wire-up. It will become smarter once it can cite your class materials.",
            "helper_context": f"Classroom summary: {classroom.name}",
            "helper_topics": "Classroom overview",
            "helper_reference": "",
            "helper_allowed_topics": "",
            "helper_backend_label": helper_backend_label(),
            "helper_delete_url": "/student/my-data",
            **privacy_meta,
            "helper_scope_token": issue_scope_token(
                context=f"Classroom summary: {classroom.name}",
                topics=["Classroom overview"],
                allowed_topics=[],
                reference="",
                signing_key=_helper_scope_signing_key(),
            ),
        },
    )
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
            "gallery_entries_by_material": gallery_entries_by_material,
            "material_access": material_access,
            "class_landing": class_landing,
            "helper_widget": helper_widget,
            "ui_density_mode": ui_density_mode,
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
    """Download this student's submissions as an offline portfolio ZIP.

    Archive contents:
    - index.html summary page
    - files/<module>/<material>/<timestamp>_<submission_id>_<original_filename>
    """
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
            **privacy_meta_context(),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@require_POST
def student_delete_work(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    submissions_qs = Submission.objects.filter(
        student=request.student,
        material__module__classroom=request.classroom,
    )
    deleted_submissions = submissions_qs.count()
    submissions_qs.delete()
    StudentMaterialResponse.objects.filter(
        student=request.student,
        material__module__classroom=request.classroom,
    ).delete()

    deleted_events, _details = StudentEvent.objects.filter(
        student=request.student,
        event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
    ).delete()

    notice = f"Deleted {deleted_submissions} submission(s) and {deleted_events} upload event record(s)."
    return redirect("/student/my-data?" + urlencode({"notice": notice}))


@require_POST
def student_end_session(request):
    return _end_student_session_response(request)


def material_upload(request, material_id: int):
    """Student upload page for a Material of type=upload or type=gallery."""
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    material = (
        Material.objects.select_related("module__classroom")
        .filter(id=material_id)
        .first()
    )
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

    if release_state.get("is_locked"):
        available_on = release_state.get("available_on")
        if available_on:
            error = f"Submissions for this lesson open on {available_on.isoformat()}."
        else:
            error = "Submissions for this lesson are not open yet."
        if request.method == "POST":
            response_status = 403
    elif request.method == "POST":
        form = SubmissionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            share_with_class = bool(request.POST.get("share_with_class")) if material.type == Material.TYPE_GALLERY else False
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
            )
            if upload_result.redirect_url:
                return redirect(upload_result.redirect_url)
            error = upload_result.error
            response_status = upload_result.response_status
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
            "submissions": submissions,
            "is_gallery_material": material.type == Material.TYPE_GALLERY,
            "upload_locked": bool(release_state.get("is_locked")),
            "upload_available_on": release_state.get("available_on"),
            **privacy_meta_context(),
        },
        status=response_status,
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def submission_download(request, submission_id: int):
    """Download a submission.

    - Staff users can download any submission.
    - Students can download their own submissions.
    - Classmates can download gallery submissions only when sharing is explicitly enabled.
    """
    s = (
        Submission.objects.select_related("student", "material__module__classroom")
        .filter(id=submission_id)
        .first()
    )
    if not s:
        return HttpResponse("Not found", status=404)

    if request.user.is_authenticated and request.user.is_staff:
        pass
    else:
        if getattr(request, "student", None) is None:
            return redirect("/")
        can_download_own = s.student_id == request.student.id
        can_download_shared_gallery = (
            s.material.type == Material.TYPE_GALLERY
            and bool(s.is_gallery_shared)
            and request.student.classroom_id == s.material.module.classroom_id
        )
        if not can_download_own and not can_download_shared_gallery:
            return HttpResponse("Forbidden", status=403)

    raw_filename = s.original_filename or Path(s.file.name).name or "submission"
    filename = safe_attachment_filename(raw_filename, fallback="submission")
    response = FileResponse(
        s.file.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/octet-stream",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


def student_logout(request):
    return _end_student_session_response(request)
__all__ = [
    "healthz",
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
