"""Shared helpers for teacher dashboard section builders."""

from __future__ import annotations

from django.conf import settings


def int_setting(setting_name: str, default: int, *, minimum: int = 1) -> int:
    raw = getattr(settings, setting_name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = int(default)
    return max(value, minimum)


def detail_int(details: dict, key: str) -> int:
    try:
        return int((details or {}).get(key) or 0)
    except Exception:
        return 0


__all__ = ["detail_int", "int_setting"]
