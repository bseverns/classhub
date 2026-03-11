#!/usr/bin/env python3
"""Validate course.yaml + lesson markdown structure for Class Hub coursepacks."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


COURSES_ROOT = Path("services/classhub/content/courses")
COURSE_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
LESSON_SLUG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VIDEO_ID_RE = re.compile(r"^V\d+$")
VALID_UI_LEVELS = {"elementary", "secondary", "advanced"}
VALID_PROGRAM_PROFILES = {"elementary", "secondary", "advanced"}


def _yaml_error(exc: yaml.YAMLError) -> str:
    mark = getattr(exc, "problem_mark", None)
    if mark is None:
        return str(exc)
    return f"line {mark.line + 1}, col {mark.column + 1}: {exc}"


def _read_yaml_mapping(path: Path, errors: list[str], *, label: str) -> dict:
    if yaml is None:
        errors.append(
            "PyYAML is required (install classhub deps: `pip install -r services/classhub/requirements.txt`)"
        )
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive IO guard
        if yaml is not None and isinstance(exc, yaml.YAMLError):
            errors.append(f"{path}: invalid YAML in {label}: {_yaml_error(exc)}")
        else:
            errors.append(f"{path}: unable to read {label}: {exc}")
        return {}

    if payload is None:
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path}: {label} must be a YAML mapping/object")
        return {}
    return payload


def _validate_front_matter_colons(front_matter_text: str, lesson_path: Path, errors: list[str]) -> None:
    for lineno, line in enumerate(front_matter_text.splitlines(), start=1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        if ":" not in line:
            continue
        _, _, value = line.partition(":")
        value = value.strip()
        if not value:
            continue
        if value[0] in ('"', "'", "|", ">", "[", "{"):
            continue
        if ":" in value:
            errors.append(
                f"{lesson_path}:{lineno}: unquoted colon in front matter value: {line.strip()}"
            )


def _safe_course_path(course_dir: Path, rel_path: str, errors: list[str], *, ref: str) -> Path | None:
    rel = (rel_path or "").strip()
    if not rel:
        errors.append(f"{ref}: missing lesson file path")
        return None
    candidate = Path(rel)
    if candidate.is_absolute():
        errors.append(f"{ref}: lesson file must be relative, got absolute path '{rel}'")
        return None
    resolved = (course_dir / candidate).resolve()
    try:
        resolved.relative_to(course_dir.resolve())
    except ValueError:
        errors.append(f"{ref}: lesson file escapes course directory: '{rel}'")
        return None
    return resolved


def _validate_date(value: str, ref: str, errors: list[str]) -> None:
    text = (value or "").strip()
    if not text:
        return
    try:
        date.fromisoformat(text)
    except ValueError:
        errors.append(f"{ref}: invalid date '{text}' (expected YYYY-MM-DD)")


def _parse_lesson_front_matter(lesson_path: Path, errors: list[str]) -> tuple[dict, str]:
    if yaml is None:
        errors.append(
            "PyYAML is required (install classhub deps: `pip install -r services/classhub/requirements.txt`)"
        )
        return {}, ""
    raw = lesson_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        errors.append(f"{lesson_path}: missing front matter block (expected leading '---')")
        return {}, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{lesson_path}: unterminated front matter block")
        return {}, ""

    front_matter_text = parts[1]
    _validate_front_matter_colons(front_matter_text, lesson_path, errors)

    try:
        fm = yaml.safe_load(front_matter_text) or {}
    except Exception as exc:
        if yaml is not None and isinstance(exc, yaml.YAMLError):
            errors.append(f"{lesson_path}: invalid front matter YAML: {_yaml_error(exc)}")
        else:
            errors.append(f"{lesson_path}: unable to parse front matter YAML: {exc}")
        return {}, ""

    if not isinstance(fm, dict):
        errors.append(f"{lesson_path}: front matter must be a YAML mapping/object")
        return {}, ""

    body = parts[2].strip()
    if not body:
        errors.append(f"{lesson_path}: markdown body is empty after front matter")
    return fm, body


def _validate_videos(videos: object, ref: str, errors: list[str]) -> None:
    if videos is None:
        return
    if not isinstance(videos, list):
        errors.append(f"{ref}: 'videos' must be a list")
        return
    for idx, row in enumerate(videos, start=1):
        item_ref = f"{ref} videos[{idx}]"
        if not isinstance(row, dict):
            errors.append(f"{item_ref}: video entry must be a mapping")
            continue
        vid = str(row.get("id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not vid:
            errors.append(f"{item_ref}: missing required field 'id'")
        elif not VIDEO_ID_RE.fullmatch(vid):
            errors.append(f"{item_ref}: invalid video id '{vid}' (expected pattern like V01)")
        if not title:
            errors.append(f"{item_ref}: missing required field 'title'")


def _iter_markdown_link_targets(markdown: str):
    """Yield raw markdown link targets from inline links/images.

    This uses bounded linear scanning instead of a complex regex to keep behavior
    predictable on untrusted text.
    """
    idx = 0
    while idx < len(markdown):
        marker = markdown.find("](", idx)
        if marker < 0:
            break
        target_start = marker + 2
        target_end = target_start
        while target_end < len(markdown):
            ch = markdown[target_end]
            if ch == ")" and (target_end == target_start or markdown[target_end - 1] != "\\"):
                break
            target_end += 1
        if target_end >= len(markdown):
            break
        target = markdown[target_start:target_end].strip()
        if target:
            yield target
        idx = target_end + 1


def _normalize_link_target(raw: str) -> str:
    token = str(raw or "").strip()
    if not token:
        return ""
    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1].strip()
    if not token:
        return ""
    for sep in (" ", "\t"):
        split_idx = token.find(sep)
        if split_idx > 0:
            token = token[:split_idx].strip()
            break
    if "#" in token:
        token = token.split("#", 1)[0].strip()
    if "?" in token:
        token = token.split("?", 1)[0].strip()
    return token


def _validate_body_links(*, body: str, lesson_path: Path, course_dir: Path, errors: list[str]) -> None:
    for raw_target in _iter_markdown_link_targets(body):
        target = _normalize_link_target(raw_target)
        if not target:
            continue
        lower_target = target.lower()
        if target.startswith("#") or lower_target.startswith(("mailto:", "tel:", "data:")):
            continue
        if target.startswith("/"):
            # Absolute app paths are runtime routes, not local content files.
            continue
        parsed = urlsplit(target)
        if parsed.scheme:
            continue
        target_path = Path(target)
        if target_path.is_absolute():
            errors.append(f"{lesson_path}: markdown link target must be relative: '{target}'")
            continue
        resolved = (lesson_path.parent / target_path).resolve()
        try:
            resolved.relative_to(course_dir.resolve())
        except ValueError:
            errors.append(f"{lesson_path}: markdown link escapes course directory: '{target}'")
            continue
        if not resolved.exists():
            errors.append(f"{lesson_path}: markdown link target not found: '{target}'")


def validate_coursepack(course_dir: Path) -> list[str]:
    errors: list[str] = []
    course_slug = course_dir.name
    manifest_path = course_dir / "course.yaml"

    if not manifest_path.exists():
        return [f"{manifest_path}: missing course manifest"]

    manifest = _read_yaml_mapping(manifest_path, errors, label="course manifest")

    manifest_slug = str(manifest.get("slug") or "").strip()
    manifest_title = str(manifest.get("title") or "").strip()

    if not manifest_slug:
        errors.append(f"{manifest_path}: missing required top-level field 'slug'")
    elif not COURSE_SLUG_RE.fullmatch(manifest_slug):
        errors.append(f"{manifest_path}: invalid slug '{manifest_slug}'")
    elif manifest_slug != course_slug:
        errors.append(
            f"{manifest_path}: slug '{manifest_slug}' does not match folder name '{course_slug}'"
        )

    if not manifest_title:
        errors.append(f"{manifest_path}: missing required top-level field 'title'")

    ui_level = str(manifest.get("ui_level") or "").strip().lower()
    if not ui_level:
        errors.append(f"{manifest_path}: missing required top-level field 'ui_level'")
    elif ui_level not in VALID_UI_LEVELS:
        errors.append(
            f"{manifest_path}: invalid ui_level '{ui_level}' (expected one of: {', '.join(sorted(VALID_UI_LEVELS))})"
        )

    program_profile = str(manifest.get("program_profile") or "").strip().lower()
    if program_profile and program_profile not in VALID_PROGRAM_PROFILES:
        errors.append(
            f"{manifest_path}: invalid program_profile '{program_profile}' "
            f"(expected one of: {', '.join(sorted(VALID_PROGRAM_PROFILES))})"
        )

    lessons = manifest.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        errors.append(f"{manifest_path}: 'lessons' must be a non-empty list")
        return errors

    seen_lesson_slugs: set[str] = set()
    seen_files: set[str] = set()
    seen_sessions: set[int] = set()

    for idx, lesson in enumerate(lessons, start=1):
        ref = f"{manifest_path}: lessons[{idx}]"
        if not isinstance(lesson, dict):
            errors.append(f"{ref}: lesson entry must be a mapping")
            continue

        lesson_slug = str(lesson.get("slug") or "").strip()
        lesson_title = str(lesson.get("title") or "").strip()
        lesson_file = str(lesson.get("file") or "").strip()
        lesson_session = lesson.get("session")

        if not lesson_slug:
            errors.append(f"{ref}: missing required field 'slug'")
        elif not LESSON_SLUG_RE.fullmatch(lesson_slug):
            errors.append(f"{ref}: invalid lesson slug '{lesson_slug}'")
        elif lesson_slug in seen_lesson_slugs:
            errors.append(f"{ref}: duplicate lesson slug '{lesson_slug}'")
        else:
            seen_lesson_slugs.add(lesson_slug)

        if not lesson_title:
            errors.append(f"{ref}: missing required field 'title'")

        if not lesson_file:
            errors.append(f"{ref}: missing required field 'file'")
        else:
            if lesson_file in seen_files:
                errors.append(f"{ref}: duplicate lesson file path '{lesson_file}'")
            else:
                seen_files.add(lesson_file)

            if not lesson_file.endswith(".md"):
                errors.append(f"{ref}: lesson file must end with .md (got '{lesson_file}')")

            lesson_file_path = Path(lesson_file)
            if not lesson_file_path.parts or lesson_file_path.parts[0] != "lessons":
                errors.append(f"{ref}: lesson file should live under lessons/ (got '{lesson_file}')")

        if lesson_session is not None:
            if not isinstance(lesson_session, int) or lesson_session <= 0:
                errors.append(f"{ref}: 'session' must be a positive integer when provided")
            elif lesson_session in seen_sessions:
                errors.append(f"{ref}: duplicate session number {lesson_session}")
            else:
                seen_sessions.add(lesson_session)

        if "available_on" in lesson:
            _validate_date(str(lesson.get("available_on") or ""), f"{ref} available_on", errors)

        _validate_videos(lesson.get("videos"), ref, errors)

        lesson_ui_level = str(lesson.get("ui_level") or "").strip().lower()
        if lesson_ui_level and lesson_ui_level not in VALID_UI_LEVELS:
            errors.append(
                f"{ref}: invalid ui_level '{lesson_ui_level}' "
                f"(expected one of: {', '.join(sorted(VALID_UI_LEVELS))})"
            )

        lesson_program_profile = str(lesson.get("program_profile") or "").strip().lower()
        if lesson_program_profile and lesson_program_profile not in VALID_PROGRAM_PROFILES:
            errors.append(
                f"{ref}: invalid program_profile '{lesson_program_profile}' "
                f"(expected one of: {', '.join(sorted(VALID_PROGRAM_PROFILES))})"
            )

        resolved = _safe_course_path(course_dir, lesson_file, errors, ref=ref)
        if resolved is None:
            continue
        if not resolved.exists():
            errors.append(f"{ref}: lesson file not found at '{lesson_file}'")
            continue

        fm, body = _parse_lesson_front_matter(resolved, errors)
        if not fm:
            continue

        fm_slug = str(fm.get("slug") or "").strip()
        fm_title = str(fm.get("title") or "").strip()
        fm_session = fm.get("session")
        fm_course = str(fm.get("course") or "").strip()
        fm_course_slug = str(fm.get("course_slug") or "").strip()

        if not fm_slug:
            errors.append(f"{resolved}: front matter missing required field 'slug'")
        elif lesson_slug and fm_slug != lesson_slug:
            errors.append(
                f"{resolved}: front matter slug '{fm_slug}' does not match manifest slug '{lesson_slug}'"
            )

        if not fm_title:
            errors.append(f"{resolved}: front matter missing required field 'title'")

        if fm_course and fm_course_slug and fm_course != fm_course_slug:
            errors.append(
                f"{resolved}: front matter 'course' ('{fm_course}') does not match "
                f"'course_slug' ('{fm_course_slug}')"
            )

        effective_course_slug = fm_course_slug or fm_course
        if not effective_course_slug:
            errors.append(f"{resolved}: front matter missing required field 'course' (or 'course_slug')")
        elif not COURSE_SLUG_RE.fullmatch(effective_course_slug):
            errors.append(
                f"{resolved}: front matter course slug '{effective_course_slug}' is invalid "
                "(expected letters/numbers/_/- only)"
            )
        elif effective_course_slug != course_slug:
            errors.append(
                f"{resolved}: front matter course slug '{effective_course_slug}' does not match "
                f"course folder/manifest slug '{course_slug}'"
            )

        if lesson_session is not None and fm_session is not None and fm_session != lesson_session:
            errors.append(
                f"{resolved}: front matter session '{fm_session}' does not match manifest session '{lesson_session}'"
            )

        if "available_on" in fm:
            _validate_date(str(fm.get("available_on") or ""), f"{resolved} front matter available_on", errors)

        _validate_videos(fm.get("videos"), str(resolved), errors)
        _validate_body_links(body=body, lesson_path=resolved, course_dir=course_dir, errors=errors)

        fm_ui_level = str(fm.get("ui_level") or "").strip().lower()
        if fm_ui_level and fm_ui_level not in VALID_UI_LEVELS:
            errors.append(
                f"{resolved}: front matter invalid ui_level '{fm_ui_level}' "
                f"(expected one of: {', '.join(sorted(VALID_UI_LEVELS))})"
            )

        fm_program_profile = str(fm.get("program_profile") or "").strip().lower()
        if fm_program_profile and fm_program_profile not in VALID_PROGRAM_PROFILES:
            errors.append(
                f"{resolved}: front matter invalid program_profile '{fm_program_profile}' "
                f"(expected one of: {', '.join(sorted(VALID_PROGRAM_PROFILES))})"
            )

    return errors


def _find_course_dirs(*, course_slug: str | None, validate_all: bool) -> list[Path]:
    if validate_all:
        return sorted(p for p in COURSES_ROOT.iterdir() if p.is_dir())
    if course_slug:
        return [COURSES_ROOT / course_slug]

    default_slug = "piper_scratch_12_session"
    return [COURSES_ROOT / default_slug]


def main() -> int:
    if yaml is None:
        print(
            "[coursepack] FAIL: PyYAML is required (install classhub deps: "
            "`pip install -r services/classhub/requirements.txt`)",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug_positional", nargs="?", default="", help="Course slug (folder name)")
    parser.add_argument("--course-slug", dest="slug_option", default="", help="Course slug (same as positional arg)")
    parser.add_argument("--all", action="store_true", help="Validate all course folders under content/courses")
    args = parser.parse_args()

    if not COURSES_ROOT.exists():
        print(f"[coursepack] FAIL: courses root not found: {COURSES_ROOT}", file=sys.stderr)
        return 1

    slug = (args.slug_option or args.slug_positional or "").strip()
    if slug and args.all:
        print("[coursepack] FAIL: use either --all or a course slug, not both", file=sys.stderr)
        return 1

    course_dirs = _find_course_dirs(course_slug=slug, validate_all=args.all)
    errors: list[str] = []

    for course_dir in course_dirs:
        if not course_dir.exists():
            errors.append(f"{course_dir}: course directory not found")
            continue
        if not course_dir.is_dir():
            errors.append(f"{course_dir}: expected a directory")
            continue

        course_errors = validate_coursepack(course_dir)
        if course_errors:
            errors.extend(course_errors)
        else:
            print(f"[coursepack] OK: {course_dir.name}")

    if errors:
        print("[coursepack] FAIL:", file=sys.stderr)
        for entry in errors:
            print(f"  - {entry}", file=sys.stderr)
        return 1

    print("[coursepack] ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
