"""RBAC teacher-home access predicates."""

from __future__ import annotations


def rbac_tools_enabled_for_user(user) -> bool:
    return bool(getattr(user, "is_superuser", False))


def rbac_tools_requested(request) -> bool:
    return (request.GET.get("rbac_tools") or "").strip() == "1"


__all__ = [
    "rbac_tools_enabled_for_user",
    "rbac_tools_requested",
]
