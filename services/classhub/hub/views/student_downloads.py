"""Student and staff submission download endpoint."""

from pathlib import Path

from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect

from ..http.headers import apply_download_safety, apply_no_store, safe_attachment_filename
from ..models import Material, Submission
from ..services.org_access import staff_can_view_submissions


def submission_download(request, submission_id: int):
    """Download a submission for staff, the owner, or an allowed gallery peer."""
    submission = (
        Submission.objects.select_related("student", "material__module__classroom")
        .filter(id=submission_id)
        .first()
    )
    if not submission:
        return HttpResponse("Not found", status=404)

    if request.user.is_authenticated and request.user.is_staff:
        module = getattr(getattr(submission, "material", None), "module", None)
        if module is None:
            return HttpResponse("Not found", status=404)
        if not staff_can_view_submissions(
            request.user,
            module.classroom,
            module_id=submission.material.module_id,
        ):
            return HttpResponse("Forbidden", status=403)
    else:
        if getattr(request, "student", None) is None:
            return redirect("/")
        can_download_own = submission.student_id == request.student.id
        can_download_shared_gallery = (
            submission.material.type == Material.TYPE_GALLERY
            and bool(submission.is_published)
            and bool(submission.is_gallery_shared)
            and request.student.classroom_id == submission.material.module.classroom_id
        )
        if not can_download_own and not can_download_shared_gallery:
            return HttpResponse("Forbidden", status=403)

    raw_filename = submission.original_filename or Path(submission.file.name).name or "submission"
    filename = safe_attachment_filename(raw_filename, fallback="submission")
    response = FileResponse(
        submission.file.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/octet-stream",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = ["submission_download"]
