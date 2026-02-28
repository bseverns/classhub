"""Headless JSON API endpoints for the teacher dashboard."""

import logging
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from common.request_safety import client_ip_from_request, fixed_window_allow
from ..http.headers import apply_no_store
from ..models import Submission
from ..services.org_access import staff_accessible_classes_ranked, staff_classroom_or_none
from ..services.teacher_roster_class import build_dashboard_context

logger = logging.getLogger(__name__)


def _json_no_store_response(payload: dict, *, status: int = 200, private: bool = False) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    apply_no_store(response, private=private, pragma=True)
    return response


def _staff_required(view_func):
    """Reject non-staff requests with a 401 JSON response instead of a redirect."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def _teacher_rate_limit(limit: int = 60, window_seconds: int = 60):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            client_ip = client_ip_from_request(
                request,
                trust_proxy_headers=getattr(settings, "REQUEST_SAFETY_TRUST_PROXY_HEADERS", False),
                xff_index=getattr(settings, "REQUEST_SAFETY_XFF_INDEX", 0),
            )
            key = f"api_rate:teacher:{request.user.id}:ip:{client_ip}"
            if not fixed_window_allow(key, limit=limit, window_seconds=window_seconds):
                return _json_no_store_response({"error": "rate_limited"}, status=429, private=True)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def _normalize_order_noop(modules):
    """No-op order normalizer for API reads (dashboard context requires one)."""
    pass


@require_GET
@_staff_required
@_teacher_rate_limit(limit=60, window_seconds=60)
def api_teacher_classes(request):
    """GET /api/v1/teacher/classes

    Returns the list of classes visible to this teacher with student counts
    and a 24-hour submission digest.
    """
    classes, assigned_class_ids = staff_accessible_classes_ranked(request.user)
    digest_since = timezone.now() - timedelta(days=1)

    classes_payload = []
    for c in classes:
        student_count = c.students.count()
        recent_submissions = Submission.objects.filter(
            material__module__classroom=c,
            uploaded_at__gte=digest_since,
        ).count()
        classes_payload.append({
            "id": c.id,
            "name": c.name,
            "join_code": c.join_code,
            "is_locked": c.is_locked,
            "student_count": student_count,
            "submissions_24h": recent_submissions,
            "is_assigned": c.id in assigned_class_ids,
        })

    return _json_no_store_response({"classes": classes_payload}, private=True)


@require_GET
@_staff_required
@_teacher_rate_limit(limit=60, window_seconds=60)
def api_teacher_class_roster(request, class_id: int):
    """GET /api/v1/teacher/class/<id>/roster

    Returns the full dashboard context for a single class: students, modules,
    materials, submission counts, outcome snapshot, and helper signals.
    """
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return _json_no_store_response({"error": "not_found"}, status=404, private=True)

    ctx = build_dashboard_context(
        request=request,
        classroom=classroom,
        normalize_order_fn=_normalize_order_noop,
    )

    students_payload = []
    submission_counts_by_student = ctx.get("submission_counts_by_student", {})
    for s in ctx["students"]:
        students_payload.append({
            "id": s.id,
            "display_name": s.display_name,
            "return_code": s.return_code,
            "created_at": s.created_at,
            "last_seen_at": s.last_seen_at,
            "submission_count": submission_counts_by_student.get(s.id, 0),
        })

    modules_payload = []
    submission_counts = ctx.get("submission_counts", {})
    for m in ctx["modules"]:
        materials_payload = []
        mats = sorted(list(m.materials.all()), key=lambda x: (x.order_index, x.id))
        for mat in mats:
            materials_payload.append({
                "id": mat.id,
                "title": mat.title,
                "type": mat.type,
                "order_index": mat.order_index,
                "submission_count": submission_counts.get(mat.id, 0),
            })
        modules_payload.append({
            "id": m.id,
            "title": m.title,
            "order_index": m.order_index,
            "materials": materials_payload,
        })

    outcome_snapshot = ctx.get("outcome_snapshot", {})
    outcome_payload = {}
    if outcome_snapshot:
        outcome_payload = {
            k: v for k, v in outcome_snapshot.items()
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }

    helper_signals = ctx.get("helper_signals", {})
    helper_payload = {}
    if helper_signals:
        helper_payload = {
            k: v for k, v in helper_signals.items()
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }

    return _json_no_store_response(
        {
            "classroom": {
                "id": classroom.id,
                "name": classroom.name,
                "join_code": classroom.join_code,
                "is_locked": classroom.is_locked,
            },
            "student_count": ctx["student_count"],
            "students": students_payload,
            "modules": modules_payload,
            "outcome_snapshot": outcome_payload,
            "helper_signals": helper_payload,
        },
        private=True,
    )


@require_GET
@_staff_required
@_teacher_rate_limit(limit=60, window_seconds=60)
def api_teacher_class_submissions(request, class_id: int):
    """GET /api/v1/teacher/class/<id>/submissions

    Returns a paginated list of submissions for a class, ordered by most
    recent first.  Accepts ?limit=50&offset=0 query parameters.
    """
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return _json_no_store_response({"error": "not_found"}, status=404, private=True)

    try:
        limit = max(1, min(100, int(request.GET.get("limit", 50))))
        offset = max(0, int(request.GET.get("offset", 0)))
    except ValueError:
        limit = 50
        offset = 0

    qs = (
        Submission.objects
        .filter(material__module__classroom=classroom)
        .select_related("student", "material")
        .only(
            "id", "uploaded_at", "original_filename",
            "student__id", "student__display_name",
            "material__id", "material__title", "material__type",
        )
        .order_by("-uploaded_at", "-id")
    )
    total = qs.count()
    page = qs[offset:offset + limit]

    submissions_payload = []
    for sub in page:
        submissions_payload.append({
            "id": sub.id,
            "uploaded_at": sub.uploaded_at,
            "original_filename": sub.original_filename,
            "student": {
                "id": sub.student_id,
                "display_name": sub.student.display_name if sub.student else None,
            },
            "material": {
                "id": sub.material_id,
                "title": sub.material.title if sub.material else None,
                "type": sub.material.type if sub.material else None,
            },
        })

    return _json_no_store_response(
        {
            "submissions": submissions_payload,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
            },
        },
        private=True,
    )


__all__ = [
    "api_teacher_classes",
    "api_teacher_class_roster",
    "api_teacher_class_submissions",
]
