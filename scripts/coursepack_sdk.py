#!/usr/bin/env python3
"""Local Authoring SDK for ClassHub coursepacks.

The SDK keeps course content as versioned files (content-as-code):
- validate structure and lesson references,
- package a portable coursepack zip artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import zipfile

from validate_coursepack import COURSES_ROOT, validate_coursepack, yaml as validate_yaml


SDK_VERSION = "0.1.0"
_IGNORED_FILE_NAMES = {".DS_Store"}


def _course_dir_for_slug(slug: str) -> Path:
    return COURSES_ROOT / slug


def _default_output_path(*, slug: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("dist") / "coursepacks" / f"{slug}_{stamp}.zip"


def _iter_pack_files(course_dir: Path):
    for path in sorted(course_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(course_dir)
        if path.name in _IGNORED_FILE_NAMES:
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        yield path, rel


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _validate_single(slug: str) -> tuple[bool, list[str]]:
    course_dir = _course_dir_for_slug(slug)
    if not course_dir.exists():
        return False, [f"{course_dir}: course directory not found"]
    if not course_dir.is_dir():
        return False, [f"{course_dir}: expected a directory"]
    errors = validate_coursepack(course_dir)
    return not errors, errors


def _validate_all() -> tuple[bool, dict[str, list[str]]]:
    if not COURSES_ROOT.exists():
        return False, {str(COURSES_ROOT): [f"{COURSES_ROOT}: courses root not found"]}
    results: dict[str, list[str]] = {}
    for course_dir in sorted(path for path in COURSES_ROOT.iterdir() if path.is_dir()):
        errors = validate_coursepack(course_dir)
        results[course_dir.name] = errors
    ok = all(not errs for errs in results.values())
    return ok, results


def _write_coursepack_zip(*, slug: str, output_path: Path) -> dict:
    course_dir = _course_dir_for_slug(slug)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_count = 0
    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for src, rel in _iter_pack_files(course_dir):
            arcname = f"{slug}/{rel.as_posix()}"
            archive.write(src, arcname=arcname)
            file_count += 1

    return {
        "slug": slug,
        "artifact": str(output_path),
        "files": file_count,
        "bytes": output_path.stat().st_size,
        "sha256": _sha256_file(output_path),
    }


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _validate_command(args: argparse.Namespace) -> int:
    if args.all:
        ok, results = _validate_all()
        payload = {
            "ok": ok,
            "sdk_version": SDK_VERSION,
            "results": results,
        }
        if args.json:
            _print_json(payload)
        else:
            for slug, errors in results.items():
                if errors:
                    print(f"[coursepack-sdk] FAIL: {slug}")
                    for entry in errors:
                        print(f"  - {entry}")
                else:
                    print(f"[coursepack-sdk] OK: {slug}")
        return 0 if ok else 1

    slug = (args.course_slug or "").strip()
    if not slug:
        print("[coursepack-sdk] FAIL: --course-slug is required unless --all is used", file=sys.stderr)
        return 1

    ok, errors = _validate_single(slug)
    payload = {
        "ok": ok,
        "sdk_version": SDK_VERSION,
        "slug": slug,
        "errors": errors,
    }
    if args.json:
        _print_json(payload)
    else:
        if ok:
            print(f"[coursepack-sdk] OK: {slug}")
        else:
            print(f"[coursepack-sdk] FAIL: {slug}")
            for entry in errors:
                print(f"  - {entry}")
    return 0 if ok else 1


def _build_or_package_command(args: argparse.Namespace, *, validate_first: bool) -> int:
    slug = (args.course_slug or "").strip()
    if not slug:
        print("[coursepack-sdk] FAIL: --course-slug is required", file=sys.stderr)
        return 1

    if validate_first:
        ok, errors = _validate_single(slug)
        if not ok:
            payload = {
                "ok": False,
                "sdk_version": SDK_VERSION,
                "slug": slug,
                "errors": errors,
            }
            if args.json:
                _print_json(payload)
            else:
                print(f"[coursepack-sdk] FAIL: {slug}")
                for entry in errors:
                    print(f"  - {entry}")
            return 1

    output_path = Path(args.output).expanduser() if args.output else _default_output_path(slug=slug)
    result = _write_coursepack_zip(slug=slug, output_path=output_path)
    payload = {
        "ok": True,
        "sdk_version": SDK_VERSION,
        **result,
    }
    if args.json:
        _print_json(payload)
    else:
        mode = "build" if validate_first else "package"
        print(f"[coursepack-sdk] OK: {mode} {slug}")
        print(f"  artifact: {result['artifact']}")
        print(f"  files: {result['files']}")
        print(f"  bytes: {result['bytes']}")
        print(f"  sha256: {result['sha256']}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate_cmd = sub.add_parser("validate", help="Validate one coursepack or all coursepacks")
    validate_cmd.add_argument("--course-slug", default="", help="Course slug under content/courses")
    validate_cmd.add_argument("--all", action="store_true", help="Validate all course folders")
    validate_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    build_cmd = sub.add_parser("build", help="Validate then package one coursepack")
    build_cmd.add_argument("--course-slug", required=True, help="Course slug under content/courses")
    build_cmd.add_argument("--output", default="", help="Output zip path (default: dist/coursepacks/<slug>_<stamp>.zip)")
    build_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    package_cmd = sub.add_parser("package", help="Package one coursepack without validation")
    package_cmd.add_argument("--course-slug", required=True, help="Course slug under content/courses")
    package_cmd.add_argument("--output", default="", help="Output zip path (default: dist/coursepacks/<slug>_<stamp>.zip)")
    package_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    return parser


def main() -> int:
    args = _parser().parse_args()

    if validate_yaml is None:
        print(
            "[coursepack-sdk] FAIL: PyYAML is required "
            "(install classhub deps: `pip install -r services/classhub/requirements.txt`)",
            file=sys.stderr,
        )
        return 1

    if args.command == "validate":
        return _validate_command(args)
    if args.command == "build":
        return _build_or_package_command(args, validate_first=True)
    if args.command == "package":
        return _build_or_package_command(args, validate_first=False)
    print(f"[coursepack-sdk] FAIL: unknown command '{args.command}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
