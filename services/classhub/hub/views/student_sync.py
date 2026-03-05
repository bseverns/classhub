"""Service worker and sync endpoints for resilient student upload flows."""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from ..http.headers import apply_no_store


@require_GET
def student_upload_sync_service_worker(request):
    """Serve the student upload sync worker script at a root-scoped URL."""
    response = render(
        request,
        "student_upload_sync_sw.js",
        content_type="application/javascript; charset=utf-8",
    )
    response["Service-Worker-Allowed"] = "/"
    apply_no_store(response, private=False, pragma=True)
    return response


__all__ = ["student_upload_sync_service_worker"]
