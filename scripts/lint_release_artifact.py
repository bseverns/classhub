#!/usr/bin/env python3
"""Validate release zip contents against forbidden runtime/local artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import PurePosixPath
from zipfile import ZipFile


BLOCKED_PARTS = {
    ".git",
    ".venv",
    ".venv_docs",
    "__pycache__",
    "__MACOSX",
    "media",
    "staticfiles",
    "data",
    ".deploy",
    "site",
}

BLOCKED_EXACT = {
    "compose/.env",
    "compose/.env.local",
}

BLOCKED_PREFIXES = (
    "compose/.env.bak",
    "compose/.env.backup",
    "compose/.env.local.",
    "compose/docker-compose.override.yml.disabled",
)

BLOCKED_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".DS_Store",
)


def _is_forbidden(path: str) -> bool:
    posix = PurePosixPath(path)
    if any(part in BLOCKED_PARTS for part in posix.parts):
        return True

    normalized = str(posix).lstrip("./")
    if normalized in BLOCKED_EXACT:
        return True
    if normalized.startswith("compose/.env.") and normalized not in {
        "compose/.env.example",
        "compose/.env.example.local",
        "compose/.env.example.domain",
    }:
        return True
    if any(normalized.startswith(prefix) for prefix in BLOCKED_PREFIXES):
        return True
    if normalized.endswith(BLOCKED_SUFFIXES):
        return True
    return False


def lint_release_zip(zip_path: str) -> list[str]:
    offenders: list[str] = []
    with ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if _is_forbidden(name):
                offenders.append(name)
    return offenders


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Class Hub release artifact contents.")
    parser.add_argument("zip_path", help="Path to a release .zip archive")
    args = parser.parse_args()

    offenders = lint_release_zip(args.zip_path)
    if offenders:
        print("Forbidden paths found in release artifact:")
        for row in offenders:
            print(f"- {row}")
        return 1

    print("Release artifact check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
