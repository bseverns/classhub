"""Public learner-facing pages that do not require an active student session."""

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from ..http.headers import apply_no_store
from ..services.lesson_handouts import resolve_reading_level
from ..services.student_home import privacy_meta_context


def healthz(request):
    # Used by Caddy/ops checks to confirm the app process is alive.
    return HttpResponse("ok", content_type="text/plain")


@require_GET
def privacy_policy(request):
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    response = render(
        request,
        "privacy.html",
        {
            "selected_reading_level": selected_reading_level,
            **privacy_meta_context(classroom=getattr(request, "classroom", None)),
        },
    )
    apply_no_store(response, private=False, pragma=True)
    return response


@require_GET
def trust_page(request):
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))
    response = render(
        request,
        "trust.html",
        {
            "selected_reading_level": selected_reading_level,
            **privacy_meta_context(classroom=getattr(request, "classroom", None)),
        },
    )
    apply_no_store(response, private=False, pragma=True)
    return response


__all__ = [
    "healthz",
    "privacy_policy",
    "trust_page",
]
