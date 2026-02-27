"""Student home page service helpers."""

import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ..models import Class, Material, Module, StudentIdentity, StudentMaterialResponse, Submission
from .content_links import build_asset_url, parse_course_lesson_url, safe_external_url
from .markdown_content import load_lesson_markdown
from .release_state import lesson_release_override_map, lesson_release_state


def _retention_days(setting_name: str, default: int) -> int:
    raw = getattr(settings, setting_name, default)
    try:
        value = int(raw)
    except Exception:
        value = int(default)
    return value if value > 0 else 0


def privacy_meta_context() -> dict:
    return {
        "submission_retention_days": _retention_days("CLASSHUB_SUBMISSION_RETENTION_DAYS", 90),
        "student_event_retention_days": _retention_days("CLASSHUB_STUDENT_EVENT_RETENTION_DAYS", 180),
    }


def helper_backend_label() -> str:
    backend = (getattr(settings, "HELPER_LLM_BACKEND", "ollama") or "ollama").strip().lower()
    if backend == "openai":
        return "Remote model (OpenAI)"
    if backend == "ollama":
        return "Local model (Ollama)"
    if backend == "mock":
        return "Mock model (Test mode)"
    return "Model backend (Unknown)"


def _sorted_module_materials(module: Module) -> list[Material]:
    mats = list(module.materials.all())
    mats.sort(key=lambda m: (m.order_index, m.id))
    return mats


def parse_checklist_items(raw: str) -> list[str]:
    items: list[str] = []
    for line in str(raw or "").splitlines():
        text = (line or "").strip()
        if not text:
            continue
        text = re.sub(r"^[-*]\s*", "", text)
        text = re.sub(r"^\d+[.)]\s*", "", text)
        text = text.strip()
        if text:
            items.append(text)
    return items


def parse_rubric_criteria(raw: str) -> list[str]:
    return parse_checklist_items(raw)


def build_material_checklist_items_map(*, modules: list[Module]) -> dict[int, list[str]]:
    material_checklist_items: dict[int, list[str]] = {}
    for module in modules:
        for mat in _sorted_module_materials(module):
            if mat.type != Material.TYPE_CHECKLIST:
                continue
            material_checklist_items[mat.id] = parse_checklist_items(mat.body)
    return material_checklist_items


def build_material_rubric_specs_map(*, modules: list[Module]) -> dict[int, dict]:
    by_material: dict[int, dict] = {}
    for module in modules:
        for mat in _sorted_module_materials(module):
            if mat.type != Material.TYPE_RUBRIC:
                continue
            scale_max = max(int(getattr(mat, "rubric_scale_max", 4) or 4), 2)
            by_material[mat.id] = {
                "criteria": parse_rubric_criteria(mat.body),
                "scale_values": list(range(1, min(scale_max, 10) + 1)),
                "scale_max": min(scale_max, 10),
            }
    return by_material


def build_material_response_map(*, student: StudentIdentity, material_ids: list[int]) -> dict[int, dict]:
    by_material: dict[int, dict] = {}
    if not material_ids:
        return by_material

    qs = (
        StudentMaterialResponse.objects.filter(student=student, material_id__in=material_ids)
        .only("material_id", "checklist_checked", "reflection_text", "updated_at")
        .order_by("material_id", "-updated_at", "-id")
    )
    for row in qs:
        if row.material_id in by_material:
            continue
        checked_indexes: list[int] = []
        raw_checked = row.checklist_checked if isinstance(row.checklist_checked, list) else []
        for value in raw_checked:
            try:
                idx = int(value)
            except Exception:
                continue
            if idx < 0 or idx in checked_indexes:
                continue
            checked_indexes.append(idx)
        by_material[row.material_id] = {
            "checklist_checked": checked_indexes,
            "reflection_text": (row.reflection_text or ""),
            "rubric_scores": [int(v) for v in (row.rubric_scores or []) if str(v).isdigit()],
            "rubric_feedback": (row.rubric_feedback or ""),
            "updated_at": row.updated_at,
        }
    return by_material


def build_gallery_entries_map(
    *,
    classroom: Class,
    viewer_student: StudentIdentity,
    material_ids: list[int],
    per_material_limit: int = 24,
) -> dict[int, list[dict]]:
    by_material: dict[int, list[dict]] = {}
    if not material_ids:
        return by_material

    limit = max(int(per_material_limit), 1)
    qs = (
        Submission.objects.filter(
            material_id__in=material_ids,
            material__module__classroom=classroom,
            material__type=Material.TYPE_GALLERY,
            is_gallery_shared=True,
        )
        .select_related("student")
        .only("id", "material_id", "student_id", "student__display_name", "uploaded_at", "original_filename")
        .order_by("-uploaded_at", "-id")
    )
    for submission in qs:
        rows = by_material.setdefault(submission.material_id, [])
        if len(rows) >= limit:
            continue
        rows.append(
            {
                "submission_id": submission.id,
                "display_name": submission.student.display_name,
                "uploaded_at": submission.uploaded_at,
                "original_filename": submission.original_filename,
                "is_owner": submission.student_id == viewer_student.id,
            }
        )
    return by_material


def build_material_access_map(request, *, classroom: Class, modules: list[Module]) -> tuple[list[int], dict[int, dict]]:
    lesson_release_cache: dict[tuple[str, str], dict] = {}
    module_lesson_cache: dict[int, tuple[str, str] | None] = {}
    release_override_map = lesson_release_override_map(classroom.id)

    def get_module_lesson(module: Module) -> tuple[str, str] | None:
        if module.id in module_lesson_cache:
            return module_lesson_cache[module.id]
        for mat in _sorted_module_materials(module):
            if mat.type != Material.TYPE_LINK:
                continue
            parsed = parse_course_lesson_url(mat.url)
            if parsed:
                module_lesson_cache[module.id] = parsed
                return parsed
        module_lesson_cache[module.id] = None
        return None

    def get_release_state(course_slug: str, lesson_slug: str) -> dict:
        key = (course_slug, lesson_slug)
        if key in lesson_release_cache:
            return lesson_release_cache[key]
        try:
            front_matter, _body, lesson_meta = load_lesson_markdown(course_slug, lesson_slug)
        except ValueError:
            front_matter = {}
            lesson_meta = {}
        state = lesson_release_state(
            request,
            front_matter,
            lesson_meta,
            classroom_id=classroom.id,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
            override_map=release_override_map,
        )
        lesson_release_cache[key] = state
        return state

    material_ids: list[int] = []
    material_access: dict[int, dict] = {}
    for module in modules:
        module_lesson = get_module_lesson(module)
        for mat in _sorted_module_materials(module):
            material_ids.append(mat.id)
            access = {
                "is_locked": False,
                "available_on": None,
                "is_lesson_link": False,
                "is_lesson_upload": False,
                "is_lesson_activity": False,
            }
            if mat.type == Material.TYPE_LINK:
                parsed = parse_course_lesson_url(mat.url)
                if parsed:
                    state = get_release_state(*parsed)
                    access["is_lesson_link"] = True
                    access["is_locked"] = bool(state.get("is_locked"))
                    access["available_on"] = state.get("available_on")
            elif mat.type in {
                Material.TYPE_UPLOAD,
                Material.TYPE_GALLERY,
                Material.TYPE_CHECKLIST,
                Material.TYPE_REFLECTION,
                Material.TYPE_RUBRIC,
            } and module_lesson:
                state = get_release_state(*module_lesson)
                access["is_lesson_upload"] = mat.type in {Material.TYPE_UPLOAD, Material.TYPE_GALLERY}
                access["is_lesson_activity"] = mat.type in {
                    Material.TYPE_CHECKLIST,
                    Material.TYPE_REFLECTION,
                    Material.TYPE_RUBRIC,
                }
                access["is_locked"] = bool(state.get("is_locked"))
                access["available_on"] = state.get("available_on")
            material_access[mat.id] = access

    return material_ids, material_access


def build_submissions_by_material(*, student: StudentIdentity, material_ids: list[int]) -> dict[int, dict]:
    by_material: dict[int, dict] = {}
    if not material_ids:
        return by_material

    qs = (
        Submission.objects.filter(student=student, material_id__in=material_ids)
        .only("id", "material_id", "uploaded_at")
        .order_by("material_id", "-uploaded_at", "-id")
    )
    for submission in qs:
        if submission.material_id not in by_material:
            by_material[submission.material_id] = {
                "count": 0,
                "last": submission.uploaded_at,
                "last_id": submission.id,
            }
        by_material[submission.material_id]["count"] += 1
    return by_material


def _normalize_landing_hero_url(raw: str) -> str:
    value = str(raw or "").strip()
    if not value:
        return ""
    if value.startswith("/") and not value.startswith("//"):
        return build_asset_url(value)
    return safe_external_url(value)


def _pick_highlight_lesson(*, lesson_links: list[dict], today):
    if not lesson_links:
        return None
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    this_week = [
        row for row in lesson_links
        if row.get("available_on") and week_start <= row["available_on"] <= week_end
    ]
    if this_week:
        this_week.sort(
            key=lambda row: (
                abs((row["available_on"] - today).days),
                row["available_on"],
                row["module_order"],
                row["module_id"],
            )
        )
        highlight = dict(this_week[0])
        highlight["is_this_week"] = True
        return highlight

    open_now = [row for row in lesson_links if not row.get("is_locked")]
    if open_now:
        open_now.sort(key=lambda row: (row["module_order"], row["module_id"]))
        highlight = dict(open_now[0])
        highlight["is_this_week"] = False
        return highlight

    upcoming = [row for row in lesson_links if row.get("available_on") and row["available_on"] >= today]
    if upcoming:
        upcoming.sort(key=lambda row: (row["available_on"], row["module_order"], row["module_id"]))
        highlight = dict(upcoming[0])
        highlight["is_this_week"] = False
        return highlight

    fallback = dict(lesson_links[0])
    fallback["is_this_week"] = False
    return fallback


def build_class_landing_context(*, classroom: Class, modules: list[Module], material_access: dict[int, dict]) -> dict:
    lesson_links: list[dict] = []
    for module in modules:
        for material in _sorted_module_materials(module):
            if material.type != Material.TYPE_LINK or not material.url:
                continue
            parsed = parse_course_lesson_url(material.url)
            if not parsed:
                continue
            access = material_access.get(material.id) or {}
            lesson_links.append(
                {
                    "module_id": module.id,
                    "module_order": int(module.order_index or 0),
                    "module_title": module.title,
                    "lesson_url": material.url,
                    "is_locked": bool(access.get("is_locked")),
                    "available_on": access.get("available_on"),
                }
            )
            break

    today = timezone.localdate()
    highlight = _pick_highlight_lesson(lesson_links=lesson_links, today=today)

    highlight_module_id = int(highlight["module_id"]) if highlight else 0
    for row in lesson_links:
        row["is_highlight"] = bool(highlight and int(row["module_id"]) == highlight_module_id)

    default_title = f"Welcome to {classroom.name}"
    landing_title = str(getattr(classroom, "student_landing_title", "") or "").strip() or default_title
    landing_message = str(getattr(classroom, "student_landing_message", "") or "").strip()

    return {
        "landing_title": landing_title,
        "landing_message": landing_message,
        "landing_hero_url": _normalize_landing_hero_url(getattr(classroom, "student_landing_hero_url", "")),
        "highlight_lesson": highlight,
        "course_lesson_links": lesson_links,
    }
