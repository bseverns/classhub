"""Live coursepack import helpers for admin/management workflows."""

from __future__ import annotations

import shutil
import uuid
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath

import yaml
from django.conf import settings
from django.core.files import File
from django.db import transaction
from django.utils._os import safe_join

from hub.models import Class, LessonAsset, LessonAssetFolder, Material, Module, Organization
from hub.services.syllabus_ingest_contracts import COURSE_SLUG_RE
from hub.services.syllabus_ingest import SyllabusIngestError, ingest_uploaded_syllabus

_SUPPORT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MAX_ZIP_FILES = 500
_MAX_EXTRACTED_BYTES = 50 * 1024 * 1024


class CoursepackImportError(Exception):
    """Raised when a coursepack cannot be safely imported."""


@dataclass(frozen=True)
class CoursepackImportResult:
    course_slug: str
    course_title: str
    classroom: Class
    course_dir: Path
    created_modules: int
    created_materials: int
    created_assets: int
    extracted_files: int = 0
    source_kind: str = "coursepack_zip"
    source_files: tuple[str, ...] = ()


def courses_dir() -> Path:
    return Path(getattr(settings, "CONTENT_ROOT", Path.cwd() / "content")) / "courses"


def _load_manifest(course_slug: str) -> dict:
    if not COURSE_SLUG_RE.fullmatch(str(course_slug or "")):
        raise CoursepackImportError("Course slug can use lowercase letters, numbers, underscores, and dashes.")
    manifest_path = courses_dir() / course_slug / "course.yaml"
    if not manifest_path.exists():
        raise CoursepackImportError(f"Course manifest not found: {manifest_path}")
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}


def _read_front_matter(course_slug: str, rel_path: str) -> dict:
    course_dir = (courses_dir() / course_slug).resolve()
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
    course_dir = (courses_dir() / course_slug).resolve()
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


def _resolve_classroom(
    *,
    manifest: dict,
    class_code: str = "",
    class_name: str = "",
    create_class: bool = False,
    organization: Organization | None = None,
) -> Class:
    class_code = str(class_code or "").strip().upper()
    class_name = str(class_name or "").strip()

    if class_code and class_name:
        raise CoursepackImportError("Use class code or class name, not both.")

    classroom = None
    if class_code:
        classroom = Class.objects.filter(join_code=class_code).first()
        if not classroom:
            raise CoursepackImportError("No class found for that code. Create one first or use create class.")
    elif class_name:
        classroom = Class.objects.filter(name=class_name).first()
        if not classroom and not create_class:
            raise CoursepackImportError("No class found for that name. Enable create class to create it.")
        if not classroom:
            classroom = Class.objects.create(name=class_name, organization=organization)
    else:
        default_name = (manifest.get("title") or manifest.get("slug") or "Imported Course").strip()
        classroom = Class.objects.filter(name=default_name).first()
        if not classroom and not create_class:
            raise CoursepackImportError(
                "No class found for course title. Enable create class, or specify class code / class name."
            )
        if not classroom:
            classroom = Class.objects.create(name=default_name, organization=organization)

    if organization and classroom.organization_id is None:
        classroom.organization = organization
        classroom.save(update_fields=["organization"])
    return classroom


@transaction.atomic
def import_coursepack_to_class(
    *,
    course_slug: str,
    class_code: str = "",
    class_name: str = "",
    create_class: bool = False,
    replace: bool = False,
    organization: Organization | None = None,
) -> CoursepackImportResult:
    course_slug = str(course_slug or "").strip()
    manifest = _load_manifest(course_slug)
    lessons = manifest.get("lessons") or []
    if not lessons:
        raise CoursepackImportError("Manifest has no lessons.")

    classroom = _resolve_classroom(
        manifest=manifest,
        class_code=class_code,
        class_name=class_name,
        create_class=create_class,
        organization=organization,
    )

    if replace:
        classroom.modules.all().delete()

    created_modules = 0
    created_materials = 0
    created_assets = 0
    support_folder = LessonAssetFolder.objects.get_or_create(
        path=f"coursepack/{course_slug}",
        defaults={"display_name": f"{course_slug} imported support"},
    )[0]

    for lesson in lessons:
        session = int(lesson.get("session") or 0)
        lesson_slug = (lesson.get("slug") or "").strip()
        title = (lesson.get("title") or lesson_slug).strip()
        rel_path = (lesson.get("file") or "").strip()

        if not lesson_slug or not rel_path:
            continue

        module_title = f"Session {session}: {title}" if session else title
        mod = Module.objects.create(classroom=classroom, title=module_title, order_index=session)
        created_modules += 1

        Material.objects.create(
            module=mod,
            title="Open lesson",
            type=Material.TYPE_LINK,
            url=f"/course/{course_slug}/{lesson_slug}",
            order_index=0,
        )
        created_materials += 1

        fm = _read_front_matter(course_slug, rel_path)
        makes = (fm.get("makes") or "").strip()
        submission = fm.get("submission") or {}
        naming = (submission.get("naming") or "").strip()
        submission_type = str(submission.get("type") or "").strip().lower()
        exts = _normalize_submission_extensions(submission, naming)
        support_image_paths = _normalize_support_image_paths(fm.get("support_images"))

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

    return CoursepackImportResult(
        course_slug=course_slug,
        course_title=(manifest.get("title") or course_slug).strip(),
        classroom=classroom,
        course_dir=courses_dir() / course_slug,
        created_modules=created_modules,
        created_materials=created_materials,
        created_assets=created_assets,
    )


def _zip_member_path(raw_name: str) -> PurePosixPath | None:
    name = str(raw_name or "").replace("\\", "/")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path


def _find_manifest_root(infos: list[zipfile.ZipInfo]) -> PurePosixPath:
    manifest_paths = []
    for info in infos:
        if info.is_dir():
            continue
        path = _zip_member_path(info.filename)
        if path and path.name == "course.yaml":
            manifest_paths.append(path)
    if not manifest_paths:
        raise CoursepackImportError("Coursepack ZIP must contain exactly one course.yaml file.")
    if len(manifest_paths) > 1:
        raise CoursepackImportError("Coursepack ZIP has multiple course.yaml files; upload one course at a time.")
    return manifest_paths[0].parent


def _load_manifest_from_zip(archive: zipfile.ZipFile, manifest_root: PurePosixPath) -> dict:
    manifest_name = "course.yaml" if str(manifest_root) == "." else f"{manifest_root}/course.yaml"
    try:
        raw = archive.read(manifest_name)
    except KeyError as exc:
        raise CoursepackImportError("Coursepack ZIP manifest could not be read.") from exc
    manifest = yaml.safe_load(raw.decode("utf-8")) or {}
    slug = str(manifest.get("slug") or "").strip()
    if not slug:
        raise CoursepackImportError("course.yaml must include a slug.")
    if not COURSE_SLUG_RE.fullmatch(slug):
        raise CoursepackImportError("Course slug can use lowercase letters, numbers, underscores, and dashes.")
    if not manifest.get("lessons"):
        raise CoursepackImportError("course.yaml must include at least one lesson.")
    return manifest


def _safe_extract_coursepack_zip(*, source_bytes: bytes, overwrite_content: bool) -> tuple[str, Path, int]:
    if not source_bytes:
        raise CoursepackImportError("Uploaded coursepack ZIP is empty.")

    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > _MAX_ZIP_FILES:
                raise CoursepackImportError("Coursepack ZIP has too many files to import safely.")
            total_size = sum(int(info.file_size or 0) for info in infos)
            if total_size > _MAX_EXTRACTED_BYTES:
                raise CoursepackImportError("Coursepack ZIP is too large to import safely.")

            manifest_root = _find_manifest_root(infos)
            manifest = _load_manifest_from_zip(archive, manifest_root)
            course_slug = str(manifest.get("slug") or "").strip()
            root = courses_dir().resolve()
            root.mkdir(parents=True, exist_ok=True)
            try:
                destination = Path(safe_join(str(root), course_slug)).resolve()
            except Exception as exc:
                raise CoursepackImportError("Course slug resolves outside the configured content root.") from exc
            if not destination.is_relative_to(root):
                raise CoursepackImportError("Course slug resolves outside the configured content root.")
            if destination.exists() and not overwrite_content:
                raise CoursepackImportError(f"Course '{course_slug}' already exists. Enable overwrite to replace it.")

            tmp_dir = Path(safe_join(str(root), f".tmp-import-{uuid.uuid4().hex}")).resolve()
            if not tmp_dir.is_relative_to(root):
                raise CoursepackImportError("Temporary import path is unsafe.")
            tmp_dir.mkdir(parents=True, exist_ok=False)
            extracted_files = 0
            try:
                for info in infos:
                    path = _zip_member_path(info.filename)
                    if path is None:
                        continue
                    try:
                        rel_path = path.relative_to(manifest_root)
                    except ValueError:
                        continue
                    if rel_path.name == "":
                        continue
                    try:
                        target = Path(safe_join(str(tmp_dir), str(rel_path))).resolve()
                    except Exception as exc:
                        raise CoursepackImportError("Coursepack ZIP contains an unsafe file path.") from exc
                    if not target.is_relative_to(tmp_dir):
                        raise CoursepackImportError("Coursepack ZIP contains an unsafe file path.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source:
                        target.write_bytes(source.read())
                    extracted_files += 1

                if destination.exists():
                    shutil.rmtree(destination)
                tmp_dir.replace(destination)
            except Exception:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise
    except zipfile.BadZipFile as exc:
        raise CoursepackImportError("Invalid coursepack ZIP.") from exc

    return course_slug, destination, extracted_files


def _zip_contains_coursepack_manifest(source_bytes: bytes) -> bool:
    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            return any((_zip_member_path(info.filename) or PurePosixPath()).name == "course.yaml" for info in infos)
    except zipfile.BadZipFile:
        return False


@transaction.atomic
def import_coursepack_zip(
    *,
    source_upload,
    class_code: str = "",
    class_name: str = "",
    create_class: bool = True,
    replace: bool = False,
    overwrite_content: bool = False,
    organization: Organization | None = None,
) -> CoursepackImportResult:
    source_name = str(getattr(source_upload, "name", "") or "").strip()
    if not source_name.lower().endswith(".zip"):
        raise CoursepackImportError("Upload a .zip coursepack.")
    course_slug, course_dir, extracted_files = _safe_extract_coursepack_zip(
        source_bytes=source_upload.read(),
        overwrite_content=overwrite_content,
    )
    result = import_coursepack_to_class(
        course_slug=course_slug,
        class_code=class_code,
        class_name=class_name,
        create_class=create_class,
        replace=replace,
        organization=organization,
    )
    return CoursepackImportResult(
        course_slug=result.course_slug,
        course_title=result.course_title,
        classroom=result.classroom,
        course_dir=course_dir,
        created_modules=result.created_modules,
        created_materials=result.created_materials,
        created_assets=result.created_assets,
        extracted_files=extracted_files,
        source_kind="coursepack_zip",
        source_files=(source_name,),
    )


@transaction.atomic
def import_content_upload_to_class(
    *,
    source_upload,
    classroom: Class,
    course_slug: str = "",
    course_title: str = "",
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    replace: bool = True,
    overwrite_content: bool = False,
) -> CoursepackImportResult:
    source_name = str(getattr(source_upload, "name", "") or "").strip()
    source_bytes = source_upload.read()
    source_suffix = Path(source_name).suffix.lower()
    if source_suffix not in {".zip", ".md", ".docx"}:
        raise CoursepackImportError("Upload a .zip, .docx, or .md source file.")

    if source_suffix == ".zip" and _zip_contains_coursepack_manifest(source_bytes):
        course_slug, course_dir, extracted_files = _safe_extract_coursepack_zip(
            source_bytes=source_bytes,
            overwrite_content=overwrite_content,
        )
        result = import_coursepack_to_class(
            course_slug=course_slug,
            class_code=classroom.join_code,
            create_class=False,
            replace=replace,
            organization=classroom.organization,
        )
        return CoursepackImportResult(
            course_slug=result.course_slug,
            course_title=result.course_title,
            classroom=result.classroom,
            course_dir=course_dir,
            created_modules=result.created_modules,
            created_materials=result.created_materials,
            created_assets=result.created_assets,
            extracted_files=extracted_files,
            source_kind="coursepack_zip",
            source_files=(source_name,),
        )

    try:
        syllabus_result = ingest_uploaded_syllabus(
            source_name=source_name,
            source_bytes=source_bytes,
            course_slug=course_slug,
            course_title=course_title,
            default_ui_level=default_ui_level,
            session_parse_mode=session_parse_mode,
            overwrite=overwrite_content,
            courses_root=courses_dir(),
        )
    except SyllabusIngestError as exc:
        raise CoursepackImportError(str(exc)) from exc

    result = import_coursepack_to_class(
        course_slug=syllabus_result.course_slug,
        class_code=classroom.join_code,
        create_class=False,
        replace=replace,
        organization=classroom.organization,
    )
    return CoursepackImportResult(
        course_slug=result.course_slug,
        course_title=result.course_title,
        classroom=result.classroom,
        course_dir=syllabus_result.course_dir,
        created_modules=result.created_modules,
        created_materials=result.created_materials,
        created_assets=result.created_assets,
        extracted_files=syllabus_result.lesson_count,
        source_kind=syllabus_result.source_kind,
        source_files=tuple(syllabus_result.source_files),
    )


__all__ = [
    "CoursepackImportError",
    "CoursepackImportResult",
    "courses_dir",
    "import_content_upload_to_class",
    "import_coursepack_to_class",
    "import_coursepack_zip",
]
