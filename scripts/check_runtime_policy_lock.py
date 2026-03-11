#!/usr/bin/env python3
"""Guardrail: enforce runtime policy lock values from compose/.env."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_ENV_FILE = Path("compose/.env")


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


def _as_int(value: str) -> int | None:
    if not re.fullmatch(r"-?\d+", value.strip()):
        return None
    try:
        return int(value.strip())
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check runtime policy lock values in compose/.env.")
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
        print(f"[runtime-policy-lock-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    def add_exact(key: str, expected: str) -> None:
        actual = (values.get(key) or "").strip()
        if actual != expected:
            failures.append(f"{key}: expected {expected!r}, got {actual or '<unset>'!r}")

    add_exact("REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", "1")
    add_exact("CLASSHUB_TELEMETRY_WRITE_MODE", "dual")
    add_exact("CLASSHUB_TELEMETRY_READ_MODE", "telemetry")

    for key in ("CLASSHUB_CERTIFICATE_MIN_SESSIONS", "CLASSHUB_CERTIFICATE_MIN_ARTIFACTS"):
        actual = (values.get(key) or "").strip()
        parsed = _as_int(actual) if actual else None
        if not (actual and parsed is not None and parsed >= 1):
            failures.append(f"{key}: expected explicit integer >=1, got {actual or '<unset>'!r}")

    if failures:
        print("[runtime-policy-lock-guard] FAIL: runtime policy lock mismatch detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print("[runtime-policy-lock-guard] expected values are defined for stability closeout policy locks", file=sys.stderr)
        return 1

    print(f"[runtime-policy-lock-guard] OK ({env_path.as_posix()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
