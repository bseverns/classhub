"""Headless JSON API endpoints for the student experience."""

import logging
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from common.request_safety import client_ip_from_request, fixed_window_allow
from ..http.headers import apply_no_store
from ..models import Submission
from ..services.student_home import (
    build_class_landing_context,
    build_material_access_map,
    build_material_checklist_items_map,
    build_gallery_entries_map,
    build_material_rubric_specs_map,
    build_material_response_map,
    build_submissions_by_material,
    privacy_meta_context,
)
from ..services.ui_density import resolve_ui_density_mode_for_modules

logger = logging.getLogger(__name__)


def _json_no_store_response(payload: dict, *, status: int = 200, private: bool = False) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    apply_no_store(response, private=private, pragma=True)
    return response


def _api_rate_limit(limit: int = 120, window_seconds: int = 60):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if getattr(request, "student", None) is None:
                return view_func(request, *args, **kwargs)
            client_ip = client_ip_from_request(
                request,
                trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
                xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
            )
            key = f"api_rate:student:{request.student.id}:ip:{client_ip}"
            if not fixed_window_allow(key, limit=limit, window_seconds=window_seconds):
                return _json_no_store_response({"error": "rate_limited"}, status=429, private=True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


@require_GET
@_api_rate_limit(limit=120, window_seconds=60)
def api_student_session(request):
    """GET /api/v1/student/session
    
    Returns the active classroom and student details.
    """
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)

    classroom = request.classroom
    student = request.student

    # Session Keep-alive Heartbeat
    student.last_seen_at = timezone.now()
    student.save(update_fields=["last_seen_at"])

    return _json_no_store_response(
        {
            "classroom": {
                "id": classroom.id,
                "name": classroom.name,
                "student_landing_title": classroom.student_landing_title,
                "student_landing_message": classroom.student_landing_message,
                "student_landing_hero_url": classroom.student_landing_hero_url,
            },
            "student": {
                "id": student.id,
                "display_name": student.display_name,
                "return_code": student.return_code,
            },
            "privacy_meta": privacy_meta_context(),
        },
        private=True,
    )


@require_GET
@_api_rate_limit(limit=120, window_seconds=60)
def api_student_modules(request):
    """GET /api/v1/student/modules
    
    Returns the accessible curriculum tree for the student.
    """
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)

    classroom = request.classroom
    student = request.student

    modules = list(classroom.modules.prefetch_related("materials").all())
    ui_density_mode = resolve_ui_density_mode_for_modules(
        modules=modules,
        program_profile=getattr(settings, "CLASSHUB_PROGRAM_PROFILE", "secondary")
    )
    material_ids, material_access = build_material_access_map(request, classroom=classroom, modules=modules)
    
    material_checklist_items = build_material_checklist_items_map(modules=modules)
    material_rubric_specs = build_material_rubric_specs_map(modules=modules)
    
    modules_payload = []
    for m in modules:
        materials_payload = []
        mats = sorted(list(m.materials.all()), key=lambda x: (x.order_index, x.id))
        
        for mat in mats:
            access = material_access.get(mat.id, {})
            materials_payload.append({
                "id": mat.id,
                "title": mat.title,
                "type": mat.type,
                "url": mat.url,
                "body": mat.body,
                "accepted_extensions": mat.accepted_extensions,
                "max_upload_mb": mat.max_upload_mb,
                "access": access,
                "checklist_items": material_checklist_items.get(mat.id, []),
                "rubric_specs": material_rubric_specs.get(mat.id, {}),
            })
        
        modules_payload.append({
            "id": m.id,
            "title": m.title,
            "materials": materials_payload,
        })

    return _json_no_store_response(
        {
            "ui_density_mode": ui_density_mode,
            "modules": modules_payload,
        },
        private=True,
    )


@require_GET
@_api_rate_limit(limit=120, window_seconds=60)
def api_student_submissions(request):
    """GET /api/v1/student/submissions
    
    Returns the student's historical work and responses.
    """
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)

    classroom = request.classroom
    student = request.student

    modules = list(classroom.modules.prefetch_related("materials").all())
    material_ids = []
    for m in modules:
        for mat in m.materials.all():
            material_ids.append(mat.id)

    # Pagination logic bounds
    try:
        limit = max(1, min(100, int(request.GET.get("limit", 50))))
        offset = max(0, int(request.GET.get("offset", 0)))
    except ValueError:
        limit = 50
        offset = 0

    submissions_qs = (
        Submission.objects.filter(student=student, material_id__in=material_ids)
        .only("id", "material_id", "uploaded_at", "original_filename")
        .order_by("-uploaded_at", "-id")
    )
    total_submissions = submissions_qs.count()
    submissions_page = submissions_qs[offset:offset + limit]

    submissions_list = []
    for sub in submissions_page:
        submissions_list.append({
            "id": sub.id,
            "material_id": sub.material_id,
            "uploaded_at": sub.uploaded_at,
            "original_filename": sub.original_filename,
        })

    submissions_by_material = build_submissions_by_material(student=student, material_ids=material_ids)
    material_responses = build_material_response_map(student=student, material_ids=material_ids)
    gallery_entries_by_material = build_gallery_entries_map(classroom=classroom, viewer_student=student, material_ids=material_ids)

    return _json_no_store_response(
        {
            "submissions": submissions_list,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_submissions,
            },
            "submissions_by_material": submissions_by_material,
            "material_responses": material_responses,
            "gallery_entries_by_material": gallery_entries_by_material,
        },
        private=True,
    )

__all__ = [
    "api_student_session",
    "api_student_modules",
    "api_student_submissions",
]
