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
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
import zipfile

from validate_coursepack import COURSES_ROOT, validate_coursepack, yaml as validate_yaml

CLASSHUB_SERVICE_DIR = Path(__file__).resolve().parents[1] / "services" / "classhub"
if str(CLASSHUB_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(CLASSHUB_SERVICE_DIR))

from hub.services.coursepack_registry import (  # noqa: E402
    CoursepackRegistryError,
    build_registry_entry,
    fetch_registry_artifact,
    new_registry_document,
    read_registry_document,
    select_registry_entry,
    upsert_registry_entry,
    validate_registry_document,
    write_registry_document,
)


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
    registry_payload = None
    checksum_file = ""

    try:
        registry_entry = build_registry_entry(
            slug=slug,
            artifact_path=output_path,
            version=str(args.version or "").strip(),
            release_channel=str(args.release_channel or "").strip(),
            artifact_url="",
            source_url=str(args.source_url or "").strip(),
            sdk_version=SDK_VERSION,
        )
        checksum_file = str(registry_entry.get("checksum_file") or "")

        registry_index = str(args.registry_index or "").strip()
        if registry_index:
            index_path = Path(registry_index).expanduser()
            artifact_url = str(args.artifact_url or "").strip()
            if not artifact_url:
                try:
                    artifact_url = os.path.relpath(
                        output_path.resolve(),
                        start=index_path.resolve().parent,
                    ).replace(os.sep, "/")
                except Exception:
                    artifact_url = output_path.name
            registry_entry = build_registry_entry(
                slug=slug,
                artifact_path=output_path,
                version=str(args.version or "").strip(),
                release_channel=str(args.release_channel or "").strip(),
                artifact_url=artifact_url,
                source_url=str(args.source_url or "").strip(),
                sdk_version=SDK_VERSION,
            )
            if index_path.exists():
                existing_payload, _ = read_registry_document(str(index_path))
            else:
                existing_payload = new_registry_document()
            registry_payload = upsert_registry_entry(existing_payload, registry_entry)
            write_registry_document(index_path, registry_payload)
    except CoursepackRegistryError as exc:
        if args.json:
            _print_json(
                {
                    "ok": False,
                    "sdk_version": SDK_VERSION,
                    "slug": slug,
                    "artifact": str(output_path),
                    "registry_error": str(exc),
                }
            )
        else:
            print(f"[coursepack-sdk] FAIL: registry export error for {slug}")
            print(f"  - {exc}")
        return 1

    payload = {
        "ok": True,
        "sdk_version": SDK_VERSION,
        **result,
        "checksum_file": checksum_file,
        "version": registry_entry.get("version"),
        "release_channel": registry_entry.get("release_channel"),
        "source_url": registry_entry.get("source_url"),
    }
    if registry_payload is not None:
        payload["registry_index"] = str(Path(args.registry_index).expanduser())
        payload["registry_entries"] = len(registry_payload.get("entries") or [])
    if args.json:
        _print_json(payload)
    else:
        mode = "build" if validate_first else "package"
        print(f"[coursepack-sdk] OK: {mode} {slug}")
        print(f"  artifact: {result['artifact']}")
        print(f"  files: {result['files']}")
        print(f"  bytes: {result['bytes']}")
        print(f"  sha256: {result['sha256']}")
        print(f"  checksum_file: {checksum_file}")
        if registry_payload is not None:
            print(f"  registry_index: {Path(args.registry_index).expanduser()}")
            print(f"  registry_entries: {len(registry_payload.get('entries') or [])}")
    return 0


def _registry_validate_command(args: argparse.Namespace) -> int:
    index_location = str(args.index or "").strip()
    try:
        payload, _ = read_registry_document(index_location)
    except CoursepackRegistryError as exc:
        if args.json:
            _print_json({"ok": False, "error": str(exc)})
        else:
            print("[coursepack-sdk] FAIL: registry validation error")
            print(f"  - {exc}")
        return 1

    errors = validate_registry_document(payload)
    payload_out = {
        "ok": not errors,
        "schema_version": payload.get("schema_version"),
        "entries": len(payload.get("entries") or []),
        "errors": errors,
    }
    if args.json:
        _print_json(payload_out)
    else:
        if errors:
            print("[coursepack-sdk] FAIL: registry index")
            for entry in errors:
                print(f"  - {entry}")
        else:
            print(f"[coursepack-sdk] OK: registry index ({payload_out['entries']} entries)")
    return 0 if not errors else 1


def _registry_list_command(args: argparse.Namespace) -> int:
    index_location = str(args.index or "").strip()
    try:
        payload, _ = read_registry_document(index_location)
    except CoursepackRegistryError as exc:
        if args.json:
            _print_json({"ok": False, "error": str(exc)})
        else:
            print("[coursepack-sdk] FAIL: registry list error")
            print(f"  - {exc}")
        return 1

    entries = payload.get("entries") or []
    if args.json:
        _print_json({"ok": True, "entries": entries})
    else:
        print(f"[coursepack-sdk] registry entries: {len(entries)}")
        for entry in entries:
            artifact = entry.get("artifact") or {}
            compatibility = entry.get("compatibility") or {}
            print(
                "  - "
                f"{entry.get('slug')}@{entry.get('version')} "
                f"[{entry.get('release_channel')}] "
                f"ui={compatibility.get('ui_level')} "
                f"profile={compatibility.get('program_profile')} "
                f"url={artifact.get('url')}"
            )
    return 0


def _registry_fetch_command(args: argparse.Namespace) -> int:
    index_location = str(args.index or "").strip()
    slug = str(args.course_slug or "").strip()
    version = str(args.version or "").strip()
    if not slug:
        print("[coursepack-sdk] FAIL: --course-slug is required", file=sys.stderr)
        return 1

    try:
        payload, source = read_registry_document(index_location)
        entry = select_registry_entry(payload, slug=slug, version=version)
        default_output = Path("dist") / "coursepacks" / str((entry.get("artifact") or {}).get("filename") or "")
        result = fetch_registry_artifact(
            source,
            entry,
            output_path=Path(args.output).expanduser() if args.output else default_output,
        )
    except CoursepackRegistryError as exc:
        if args.json:
            _print_json({"ok": False, "error": str(exc)})
        else:
            print("[coursepack-sdk] FAIL: registry fetch error")
            print(f"  - {exc}")
        return 1

    if args.json:
        _print_json({"ok": True, **result})
    else:
        print(f"[coursepack-sdk] OK: fetched {result['slug']}@{result['version']}")
        print(f"  artifact: {result['artifact']}")
        print(f"  bytes: {result['bytes']}")
        print(f"  sha256: {result['sha256']}")
        print(f"  checksum_file: {result['checksum_file']}")
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
    build_cmd.add_argument("--version", default="", help="Registry version tag (default: UTC timestamp)")
    build_cmd.add_argument("--release-channel", default="stable", help="Registry release channel (default: stable)")
    build_cmd.add_argument("--source-url", default="", help="Source URL/URI for registry entry")
    build_cmd.add_argument("--registry-index", default="", help="Create or update a registry index JSON file")
    build_cmd.add_argument("--artifact-url", default="", help="Artifact URL/path to store in registry entry")
    build_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    package_cmd = sub.add_parser("package", help="Package one coursepack without validation")
    package_cmd.add_argument("--course-slug", required=True, help="Course slug under content/courses")
    package_cmd.add_argument("--output", default="", help="Output zip path (default: dist/coursepacks/<slug>_<stamp>.zip)")
    package_cmd.add_argument("--version", default="", help="Registry version tag (default: UTC timestamp)")
    package_cmd.add_argument("--release-channel", default="stable", help="Registry release channel (default: stable)")
    package_cmd.add_argument("--source-url", default="", help="Source URL/URI for registry entry")
    package_cmd.add_argument("--registry-index", default="", help="Create or update a registry index JSON file")
    package_cmd.add_argument("--artifact-url", default="", help="Artifact URL/path to store in registry entry")
    package_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    registry_validate_cmd = sub.add_parser("registry-validate", help="Validate a coursepack registry index JSON file")
    registry_validate_cmd.add_argument("--index", required=True, help="Registry index path or URL")
    registry_validate_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    registry_list_cmd = sub.add_parser("registry-list", help="List entries in a coursepack registry index")
    registry_list_cmd.add_argument("--index", required=True, help="Registry index path or URL")
    registry_list_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

    registry_fetch_cmd = sub.add_parser("registry-fetch", help="Fetch and verify an artifact from a registry index")
    registry_fetch_cmd.add_argument("--index", required=True, help="Registry index path or URL")
    registry_fetch_cmd.add_argument("--course-slug", required=True, help="Course slug to fetch")
    registry_fetch_cmd.add_argument("--version", default="", help="Optional version to fetch (defaults to latest)")
    registry_fetch_cmd.add_argument("--output", default="", help="Output zip path (default: dist/coursepacks/<artifact filename>)")
    registry_fetch_cmd.add_argument("--json", action="store_true", help="Emit JSON report")

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
    if args.command == "registry-validate":
        return _registry_validate_command(args)
    if args.command == "registry-list":
        return _registry_list_command(args)
    if args.command == "registry-fetch":
        return _registry_fetch_command(args)
    print(f"[coursepack-sdk] FAIL: unknown command '{args.command}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
