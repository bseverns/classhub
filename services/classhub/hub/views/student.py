"""Student/session/upload endpoint callables."""

import json
import logging
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from common.helper_scope import issue_scope_token

from ..forms import SubmissionUploadForm
from ..models import (
    Class,
    Material,
    StudentEvent,
    StudentIdentity,
    Submission,
)
from ..http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ..services.filenames import safe_filename
from ..services.ip_privacy import minimize_student_event_ip
from ..services.student_home import (
    build_material_access_map,
    build_submissions_by_material,
    helper_backend_label,
    privacy_meta_context,
)
from ..services.student_join import (
    JoinValidationError,
    apply_device_hint_cookie,
    clear_device_hint_cookie,
    resolve_join_student,
)
from ..services.student_uploads import process_material_upload_form, resolve_upload_release_state
from ..services.upload_scan import scan_uploaded_file
from ..services.upload_policy import parse_extensions
from ..services.upload_validation import validate_upload_content
from common.request_safety import client_ip_from_request, fixed_window_allow

logger = logging.getLogger(__name__)

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


def healthz(request):
    # Used by Caddy/ops checks to confirm the app process is alive.
    return HttpResponse("ok", content_type="text/plain")


def index(request):
    """Landing page.

    - If student session exists, send them to /student
    - Otherwise, show join form

    Teachers/admins sign in at /admin/login/ and then use /teach.
    """
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    get_token(request)
    response = render(
        request,
        "student_join.html",
        {
            **privacy_meta_context(),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@require_POST
def join_class(request):
    """Join via class code + display name.

    Body (JSON): {"class_code": "ABCD1234", "display_name": "Ada", "return_code": "ABC234"}

    Stores student identity in session cookie.
    If return_code is omitted, rejoin attempts proceed in this order:
    1) signed same-device cookie hint
    2) class + display-name fallback match
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_no_store_response({"error": "bad_json"}, status=400)

    client_ip = client_ip_from_request(
        request,
        trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
        xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
    )
    request_id = (request.META.get("HTTP_X_REQUEST_ID", "") or "").strip()
    join_limit = int(getattr(settings, "JOIN_RATE_LIMIT_PER_MINUTE", 20))
    if not fixed_window_allow(
        f"join:ip:{client_ip}:m",
        limit=join_limit,
        window_seconds=60,
        request_id=request_id,
    ):
        return _json_no_store_response({"error": "rate_limited"}, status=429)

    code = (payload.get("class_code") or "").strip().upper()
    name = (payload.get("display_name") or "").strip()[:80]
    return_code = (payload.get("return_code") or "").strip().upper()

    if not code or not name:
        return _json_no_store_response({"error": "missing_fields"}, status=400)

    classroom = Class.objects.filter(join_code=code).first()
    if not classroom:
        return _json_no_store_response({"error": "invalid_code"}, status=404)
    if classroom.is_locked:
        return _json_no_store_response({"error": "class_locked"}, status=403)

    with transaction.atomic():
        Class.objects.select_for_update().filter(id=classroom.id).first()
        try:
            join_result = resolve_join_student(
                request=request,
                classroom=classroom,
                display_name=name,
                return_code=return_code,
            )
        except JoinValidationError as exc:
            return _json_no_store_response({"error": exc.code}, status=400)
        student = join_result.student
        rejoined = join_result.rejoined
        join_mode = join_result.join_mode

        student.last_seen_at = timezone.now()
        student.save(update_fields=["last_seen_at"])

    # Rotate identifiers on join to reduce session fixation blast radius.
    request.session.cycle_key()
    request.session["student_id"] = student.id
    request.session["class_id"] = classroom.id
    request.session["class_epoch"] = int(getattr(classroom, "session_epoch", 1) or 1)
    rotate_token(request)

    response = _json_no_store_response({"ok": True, "return_code": student.return_code, "rejoined": rejoined})
    apply_device_hint_cookie(response, classroom=classroom, student=student)
    if join_mode == "return_code":
        event_type = StudentEvent.EVENT_REJOIN_RETURN_CODE
    elif join_mode in {"device_hint", "name_match"}:
        event_type = StudentEvent.EVENT_REJOIN_DEVICE_HINT
    else:
        event_type = StudentEvent.EVENT_CLASS_JOIN
    _emit_student_event(
        event_type=event_type,
        classroom=classroom,
        student=student,
        source="classhub.join_class",
        details={"join_mode": join_mode},
        ip_address=client_ip,
    )
    return response


def student_home(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    request.student.last_seen_at = timezone.now()
    request.student.save(update_fields=["last_seen_at"])

    classroom = request.classroom
    modules = list(classroom.modules.prefetch_related("materials").all())
    material_ids, material_access = build_material_access_map(request, classroom=classroom, modules=modules)
    submissions_by_material = build_submissions_by_material(student=request.student, material_ids=material_ids)

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
            "material_access": material_access,
            "helper_widget": helper_widget,
            **privacy_meta,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def student_portfolio_export(request):
    """Download this student's submissions as an offline portfolio ZIP.

    Archive contents:
    - index.html summary page
    - files/<module>/<material>/<timestamp>_<submission_id>_<original_filename>
    """
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    student = request.student
    classroom = request.classroom
    submissions = list(
        Submission.objects.filter(student=student, material__module__classroom=classroom)
        .select_related("material__module")
        .order_by("uploaded_at", "id")
    )

    tmp = tempfile.TemporaryFile(mode="w+b")

    generated_at = timezone.localtime(timezone.now())
    rows: list[dict] = []
    used_archive_paths: set[str] = set()

    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for sub in submissions:
            local_uploaded_at = timezone.localtime(sub.uploaded_at)
            module_label = safe_filename(sub.material.module.title or "module")
            material_label = safe_filename(sub.material.title or "material")
            original = safe_filename(sub.original_filename or Path(sub.file.name).name or "submission")
            timestamp = local_uploaded_at.strftime("%Y%m%d_%H%M%S")
            archive_path = f"files/{module_label}/{material_label}/{timestamp}_{sub.id}_{original}"
            if archive_path in used_archive_paths:
                archive_path = f"files/{module_label}/{material_label}/{timestamp}_{sub.id}_dup_{original}"
            used_archive_paths.add(archive_path)

            included = False
            status = "ok"
            try:
                source_path = sub.file.path
                archive.write(source_path, arcname=archive_path)
                included = True
            except Exception:
                try:
                    with sub.file.open("rb") as fh:
                        archive.writestr(archive_path, fh.read())
                    included = True
                except Exception:
                    status = "missing"

            rows.append(
                {
                    "submission_id": sub.id,
                    "module_title": sub.material.module.title,
                    "material_title": sub.material.title,
                    "uploaded_at": local_uploaded_at,
                    "original_filename": sub.original_filename or Path(sub.file.name).name,
                    "note": sub.note or "",
                    "archive_path": archive_path,
                    "included": included,
                    "status": status,
                }
            )

        index_html = render_to_string(
            "student_portfolio_index.html",
            {
                "student": student,
                "classroom": classroom,
                "generated_at": generated_at,
                "rows": rows,
                "submission_count": len(rows),
                "included_count": sum(1 for row in rows if row["included"]),
            },
        )
        archive.writestr("index.html", index_html.encode("utf-8"))

    stamp = generated_at.strftime("%Y%m%d")
    filename_mode = str(getattr(settings, "CLASSHUB_PORTFOLIO_FILENAME_MODE", "generic") or "generic").strip().lower()
    if filename_mode == "descriptive":
        student_name = safe_filename(student.display_name or "student")
        class_name = safe_filename(classroom.name or "classroom")
        filename = safe_attachment_filename(f"{class_name}_{student_name}_portfolio_{stamp}.zip")
    else:
        filename = safe_attachment_filename(f"portfolio_{stamp}.zip")
    tmp.seek(0)
    response = FileResponse(
        tmp,
        as_attachment=True,
        filename=filename,
        content_type="application/zip",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


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

    deleted_events, _details = StudentEvent.objects.filter(
        student=request.student,
        event_type=StudentEvent.EVENT_SUBMISSION_UPLOAD,
    ).delete()

    notice = f"Deleted {deleted_submissions} submission(s) and {deleted_events} upload event record(s)."
    return redirect("/student/my-data?" + urlencode({"notice": notice}))


@require_POST
def student_end_session(request):
    request.session.flush()
    response = redirect("/")
    clear_device_hint_cookie(response)
    return response


def material_upload(request, material_id: int):
    """Student upload page for a Material of type=upload."""
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    material = (
        Material.objects.select_related("module__classroom")
        .filter(id=material_id)
        .first()
    )
    if not material or material.module.classroom_id != request.classroom.id:
        return HttpResponse("Not found", status=404)
    if material.type != Material.TYPE_UPLOAD:
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
    - Students can only download their own submissions.
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
        if s.student_id != request.student.id:
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
    request.session.flush()
    response = redirect("/")
    clear_device_hint_cookie(response)
    return response


__all__ = [
    "healthz",
    "index",
    "join_class",
    "student_home",
    "student_portfolio_export",
    "student_my_data",
    "student_delete_work",
    "student_end_session",
    "material_upload",
    "submission_download",
    "student_logout",
]
