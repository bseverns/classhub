#!/usr/bin/env python3
"""Validate the embedded and detached ClassHub release artifact contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from release_artifact import ArtifactError, verify_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Class Hub release artifact contents.")
    parser.add_argument("zip_path", help="Path to a release .zip archive")
    args = parser.parse_args()

    try:
        manifest = verify_artifact(Path(args.zip_path))
    except ArtifactError as exc:
        print(f"Release artifact check failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Release artifact check passed: "
        f"version={manifest['version']} commit={manifest['source']['commit']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
