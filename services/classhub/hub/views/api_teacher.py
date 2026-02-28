"""Headless JSON API endpoints for the teacher dashboard."""

import logging
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from common.request_safety import client_ip_from_request, fixed_window_allow
from ..http.headers import apply_no_store
from ..models import Class, Submission
from ..services.org_access import (
    staff_accessible_classes_ranked,
    staff_can_manage_classroom,
    staff_classroom_or_none,
)
from ..services.teacher_roster_class import build_dashboard_context
from .teacher_parts.shared_ordering import _next_unique_class_join_code
from .teacher_parts.shared_routing import _audit

logger = logging.getLogger(__name__)


def _json_no_store_response(payload: dict, *, status: int = 200, private: bool = False) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    apply_no_store(response, private=private, pragma=True)
    return response


def _staff_required(view_func):
    """Reject non-staff or OTP-unverified requests with a 401 JSON response."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_staff):
            return _json_no_store_response({"error": "unauthorized"}, status=401, private=True)
        if getattr(settings, "TEACHER_2FA_REQUIRED", True):
            is_verified_attr = getattr(request.user, "is_verified", None)
            is_verified = bool(
                is_verified_attr() if callable(is_verified_attr) else is_verified_attr
            )
            if not is_verified:
                return _json_no_store_response({"error": "otp_required"}, status=401, private=True)
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

    # Annotate counts in bulk to avoid N+1 per-class queries.
    from django.db.models import Count, Q
    class_ids = [c.id for c in classes]
    student_counts = dict(
        Class.objects.filter(id__in=class_ids)
        .annotate(sc=Count("students"))
        .values_list("id", "sc")
    )
    submission_counts = dict(
        Class.objects.filter(id__in=class_ids)
        .annotate(
            rc=Count(
                "modules__materials__submissions",
                filter=Q(modules__materials__submissions__uploaded_at__gte=digest_since),
            )
        )
        .values_list("id", "rc")
    )

    classes_payload = []
    for c in classes:
        classes_payload.append({
            "id": c.id,
            "name": c.name,
            "join_code": c.join_code,
            "is_locked": c.is_locked,
            "enrollment_mode": c.enrollment_mode,
            "student_count": student_counts.get(c.id, 0),
            "submissions_24h": submission_counts.get(c.id, 0),
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
                "enrollment_mode": classroom.enrollment_mode,
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


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------

def _manage_or_403(request, classroom):
    """Return a 403 JSON response if user cannot manage this class, else None."""
    if not staff_can_manage_classroom(request.user, classroom):
        return _json_no_store_response({"error": "forbidden"}, status=403, private=True)
    return None


@require_POST
@_staff_required
@_teacher_rate_limit(limit=30, window_seconds=60)
def api_teacher_toggle_lock(request, class_id: int):
    """POST /api/v1/teacher/class/<id>/toggle-lock

    Toggles the class lock state. Returns the new state.
    """
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return _json_no_store_response({"error": "not_found"}, status=404, private=True)
    denied = _manage_or_403(request, classroom)
    if denied:
        return denied

    classroom.is_locked = not classroom.is_locked
    classroom.save(update_fields=["is_locked"])
    _audit(
        request,
        action="class.toggle_lock",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Toggled class lock to {classroom.is_locked}",
        metadata={"is_locked": classroom.is_locked},
    )
    return _json_no_store_response(
        {"classroom_id": classroom.id, "is_locked": classroom.is_locked},
        private=True,
    )


@require_POST
@_staff_required
@_teacher_rate_limit(limit=30, window_seconds=60)
def api_teacher_rotate_code(request, class_id: int):
    """POST /api/v1/teacher/class/<id>/rotate-code

    Generates a new join code for the class. Returns the new code.
    """
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return _json_no_store_response({"error": "not_found"}, status=404, private=True)
    denied = _manage_or_403(request, classroom)
    if denied:
        return denied

    classroom.join_code = _next_unique_class_join_code()
    classroom.save(update_fields=["join_code"])
    _audit(
        request,
        action="class.rotate_code",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary="Rotated class join code",
        metadata={"join_code": classroom.join_code},
    )
    return _json_no_store_response(
        {"classroom_id": classroom.id, "join_code": classroom.join_code},
        private=True,
    )


_VALID_ENROLLMENT_MODES = {
    Class.ENROLLMENT_OPEN,
    Class.ENROLLMENT_INVITE_ONLY,
    Class.ENROLLMENT_CLOSED,
}


@require_POST
@_staff_required
@_teacher_rate_limit(limit=30, window_seconds=60)
def api_teacher_set_enrollment_mode(request, class_id: int):
    """POST /api/v1/teacher/class/<id>/set-enrollment-mode

    Sets the enrollment mode. Accepts JSON body: {"enrollment_mode": "open"}
    """
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return _json_no_store_response({"error": "not_found"}, status=404, private=True)
    denied = _manage_or_403(request, classroom)
    if denied:
        return denied

    import json as _json
    try:
        body = _json.loads(request.body)
        enrollment_mode = (body.get("enrollment_mode") or "").strip().lower()
    except (ValueError, AttributeError):
        enrollment_mode = (request.POST.get("enrollment_mode") or "").strip().lower()

    if enrollment_mode not in _VALID_ENROLLMENT_MODES:
        return _json_no_store_response(
            {"error": "invalid_enrollment_mode", "valid_modes": sorted(_VALID_ENROLLMENT_MODES)},
            status=400,
            private=True,
        )

    old_mode = classroom.enrollment_mode
    classroom.enrollment_mode = enrollment_mode
    classroom.save(update_fields=["enrollment_mode"])
    _audit(
        request,
        action="class.set_enrollment_mode",
        classroom=classroom,
        target_type="Class",
        target_id=str(classroom.id),
        summary=f"Set class enrollment mode to {enrollment_mode}",
        metadata={"old_mode": old_mode, "enrollment_mode": enrollment_mode},
    )
    return _json_no_store_response(
        {"classroom_id": classroom.id, "enrollment_mode": enrollment_mode},
        private=True,
    )


__all__ = [
    "api_teacher_classes",
    "api_teacher_class_roster",
    "api_teacher_class_submissions",
    "api_teacher_toggle_lock",
    "api_teacher_rotate_code",
    "api_teacher_set_enrollment_mode",
]
