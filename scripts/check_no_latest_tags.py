#!/usr/bin/env python3
"""Guardrail: committed image pins must stay explicit and upgrade-ready."""

from __future__ import annotations

import re
import sys
from pathlib import Path


TARGET_PATTERNS = (
    "compose/docker-compose*.yml",
    "compose/.env.example*",
)
REQUIRED_IMAGE_ENV_KEYS = (
    "CADDY_IMAGE",
    "POSTGRES_IMAGE",
    "REDIS_IMAGE",
    "OLLAMA_IMAGE",
    "MINIO_IMAGE",
)
IMAGE_REF_RE = re.compile(r"^[A-Za-z0-9./_-]+(?::[^:@\s]+)?(?:@sha256:[0-9a-f]{64})?$")
FLOATING_TAG_RE = re.compile(r"^v?\d+(?:\.\d+)?(?:[-_][A-Za-z0-9._-]+)?$")


def _iter_target_files() -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in TARGET_PATTERNS:
        for path in sorted(Path().glob(pattern)):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(path)
    return paths


def _tag_from_image_ref(image_ref: str) -> str:
    if "@sha256:" in image_ref:
        image_ref = image_ref.split("@sha256:", 1)[0]
    last_slash = image_ref.rfind("/")
    last_colon = image_ref.rfind(":")
    if last_colon <= last_slash:
        return ""
    return image_ref[last_colon + 1 :].strip()


def _is_immutable_ready_tag(tag: str) -> bool:
    normalized = (tag or "").strip()
    if not normalized:
        return False
    if normalized == "latest":
        return False
    if normalized.startswith("RELEASE."):
        return True
    if re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?", normalized):
        return True
    if normalized.count(".") >= 2:
        return True
    if re.search(r"\d\.\d+\.\d+", normalized):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}", normalized):
        return True
    if FLOATING_TAG_RE.fullmatch(normalized):
        return False
    return "." in normalized


def _validate_image_ref(path: Path, *, lineno: int, image_ref: str, failures: list[str]) -> None:
    normalized = image_ref.strip()
    if not normalized:
        failures.append(f"{path}:{lineno}: image ref is blank")
        return
    if ":latest" in normalized:
        failures.append(f"{path}:{lineno}: disallowed ':latest' image tag: {normalized}")
    if not IMAGE_REF_RE.match(normalized):
        failures.append(f"{path}:{lineno}: malformed image ref: {normalized}")
        return
    if "@sha256:" in normalized:
        return
    tag = _tag_from_image_ref(normalized)
    if not _is_immutable_ready_tag(tag):
        failures.append(
            f"{path}:{lineno}: image ref must use an exact version tag or digest (found {normalized})"
        )


def _find_latest_tag_violations(path: Path) -> list[str]:
    violations: list[str] = []
    seen_required_keys: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if path.name.startswith(".env.example") and "=" in stripped:
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key in REQUIRED_IMAGE_ENV_KEYS:
                seen_required_keys.add(key)
                _validate_image_ref(path, lineno=lineno, image_ref=value, failures=violations)
            continue
        if path.suffix in {".yml", ".yaml"} and stripped.startswith("image:"):
            image_value = stripped.split("image:", 1)[1].strip()
            if image_value.startswith("${") and ":-" in image_value and image_value.endswith("}"):
                image_value = image_value.split(":-", 1)[1][:-1]
            _validate_image_ref(path, lineno=lineno, image_ref=image_value, failures=violations)

    if path.name.startswith(".env.example"):
        missing = sorted(set(REQUIRED_IMAGE_ENV_KEYS) - seen_required_keys)
        for key in missing:
            violations.append(f"{path}: missing required image pin {key}")
    return violations


def main() -> int:
    targets = _iter_target_files()
    if not targets:
        print("[image-tag-guard] FAIL: no target files matched", file=sys.stderr)
        return 1

    violations: list[str] = []
    for path in targets:
        violations.extend(_find_latest_tag_violations(path))

    if violations:
        print("[image-tag-guard] FAIL: image pin policy drift detected:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print("[image-tag-guard] OK (exact tags/digests enforced for committed compose image pins)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
