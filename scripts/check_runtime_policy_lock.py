#!/usr/bin/env python3
"""Guardrail: enforce runtime policy lock values from compose/.env."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ENV_FILE = Path("compose/.env")
BASELINE_PROFILE = "baseline"
RELEASE_PROFILE = "release"


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


def _actual(value: str) -> str:
    return value or "<unset>"


def _add_row(
    rows: list[dict[str, str]],
    failures: list[str],
    *,
    key: str,
    expected: str,
    actual: str,
    ok: bool,
) -> None:
    status = "PASS" if ok else "FAIL"
    rows.append(
        {
            "key": key,
            "expected": expected,
            "actual": _actual(actual),
            "status": status,
        }
    )
    if not ok:
        failures.append(f"{key}: expected {expected!r}, got {_actual(actual)!r}")


def _evaluate_baseline(values: dict[str, str]) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    failures: list[str] = []

    require_org = (values.get("REQUIRE_ORG_MEMBERSHIP_FOR_STAFF") or "").strip()
    _add_row(
        rows,
        failures,
        key="REQUIRE_ORG_MEMBERSHIP_FOR_STAFF",
        expected="explicit 0 or 1",
        actual=require_org,
        ok=require_org in {"0", "1"},
    )

    write_mode = (values.get("CLASSHUB_TELEMETRY_WRITE_MODE") or "").strip().lower()
    read_mode = (values.get("CLASSHUB_TELEMETRY_READ_MODE") or "").strip().lower()
    _add_row(
        rows,
        failures,
        key="CLASSHUB_TELEMETRY_WRITE_MODE",
        expected="off, dual, or telemetry_only",
        actual=write_mode,
        ok=write_mode in {"off", "dual", "telemetry_only"},
    )
    _add_row(
        rows,
        failures,
        key="CLASSHUB_TELEMETRY_READ_MODE",
        expected="core or telemetry",
        actual=read_mode,
        ok=read_mode in {"core", "telemetry"},
    )

    pairing_ok = True
    if write_mode == "off" and read_mode == "telemetry":
        pairing_ok = False
    if write_mode == "telemetry_only" and read_mode != "telemetry":
        pairing_ok = False
    _add_row(
        rows,
        failures,
        key="TELEMETRY_MODE_PAIRING",
        expected="off->core, dual->core|telemetry, telemetry_only->telemetry",
        actual=f"write={_actual(write_mode)}, read={_actual(read_mode)}",
        ok=pairing_ok,
    )

    for key in ("CLASSHUB_CERTIFICATE_MIN_SESSIONS", "CLASSHUB_CERTIFICATE_MIN_ARTIFACTS"):
        actual = (values.get(key) or "").strip()
        parsed = _as_int(actual) if actual else None
        _add_row(
            rows,
            failures,
            key=key,
            expected="explicit integer >=1",
            actual=actual,
            ok=bool(actual and parsed is not None and parsed >= 1),
        )

    return rows, failures


def _evaluate_release(values: dict[str, str]) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    failures: list[str] = []

    _add_row(
        rows,
        failures,
        key="REQUIRE_ORG_MEMBERSHIP_FOR_STAFF",
        expected="1",
        actual=(values.get("REQUIRE_ORG_MEMBERSHIP_FOR_STAFF") or "").strip(),
        ok=(values.get("REQUIRE_ORG_MEMBERSHIP_FOR_STAFF") or "").strip() == "1",
    )
    _add_row(
        rows,
        failures,
        key="CLASSHUB_TELEMETRY_WRITE_MODE",
        expected="dual",
        actual=(values.get("CLASSHUB_TELEMETRY_WRITE_MODE") or "").strip().lower(),
        ok=(values.get("CLASSHUB_TELEMETRY_WRITE_MODE") or "").strip().lower() == "dual",
    )
    _add_row(
        rows,
        failures,
        key="CLASSHUB_TELEMETRY_READ_MODE",
        expected="telemetry",
        actual=(values.get("CLASSHUB_TELEMETRY_READ_MODE") or "").strip().lower(),
        ok=(values.get("CLASSHUB_TELEMETRY_READ_MODE") or "").strip().lower() == "telemetry",
    )

    for key in ("CLASSHUB_CERTIFICATE_MIN_SESSIONS", "CLASSHUB_CERTIFICATE_MIN_ARTIFACTS"):
        actual = (values.get(key) or "").strip()
        parsed = _as_int(actual) if actual else None
        _add_row(
            rows,
            failures,
            key=key,
            expected="explicit integer >=1",
            actual=actual,
            ok=bool(actual and parsed is not None and parsed >= 1),
        )

    return rows, failures


def _render_markdown(*, env_path: Path, profile: str, rows: list[dict[str, str]]) -> str:
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Runtime Lock Check",
        f"- Captured at (UTC): {captured_at}",
        f"- Source: {env_path.as_posix()}",
        f"- Profile: {profile}",
        "",
        "| Key | Expected | Actual | Status |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['key']} | {row['expected']} | {row['actual']} | {row['status']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check runtime policy lock values in compose/.env.")
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to env file (default: compose/.env)",
    )
    parser.add_argument(
        "--profile",
        choices=[BASELINE_PROFILE, RELEASE_PROFILE],
        default=BASELINE_PROFILE,
        help="Validation profile (default: baseline).",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Emit a markdown report (useful for evidence logs).",
    )
    args = parser.parse_args()
    env_path = Path(args.env_file)

    try:
        values = _parse_env_file(env_path)
    except FileNotFoundError as exc:
        print(f"[runtime-policy-lock-guard] FAIL: {exc}")
        return 1

    if args.profile == RELEASE_PROFILE:
        rows, failures = _evaluate_release(values)
    else:
        rows, failures = _evaluate_baseline(values)

    if args.markdown:
        print(_render_markdown(env_path=env_path, profile=args.profile, rows=rows))
        print("")

    if failures:
        print(
            f"[runtime-policy-lock-guard] FAIL: profile={args.profile} runtime policy lock mismatch detected:"
        )
        for row in failures:
            print(f"  - {row}")
        if args.profile == RELEASE_PROFILE:
            print(
                "[runtime-policy-lock-guard] release profile is required for stability closeout sign-off."
            )
        return 1

    print(f"[runtime-policy-lock-guard] OK profile={args.profile} ({env_path.as_posix()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
