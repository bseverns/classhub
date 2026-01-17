import json
from pathlib import Path
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.middleware.csrf import get_token
from django.conf import settings

import yaml
import markdown as md
import bleach

from .forms import SubmissionUploadForm
from .models import Class, Material, StudentIdentity, Submission


# --- Repo-authored course content (markdown) ---------------------------------

_COURSES_DIR = Path(settings.CONTENT_ROOT) / "courses"


def _load_course_manifest(course_slug: str) -> dict:
    manifest_path = _COURSES_DIR / course_slug / "course.yaml"
    if not manifest_path.exists():
        return {}
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}


def _load_lesson_markdown(course_slug: str, lesson_slug: str) -> tuple[dict, str]:
    """Return (front_matter, markdown_body)."""
    manifest = _load_course_manifest(course_slug)
    lessons = manifest.get("lessons") or []
    match = next((l for l in lessons if (l.get("slug") == lesson_slug)), None)
    if not match:
        return {}, ""

    rel = match.get("file")
    if not rel:
        return {}, ""
    lesson_path = (_COURSES_DIR / course_slug / rel).resolve()
    if not lesson_path.exists():
        return {}, ""

    raw = lesson_path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\n")
            return fm, body
    return {}, raw


def _render_markdown_to_safe_html(markdown_text: str) -> str:
    html = md.markdown(
        markdown_text,
        extensions=["fenced_code", "tables", "toc"],
        output_format="html5",
    )

    allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS).union(
        {
            "p",
            "pre",
            "code",
            "h1",
            "h2",
            "h3",
            "h4",
            "hr",
            "br",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "details",
            "summary",
        }
    )

    allowed_attrs = {
        **bleach.sanitizer.ALLOWED_ATTRIBUTES,
        "a": ["href", "title", "target", "rel"],
        "code": ["class"],
        "pre": ["class"],
    }

    cleaned = bleach.clean(html, tags=list(allowed_tags), attributes=allowed_attrs, strip=True)
    return cleaned


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def index(request):
    """Landing page.

    - If student session exists, send them to /student
    - Otherwise, show join form

    Teachers/admins can use /admin for now.
    """
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    get_token(request)
    return render(request, "student_join.html", {})


@require_POST
def join_class(request):
    """Join via class code + display name.

    Body (JSON): {"class_code": "ABCD1234", "display_name": "Ada"}

    Stores student identity in session cookie.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad_json"}, status=400)

    code = (payload.get("class_code") or "").strip().upper()
    name = (payload.get("display_name") or "").strip()[:80]

    if not code or not name:
        return JsonResponse({"error": "missing_fields"}, status=400)

    classroom = Class.objects.filter(join_code=code).first()
    if not classroom:
        return JsonResponse({"error": "invalid_code"}, status=404)
    if classroom.is_locked:
        return JsonResponse({"error": "class_locked"}, status=403)

    student = StudentIdentity.objects.create(classroom=classroom, display_name=name)
    student.last_seen_at = timezone.now()
    student.save(update_fields=["last_seen_at"])

    request.session["student_id"] = student.id
    request.session["class_id"] = classroom.id

    return JsonResponse({"ok": True})


def student_home(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    # Update last seen (cheap pulse; later do this asynchronously)
    request.student.last_seen_at = timezone.now()
    request.student.save(update_fields=["last_seen_at"])

    classroom = request.classroom
    modules = classroom.modules.prefetch_related("materials").all()

    # Submission status for this student (shown next to upload materials)
    material_ids = []
    for m in modules:
        for mat in m.materials.all():
            material_ids.append(mat.id)

    submissions_by_material = {}
    if material_ids:
        qs = (
            Submission.objects.filter(student=request.student, material_id__in=material_ids)
            .only("id", "material_id", "uploaded_at")
            .order_by("material_id", "-uploaded_at", "-id")
        )
        for s in qs:
            if s.material_id not in submissions_by_material:
                submissions_by_material[s.material_id] = {"count": 0, "last": s.uploaded_at, "last_id": s.id}
            submissions_by_material[s.material_id]["count"] += 1

    return render(
        request,
        "student_class.html",
        {
            "student": request.student,
            "classroom": classroom,
            "modules": modules,
            "submissions_by_material": submissions_by_material,
        },
    )


def _parse_extensions(ext_csv: str) -> list[str]:
    parts = [p.strip().lower() for p in (ext_csv or "").split(",") if p.strip()]
    out = []
    for p in parts:
        if not p.startswith("."):
            p = "." + p
        if p not in out:
            out.append(p)
    return out


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

    allowed_exts = _parse_extensions(material.accepted_extensions) or [".sb3"]
    max_bytes = int(material.max_upload_mb) * 1024 * 1024

    error = ""

    if request.method == "POST":
        form = SubmissionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            note = (form.cleaned_data.get("note") or "").strip()

            name = (getattr(f, "name", "") or "upload").strip()
            lower = name.lower()
            ext = "." + lower.rsplit(".", 1)[-1] if "." in lower else ""

            if ext not in allowed_exts:
                error = f"File type not allowed. Allowed: {', '.join(allowed_exts)}"
            elif getattr(f, "size", 0) and f.size > max_bytes:
                error = f"File too large. Max size: {material.max_upload_mb}MB"
            else:
                Submission.objects.create(
                    material=material,
                    student=request.student,
                    original_filename=name,
                    file=f,
                    note=note,
                )
                return redirect(f"/material/{material.id}/upload")
    else:
        form = SubmissionUploadForm()

    submissions = Submission.objects.filter(material=material, student=request.student).all()

    return render(
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
        },
    )


def submission_download(request, submission_id: int):
    """Download a submission.

    - Staff users can download any submission.
    - Students can only download their own submissions.

    We intentionally avoid serving uploads as public /media files.
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

    filename = s.original_filename or Path(s.file.name).name
    return FileResponse(s.file.open("rb"), as_attachment=True, filename=filename)


def student_logout(request):
    request.session.flush()
    return redirect("/")


def course_overview(request, course_slug: str):
    """Tiny course landing page.

    This does not require a student session; it simply renders the manifest so
    teachers can verify links.
    """
    manifest = _load_course_manifest(course_slug)
    if not manifest:
        return HttpResponse("Course not found", status=404)

    return render(
        request,
        "course_overview.html",
        {
            "course_slug": course_slug,
            "course": manifest,
            "lessons": manifest.get("lessons") or [],
        },
    )


def course_lesson(request, course_slug: str, lesson_slug: str):
    """Render a markdown lesson page from disk."""
    manifest = _load_course_manifest(course_slug)
    if not manifest:
        return HttpResponse("Course not found", status=404)

    fm, body_md = _load_lesson_markdown(course_slug, lesson_slug)
    if not body_md:
        return HttpResponse("Lesson not found", status=404)

    html = _render_markdown_to_safe_html(body_md)

    lessons = manifest.get("lessons") or []
    idx = next((i for i, l in enumerate(lessons) if l.get("slug") == lesson_slug), None)
    prev_l = lessons[idx - 1] if isinstance(idx, int) and idx > 0 else None
    next_l = lessons[idx + 1] if isinstance(idx, int) and idx + 1 < len(lessons) else None

    return render(
        request,
        "lesson_page.html",
        {
            "course_slug": course_slug,
            "course": manifest,
            "lesson_slug": lesson_slug,
            "front_matter": fm,
            "lesson_html": html,
            "prev": prev_l,
            "next": next_l,
        },
    )
