"""Teacher URL, redirect, and utility helper functions."""

import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.http import HttpResponse
from django.utils._os import safe_join
from django.utils.http import url_has_allowed_host_and_scheme

from ...services.audit import log_audit_event


def _safe_teacher_return_path(raw: str, fallback: str) -> str:
    parsed = urlparse((raw or "").strip())
    if parsed.scheme or parsed.netloc:
        return fallback
    if not parsed.path.startswith("/teach"):
        return fallback
    return (raw or "").strip() or fallback


def _teach_class_path(class_id: int | str) -> str:
    try:
        parsed_id = int(class_id)
    except Exception:
        return "/teach"
    if parsed_id <= 0:
        return "/teach"
    return f"/teach/class/{parsed_id}"


def _teach_module_path(module_id: int | str) -> str:
    try:
        parsed_id = int(module_id)
    except Exception:
        return "/teach"
    if parsed_id <= 0:
        return "/teach"
    return f"/teach/module/{parsed_id}"


def _safe_internal_redirect(request, to: str, fallback: str = "/teach"):
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
    # Keep redirects local-only and avoid framework URL sink ambiguity for static analysis.
    response = HttpResponse(status=302)
    response["Location"] = candidate
    return response


def _with_notice(path: str, notice: str = "", error: str = "", extra: dict | None = None) -> str:
    params = {}
    if notice:
        params["notice"] = notice
    if error:
        params["error"] = error
    for key, value in (extra or {}).items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            params[key] = text
    if not params:
        return path
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}{urlencode(params)}"


def _audit(request, *, action: str, summary: str = "", classroom=None, target_type: str = "", target_id: str = "", metadata=None):
    log_audit_event(
        request,
        action=action,
        summary=summary,
        classroom=classroom,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )


def _lesson_video_redirect_params(course_slug: str, lesson_slug: str, class_id: int = 0, notice: str = "") -> str:
    query = {"course_slug": course_slug, "lesson_slug": lesson_slug}
    if class_id:
        query["class_id"] = str(class_id)
    if notice:
        query["notice"] = notice
    return urlencode(query)


def _normalize_optional_slug_tag(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", (raw or "").strip().lower())
    return value.strip("-_")


def _parse_positive_int(raw: str, *, min_value: int, max_value: int) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    if parsed < min_value or parsed > max_value:
        return None
    return parsed


def _split_helper_topics_text(raw: str) -> list[str]:
    parts: list[str] = []
    normalized = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in normalized.split("\n"):
        for segment in line.split("|"):
            token = segment.strip()
            if token:
                parts.append(token)
    return parts


def _normalize_helper_topics_text(raw: str) -> str:
    return "\n".join(_split_helper_topics_text(raw))


def _authoring_template_output_dir() -> Path:
    return Path(getattr(settings, "CLASSHUB_AUTHORING_TEMPLATE_DIR", "/uploads/authoring_templates"))


def _resolve_authoring_template_download_path(slug: str, suffix: str) -> Path | None:
    output_dir = _authoring_template_output_dir().resolve()
    try:
        joined = safe_join(str(output_dir), f"{slug}-{suffix}")
    except Exception:
        return None
    candidate = Path(joined).resolve()
    if not candidate.is_relative_to(output_dir):
        return None
    return candidate


def _lesson_asset_redirect_params(folder_id: int = 0, course_slug: str = "", lesson_slug: str = "", status: str = "all", notice: str = "") -> str:
    query = {"status": status or "all"}
    if folder_id:
        query["folder_id"] = str(folder_id)
    if course_slug:
        query["course_slug"] = course_slug
    if lesson_slug:
        query["lesson_slug"] = lesson_slug
    if notice:
        query["notice"] = notice
    return urlencode(query)


__all__ = [name for name in globals() if not name.startswith("__")]
