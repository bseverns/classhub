#!/usr/bin/env python3
"""Guardrail: keep /teach/class template decomposition and section contracts stable."""

from __future__ import annotations

import sys
from pathlib import Path


MAIN_TEMPLATE = Path("services/classhub/templates/teach_class.html")
MAX_MAIN_TEMPLATE_LINES = 220
TEACH_CLASS_INCLUDE_DIR = Path("services/classhub/templates/includes/teach_class")
EXPECTED_INCLUDES: tuple[Path, ...] = (
    Path("services/classhub/templates/includes/teach_class/class_setup_and_roster_card.html"),
    Path("services/classhub/templates/includes/teach_class/support_board_card.html"),
    Path("services/classhub/templates/includes/teach_class/outcomes_snapshot_card.html"),
    Path("services/classhub/templates/includes/teach_class/helper_signals_card.html"),
    Path("services/classhub/templates/includes/teach_class/lesson_tracker_card.html"),
    Path("services/classhub/templates/includes/teach_class/module_editor_card.html"),
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open("r", encoding="utf-8"))


def _require_snippets(text: str, *, path: Path, snippets: list[str], failures: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path}: missing snippet {snippet!r}")


def main() -> int:
    failures: list[str] = []
    try:
        main_text = _read(MAIN_TEMPLATE)
    except RuntimeError as exc:
        print(f"[teach-class-template-guard] FAIL: {exc}", file=sys.stderr)
        return 1

    main_line_count = _line_count(MAIN_TEMPLATE)
    if main_line_count > MAX_MAIN_TEMPLATE_LINES:
        failures.append(
            f"{MAIN_TEMPLATE}: expected <= {MAX_MAIN_TEMPLATE_LINES} lines, found {main_line_count}"
        )

    _require_snippets(
        main_text,
        path=MAIN_TEMPLATE,
        snippets=["Start Here In This Class"],
        failures=failures,
    )

    combined_include_text = ""
    for include_path in EXPECTED_INCLUDES:
        include_snippet = f'{{% include "{include_path.as_posix().split("services/classhub/templates/", 1)[1]}" %}}'
        if include_snippet not in main_text:
            failures.append(f"{MAIN_TEMPLATE}: missing include {include_snippet!r}")
        try:
            include_text = _read(include_path)
        except RuntimeError as exc:
            failures.append(str(exc))
            continue
        combined_include_text += "\n" + include_text

    class_setup_template = Path(
        "services/classhub/templates/includes/teach_class/class_setup_and_roster_card.html"
    )
    try:
        class_setup_text = _read(class_setup_template)
    except RuntimeError as exc:
        failures.append(str(exc))
        class_setup_text = ""
    _require_snippets(
        class_setup_text,
        path=class_setup_template,
        snippets=[
            '{% include "includes/teach_class/class_setup_landing_section.html" %}',
            '{% include "includes/teach_class/class_setup_invites_section.html" %}',
            '{% include "includes/teach_class/class_setup_staff_assignments_section.html" %}',
            '{% include "includes/teach_class/class_setup_roster_section.html" %}',
        ],
        failures=failures,
    )

    # Include nested section partials in anchor checks.
    for nested_path in sorted(TEACH_CLASS_INCLUDE_DIR.glob("*.html")):
        try:
            combined_include_text += "\n" + _read(nested_path)
        except RuntimeError as exc:
            failures.append(str(exc))

    # Keep section anchors in decomposed partials, not the root template.
    moved_section_ids = [
        "section-landing-page",
        "section-invite-links",
        "section-roster",
        "section-support-board",
        "section-outcomes",
        "section-helper-signals",
        "section-lesson-tracker",
        "section-module-editor",
    ]
    for section_id in moved_section_ids:
        in_main = f'id="{section_id}"' in main_text
        in_includes = f'id="{section_id}"' in combined_include_text
        if in_main:
            failures.append(f"{MAIN_TEMPLATE}: expected {section_id} to remain in include partials, not root template")
        if not in_includes:
            failures.append(f"includes/teach_class/*: missing section anchor {section_id}")

    if failures:
        print("[teach-class-template-guard] FAIL: teach_class decomposition contract drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[teach-class-template-guard] keep root template focused and section cards in include partials",
            file=sys.stderr,
        )
        return 1

    print(
        "[teach-class-template-guard] OK "
        f"(root={MAIN_TEMPLATE.as_posix()} lines={main_line_count}; includes={len(EXPECTED_INCLUDES)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
