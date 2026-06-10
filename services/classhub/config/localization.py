"""Request-scoped localization helpers for Class Hub."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass

from django.conf import settings
from django.utils import translation
from django.utils.translation import get_language_from_request, get_language_info


_SUPPORTED_HELPER_LANGUAGES = {"en", "es", "so", "ksw"}
_localization_var: ContextVar["LocalizationContext | None"] = ContextVar(
    "classhub_localization_context",
    default=None,
)


@dataclass(frozen=True)
class LocalizationContext:
    code: str
    html_lang: str
    helper_code: str
    is_rtl: bool
    language_name: str


def _normalize_language_code(raw: str) -> str:
    value = str(raw or "").strip().lower().replace("_", "-")
    if not value:
        return "en"
    primary = value.split("-", 1)[0]
    return primary or "en"


def normalize_helper_language_code(raw: str) -> str:
    code = _normalize_language_code(raw)
    if code in _SUPPORTED_HELPER_LANGUAGES:
        return code
    return "en"


def available_language_codes() -> set[str]:
    codes: set[str] = set()
    for lang_code, _lang_name in getattr(settings, "LANGUAGES", []):
        codes.add(_normalize_language_code(lang_code))
    return codes or {"en"}


def resolve_language_override(raw: str) -> str:
    if not str(raw or "").strip():
        return ""
    code = _normalize_language_code(raw)
    if code in available_language_codes():
        return code
    return ""


def resolve_request_language(request, raw_override: str = "") -> str:
    override_code = resolve_language_override(raw_override)
    if override_code:
        return override_code
    default_language = str(getattr(settings, "LANGUAGE_CODE", "en") or "en")
    requested = (
        getattr(request, "LANGUAGE_CODE", "")
        or translation.get_language()
        or get_language_from_request(request, check_path=False)
        or default_language
    )
    return _normalize_language_code(requested or default_language)


def _resolve_language_name(code: str) -> str:
    for lang_code, lang_name in getattr(settings, "LANGUAGES", []):
        if str(lang_code or "").strip().lower() == code:
            return str(lang_name or code)
    try:
        info = get_language_info(code)
    except KeyError:
        return code
    return str(info.get("name_local") or info.get("name") or code)


def _resolve_is_rtl(code: str) -> bool:
    try:
        info = get_language_info(code)
    except KeyError:
        return False
    return bool(info.get("bidi"))


def build_localization_context(request) -> LocalizationContext:
    default_language = str(getattr(settings, "LANGUAGE_CODE", "en") or "en")
    resolved = (
        getattr(request, "LANGUAGE_CODE", "")
        or translation.get_language()
        or get_language_from_request(request, check_path=False)
        or default_language
    )
    code = _normalize_language_code(resolved or default_language)
    return LocalizationContext(
        code=code,
        html_lang=code,
        helper_code=normalize_helper_language_code(code),
        is_rtl=_resolve_is_rtl(code),
        language_name=_resolve_language_name(code),
    )


def localization_from_request(request) -> LocalizationContext:
    existing = getattr(request, "localization", None)
    if isinstance(existing, LocalizationContext):
        return existing
    context = build_localization_context(request)
    request.localization = context
    return context


def set_localization_context(context: LocalizationContext) -> Token:
    return _localization_var.set(context)


def reset_localization_context(token: Token) -> None:
    _localization_var.reset(token)


def get_localization_context() -> LocalizationContext | None:
    return _localization_var.get()


@contextmanager
def request_language_override(request, raw_code: str):
    active_language = _normalize_language_code(translation.get_language() or getattr(request, "LANGUAGE_CODE", "en"))
    override_code = resolve_language_override(raw_code) or active_language

    had_language = hasattr(request, "LANGUAGE_CODE")
    previous_language = getattr(request, "LANGUAGE_CODE", "")
    had_localization = hasattr(request, "localization")
    previous_localization = getattr(request, "localization", None)

    request.LANGUAGE_CODE = override_code
    if had_localization:
        delattr(request, "localization")

    with translation.override(override_code):
        try:
            yield localization_from_request(request)
        finally:
            if had_language:
                request.LANGUAGE_CODE = previous_language
            elif hasattr(request, "LANGUAGE_CODE"):
                delattr(request, "LANGUAGE_CODE")
            if had_localization:
                request.localization = previous_localization
            elif hasattr(request, "localization"):
                delattr(request, "localization")
