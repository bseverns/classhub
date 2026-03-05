"""Import a repo-authored course pack into the DB as Modules + Materials.

Why this exists:
- Curriculum should be versioned in git (content/courses/...)
- The DB should only be an index + per-class ordering

Usage:
  python manage.py import_coursepack --course-slug piper_scratch_12_session --create-class

Or target an existing class:
  python manage.py import_coursepack --course-slug piper_scratch_12_session --class-code ABCD1234 --replace

Notes:
- This command creates one Module per lesson session.
- Each module gets a link material that points to the markdown renderer route:
    /course/<course_slug>/<lesson_slug>
"""

from __future__ import annotations

from pathlib import Path

import yaml
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils._os import safe_join

from hub.models import Class, LessonAsset, LessonAssetFolder, Material, Module

_SUPPORT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _courses_dir() -> Path:
    return Path(getattr(settings, "CONTENT_ROOT", Path.cwd() / "content")) / "courses"


def _load_manifest(course_slug: str) -> dict:
    manifest_path = _courses_dir() / course_slug / "course.yaml"
    if not manifest_path.exists():
        raise CommandError(f"Course manifest not found: {manifest_path}")
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}


def _read_front_matter(course_slug: str, rel_path: str) -> dict:
    course_dir = (_courses_dir() / course_slug).resolve()
    try:
        joined = safe_join(str(course_dir), str(rel_path or ""))
    except Exception:
        return {}
    lesson_path = Path(joined).resolve()
    if not lesson_path.is_relative_to(course_dir):
        return {}
    if not lesson_path.exists():
        return {}
    raw = lesson_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _normalize_submission_extensions(submission: dict, naming: str) -> list[str]:
    accepted = submission.get("accepted") or []
    if isinstance(accepted, str):
        accepted = [p.strip() for p in accepted.replace("|", ",").split(",") if p.strip()]

    exts = []
    for raw in accepted:
        ext = str(raw).strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        if ext not in exts:
            exts.append(ext)

    if not exts and naming:
        maybe_ext = Path(naming).suffix.strip().lower()
        if maybe_ext.startswith("."):
            exts.append(maybe_ext)

    return exts


def _normalize_support_image_paths(raw_value) -> list[str]:
    rows = raw_value if isinstance(raw_value, list) else ([raw_value] if isinstance(raw_value, str) else [])
    output: list[str] = []
    for row in rows:
        rel = str(row or "").strip().replace("\\", "/")
        if not rel or rel.startswith("/"):
            continue
        if rel not in output:
            output.append(rel)
    return output


def _safe_course_file(course_slug: str, rel_path: str) -> Path | None:
    course_dir = (_courses_dir() / course_slug).resolve()
    rel = str(rel_path or "").strip()
    if not rel:
        return None
    try:
        joined = safe_join(str(course_dir), rel)
    except Exception:
        return None
    candidate = Path(joined).resolve()
    if not candidate.is_relative_to(course_dir):
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    if candidate.suffix.lower() not in _SUPPORT_IMAGE_EXTENSIONS:
        return None
    return candidate


def _title_from_filename(filename: str) -> str:
    stem = Path(str(filename or "").strip()).stem
    text = " ".join(stem.replace("_", " ").replace("-", " ").split())
    return text.title() if text else "Support Image"


def _upsert_lesson_support_asset(
    *,
    folder: LessonAssetFolder,
    course_slug: str,
    lesson_slug: str,
    source_path: Path,
) -> LessonAsset:
    original_name = source_path.name[:255]
    existing = LessonAsset.objects.filter(
        folder=folder,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
        original_filename=original_name,
    ).first()
    with source_path.open("rb") as stream:
        payload = File(stream, name=source_path.name)
        if existing:
            existing.title = _title_from_filename(source_path.name)[:200]
            existing.description = "Imported from syllabus source zip."
            existing.is_active = True
            existing.file.save(source_path.name, payload, save=False)
            existing.save(
                update_fields=[
                    "title",
                    "description",
                    "is_active",
                    "file",
                    "updated_at",
                ]
            )
            return existing
        return LessonAsset.objects.create(
            folder=folder,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            title=_title_from_filename(source_path.name)[:200],
            description="Imported from syllabus source zip.",
            original_filename=original_name,
            file=payload,
            is_active=True,
        )


class Command(BaseCommand):
    help = "Import a repo-authored course pack into Modules + Materials."

    def add_arguments(self, parser):
        parser.add_argument("--course-slug", default="piper_scratch_12_session")

        group = parser.add_mutually_exclusive_group()
        group.add_argument("--class-code", default="")
        group.add_argument("--class-name", default="")

        parser.add_argument(
            "--create-class",
            action="store_true",
            help="Create a new Class if it does not exist (uses course title by default).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing modules/materials for the class before importing.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        course_slug = opts["course_slug"]
        manifest = _load_manifest(course_slug)

        lessons = manifest.get("lessons") or []
        if not lessons:
            raise CommandError("Manifest has no lessons.")

        # Resolve/construct Class
        classroom = None
        if opts.get("class_code"):
            classroom = Class.objects.filter(join_code=opts["class_code"].strip().upper()).first()
            if not classroom:
                raise CommandError("No class found for that code. Create one in /admin or use --create-class.")
        elif opts.get("class_name"):
            classroom = Class.objects.filter(name=opts["class_name"].strip()).first()
            if not classroom and not opts.get("create_class"):
                raise CommandError("No class found for that name. Use --create-class to create it.")
            if not classroom:
                classroom = Class.objects.create(name=opts["class_name"].strip())
        else:
            # Default: class name = course title
            default_name = (manifest.get("title") or course_slug).strip()
            classroom = Class.objects.filter(name=default_name).first()
            if not classroom and not opts.get("create_class"):
                raise CommandError(
                    "No class found for course title. Use --create-class, or specify --class-code / --class-name."
                )
            if not classroom:
                classroom = Class.objects.create(name=default_name)

        if opts.get("replace"):
            classroom.modules.all().delete()

        # Import
        created_modules = 0
        created_materials = 0
        created_assets = 0
        support_folder = LessonAssetFolder.objects.get_or_create(
            path=f"coursepack/{course_slug}",
            defaults={"display_name": f"{course_slug} imported support"},
        )[0]

        for l in lessons:
            session = int(l.get("session") or 0)
            lesson_slug = (l.get("slug") or "").strip()
            title = (l.get("title") or lesson_slug).strip()
            rel_path = (l.get("file") or "").strip()

            if not lesson_slug or not rel_path:
                continue

            module_title = f"Session {session}: {title}" if session else title
            mod = Module.objects.create(classroom=classroom, title=module_title, order_index=session)
            created_modules += 1

            # Main lesson link
            Material.objects.create(
                module=mod,
                title="Open lesson",
                type=Material.TYPE_LINK,
                url=f"/course/{course_slug}/{lesson_slug}",
                order_index=0,
            )
            created_materials += 1

            # Quick-glance summary (text)
            fm = _read_front_matter(course_slug, rel_path)
            makes = (fm.get("makes") or "").strip()
            submission = fm.get("submission") or {}
            naming = (submission.get("naming") or "").strip()
            submission_type = str(submission.get("type") or "").strip().lower()
            exts = _normalize_submission_extensions(submission, naming)
            support_image_paths = _normalize_support_image_paths(fm.get("support_images"))

            # If the lesson expects a file submission, add a built-in dropbox.
            # This lets students submit privately from the lesson itself.
            if submission_type == "file":
                Material.objects.create(
                    module=mod,
                    title="Homework dropbox",
                    type=Material.TYPE_UPLOAD,
                    accepted_extensions=",".join(exts or [".sb3"]),
                    max_upload_mb=50,
                    order_index=2,
                )
                created_materials += 1

            summary_lines = []
            if makes:
                summary_lines.append(f"Makes: {makes}")
            if naming:
                summary_lines.append(f"Submit: {naming}")
            elif exts:
                summary_lines.append(f"Submit: {', '.join(exts)}")

            if summary_lines:
                Material.objects.create(
                    module=mod,
                    title="Today at a glance",
                    type=Material.TYPE_TEXT,
                    body="\n".join(summary_lines),
                    order_index=1,
                )
                created_materials += 1

            support_order_index = 10
            for rel_image_path in support_image_paths:
                source_path = _safe_course_file(course_slug, rel_image_path)
                if source_path is None:
                    continue
                asset = _upsert_lesson_support_asset(
                    folder=support_folder,
                    course_slug=course_slug,
                    lesson_slug=lesson_slug,
                    source_path=source_path,
                )
                created_assets += 1
                Material.objects.create(
                    module=mod,
                    title=f"Support image: {asset.title}",
                    type=Material.TYPE_LINK,
                    url=f"/lesson-asset/{asset.id}/download",
                    order_index=support_order_index,
                )
                created_materials += 1
                support_order_index += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported course '{course_slug}' into class '{classroom.name}' ({classroom.join_code}). "
            f"Modules: {created_modules}, materials: {created_materials}, support assets: {created_assets}."
        ))
