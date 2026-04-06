#!/usr/bin/env python3
"""Guardrail: keep family-visible i18n tranche explicit and enforceable."""

from __future__ import annotations

import sys
from pathlib import Path


LOCALIZATION_DOC = Path("docs/LOCALIZATION.md")
I18N_TESTS = Path("services/classhub/hub/tests/test_i18n.py")
STUDENT_TEMPLATE = Path("services/classhub/templates/student_class.html")
TEACH_DAY_TEMPLATE = Path("services/classhub/templates/includes/teach_home/day_sections.html")
LOCALE_FILES: tuple[Path, ...] = (
    Path("services/classhub/locale/es/LC_MESSAGES/django.po"),
    Path("services/classhub/locale/so/LC_MESSAGES/django.po"),
    Path("services/classhub/locale/ksw/LC_MESSAGES/django.po"),
)

REQUIRED_DOC_SNIPPETS: tuple[str, ...] = (
    "## Family-visible first tranche",
    "`/student`",
    "`/teach?portal_mode=day`",
    "python3 scripts/check_i18n_family_visible_contract.py",
)

REQUIRED_TEST_SNIPPETS: tuple[str, ...] = (
    "def test_student_class_page_spanish_renders_translated_core_copy",
    "def test_teach_home_day_mode_spanish_renders_translated_core_copy",
    "def test_student_class_page_somali_renders_translated_core_copy",
    "def test_teach_home_day_mode_somali_renders_translated_core_copy",
    "def test_student_class_page_sgaw_karen_renders_translated_core_copy",
    "def test_teach_home_day_mode_sgaw_karen_renders_translated_core_copy",
)

REQUIRED_STUDENT_TEMPLATE_SNIPPETS: tuple[str, ...] = (
    '{% trans "Your return code:" %}',
    '{% trans "Quick check-in" %}',
    '{% trans "Return image: look for this picture when you come back to class." %}',
)

REQUIRED_TEACH_DAY_TEMPLATE_SNIPPETS: tuple[str, ...] = (
    "{% load i18n %}",
    '{% trans "Classes" %}',
    '{% trans "What Changed Since Yesterday" %}',
    '{% trans "End-of-Class Closeout" %}',
    '{% trans "Recent submissions" %}',
    "{% blocktrans with window_start=",
    "{% blocktrans with class_name=row.classroom.name student_total=row.student_total %}",
    "{% blocktrans with pending_count=row.students_without_submissions %}",
)

REQUIRED_LOCALE_MSGIDS: tuple[str, ...] = (
    "Return image: look for this picture when you come back to class.",
    "Quick check-in",
    "Classes",
    "What Changed Since Yesterday",
    "End-of-Class Closeout",
    "Recent submissions",
    "Window started %(window_start)s",
    "%(class_name)s · %(student_total)s students",
    "%(pending_count)s still need a first upload.",
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"unable to read {path}: {exc}") from exc


def _require_snippets(text: str, *, path: Path, snippets: tuple[str, ...], failures: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            failures.append(f"{path}: missing snippet {snippet!r}")


def _extract_msgstr(po_text: str, msgid: str) -> str | None:
    lines = po_text.splitlines()
    target = f'msgid "{msgid}"'
    for idx, line in enumerate(lines):
        if line != target:
            continue
        for next_idx in range(idx + 1, len(lines)):
            next_line = lines[next_idx]
            if not next_line:
                continue
            if next_line.startswith("#"):
                continue
            if next_line.startswith("msgstr "):
                if next_line == 'msgstr ""':
                    return ""
                prefix = 'msgstr "'
                if next_line.startswith(prefix) and next_line.endswith('"'):
                    return next_line[len(prefix) : -1]
                return ""
            if next_line.startswith("msgid "):
                return None
            return None
    return None


def main() -> int:
    failures: list[str] = []
    try:
        localization_doc = _read(LOCALIZATION_DOC)
        i18n_tests = _read(I18N_TESTS)
        student_template = _read(STUDENT_TEMPLATE)
        teach_day_template = _read(TEACH_DAY_TEMPLATE)
    except RuntimeError as exc:
        print(f"[i18n-family-visible-guard] FAIL: {exc}", file=sys.stderr)
        return 1
    locale_payloads: dict[Path, str] = {}
    for locale_path in LOCALE_FILES:
        try:
            locale_payloads[locale_path] = _read(locale_path)
        except RuntimeError as exc:
            print(f"[i18n-family-visible-guard] FAIL: {exc}", file=sys.stderr)
            return 1

    _require_snippets(
        localization_doc,
        path=LOCALIZATION_DOC,
        snippets=REQUIRED_DOC_SNIPPETS,
        failures=failures,
    )
    _require_snippets(
        i18n_tests,
        path=I18N_TESTS,
        snippets=REQUIRED_TEST_SNIPPETS,
        failures=failures,
    )
    _require_snippets(
        student_template,
        path=STUDENT_TEMPLATE,
        snippets=REQUIRED_STUDENT_TEMPLATE_SNIPPETS,
        failures=failures,
    )
    _require_snippets(
        teach_day_template,
        path=TEACH_DAY_TEMPLATE,
        snippets=REQUIRED_TEACH_DAY_TEMPLATE_SNIPPETS,
        failures=failures,
    )

    for locale_path, locale_text in locale_payloads.items():
        for msgid in REQUIRED_LOCALE_MSGIDS:
            msgstr = _extract_msgstr(locale_text, msgid)
            if msgstr is None:
                failures.append(f"{locale_path}: missing msgid {msgid!r}")
                continue
            if not msgstr.strip():
                failures.append(f"{locale_path}: empty msgstr for msgid {msgid!r}")

    if failures:
        print("[i18n-family-visible-guard] FAIL: family-visible i18n contract drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[i18n-family-visible-guard] keep route scope, tests, and translations aligned for /student + /teach day mode across es/so/ksw",
            file=sys.stderr,
        )
        return 1

    print("[i18n-family-visible-guard] OK (family-visible i18n tranche contracts are aligned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
