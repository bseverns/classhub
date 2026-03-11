#!/usr/bin/env python3
"""Guardrail: advanced policy/RBAC tools must stay superuser + advanced-mode gated."""

from __future__ import annotations

import sys
from pathlib import Path


HOME_CONTEXT = Path("services/classhub/hub/views/teacher_parts/content_home_context.py")
HOME_VIEW = Path("services/classhub/hub/views/teacher_parts/content_home.py")
RBAC_ENDPOINTS = Path("services/classhub/hub/views/teacher_parts/content_rbac_view_endpoints.py")
SETUP_SECTIONS_TEMPLATE = Path("services/classhub/templates/includes/teach_home/setup_sections.html")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _require_snippets(*, text: str, path: Path, snippets: list[str], failures: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path}: missing snippet {snippet!r}")


def main() -> int:
    failures: list[str] = []
    try:
        home_context_text = _read(HOME_CONTEXT)
        home_view_text = _read(HOME_VIEW)
        rbac_endpoints_text = _read(RBAC_ENDPOINTS)
        setup_sections_text = _read(SETUP_SECTIONS_TEMPLATE)
    except RuntimeError as exc:
        print(f"[teacher-policy-mode-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    _require_snippets(
        text=home_context_text,
        path=HOME_CONTEXT,
        snippets=[
            "def _read_advanced_tools_state(request, *, user) -> bool:",
            "if not user.is_superuser:",
            "return False",
            'show_policy_sections = bool(advanced_tools_enabled and user.is_superuser and portal_mode in {"all", "policy"})',
            "if advanced_tools_enabled and user.is_superuser:",
        ],
        failures=failures,
    )
    _require_snippets(
        text=home_view_text,
        path=HOME_VIEW,
        snippets=[
            "rbac_tools_enabled = rbac_tools_enabled_for_user(request.user)",
            "rbac_tools_active = rbac_tools_requested(request) and rbac_tools_enabled",
            "advanced_tools_enabled = _read_advanced_tools_state(request, user=request.user)",
        ],
        failures=failures,
    )
    _require_snippets(
        text=rbac_endpoints_text,
        path=RBAC_ENDPOINTS,
        snippets=[
            "def rbac_tools_enabled_for_user(user) -> bool:",
            'return bool(getattr(user, "is_superuser", False))',
        ],
        failures=failures,
    )
    _require_snippets(
        text=setup_sections_text,
        path=SETUP_SECTIONS_TEMPLATE,
        snippets=[
            "{% if rbac_tools_enabled and advanced_tools_enabled %}",
            "{% if request.user.is_superuser and advanced_tools_enabled %}",
        ],
        failures=failures,
    )

    if failures:
        print("[teacher-policy-mode-guard] FAIL: policy/RBAC mode contract drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[teacher-policy-mode-guard] keep policy tools behind superuser + advanced-mode gating",
            file=sys.stderr,
        )
        return 1

    print("[teacher-policy-mode-guard] OK (advanced policy/RBAC mode gating contract intact)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
