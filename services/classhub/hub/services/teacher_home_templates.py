"""Service helpers for teacher-home authoring template generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from django.conf import settings


@dataclass(frozen=True)
class AuthoringTemplateGenerationResult:
    form_values: dict[str, str]
    error: str = ""
    notice: str = ""
    slug: str = ""
    title: str = ""
    sessions: int = 0
    duration: int = 0
    output_dir: Path | None = None
    output_paths: tuple[str, ...] = ()


def generate_authoring_templates_from_form(
    *,
    post_data,
    template_slug_re,
    parse_positive_int_fn: Callable[..., int | None],
    generate_authoring_templates_fn,
) -> AuthoringTemplateGenerationResult:
    slug = (post_data.get("template_slug") or "").strip().lower()
    title = (post_data.get("template_title") or "").strip()
    sessions_raw = (post_data.get("template_sessions") or "").strip()
    duration_raw = (post_data.get("template_duration") or "").strip()

    form_values = {
        "template_slug": slug,
        "template_title": title,
        "template_sessions": sessions_raw,
        "template_duration": duration_raw,
    }
    if not slug:
        return AuthoringTemplateGenerationResult(
            form_values=form_values,
            error="Course slug is required.",
        )
    if not template_slug_re.match(slug):
        return AuthoringTemplateGenerationResult(
            form_values=form_values,
            error="Course slug can use lowercase letters, numbers, underscores, and dashes.",
        )
    if not title:
        return AuthoringTemplateGenerationResult(
            form_values=form_values,
            error="Course title is required.",
        )

    sessions = parse_positive_int_fn(sessions_raw, min_value=1, max_value=60)
    if sessions is None:
        return AuthoringTemplateGenerationResult(
            form_values=form_values,
            error="Sessions must be a whole number between 1 and 60.",
        )
    duration = parse_positive_int_fn(duration_raw, min_value=15, max_value=240)
    if duration is None:
        return AuthoringTemplateGenerationResult(
            form_values=form_values,
            error="Session duration must be between 15 and 240 minutes.",
        )

    age_band = (getattr(settings, "CLASSHUB_AUTHORING_TEMPLATE_AGE_BAND_DEFAULT", "5th-7th") or "5th-7th").strip()
    output_dir = Path(getattr(settings, "CLASSHUB_AUTHORING_TEMPLATE_DIR", "/uploads/authoring_templates"))

    try:
        generation = generate_authoring_templates_fn(
            slug=slug,
            title=title,
            sessions=sessions,
            duration=duration,
            age_band=age_band,
            out_dir=output_dir,
            overwrite=True,
        )
    except (OSError, ValueError) as exc:
        return AuthoringTemplateGenerationResult(
            form_values=form_values,
            error=f"Template generation failed: {exc}",
        )

    return AuthoringTemplateGenerationResult(
        form_values=form_values,
        notice=f"Generated templates for {slug} in {output_dir}.",
        slug=slug,
        title=title,
        sessions=sessions,
        duration=duration,
        output_dir=output_dir,
        output_paths=tuple(str(path) for path in (generation.output_paths or [])),
    )


__all__ = [
    "AuthoringTemplateGenerationResult",
    "generate_authoring_templates_from_form",
]
