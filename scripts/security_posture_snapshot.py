#!/usr/bin/env python3
"""Render a compact operator-facing security posture snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_ENV_FILE = Path("compose/.env")
REGISTRY_PATH = Path("docs/_registry/runtime_contracts.json")
IMAGE_KEYS = ("CADDY_IMAGE", "POSTGRES_IMAGE", "REDIS_IMAGE", "OLLAMA_IMAGE", "MINIO_IMAGE")


def _parse_env_file(path: Path) -> dict[str, str]:
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


def _load_registry() -> dict:
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"{REGISTRY_PATH} must contain a mapping")
    return raw


def _format_stage(values: dict[str, str]) -> str:
    mode = (values.get("DJANGO_CSP_MODE") or "").strip().lower().replace("_", "-") or "<unset>"
    enforced = (values.get("DJANGO_CSP_POLICY") or "").strip()
    if mode == "strict" and "'unsafe-inline'" in enforced and "style-src" in enforced:
        return "strict canary (scripts locked, styles transitional)"
    if mode == "strict":
        return "strict enforced"
    if mode == "relaxed":
        return "relaxed enforced + strict report-only"
    if mode == "report-only":
        return "strict report-only transitional"
    return mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to env file (default: compose/.env)",
    )
    args = parser.parse_args()

    env_path = Path(args.env_file)
    values = _parse_env_file(env_path)
    registry = _load_registry()
    runtime = registry.get("runtime") or {}
    features = registry.get("features") or {}

    print("# Security Posture Snapshot")
    print(f"- Source env: {env_path.as_posix()}")
    print("")
    print("## Active posture")
    print(f"- CSP stage: {_format_stage(values)}")
    print(f"- Staff org boundary: REQUIRE_ORG_MEMBERSHIP_FOR_STAFF={values.get('REQUIRE_ORG_MEMBERSHIP_FOR_STAFF', '<unset>')}")
    print(
        "- Teacher SSO: "
        f"enabled={values.get('CLASSHUB_TEACHER_SSO_ENABLED', '<unset>')} "
        f"providers={values.get('CLASSHUB_TEACHER_SSO_PROVIDERS', '<unset>') or '<none>'}"
    )
    print(f"- Image pin policy: {runtime.get('image_pins', {}).get('policy', 'unknown')}")
    print("")
    print("## Transitional items")
    print(f"- {runtime.get('csp', {}).get('note', '').strip()}")
    print(f"- {features.get('teacher_sso_google', {}).get('note', '').strip()}")
    print(f"- {runtime.get('image_pins', {}).get('note', '').strip()}")
    print("")
    print("## Critical flags")
    print(f"- DJANGO_CSP_MODE={values.get('DJANGO_CSP_MODE', '<unset>')}")
    print(f"- DJANGO_CSP_POLICY={'set' if (values.get('DJANGO_CSP_POLICY') or '').strip() else 'unset'}")
    print(f"- DJANGO_CSP_REPORT_ONLY_POLICY={'set' if (values.get('DJANGO_CSP_REPORT_ONLY_POLICY') or '').strip() else 'unset'}")
    print(f"- CLASSHUB_TEACHER_SSO_ENABLED={values.get('CLASSHUB_TEACHER_SSO_ENABLED', '<unset>')}")
    print(f"- CLASSHUB_TEACHER_SSO_PROVIDERS={values.get('CLASSHUB_TEACHER_SSO_PROVIDERS', '<unset>') or '<none>'}")
    for key in IMAGE_KEYS:
        print(f"- {key}={values.get(key, '<unset>')}")
    print("")
    print("## Docs refresh rule")
    print("- Refresh docs when a registry-backed shipped status or repo default posture changes.")
    print("- Operator-local `.env` overrides do not change product docs by themselves.")
    print(f"- Canonical registry: {REGISTRY_PATH.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
