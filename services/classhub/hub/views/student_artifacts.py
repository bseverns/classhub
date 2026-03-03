"""Student artifact portfolio and gallery views."""

from __future__ import annotations

from datetime import date
from urllib.parse import urlencode, urlparse

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from ..http.headers import apply_no_store
from ..models import Material, Module, Submission
from ..services.student_home import privacy_meta_context


def _parse_module_id(raw: str, *, classroom_id: int) -> int | None:
    try:
        module_id = int((raw or "").strip() or 0)
    except Exception:
        module_id = 0
    if module_id <= 0:
        return None
    if not Module.objects.filter(id=module_id, classroom_id=classroom_id).exists():
        return None
    return module_id


def _parse_date_filter(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except Exception:
        return None


def _normalize_station(raw: str) -> str:
    return " ".join(str(raw or "").split())[:80]


def _safe_student_return_path(raw: str, fallback: str) -> str:
    candidate = (raw or "").strip()
    if not candidate:
        return fallback
    if candidate.startswith("//"):
        return fallback
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not parsed.path.startswith(("/student", "/material")):
        return fallback
    if not candidate.startswith("/"):
        return fallback
    return candidate


def _artifact_status(submission: Submission) -> str:
    if not submission.file or not submission.file.name:
        return "Tombstoned"
    try:
        exists = bool(submission.file.storage.exists(submission.file.name))
    except Exception:
        exists = False
    return "Available" if exists else "Tombstoned"


def _safe_student_redirect(request, to: str, *, fallback: str = "/student"):
    candidate = (to or "").strip() or fallback
    if candidate.startswith("//"):
        candidate = fallback
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        candidate = fallback
    if not candidate.startswith("/"):
        candidate = fallback
    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        candidate = fallback
    response = HttpResponse(status=302)
    response["Location"] = candidate
    return response


def _with_notice(path: str, *, notice: str) -> str:
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}{urlencode({'notice': notice})}"


@require_GET
def student_portfolio(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    student = request.student
    classroom = request.classroom
    selected_lesson_id = _parse_module_id(request.GET.get("lesson") or "", classroom_id=classroom.id)
    selected_date = _parse_date_filter(request.GET.get("date") or "")
    selected_station = _normalize_station(request.GET.get("station") or "")

    base_qs = (
        Submission.objects.filter(student=student, material__module__classroom=classroom)
        .select_related("material__module", "remix_of", "remix_of__student")
        .order_by("-uploaded_at", "-id")
    )
    filtered_qs = base_qs
    if selected_lesson_id is not None:
        filtered_qs = filtered_qs.filter(material__module_id=selected_lesson_id)
    if selected_date is not None:
        filtered_qs = filtered_qs.filter(uploaded_at__date=selected_date)
    if selected_station:
        filtered_qs = filtered_qs.filter(station_label__iexact=selected_station)

    lesson_options = list(
        Module.objects.filter(classroom=classroom, materials__submissions__student=student)
        .order_by("order_index", "id")
        .distinct()
        .values("id", "title")
    )
    station_options = list(
        base_qs.exclude(station_label="")
        .values_list("station_label", flat=True)
        .order_by("station_label")
        .distinct()
    )
    artifacts = list(filtered_qs)

    response = render(
        request,
        "student_portfolio.html",
        {
            "student": student,
            "classroom": classroom,
            "artifacts": artifacts,
            "artifact_statuses": {sub.id: _artifact_status(sub) for sub in artifacts},
            "artifact_count_total": base_qs.count(),
            "artifact_count_filtered": len(artifacts),
            "lesson_options": lesson_options,
            "station_options": station_options,
            "selected_lesson_id": selected_lesson_id or 0,
            "selected_date": selected_date.isoformat() if selected_date else "",
            "selected_station": selected_station,
            **privacy_meta_context(classroom=classroom),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@require_GET
def student_gallery_wall(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    classroom = request.classroom
    gallery_modules = list(
        Module.objects.filter(classroom=classroom, materials__type=Material.TYPE_GALLERY)
        .order_by("order_index", "id")
        .distinct()
    )
    selected_module_id = _parse_module_id(request.GET.get("module_id") or "", classroom_id=classroom.id)
    selected_module = None
    if selected_module_id is not None:
        selected_module = next((module for module in gallery_modules if module.id == selected_module_id), None)
    if selected_module is None and gallery_modules:
        selected_module = gallery_modules[0]

    gallery_items: list[Submission] = []
    gallery_disabled = bool(selected_module and not selected_module.gallery_enabled)
    if selected_module is not None and not gallery_disabled:
        gallery_items = list(
            Submission.objects.filter(
                material__module=selected_module,
                material__type=Material.TYPE_GALLERY,
                is_published=True,
                is_gallery_shared=True,
            )
            .select_related("student", "material", "remix_of", "remix_of__student")
            .order_by("-published_at", "-uploaded_at", "-id")
        )

    notice = (request.GET.get("notice") or "").strip()
    response = render(
        request,
        "student_gallery.html",
        {
            "student": request.student,
            "classroom": classroom,
            "gallery_modules": gallery_modules,
            "selected_module": selected_module,
            "gallery_items": gallery_items,
            "gallery_disabled": gallery_disabled,
            "notice": notice,
            **privacy_meta_context(classroom=classroom),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@require_POST
def student_set_submission_publish(request, submission_id: int):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    submission = (
        Submission.objects.select_related("material__module")
        .filter(
            id=submission_id,
            student=request.student,
            material__module__classroom=request.classroom,
            material__type=Material.TYPE_GALLERY,
        )
        .first()
    )
    if submission is None:
        return HttpResponse("Not found", status=404)

    publish_requested = (request.POST.get("publish") or "").strip() == "1"
    module_gallery_enabled = bool(getattr(submission.material.module, "gallery_enabled", True))
    now = timezone.now()

    update_fields: list[str] = []
    if publish_requested:
        if not module_gallery_enabled:
            redirect_to = _safe_student_return_path(
                request.POST.get("return_to") or "",
                fallback=f"/material/{submission.material_id}/upload",
            )
            message = "Session gallery is disabled by your teacher."
            return _safe_student_redirect(
                request,
                _with_notice(redirect_to, notice=message),
                fallback=_with_notice(f"/material/{submission.material_id}/upload", notice=message),
            )
        if not submission.is_published:
            submission.is_published = True
            submission.published_at = now
            update_fields.extend(["is_published", "published_at"])
    else:
        if submission.is_published or submission.published_at is not None:
            submission.is_published = False
            submission.published_at = None
            update_fields.extend(["is_published", "published_at"])

    if update_fields:
        submission.save(update_fields=update_fields)

    redirect_to = _safe_student_return_path(
        request.POST.get("return_to") or "",
        fallback=f"/material/{submission.material_id}/upload",
    )
    if publish_requested:
        notice = "Published to gallery." if submission.is_gallery_shared else "Published. Waiting for teacher approval."
    else:
        notice = "Removed from gallery."
    return _safe_student_redirect(
        request,
        _with_notice(redirect_to, notice=notice),
        fallback=_with_notice(f"/material/{submission.material_id}/upload", notice=notice),
    )


__all__ = [
    "student_portfolio",
    "student_gallery_wall",
    "student_set_submission_publish",
]
