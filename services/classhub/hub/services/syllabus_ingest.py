"""Teacher-facing syllabus ingestion helpers (.md/.docx/.zip)."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

from .content_links import courses_dir
from .syllabus_ingest_contracts import (
    COURSE_SLUG_RE,
    SUPPORTED_EXTENSIONS,
    TEXT_EXTENSIONS,
    SyllabusIngestError,
    SyllabusIngestResult,
    _ZipLessonImage,
    _ZipTextDoc,
)
from .syllabus_ingest_course_writer import _write_course
from .syllabus_ingest_metadata_infer import (
    _extract_minutes,
    _extract_session_count,
    _normalize_ui_level,
    _pick_first,
    _resolve_ui_level,
)
from .syllabus_ingest_text_parse import (
    _collect_sections,
    _derive_duration_from_docs,
    _extract_bullets,
    _find_section,
    _first_h1_title,
    _parse_inline_metadata,
    _parse_overview,
    _parse_sessions,
    _parse_sessions_from_zip_docs,
    _read_text_blob,
    _slugify,
)
from .syllabus_ingest_zip_helpers import (
    _candidate_overview_score,
    _extract_prefixed_session_number,
    _normalize_zip_member_path,
    _safe_binary_extension,
)


def _build_support_image_filename(
    *,
    session_num: int,
    source_name: str,
    seen: set[str],
) -> str:
    suffix = _safe_binary_extension(source_name)
    raw_stem = Path(str(source_name or "").strip()).stem
    stem_source = raw_stem
    parsed_session = _extract_prefixed_session_number(raw_stem)
    if parsed_session == session_num:
        idx = 0
        while idx < len(raw_stem) and raw_stem[idx].isdigit() and idx < 2:
            idx += 1
        if idx < len(raw_stem):
            stem_source = raw_stem[idx + 1 :].strip(" _-")
    stem = _slugify(stem_source or raw_stem)
    base = f"s{session_num:02d}-{stem or 'image'}"
    candidate = f"{base}{suffix}"
    counter = 2
    while candidate in seen:
        candidate = f"{base}-{counter}{suffix}"
        counter += 1
    seen.add(candidate)
    return candidate


def _zip_text_documents(source_bytes: bytes) -> list[_ZipTextDoc]:
    docs: list[_ZipTextDoc] = []
    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > 500:
                raise SyllabusIngestError("Zip archive has too many files to ingest safely.")
            total_size = 0
            for info in infos:
                normalized_member_path = _normalize_zip_member_path(info.filename)
                if not normalized_member_path:
                    continue
                total_size += int(info.file_size or 0)
                if total_size > 30 * 1024 * 1024:
                    raise SyllabusIngestError("Zip archive is too large to ingest safely.")
                suffix = PurePosixPath(normalized_member_path).suffix.lower()
                if suffix not in TEXT_EXTENSIONS:
                    continue
                with archive.open(info, "r") as stream:
                    raw = stream.read()
                text = _read_text_blob(suffix=suffix, raw=raw)
                docs.append(
                    _ZipTextDoc(
                        path=normalized_member_path,
                        text=text,
                        size=int(info.file_size or len(raw)),
                        suffix=suffix,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise SyllabusIngestError("Invalid ZIP source.") from exc
    return docs


def _zip_lesson_images(*, source_bytes: bytes, valid_session_numbers: set[int]) -> list[_ZipLessonImage]:
    if not valid_session_numbers:
        return []
    images: list[_ZipLessonImage] = []
    seen_output_names: set[str] = set()
    try:
        with zipfile.ZipFile(BytesIO(source_bytes)) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if len(infos) > 500:
                raise SyllabusIngestError("Zip archive has too many files to ingest safely.")
            total_size = 0
            for info in infos:
                normalized_member_path = _normalize_zip_member_path(info.filename)
                if not normalized_member_path:
                    continue
                total_size += int(info.file_size or 0)
                if total_size > 30 * 1024 * 1024:
                    raise SyllabusIngestError("Zip archive is too large to ingest safely.")
                filename = Path(normalized_member_path).name
                session_num = _extract_prefixed_session_number(filename)
                if session_num is None or session_num not in valid_session_numbers:
                    continue
                try:
                    output_filename = _build_support_image_filename(
                        session_num=session_num,
                        source_name=filename,
                        seen=seen_output_names,
                    )
                except SyllabusIngestError:
                    continue
                with archive.open(info, "r") as stream:
                    raw = stream.read()
                images.append(
                    _ZipLessonImage(
                        path=normalized_member_path,
                        session=session_num,
                        output_filename=output_filename,
                        raw=raw,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise SyllabusIngestError("Invalid ZIP source.") from exc
    return images


def _parse_zip_source(
    *,
    source_bytes: bytes,
    session_parse_mode: str,
) -> tuple[list[dict], dict[str, str], str, list[str], int | None, list[_ZipLessonImage]]:
    docs = _zip_text_documents(source_bytes)
    if not docs:
        raise SyllabusIngestError("Zip archive has no supported .md or .docx files.")

    sessions, session_paths, session_source = _parse_sessions_from_zip_docs(
        docs,
        session_parse_mode=session_parse_mode,
    )
    if not sessions:
        raise SyllabusIngestError("No session headings found in zip source.")

    metadata: dict[str, str] = {}
    if session_source:
        metadata.update(
            _parse_inline_metadata(
                session_source,
                stop_on_session_header=True,
                session_parse_mode=session_parse_mode,
            )
        )

    overview_doc = max(
        docs,
        key=lambda item: (_candidate_overview_score(item.path), item.size, item.path.lower()),
    )
    overview_meta = _parse_overview(overview_doc.text)
    metadata = {**overview_meta, **metadata}

    inferred_duration = _derive_duration_from_docs(docs)
    session_numbers = {int(row.get("session") or 0) for row in sessions if int(row.get("session") or 0) > 0}
    lesson_images = _zip_lesson_images(source_bytes=source_bytes, valid_session_numbers=session_numbers)
    source_files = sorted(set(session_paths + [overview_doc.path] + [row.path for row in lesson_images]))
    title_fallback = _first_h1_title(overview_doc.text) or _first_h1_title(session_source)
    return sessions, metadata, title_fallback, source_files, inferred_duration, lesson_images


def _parse_text_source(
    *,
    source_text: str,
    overview_text: str,
    session_parse_mode: str,
) -> tuple[list[dict], dict[str, str], str, list[str], int | None, list[_ZipLessonImage]]:
    sessions = _parse_sessions(source_text, session_parse_mode=session_parse_mode)
    if not sessions:
        raise SyllabusIngestError("No sessions found. Expected headings like: Session 01: Title")

    sessions_preamble_info = _parse_inline_metadata(
        source_text,
        stop_on_session_header=True,
        session_parse_mode=session_parse_mode,
    )
    overview_info = _parse_overview(overview_text) if overview_text else {}
    metadata = {**overview_info, **sessions_preamble_info}
    title_fallback = _first_h1_title(overview_text) or _first_h1_title(source_text)
    inferred_duration = _extract_minutes(overview_text) if overview_text else None
    return sessions, metadata, title_fallback, [], inferred_duration, []


def ingest_uploaded_syllabus(
    *,
    source_name: str,
    source_bytes: bytes,
    course_slug: str = "",
    course_title: str = "",
    overview_name: str = "",
    overview_bytes: bytes | None = None,
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    overwrite: bool = False,
    courses_root: Path | None = None,
) -> SyllabusIngestResult:
    if not source_name:
        raise SyllabusIngestError("Source file name is required.")
    if not source_bytes:
        raise SyllabusIngestError("Source file is empty.")

    source_suffix = Path(source_name).suffix.lower()
    if source_suffix not in SUPPORTED_EXTENSIONS:
        raise SyllabusIngestError("Unsupported source format. Use .md, .docx, or .zip.")

    overview_text = ""
    source_files = [Path(source_name).name]
    if overview_bytes is not None:
        overview_suffix = Path(overview_name or "").suffix.lower()
        if overview_suffix not in TEXT_EXTENSIONS:
            raise SyllabusIngestError("Overview file must be .md or .docx.")
        overview_text = _read_text_blob(suffix=overview_suffix, raw=overview_bytes)
        if overview_name:
            source_files.append(Path(overview_name).name)

    if source_suffix == ".zip":
        sessions, metadata, title_fallback, zip_source_files, inferred_duration, lesson_images = _parse_zip_source(
            source_bytes=source_bytes,
            session_parse_mode=session_parse_mode,
        )
        source_kind = "zip"
        if zip_source_files:
            source_files = zip_source_files
    else:
        source_text = _read_text_blob(suffix=source_suffix, raw=source_bytes)
        sessions, metadata, title_fallback, _unused, inferred_duration, lesson_images = _parse_text_source(
            source_text=source_text,
            overview_text=overview_text,
            session_parse_mode=session_parse_mode,
        )
        source_kind = source_suffix.lstrip(".")

    if not sessions:
        raise SyllabusIngestError("No sessions found in source.")

    normalized_default_ui = _normalize_ui_level(default_ui_level) or "secondary"
    ui_level = _resolve_ui_level(metadata, default_ui_level=normalized_default_ui)
    explicit_program_profile = _normalize_ui_level(_pick_first(metadata, "program_profile"))
    program_profile = explicit_program_profile or ui_level

    chosen_title = (course_title or "").strip()
    if not chosen_title:
        chosen_title = _pick_first(metadata, "title") or title_fallback
    if not chosen_title:
        raise SyllabusIngestError("Missing course title. Provide a title or include a top-level # heading.")

    chosen_slug = (course_slug or "").strip().lower()
    if not chosen_slug:
        chosen_slug = _slugify(chosen_title).replace("-", "_")
    if not COURSE_SLUG_RE.fullmatch(chosen_slug):
        raise SyllabusIngestError("Course slug can use lowercase letters, numbers, underscores, and dashes.")

    duration_candidates = [
        _pick_first(metadata, "meeting_time"),
        _pick_first(metadata, "session_length"),
        _pick_first(metadata, "duration"),
    ]
    derived_duration = next((m for m in (_extract_minutes(text) for text in duration_candidates) if m), None)
    duration = derived_duration or inferred_duration or 75

    derived_sessions = _extract_session_count(_pick_first(metadata, "duration", "meeting_time", "total_sessions"))
    if derived_sessions and len(sessions) > derived_sessions:
        sessions = sorted(sessions, key=lambda item: int(item.get("session") or 0))[:derived_sessions]
    else:
        sessions = sorted(sessions, key=lambda item: int(item.get("session") or 0))

    grade_band = _pick_first(metadata, "grade_band", "grade_level")
    age_band = _pick_first(metadata, "age_band", "ages")
    needs: list[str] = []
    if overview_text:
        sections = _collect_sections(overview_text.splitlines())
        needs = _extract_bullets(_find_section(sections, "materials"))

    root = Path(courses_root or courses_dir())
    written_dir = _write_course(
        root_dir=root,
        slug=chosen_slug,
        title=chosen_title,
        sessions=sessions,
        duration=duration,
        grade_band=grade_band,
        age_band=age_band,
        needs=needs,
        ui_level=ui_level,
        program_profile=program_profile,
        overwrite=overwrite,
        lesson_images=lesson_images,
    )
    return SyllabusIngestResult(
        course_slug=chosen_slug,
        course_title=chosen_title,
        course_dir=written_dir,
        lesson_count=len(sessions),
        source_kind=source_kind,
        source_files=sorted(set(source_files)),
        ui_level=ui_level,
    )


def ingest_uploaded_syllabus_files(
    *,
    source_upload,
    course_slug: str = "",
    course_title: str = "",
    overview_upload=None,
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    overwrite: bool = False,
    courses_root: Path | None = None,
) -> SyllabusIngestResult:
    source_name = str(getattr(source_upload, "name", "") or "").strip()
    source_bytes = source_upload.read()
    overview_name = ""
    overview_bytes = None
    if overview_upload is not None:
        overview_name = str(getattr(overview_upload, "name", "") or "").strip()
        overview_bytes = overview_upload.read()

    return ingest_uploaded_syllabus(
        source_name=source_name,
        source_bytes=source_bytes,
        course_slug=course_slug,
        course_title=course_title,
        overview_name=overview_name,
        overview_bytes=overview_bytes,
        default_ui_level=default_ui_level,
        session_parse_mode=session_parse_mode,
        overwrite=overwrite,
        courses_root=courses_root,
    )


def ingest_uploaded_syllabus_path(
    *,
    source_path: Path,
    course_slug: str = "",
    course_title: str = "",
    overview_path: Path | None = None,
    default_ui_level: str = "secondary",
    session_parse_mode: str = "auto",
    overwrite: bool = False,
    courses_root: Path | None = None,
) -> SyllabusIngestResult:
    source = Path(source_path)
    if not source.exists():
        raise SyllabusIngestError(f"Source file not found: {source}")
    source_name = source.name
    source_bytes = source.read_bytes()
    overview_name = ""
    overview_bytes = None
    if overview_path is not None:
        overview = Path(overview_path)
        if not overview.exists():
            raise SyllabusIngestError(f"Overview file not found: {overview}")
        overview_name = overview.name
        overview_bytes = overview.read_bytes()

    return ingest_uploaded_syllabus(
        source_name=source_name,
        source_bytes=source_bytes,
        course_slug=course_slug,
        course_title=course_title,
        overview_name=overview_name,
        overview_bytes=overview_bytes,
        default_ui_level=default_ui_level,
        session_parse_mode=session_parse_mode,
        overwrite=overwrite,
        courses_root=courses_root,
    )


__all__ = [
    "COURSE_SLUG_RE",
    "SUPPORTED_EXTENSIONS",
    "SyllabusIngestError",
    "SyllabusIngestResult",
    "ingest_uploaded_syllabus",
    "ingest_uploaded_syllabus_files",
    "ingest_uploaded_syllabus_path",
]
