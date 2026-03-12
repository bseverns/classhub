#!/usr/bin/env python3
"""Guardrail: keep Somali locale coverage aligned with Spanish coverage."""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ES_PO = Path("services/classhub/locale/es/LC_MESSAGES/django.po")
SO_PO = Path("services/classhub/locale/so/LC_MESSAGES/django.po")


@dataclass(frozen=True)
class PoEntry:
    msgid: str
    msgid_plural: str | None
    msgstr_single: str | None
    msgstr_plural_0: str | None
    msgstr_plural_1: str | None


_QUOTED_LINE = re.compile(r'^[a-zA-Z0-9_\[\]]+\s+"(.*)"$')


def _unquote_line(line: str) -> str:
    match = _QUOTED_LINE.match(line)
    if not match:
        return ""
    quoted = match.group(1)
    try:
        return ast.literal_eval(f'"{quoted}"')
    except (SyntaxError, ValueError):
        return quoted


def _parse_entries(path: Path) -> dict[str, PoEntry]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: dict[str, PoEntry] = {}

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.startswith('msgid "'):
            idx += 1
            continue

        msgid = _unquote_line(line)
        idx += 1
        if msgid == "":
            # Header entry.
            continue

        msgid_plural: str | None = None
        msgstr_single: str | None = None
        msgstr_plural_0: str | None = None
        msgstr_plural_1: str | None = None

        while idx < len(lines):
            row = lines[idx]
            if row.startswith('msgid "'):
                break
            if row.startswith('msgid_plural "'):
                msgid_plural = _unquote_line(row)
            elif row.startswith('msgstr "'):
                msgstr_single = _unquote_line(row)
            elif row.startswith('msgstr[0] "'):
                msgstr_plural_0 = _unquote_line(row)
            elif row.startswith('msgstr[1] "'):
                msgstr_plural_1 = _unquote_line(row)
            idx += 1

        entries[msgid] = PoEntry(
            msgid=msgid,
            msgid_plural=msgid_plural,
            msgstr_single=msgstr_single,
            msgstr_plural_0=msgstr_plural_0,
            msgstr_plural_1=msgstr_plural_1,
        )

    return entries


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def main() -> int:
    try:
        es_entries = _parse_entries(ES_PO)
        so_entries = _parse_entries(SO_PO)
    except FileNotFoundError as exc:
        print(f"[i18n-es-so-parity] FAIL: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    missing_msgids = sorted(set(es_entries) - set(so_entries))
    for msgid in missing_msgids:
        failures.append(f"Somali locale missing msgid: {msgid!r}")

    for msgid, es_entry in es_entries.items():
        so_entry = so_entries.get(msgid)
        if so_entry is None:
            continue

        if _is_blank(so_entry.msgstr_single) and es_entry.msgid_plural is None:
            failures.append(f"Somali msgstr is empty for msgid: {msgid!r}")

        if es_entry.msgid_plural is not None:
            if _is_blank(so_entry.msgstr_plural_0):
                failures.append(f"Somali msgstr[0] is empty for plural msgid: {msgid!r}")
            if _is_blank(so_entry.msgstr_plural_1):
                failures.append(f"Somali msgstr[1] is empty for plural msgid: {msgid!r}")

    if failures:
        print("[i18n-es-so-parity] FAIL: Spanish/Somali locale parity drift detected:", file=sys.stderr)
        for row in failures:
            print(f"  - {row}", file=sys.stderr)
        print(
            "[i18n-es-so-parity] keep Somali coverage non-empty for every Spanish msgid",
            file=sys.stderr,
        )
        return 1

    print(
        f"[i18n-es-so-parity] OK: es msgids={len(es_entries)} so msgids={len(so_entries)} "
        "and Somali coverage is non-empty for all Spanish entries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
