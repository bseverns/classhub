"""Centralized response hardening helpers for cache/download behavior."""

from __future__ import annotations

from django.http import HttpResponse

from ..services.filenames import safe_filename


def apply_no_store(response: HttpResponse, *, private: bool = True, pragma: bool = True) -> HttpResponse:
    """Mark a response as non-cacheable for browser/shared cache safety."""
    response["Cache-Control"] = "private, no-store" if private else "no-store"
    if pragma:
        response["Pragma"] = "no-cache"
    return response


def apply_download_safety(response: HttpResponse) -> HttpResponse:
    """Apply strict browser handling for attachment/download responses."""
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Referrer-Policy"] = "no-referrer"
    return response


def safe_attachment_filename(name: str, *, fallback: str = "download", max_length: int = 255) -> str:
    """Return a conservative attachment filename safe for HTTP headers."""
    cleaned = safe_filename((name or fallback).strip())[:max_length]
    return cleaned or fallback

