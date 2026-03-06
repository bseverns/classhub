"""Service worker and sync endpoints for resilient student upload flows."""

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
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


@require_GET
def student_shell_manifest(request):
    """Serve an installable web manifest for the student kiosk shell."""
    payload = {
        "id": "classhub-student-kiosk",
        "name": f"{getattr(settings, 'CLASSHUB_PRODUCT_NAME', 'Class Hub')} Student Kiosk",
        "short_name": "ClassHub",
        "description": "Focused student join + class + upload shell for classroom devices.",
        "start_url": "/?kiosk=1",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#edf3f6",
        "theme_color": "#10253a",
        "icons": [
            {
                "src": static("icons/student-kiosk-192.svg"),
                "sizes": "192x192",
                "type": "image/svg+xml",
                "purpose": "any",
            },
            {
                "src": static("icons/student-kiosk-512.svg"),
                "sizes": "512x512",
                "type": "image/svg+xml",
                "purpose": "any",
            },
        ],
    }
    response = JsonResponse(payload)
    response["Content-Type"] = "application/manifest+json; charset=utf-8"
    apply_no_store(response, private=False, pragma=True)
    return response


__all__ = ["student_upload_sync_service_worker", "student_shell_manifest"]
