#!/usr/bin/env python3
"""Guardrail: CSP rollout posture must stay explicit and safe."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_ENV_FILE = Path("compose/.env")
VALID_CSP_MODES = {"relaxed", "report-only", "strict"}


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"missing env file: {path}")
    rows: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        rows[key] = value
    return rows


def _normalize_mode(raw_mode: str) -> str:
    mode = (raw_mode or "").strip().lower()
    if mode in {"report_only", "reportonly"}:
        mode = "report-only"
    return mode


def _extract_directive_tokens(policy: str, directive: str) -> list[str]:
    for raw_part in policy.split(";"):
        part = raw_part.strip()
        if not part:
            continue
        if not part.startswith(f"{directive} "):
            continue
        return [token.strip() for token in part.split()[1:] if token.strip()]
    return []


def _contains_inline_script(policy: str) -> bool:
    return "'unsafe-inline'" in _extract_directive_tokens(policy, "script-src")


def _contains_inline_style(policy: str) -> bool:
    return "'unsafe-inline'" in _extract_directive_tokens(policy, "style-src")


def _has_safe_script_lock(policy: str) -> bool:
    tokens = _extract_directive_tokens(policy, "script-src")
    return bool(tokens) and "'unsafe-inline'" not in tokens


def _render_stage(mode: str, enforced: str, report_only: str) -> str:
    if mode == "strict":
        if enforced and _contains_inline_style(enforced):
            return "strict-canary (inline styles still temporarily allowed)"
        return "strict-enforced"
    if mode == "relaxed":
        return "relaxed-enforced + strict-report-only"
    if mode == "report-only":
        return "strict-report-only transitional stage"
    if enforced or report_only:
        return "custom override"
    return "unset/invalid"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to env file (default: compose/.env)",
    )
    args = parser.parse_args()

    env_path = Path(args.env_file)
    try:
        values = _parse_env_file(env_path)
    except FileNotFoundError as exc:
        print(f"[csp-runtime-contract] FAIL: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    mode = _normalize_mode(values.get("DJANGO_CSP_MODE", ""))
    enforced = (values.get("DJANGO_CSP_POLICY") or "").strip()
    report_only = (values.get("DJANGO_CSP_REPORT_ONLY_POLICY") or "").strip()

    if mode not in VALID_CSP_MODES:
        failures.append(
            f"DJANGO_CSP_MODE must be one of {', '.join(sorted(VALID_CSP_MODES))}; got {mode or '<unset>'!r}"
        )

    if enforced and _contains_inline_script(enforced):
        failures.append("DJANGO_CSP_POLICY must not allow inline script execution in script-src")

    if report_only and _contains_inline_script(report_only):
        failures.append("DJANGO_CSP_REPORT_ONLY_POLICY must not allow inline script execution in script-src")

    if report_only and _contains_inline_style(report_only):
        failures.append(
            "DJANGO_CSP_REPORT_ONLY_POLICY must stay style-strict so report-only telemetry reflects the target state"
        )

    if enforced and _contains_inline_style(enforced) and not _has_safe_script_lock(enforced):
        failures.append(
            "DJANGO_CSP_POLICY may temporarily allow inline styles only when script-src is present and disallows 'unsafe-inline'"
        )

    if enforced and mode == "report-only":
        failures.append("DJANGO_CSP_MODE=report-only must not ship with an enforced DJANGO_CSP_POLICY override")

    stage = _render_stage(mode=mode, enforced=enforced, report_only=report_only)

    if failures:
        print(
            f"[csp-runtime-contract] FAIL: CSP rollout contract drift detected for {env_path.as_posix()}:",
            file=sys.stderr,
        )
        print(f"  - effective stage: {stage}", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        print(
            "  - acceptance check: report-only stays strict, and strict canary may allow inline styles only after inline scripts are gone",
            file=sys.stderr,
        )
        return 1

    print(f"[csp-runtime-contract] OK ({env_path.as_posix()} -> {stage})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
