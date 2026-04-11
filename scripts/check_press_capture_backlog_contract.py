#!/usr/bin/env python3
"""Guardrail: keep public press/screenshot backlog explicit and bounded."""

from __future__ import annotations

import re
import sys
from pathlib import Path


PLACEHOLDERS_PATH = Path("press/screenshots/PLACEHOLDERS.md")
PUBLIC_OVERVIEW_PATH = Path("docs/PUBLIC_OVERVIEW.md")
CURRENT_STATE_PATH = Path("docs/CURRENT_STATE.md")
SHOTLIST_PATH = Path("press/screenshots/SHOTLIST.md")
MAX_BACKLOG_ITEMS = 5


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _extract_capture_backlog_filenames(placeholders_text: str) -> list[str]:
    section_start = placeholders_text.find("## Capture backlog")
    if section_start < 0:
        return []
    next_section = placeholders_text.find("\n## ", section_start + 1)
    if next_section < 0:
        next_section = len(placeholders_text)
    section = placeholders_text[section_start:next_section]
    return re.findall(r"^\s*\d+\.\s+`([^`]+)`", section, flags=re.MULTILINE)


def main() -> int:
    failures: list[str] = []
    try:
        placeholders = _read(PLACEHOLDERS_PATH)
        public_overview = _read(PUBLIC_OVERVIEW_PATH)
        current_state = _read(CURRENT_STATE_PATH)
        shotlist = _read(SHOTLIST_PATH)
    except RuntimeError as exc:
        print(f"[press-capture-backlog-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    filenames = _extract_capture_backlog_filenames(placeholders)
    if not filenames:
        failures.append(f"{PLACEHOLDERS_PATH}: missing or empty '## Capture backlog' list")
    elif len(filenames) > MAX_BACKLOG_ITEMS:
        failures.append(
            f"{PLACEHOLDERS_PATH}: backlog has {len(filenames)} items (max {MAX_BACKLOG_ITEMS})"
        )

    for required_marker in ("## Backlog governance", "Owner:", "Target closeout date:"):
        if required_marker not in placeholders:
            failures.append(f"{PLACEHOLDERS_PATH}: missing governance marker {required_marker!r}")

    if "Pending captures are tracked in `press/screenshots/PLACEHOLDERS.md`" not in public_overview:
        failures.append(f"{PUBLIC_OVERVIEW_PATH}: missing pending-capture pointer to placeholders")
    if "Screenshot backlog is now narrow and explicit in `press/screenshots/PLACEHOLDERS.md`" not in current_state:
        failures.append(f"{CURRENT_STATE_PATH}: missing narrow-backlog status marker")

    for filename in filenames:
        if filename not in shotlist:
            failures.append(f"{SHOTLIST_PATH}: missing backlog filename `{filename}`")

    if failures:
        print("[press-capture-backlog-guard] FAIL: public/press backlog contract drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[press-capture-backlog-guard] keep backlog bounded and governance metadata explicit",
            file=sys.stderr,
        )
        return 1

    print(
        "[press-capture-backlog-guard] OK "
        f"(capture backlog={len(filenames)} item(s), max={MAX_BACKLOG_ITEMS})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
