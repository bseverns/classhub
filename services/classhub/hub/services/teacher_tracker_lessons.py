"""Lesson tracker row builders for teacher dashboard tracker panels."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from ..models import Class, Material, Module, Submission
from .content_links import parse_course_lesson_url
from .helper_topics import build_allowed_topics, build_lesson_topics
from .markdown_content import load_lesson_markdown, load_teacher_material_html
from .release_state import lesson_release_override_map, lesson_release_state
from .teacher_tracker_cache import _cache_get_or_build
from .teacher_tracker_types import LessonTrackerDropboxRow, LessonTrackerHelperDefaults, LessonTrackerRow


def _material_submission_counts(material_ids: list[int]) -> dict[int, int]:
    counts = {}
    if not material_ids:
        return counts
    rows = (
        Submission.objects.filter(material_id__in=material_ids)
        .values("material_id")
        .annotate(total=models.Count("student_id", distinct=True))
    )
    for row in rows:
        material_id = int(row["material_id"])
        counts[material_id] = int(row.get("total") or 0)
    return counts


def _material_latest_upload_map(material_ids: list[int]) -> dict[int, timezone.datetime]:
    latest = {}
    if not material_ids:
        return latest
    rows = (
        Submission.objects.filter(material_id__in=material_ids)
        .values("material_id")
        .annotate(last_uploaded_at=models.Max("uploaded_at"))
    )
    for row in rows:
        latest[int(row["material_id"])] = row["last_uploaded_at"]
    return latest


def _compute_lesson_tracker_rows(
    request, classroom_id: int, modules: list[Module], student_count: int
) -> list[LessonTrackerRow]:
    rows: list[LessonTrackerRow] = []
    upload_material_ids = []
    module_materials_map: dict[int, list[Material]] = {}
    teacher_material_html_by_lesson: dict[tuple[str, str], str] = {}
    lesson_title_by_lesson: dict[tuple[str, str], str] = {}
    lesson_release_by_lesson: dict[tuple[str, str], dict] = {}
    helper_defaults_by_lesson: dict[tuple[str, str], LessonTrackerHelperDefaults] = {}
    release_override_map = lesson_release_override_map(classroom_id)

    for module in modules:
        prefetched = getattr(module, "_prefetched_objects_cache", {}).get("materials")
        if prefetched is None:
            raise ValueError(
                "lesson tracker requires modules prefetched with materials; use prefetch_related('materials')"
            )
        mats = list(prefetched)
        mats.sort(key=lambda m: (m.order_index, m.id))
        module_materials_map[module.id] = mats
        for mat in mats:
            if mat.type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
                upload_material_ids.append(mat.id)

    submission_counts = _material_submission_counts(upload_material_ids)
    latest_upload_map = _material_latest_upload_map(upload_material_ids)

    for module in modules:
        mats = module_materials_map.get(module.id, [])
        dropboxes: list[LessonTrackerDropboxRow] = []
        for mat in mats:
            if mat.type not in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}:
                continue
            submitted = submission_counts.get(mat.id, 0)
            dropboxes.append(
                {
                    "id": mat.id,
                    "title": mat.title,
                    "submitted": submitted,
                    "missing": max(student_count - submitted, 0),
                    "last_uploaded_at": latest_upload_map.get(mat.id),
                }
            )

        review_dropbox = None
        if dropboxes:
            review_dropbox = max(dropboxes, key=lambda d: (d["missing"], d["submitted"], -int(d["id"])))

        if review_dropbox and review_dropbox["missing"] > 0:
            review_url = f"/teach/material/{review_dropbox['id']}/submissions?show=missing"
            review_label = f"Review missing now ({review_dropbox['missing']})"
        elif review_dropbox:
            review_url = f"/teach/material/{review_dropbox['id']}/submissions"
            review_label = "Review submissions"
        else:
            review_url = ""
            review_label = ""

        seen_lessons = set()
        for mat in mats:
            if mat.type != Material.TYPE_LINK:
                continue
            parsed = parse_course_lesson_url(mat.url)
            if not parsed:
                continue
            lesson_key = parsed
            if lesson_key in seen_lessons:
                continue
            seen_lessons.add(lesson_key)
            course_slug, lesson_slug = parsed

            if lesson_key not in teacher_material_html_by_lesson:
                teacher_material_html_by_lesson[lesson_key] = load_teacher_material_html(course_slug, lesson_slug)
                try:
                    front_matter, _body_markdown, lesson_meta = load_lesson_markdown(course_slug, lesson_slug)
                except ValueError:
                    front_matter = {}
                    lesson_meta = {}
                lesson_title_by_lesson[lesson_key] = (
                    str(front_matter.get("title") or "").strip() or mat.title
                )
                helper_defaults_by_lesson[lesson_key] = {
                    "context": str(front_matter.get("title") or lesson_slug).strip() or lesson_slug,
                    "topics": build_lesson_topics(front_matter),
                    "allowed_topics": build_allowed_topics(front_matter),
                    "reference": str(lesson_meta.get("helper_reference") or "").strip(),
                }
                lesson_release_by_lesson[lesson_key] = lesson_release_state(
                    request,
                    front_matter,
                    lesson_meta,
                    classroom_id=classroom_id,
                    course_slug=course_slug,
                    lesson_slug=lesson_slug,
                    override_map=release_override_map,
                    respect_staff_bypass=False,
                )

            release_override = release_override_map.get(lesson_key)
            helper_context_override = (getattr(release_override, "helper_context_override", "") or "").strip()
            helper_topics_override = (getattr(release_override, "helper_topics_override", "") or "").strip()
            helper_allowed_topics_override = (getattr(release_override, "helper_allowed_topics_override", "") or "").strip()
            helper_reference_override = (getattr(release_override, "helper_reference_override", "") or "").strip()
            has_helper_override = bool(
                helper_context_override
                or helper_topics_override
                or helper_allowed_topics_override
                or helper_reference_override
            )

            helper_defaults = helper_defaults_by_lesson.get(
                lesson_key,
                {"context": lesson_slug, "topics": [], "allowed_topics": [], "reference": ""},
            )
            rows.append(
                {
                    "module": module,
                    "lesson_title": lesson_title_by_lesson.get(lesson_key, mat.title),
                    "lesson_url": mat.url,
                    "course_slug": course_slug,
                    "lesson_slug": lesson_slug,
                    "dropboxes": dropboxes,
                    "review_url": review_url,
                    "review_label": review_label,
                    "teacher_material_html": teacher_material_html_by_lesson.get(lesson_key, ""),
                    "release_state": lesson_release_by_lesson.get(lesson_key, {}),
                    "helper_tuning": {
                        "has_override": has_helper_override,
                        "context_value": helper_context_override,
                        "topics_value": helper_topics_override,
                        "allowed_topics_value": helper_allowed_topics_override,
                        "reference_value": helper_reference_override,
                        "default_context": helper_defaults.get("context", ""),
                        "default_topics": helper_defaults.get("topics", []),
                        "default_allowed_topics": helper_defaults.get("allowed_topics", []),
                        "default_reference": helper_defaults.get("reference", ""),
                    },
                }
            )

    return rows


def _serialize_lesson_tracker_rows(rows: list[LessonTrackerRow]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for row in rows:
        module = row.get("module")
        if not module or not getattr(module, "id", None):
            continue
        payload.append(
            {
                "module_id": int(module.id),
                "lesson_title": str(row.get("lesson_title") or ""),
                "lesson_url": str(row.get("lesson_url") or ""),
                "course_slug": str(row.get("course_slug") or ""),
                "lesson_slug": str(row.get("lesson_slug") or ""),
                "dropboxes": [dict(dropbox) for dropbox in row.get("dropboxes") or []],
                "review_url": str(row.get("review_url") or ""),
                "review_label": str(row.get("review_label") or ""),
                "teacher_material_html": str(row.get("teacher_material_html") or ""),
                "release_state": dict(row.get("release_state") or {}),
                "helper_tuning": dict(row.get("helper_tuning") or {}),
            }
        )
    return payload


def _hydrate_lesson_tracker_rows(payload: list[dict[str, object]], modules: list[Module]) -> list[LessonTrackerRow]:
    modules_by_id = {int(module.id): module for module in modules if getattr(module, "id", None)}
    hydrated: list[LessonTrackerRow] = []
    for cached in payload:
        try:
            module_id = int(cached.get("module_id") or 0)
        except Exception:
            module_id = 0
        module = modules_by_id.get(module_id)
        if module is None:
            continue
        hydrated.append(
            {
                "module": module,
                "lesson_title": str(cached.get("lesson_title") or ""),
                "lesson_url": str(cached.get("lesson_url") or ""),
                "course_slug": str(cached.get("course_slug") or ""),
                "lesson_slug": str(cached.get("lesson_slug") or ""),
                "dropboxes": [dict(dropbox) for dropbox in cached.get("dropboxes") or []],
                "review_url": str(cached.get("review_url") or ""),
                "review_label": str(cached.get("review_label") or ""),
                "teacher_material_html": str(cached.get("teacher_material_html") or ""),
                "release_state": dict(cached.get("release_state") or {}),
                "helper_tuning": dict(cached.get("helper_tuning") or {}),
            }
        )
    return hydrated


def _build_lesson_tracker_rows(
    request,
    classroom_id: int,
    modules: list[Module],
    student_count: int,
    *,
    class_session_epoch: int | None = None,
) -> list[LessonTrackerRow]:
    module_signature_parts: list[str] = []
    for module in modules:
        prefetched = getattr(module, "_prefetched_objects_cache", {}).get("materials")
        if prefetched is None:
            raise ValueError(
                "lesson tracker requires modules prefetched with materials; use prefetch_related('materials')"
            )
        module_signature_parts.append(f"{int(module.id)}:{int(module.order_index)}:{len(prefetched)}")

    cached_payload = _cache_get_or_build(
        "lesson-tracker",
        key_parts=[
            str(int(classroom_id)),
            str(int(class_session_epoch or 0)),
            str(int(student_count)),
            ",".join(module_signature_parts),
        ],
        builder=lambda: _serialize_lesson_tracker_rows(
            _compute_lesson_tracker_rows(request, classroom_id, modules, student_count)
        ),
    )
    if not isinstance(cached_payload, list):
        return _compute_lesson_tracker_rows(request, classroom_id, modules, student_count)
    return _hydrate_lesson_tracker_rows(cached_payload, modules)


__all__ = [
    "_build_lesson_tracker_rows",
    "_material_latest_upload_map",
    "_material_submission_counts",
]
