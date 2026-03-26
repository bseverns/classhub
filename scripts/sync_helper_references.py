#!/usr/bin/env python3
"""Synchronize helper reference files for one or more course manifests.

Safe defaults:
- scans all `content/courses/*/course.yaml` manifests when no course is specified,
- preserves existing course-level reference files unless explicitly overwritten,
- generates lesson reference files only for lessons whose `helper_reference`
  differs from the course-level `helper_reference`.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - CLI dependency guard
    print(
        "[helper-ref-sync] FAIL: PyYAML is required. "
        "Run this from the project Python environment or install repo deps first.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from generate_lesson_references import SAFE_KEY_RE, generate_reference_text


COURSES_ROOT = Path("services/classhub/content/courses")
DEFAULT_OUT_DIR = Path("services/homework_helper/tutor/reference")


@dataclass(frozen=True)
class PlannedWrite:
    key: str
    path: Path
    content: str
    source: str
    kind: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--course",
        action="append",
        default=[],
        help="Explicit path(s) to course.yaml to process.",
    )
    parser.add_argument(
        "--course-slug",
        action="append",
        default=[],
        help="Process only one or more course folder slugs under content/courses.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT_DIR),
        help=f"Output directory for helper reference markdown (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--overwrite-course-refs",
        action="store_true",
        help="Replace existing course-level reference files instead of preserving them.",
    )
    parser.add_argument(
        "--all-lesson-refs",
        action="store_true",
        help=(
            "Generate one lesson reference file for every lesson slug, even when the "
            "manifest routes that lesson to the shared course reference."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned writes without touching the filesystem.",
    )
    return parser.parse_args()


def _iter_course_manifests(*, explicit_paths: list[str], course_slugs: list[str]) -> list[Path]:
    manifests: list[Path] = []
    seen: set[Path] = set()

    for raw in explicit_paths:
        path = Path(raw).resolve()
        if path not in seen:
            manifests.append(path)
            seen.add(path)

    if course_slugs:
        for slug in course_slugs:
            path = (COURSES_ROOT / slug / "course.yaml").resolve()
            if path not in seen:
                manifests.append(path)
                seen.add(path)
        return manifests

    if manifests:
        return manifests

    if not COURSES_ROOT.exists():
        return []

    for path in sorted(COURSES_ROOT.glob("*/course.yaml")):
        resolved = path.resolve()
        if resolved not in seen:
            manifests.append(resolved)
            seen.add(resolved)
    return manifests


def _safe_reference_key(raw: str, *, context: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    if not SAFE_KEY_RE.match(value):
        raise ValueError(f"{context}: invalid helper reference key '{value}'")
    return value


def _render_course_reference(*, manifest: dict, course_slug: str) -> str:
    title = str(manifest.get("title") or course_slug).strip()
    sessions = manifest.get("sessions")
    duration = manifest.get("default_duration_minutes")
    ui_level = str(manifest.get("ui_level") or "").strip()
    program_profile = str(manifest.get("program_profile") or "").strip()
    grade_band = str(manifest.get("grade_band") or "").strip()
    age_band = str(manifest.get("age_band") or "").strip()
    needs = list(manifest.get("needs") or [])
    privacy = list(manifest.get("privacy") or [])
    lessons = list(manifest.get("lessons") or [])

    lines: list[str] = []
    lines.append(f"# Reference: {course_slug}")
    lines.append("")
    lines.append("## Course summary")
    lines.append(f"- Title: {title}")
    lines.append(f"- Course slug: {course_slug}")
    if sessions:
        lines.append(f"- Sessions: {sessions}")
    if duration:
        lines.append(f"- Default duration: {duration} minutes")
    if ui_level:
        lines.append(f"- UI level: {ui_level}")
    if program_profile:
        lines.append(f"- Program profile: {program_profile}")
    if grade_band:
        lines.append(f"- Grade band: {grade_band}")
    if age_band:
        lines.append(f"- Age band: {age_band}")

    if needs:
        lines.append("")
        lines.append("## Materials and environment")
        for item in needs:
            text = str(item or "").strip()
            if text:
                lines.append(f"- {text}")

    if privacy:
        lines.append("")
        lines.append("## Privacy and classroom boundaries")
        for item in privacy:
            text = str(item or "").strip()
            if text:
                lines.append(f"- {text}")

    if lessons:
        lines.append("")
        lines.append("## Lesson progression")
        for lesson in lessons:
            session = lesson.get("session")
            lesson_title = str(lesson.get("title") or lesson.get("slug") or "").strip()
            if not lesson_title:
                continue
            if session is None:
                lines.append(f"- {lesson_title}")
            else:
                lines.append(f"- Session {session}: {lesson_title}")

    lines.append("")
    lines.append("## Helper response posture")
    lines.append("- Keep the answer tied to the current lesson goal and classroom tools.")
    lines.append("- Prefer one diagnostic or coaching step at a time, then ask what happened.")
    lines.append("- Use course vocabulary and routines instead of generic tutoring language.")
    lines.append("- Do not request or infer student personal information.")
    lines.append("")
    return "\n".join(lines)


def _plan_course_reference(
    *,
    manifest: dict,
    course_slug: str,
    out_dir: Path,
    overwrite_existing: bool,
) -> PlannedWrite | None:
    course_key = _safe_reference_key(
        str(manifest.get("helper_reference") or ""),
        context=f"{course_slug} course.yaml",
    )
    if not course_key:
        return None

    path = out_dir / f"{course_key}.md"
    if path.exists() and not overwrite_existing:
        return None

    content = _render_course_reference(manifest=manifest, course_slug=course_slug)
    return PlannedWrite(
        key=course_key,
        path=path,
        content=content,
        source=f"{course_slug}:course",
        kind="course",
    )


def _plan_lesson_references(
    *,
    manifest: dict,
    course_path: Path,
    out_dir: Path,
    all_lesson_refs: bool,
) -> list[PlannedWrite]:
    course_slug = course_path.parent.name
    course_key = _safe_reference_key(
        str(manifest.get("helper_reference") or ""),
        context=f"{course_slug} course.yaml",
    )
    course_dir = course_path.parent
    planned: list[PlannedWrite] = []

    for lesson in list(manifest.get("lessons") or []):
        lesson_slug = str(lesson.get("slug") or "").strip()
        if not lesson_slug:
            continue

        if all_lesson_refs:
            target_key = _safe_reference_key(lesson_slug, context=f"{course_slug}/{lesson_slug}")
        else:
            target_key = _safe_reference_key(
                str(lesson.get("helper_reference") or ""),
                context=f"{course_slug}/{lesson_slug}",
            )
            if not target_key or target_key == course_key:
                continue

        _, content = generate_reference_text(lesson_meta=lesson, course_dir=course_dir)
        planned.append(
            PlannedWrite(
                key=target_key,
                path=out_dir / f"{target_key}.md",
                content=content,
                source=f"{course_slug}:{lesson_slug}",
                kind="lesson",
            )
        )
    return planned


def _register_write(plan: PlannedWrite, *, seen_keys: dict[str, str]) -> None:
    previous = seen_keys.get(plan.key)
    if previous and previous != plan.source:
        raise ValueError(
            "duplicate helper reference key "
            f"'{plan.key}' requested by both '{previous}' and '{plan.source}'"
        )
    seen_keys[plan.key] = plan.source


def main() -> int:
    args = _parse_args()
    manifests = _iter_course_manifests(explicit_paths=args.course, course_slugs=args.course_slug)
    out_dir = Path(args.out)

    if not manifests:
        print("[helper-ref-sync] FAIL: no course manifests found", file=sys.stderr)
        return 1

    plans: list[PlannedWrite] = []
    seen_keys: dict[str, str] = {}
    preserved_course_refs = 0

    for course_path in manifests:
        if not course_path.exists():
            print(f"[helper-ref-sync] FAIL: missing course manifest: {course_path}", file=sys.stderr)
            return 1

        try:
            manifest = yaml.safe_load(course_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            print(f"[helper-ref-sync] FAIL: unable to read {course_path}: {exc}", file=sys.stderr)
            return 1

        course_slug = course_path.parent.name
        try:
            course_plan = _plan_course_reference(
                manifest=manifest,
                course_slug=course_slug,
                out_dir=out_dir,
                overwrite_existing=args.overwrite_course_refs,
            )
            if course_plan is None:
                course_key = str(manifest.get("helper_reference") or "").strip()
                if course_key and (out_dir / f"{course_key}.md").exists():
                    preserved_course_refs += 1
            else:
                _register_write(course_plan, seen_keys=seen_keys)
                plans.append(course_plan)

            for lesson_plan in _plan_lesson_references(
                manifest=manifest,
                course_path=course_path,
                out_dir=out_dir,
                all_lesson_refs=args.all_lesson_refs,
            ):
                _register_write(lesson_plan, seen_keys=seen_keys)
                plans.append(lesson_plan)
        except Exception as exc:
            print(f"[helper-ref-sync] FAIL: {exc}", file=sys.stderr)
            return 1

    if args.dry_run:
        print(
            "[helper-ref-sync] DRY RUN "
            f"course_manifests={len(manifests)} planned_writes={len(plans)} preserved_course_refs={preserved_course_refs}"
        )
        for plan in plans:
            print(f"  - {plan.kind}: {plan.path} <- {plan.source}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for plan in plans:
        plan.path.write_text(plan.content, encoding="utf-8")
        written += 1

    print(
        "[helper-ref-sync] OK "
        f"course_manifests={len(manifests)} written={written} preserved_course_refs={preserved_course_refs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
