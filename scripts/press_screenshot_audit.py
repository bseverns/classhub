#!/usr/bin/env python3
"""Inventory and sanity-check press screenshot assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRESS_DIR = ROOT / "press" / "screenshots"
DOCS_DIR = ROOT / "docs" / "images" / "press"
SHOTLIST_PATH = PRESS_DIR / "SHOTLIST.md"
PLACEHOLDERS_PATH = PRESS_DIR / "PLACEHOLDERS.md"
SUSPICIOUS_SIZE_BYTES = 10_000


@dataclass
class FileInfo:
    path: str
    size_bytes: int
    sha256: str
    width: int
    height: int


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_file(path: Path) -> FileInfo:
    width, height = _parse_png_size(path)
    return FileInfo(
        path=str(path.relative_to(ROOT)),
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
        width=width,
        height=height,
    )


def _list_pngs(folder: Path) -> dict[str, FileInfo]:
    rows: dict[str, FileInfo] = {}
    if not folder.exists():
        return rows
    for path in sorted(folder.glob("*.png")):
        rows[path.name] = _scan_file(path)
    return rows


def _shotlist_filenames() -> list[str]:
    text = _read_text(SHOTLIST_PATH)
    section_start = text.find("## Capture targets")
    section_end = text.find("## Storyline overlays", section_start)
    section = text[section_start:section_end]
    return [name for _num, name in re.findall(r"^\s*(\d+)\.\s+`([^`]+)`", section, flags=re.MULTILINE)]


def _backlog_filenames() -> list[str]:
    text = _read_text(PLACEHOLDERS_PATH)
    section_start = text.find("## Capture backlog")
    section_end = text.find("\n## ", section_start + 1)
    if section_end < 0:
        section_end = len(text)
    section = text[section_start:section_end]
    return re.findall(r"^\s*\d+\.\s+`([^`]+)`", section, flags=re.MULTILINE)


def _build_report() -> dict:
    press_files = _list_pngs(PRESS_DIR)
    docs_files = _list_pngs(DOCS_DIR)
    shotlist = _shotlist_filenames()
    backlog = set(_backlog_filenames())
    sha_to_names: dict[str, list[str]] = defaultdict(list)
    for name, info in press_files.items():
        sha_to_names[info.sha256].append(name)

    rows = []
    missing_press = []
    missing_docs = []
    suspicious = []
    mismatched = []

    for name in shotlist:
        press_info = press_files.get(name)
        docs_info = docs_files.get(name)
        is_backlog = name in backlog
        row = {
            "filename": name,
            "in_backlog": is_backlog,
            "press": asdict(press_info) if press_info else None,
            "docs": asdict(docs_info) if docs_info else None,
            "hash_match": bool(press_info and docs_info and press_info.sha256 == docs_info.sha256),
            "suspicious_small": bool(press_info and press_info.size_bytes < SUSPICIOUS_SIZE_BYTES),
            "duplicate_hash_group": sorted(sha_to_names.get(press_info.sha256, [])) if press_info else [],
        }
        rows.append(row)
        if press_info is None and not is_backlog:
            missing_press.append(name)
        if docs_info is None and not is_backlog:
            missing_docs.append(name)
        if press_info and docs_info and press_info.sha256 != docs_info.sha256:
            mismatched.append(name)
        if press_info and press_info.size_bytes < SUSPICIOUS_SIZE_BYTES:
            suspicious.append(name)

    return {
        "press_dir": str(PRESS_DIR.relative_to(ROOT)),
        "docs_dir": str(DOCS_DIR.relative_to(ROOT)),
        "shotlist_count": len(shotlist),
        "backlog_count": len(backlog),
        "missing_press": missing_press,
        "missing_docs": missing_docs,
        "mismatched_pairs": mismatched,
        "suspicious_small_files": suspicious,
        "rows": rows,
    }


def _print_summary(report: dict) -> None:
    print("[press-screenshot-audit] Shotlist inventory")
    print(f"  - shotlist targets: {report['shotlist_count']}")
    print(f"  - backlog targets: {report['backlog_count']}")
    print(f"  - missing in press/screenshots: {len(report['missing_press'])}")
    print(f"  - missing in docs/images/press: {len(report['missing_docs'])}")
    print(f"  - mismatched press/docs hashes: {len(report['mismatched_pairs'])}")
    print(f"  - suspiciously small press files: {len(report['suspicious_small_files'])}")

    if report["missing_press"]:
        print("  - missing press files: " + ", ".join(report["missing_press"]))
    if report["missing_docs"]:
        print("  - missing docs files: " + ", ".join(report["missing_docs"]))
    if report["mismatched_pairs"]:
        print("  - mismatched pairs: " + ", ".join(report["mismatched_pairs"]))
    if report["suspicious_small_files"]:
        print("  - suspicious small files: " + ", ".join(report["suspicious_small_files"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit press screenshot inventory and spot likely blank assets.")
    parser.add_argument("--json-out", default="", help="Optional path to write JSON report")
    args = parser.parse_args()

    report = _build_report()
    _print_summary(report)

    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"[press-screenshot-audit] wrote JSON report: {out_path}")

    # Fail only on non-backlog drift that implies public evidence is likely wrong.
    failures = []
    if report["missing_press"]:
        failures.append("missing press screenshots outside backlog")
    if report["missing_docs"]:
        failures.append("missing docs screenshots outside backlog")
    if report["mismatched_pairs"]:
        failures.append("press/docs screenshot copies diverged")
    suspicious_non_backlog = {
        row["filename"]
        for row in report["rows"]
        if row["suspicious_small"] and not row["in_backlog"]
    }
    if suspicious_non_backlog:
        failures.append("suspiciously small screenshots outside backlog")

    if failures:
        print("[press-screenshot-audit] FAIL: " + "; ".join(failures), file=sys.stderr)
        return 1
    print("[press-screenshot-audit] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
