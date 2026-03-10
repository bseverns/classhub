"""Pure helper utilities used by hub models."""

from __future__ import annotations

import re
import secrets
from pathlib import Path


def gen_class_code(length: int = 8) -> str:
    """Generate a human-friendly class code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gen_student_return_code(length: int = 6) -> str:
    """Generate a short student return code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def gen_student_invite_token(length: int = 24) -> str:
    """Generate a URL-safe invite token."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _submission_upload_to(instance, filename: str) -> str:
    """Upload path for student submissions."""
    ext = Path(str(filename or "")).suffix.lower()
    if not ext.startswith("."):
        ext = ""
    else:
        ext_body = ext[1:]
        if not ext_body or len(ext_body) > 16 or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789" for ch in ext_body):
            ext = ""
    stored_name = f"{secrets.token_hex(16)}{ext}"

    classroom_id = instance.material.module.classroom_id
    material_id = instance.material_id
    student_id = instance.student_id
    return f"submissions/class_{classroom_id}/material_{material_id}/student_{student_id}/{stored_name}"


def _safe_path_part(raw: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", (raw or "").strip().lower())
    value = value.strip("-")
    return value or "unknown"


def _lesson_video_upload_to(instance, filename: str) -> str:
    course = _safe_path_part(instance.course_slug)
    lesson = _safe_path_part(instance.lesson_slug)
    return f"lesson_videos/{course}/{lesson}/{filename}"


def _normalize_asset_folder_path(raw: str) -> str:
    parts = []
    for segment in str(raw or "").replace("\\", "/").split("/"):
        segment = segment.strip()
        if not segment:
            continue
        parts.append(_safe_path_part(segment))
    return "/".join(parts) or "general"


def _safe_asset_filename(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", (raw or "").strip())
    value = value.strip("._")
    return value or "asset"


def gen_certificate_code(length: int = 12) -> str:
    """Generate a human-friendly certificate code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _lesson_asset_upload_to(instance, filename: str) -> str:
    folder_path = _normalize_asset_folder_path(getattr(instance.folder, "path", "general"))
    return f"lesson_assets/{folder_path}/{_safe_asset_filename(filename)}"


__all__ = [
    "gen_certificate_code",
    "gen_class_code",
    "gen_student_invite_token",
    "gen_student_return_code",
    "_lesson_asset_upload_to",
    "_lesson_video_upload_to",
    "_normalize_asset_folder_path",
    "_safe_asset_filename",
    "_safe_path_part",
    "_submission_upload_to",
]
