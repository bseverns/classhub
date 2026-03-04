"""RBAC simulation API endpoints for teacher/operator debugging."""

import json

from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST

from ..services.org_access import evaluate_staff_capability, staff_can_export_syllabi, staff_classroom_or_none
from .api_teacher import _json_no_store_response, _staff_required, _teacher_rate_limit
from .teacher_parts.shared_routing import _audit

User = get_user_model()


def _rbac_simulation_or_403(request):
    """Return a 403 JSON response if user lacks org-level RBAC simulation rights."""
    if not staff_can_export_syllabi(request.user):
        return _json_no_store_response({"error": "forbidden"}, status=403, private=True)
    return None


def _parse_optional_positive_int(raw_value):
    if raw_value in (None, ""):
        return None
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return -1
    return parsed if parsed > 0 else -1


def _parse_simulation_request(request):
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    return {
        "user_id": _parse_optional_positive_int(body.get("user_id") or request.POST.get("user_id")),
        "capability": str(body.get("capability") or request.POST.get("capability") or "").strip().lower(),
        "class_id": _parse_optional_positive_int(body.get("class_id") or request.POST.get("class_id")),
        "module_id": _parse_optional_positive_int(body.get("module_id") or request.POST.get("module_id")),
    }


def _invalid_param_response(parsed):
    if parsed["user_id"] is None:
        return _json_no_store_response({"error": "user_id_required"}, status=400, private=True)
    if parsed["user_id"] <= 0:
        return _json_no_store_response({"error": "invalid_user_id"}, status=400, private=True)
    if not parsed["capability"]:
        return _json_no_store_response({"error": "capability_required"}, status=400, private=True)
    if parsed["class_id"] is not None and parsed["class_id"] <= 0:
        return _json_no_store_response({"error": "invalid_class_id"}, status=400, private=True)
    if parsed["module_id"] is not None and parsed["module_id"] <= 0:
        return _json_no_store_response({"error": "invalid_module_id"}, status=400, private=True)
    if parsed["module_id"] is not None and parsed["class_id"] is None:
        return _json_no_store_response({"error": "module_scope_requires_class_id"}, status=400, private=True)
    return None


def _decision_payload(decision):
    return {
        "allowed": bool(decision.allowed),
        "capability": decision.capability,
        "reason": decision.reason,
        "role": decision.role,
        "organization_id": decision.organization_id,
        "classroom_id": decision.classroom_id,
        "module_id": decision.module_id,
    }


@require_POST
@_staff_required
@_teacher_rate_limit(limit=30, window_seconds=60)
def api_teacher_rbac_simulate(request):
    """POST /api/v1/teacher/rbac/simulate (read-only decision simulation)."""
    denied = _rbac_simulation_or_403(request)
    if denied:
        return denied

    parsed = _parse_simulation_request(request)
    invalid = _invalid_param_response(parsed)
    if invalid:
        return invalid

    target_user = User.objects.filter(id=parsed["user_id"], is_staff=True).only("id", "username").first()
    if target_user is None:
        return _json_no_store_response({"error": "target_staff_user_not_found"}, status=404, private=True)

    classroom = None
    if parsed["class_id"] is not None:
        classroom = staff_classroom_or_none(request.user, parsed["class_id"])
        if classroom is None:
            return _json_no_store_response({"error": "class_not_found"}, status=404, private=True)

    decision = evaluate_staff_capability(
        target_user,
        parsed["capability"],
        classroom=classroom,
        module_id=parsed["module_id"],
    )
    payload = _decision_payload(decision)
    _audit(
        request,
        action="rbac.simulate",
        classroom=classroom,
        target_type="User",
        target_id=str(target_user.id),
        summary=f"Simulated RBAC decision for user {target_user.id} capability {parsed['capability']}",
        metadata={**parsed, "simulated_user_id": target_user.id, "decision": payload},
    )
    return _json_no_store_response(
        {
            "target_user": {"id": target_user.id, "username": target_user.username},
            "decision": payload,
        },
        private=True,
    )


__all__ = ["api_teacher_rbac_simulate"]
