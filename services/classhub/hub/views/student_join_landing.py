"""Join-page rendering separated from join transaction handling."""

from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from ..http.headers import apply_no_store
from ..services.join_flow_service import generate_pseudonym
from ..services.lesson_handouts import resolve_reading_level
from ..services.student_home import privacy_meta_context
from .student_join import _resolve_invite_link


def _invite_error_message(code: str) -> str:
    messages = {
        "invite_invalid": _("That invite link is not valid."),
        "invite_inactive": _("That invite link has been disabled."),
        "invite_expired": _("That invite link has expired."),
        "invite_seat_cap_reached": _("This invite is full right now. Ask your teacher for a new invite link."),
    }
    return messages.get(code, _("That invite link is not usable right now."))


def _render_join_page(request, *, invite_token: str = ""):
    invite, invite_error = _resolve_invite_link(invite_token, enforce_seat_cap=False) if invite_token else (None, "")
    if invite is not None and not invite.has_seat_available():
        invite_error = "invite_seat_cap_reached"
    get_token(request)

    default_display_name = ""
    if getattr(settings, "NAME_PSEUDONYM_DEFAULT", True):
        default_display_name = generate_pseudonym()
    selected_reading_level = resolve_reading_level(request.GET.get("reading_level"))

    response = render(
        request,
        "student_join.html",
        {
            "invite_join_classroom": invite.classroom if invite else None,
            "invite_join_token": invite.token if invite else "",
            "invite_join_error": invite_error,
            "invite_join_error_message": _invite_error_message(invite_error) if invite_error else "",
            "default_display_name": default_display_name,
            "selected_reading_level": selected_reading_level,
            **privacy_meta_context(),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


def invite_join(request, invite_token: str):
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    return _render_join_page(request, invite_token=invite_token.strip())


def index(request):
    """Landing page for class-code + no-login student access."""
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    return _render_join_page(request, invite_token=(request.GET.get("invite") or "").strip())


__all__ = [
    "index",
    "invite_join",
]
