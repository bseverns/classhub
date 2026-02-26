#!/usr/bin/env python3
"""Guardrail: block new wildcard imports in ClassHub view modules.

This guard supports incremental cleanup by allowing a small temporary baseline
of known wildcard imports while failing any new usages.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


VIEWS_ROOT = Path("services/classhub/hub/views")
WILDCARD_IMPORT_RE = re.compile(r"^\s*from\s+[.\w]+\s+import\s+\*(?:\s+#.*)?$", re.MULTILINE)

# Temporary baseline while legacy modules are being split and cleaned.
ALLOWED_WILDCARD_IMPORT_COUNTS: dict[str, int] = {
    "services/classhub/hub/views/__init__.py": 5,
    "services/classhub/hub/views/teacher_parts/auth.py": 1,
    "services/classhub/hub/views/teacher_parts/content.py": 1,
    "services/classhub/hub/views/teacher_parts/roster_class.py": 1,
    "services/classhub/hub/views/teacher_parts/roster_materials.py": 1,
    "services/classhub/hub/views/teacher_parts/roster_students.py": 1,
    "services/classhub/hub/views/teacher_parts/videos.py": 1,
}


def _iter_view_files() -> list[Path]:
    if not VIEWS_ROOT.is_dir():
        return []
    return sorted(VIEWS_ROOT.rglob("*.py"))


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def main() -> int:
    files = _iter_view_files()
    if not files:
        print(f"[view-wildcard-import-guard] FAIL: missing view root: {VIEWS_ROOT}", file=sys.stderr)
        return 1

    counts_by_path: dict[str, int] = {}
    violations: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        matches = list(WILDCARD_IMPORT_RE.finditer(text))
        if not matches:
            continue

        path_str = path.as_posix()
        counts_by_path[path_str] = len(matches)
        allowed_count = ALLOWED_WILDCARD_IMPORT_COUNTS.get(path_str, 0)

        if len(matches) > allowed_count:
            for match in matches[allowed_count:]:
                line = _line_number(text, match.start())
                snippet = text[match.start() : text.find("\n", match.start())].strip()
                violations.append(f"{path_str}:{line}: {snippet}")

    unexpected_allowlist_entries = sorted(set(ALLOWED_WILDCARD_IMPORT_COUNTS) - set(counts_by_path))
    if unexpected_allowlist_entries:
        print(
            "[view-wildcard-import-guard] NOTE: allowlist entries now clean (can be removed):",
            file=sys.stderr,
        )
        for row in unexpected_allowlist_entries:
            print(f"  - {row}", file=sys.stderr)

    if violations:
        print("[view-wildcard-import-guard] FAIL: new wildcard imports detected:", file=sys.stderr)
        for row in violations:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[view-wildcard-import-guard] if intentional, adjust ALLOWED_WILDCARD_IMPORT_COUNTS in the guard script",
            file=sys.stderr,
        )
        return 1

    total = sum(counts_by_path.values())
    print(f"[view-wildcard-import-guard] OK ({len(files)} view files checked, {total} wildcard import(s) in baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
