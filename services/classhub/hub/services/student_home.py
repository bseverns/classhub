"""Student home page service helpers."""

from django.conf import settings

from ..models import Class, Material, Module, StudentIdentity, Submission
from .content_links import parse_course_lesson_url
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
            access = {"is_locked": False, "available_on": None, "is_lesson_link": False, "is_lesson_upload": False}
            if mat.type == Material.TYPE_LINK:
                parsed = parse_course_lesson_url(mat.url)
                if parsed:
                    state = get_release_state(*parsed)
                    access["is_lesson_link"] = True
                    access["is_locked"] = bool(state.get("is_locked"))
                    access["available_on"] = state.get("available_on")
            elif mat.type == Material.TYPE_UPLOAD and module_lesson:
                state = get_release_state(*module_lesson)
                access["is_lesson_upload"] = True
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
