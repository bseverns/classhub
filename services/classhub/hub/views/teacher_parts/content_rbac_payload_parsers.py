"""RBAC payload parsers and shared validation helpers for teacher endpoints."""

from __future__ import annotations

import re

from ...models import (
    ClassStaffModuleScopeGrant,
    Organization,
    OrganizationMembership,
    OrganizationRoleCapability,
)
from .shared import (
    _parse_positive_int,
    get_user_model,
    staff_accessible_classes_ranked,
    staff_classroom_or_none,
)

SCOPED_CAPABILITY_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.CAPABILITY_CHOICES}
SIMULATION_CAPABILITY_VALUES = {value for value, _label in OrganizationRoleCapability.CAPABILITY_CHOICES}
CUSTOM_ROLE_CAPABILITY_VALUES = {value for value, _label in OrganizationRoleCapability.CAPABILITY_CHOICES}
EFFECT_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.EFFECT_CHOICES}
CUSTOM_ROLE_SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


def resolve_staff_user(user_id_raw: str):
    user_id = _parse_positive_int(user_id_raw, min_value=1, max_value=2_147_483_647)
    if user_id is None:
        return None
    User = get_user_model()
    return User.objects.filter(id=user_id, is_staff=True, is_active=True).only("id", "username", "is_superuser").first()


def target_user_has_org_membership(user, *, organization_id: int | None) -> bool:
    if user.is_superuser:
        return True
    if not organization_id:
        return True
    return OrganizationMembership.objects.filter(
        user=user,
        organization_id=organization_id,
        is_active=True,
        organization__is_active=True,
    ).exists()


def accessible_org_ids_for_user(user) -> set[int]:
    classes, _assigned = staff_accessible_classes_ranked(user)
    return {int(c.organization_id) for c in classes if c.organization_id}


def resolve_accessible_org_for_user(user, org_id_raw: str):
    org_id = _parse_positive_int(org_id_raw, min_value=1, max_value=2_147_483_647)
    if org_id is None:
        return None
    accessible_org_ids = accessible_org_ids_for_user(user)
    if org_id not in accessible_org_ids:
        return None
    return Organization.objects.filter(id=org_id, is_active=True).only("id", "name").first()


def parse_scope_grant_payload(request):
    classroom = staff_classroom_or_none(request.user, request.POST.get("rbac_class_id"))
    if classroom is None:
        return None, "Class is required."

    target_user = resolve_staff_user(request.POST.get("rbac_user_id") or "")
    if target_user is None:
        return None, "Staff user is required."
    if not target_user_has_org_membership(target_user, organization_id=classroom.organization_id):
        return None, "Target user must be active in the class organization."

    capability = (request.POST.get("rbac_capability") or "").strip()
    if capability not in SCOPED_CAPABILITY_VALUES:
        return None, "Unsupported scoped-grant capability."

    effect = (request.POST.get("rbac_effect") or "").strip()
    if effect not in EFFECT_VALUES:
        return None, "Unsupported grant effect."

    module_start = _parse_positive_int(request.POST.get("rbac_module_start") or "", min_value=0, max_value=50_000)
    module_end = _parse_positive_int(request.POST.get("rbac_module_end") or "", min_value=0, max_value=50_000)
    if module_start is None or module_end is None:
        return None, "Module range must be whole numbers."
    if module_end < module_start:
        return None, "Module end must be greater than or equal to module start."
    return {
        "classroom_id": int(classroom.id),
        "target_user_id": int(target_user.id),
        "capability": capability,
        "effect": effect,
        "module_start": module_start,
        "module_end": module_end,
        "is_active": (request.POST.get("rbac_grant_active") or "0").strip() == "1",
    }, ""


def parse_custom_role_upsert_payload(request):
    org = resolve_accessible_org_for_user(request.user, request.POST.get("rbac_custom_role_org_id") or "")
    if org is None:
        return None, "Organization is required."
    slug = (request.POST.get("rbac_custom_role_slug") or "").strip().lower()
    if not CUSTOM_ROLE_SLUG_RE.match(slug):
        return None, "Custom role slug must match [a-z0-9_-] and be <=64 chars."
    name = (request.POST.get("rbac_custom_role_name") or "").strip()
    if not name:
        return None, "Custom role name is required."
    description = (request.POST.get("rbac_custom_role_description") or "").strip()
    return {
        "organization_id": int(org.id),
        "slug": slug,
        "name": name[:120],
        "description": description[:500],
        "is_active": (request.POST.get("rbac_custom_role_active") or "0").strip() == "1",
    }, ""


def parse_custom_role_capability_payload(request):
    org = resolve_accessible_org_for_user(request.user, request.POST.get("rbac_custom_role_cap_org_id") or "")
    if org is None:
        return None, "Organization is required."
    slug = (request.POST.get("rbac_custom_role_cap_slug") or "").strip().lower()
    if not CUSTOM_ROLE_SLUG_RE.match(slug):
        return None, "Role slug is required."
    capability = (request.POST.get("rbac_custom_role_capability") or "").strip().lower()
    if capability not in CUSTOM_ROLE_CAPABILITY_VALUES:
        return None, "Select a valid capability."
    return {
        "organization_id": int(org.id),
        "slug": slug,
        "capability": capability,
        "is_active": (request.POST.get("rbac_custom_role_cap_active") or "0").strip() == "1",
    }, ""


def parse_custom_role_assignment_payload(request):
    org = resolve_accessible_org_for_user(request.user, request.POST.get("rbac_custom_role_assign_org_id") or "")
    if org is None:
        return None, "Organization is required."
    slug = (request.POST.get("rbac_custom_role_assign_slug") or "").strip().lower()
    if not CUSTOM_ROLE_SLUG_RE.match(slug):
        return None, "Role slug is required."
    target_user = resolve_staff_user(request.POST.get("rbac_custom_role_assign_user_id") or "")
    if target_user is None:
        return None, "Staff user is required."
    if not target_user_has_org_membership(target_user, organization_id=int(org.id)):
        return None, "Target user must be active in the selected organization."
    return {
        "organization_id": int(org.id),
        "slug": slug,
        "target_user_id": int(target_user.id),
        "is_active": (request.POST.get("rbac_custom_role_assign_active") or "0").strip() == "1",
    }, ""


def parse_simulation_payload(request):
    target_user = resolve_staff_user(request.POST.get("rbac_sim_user_id") or "")
    if target_user is None:
        return None, "Simulation target staff user is required."

    capability = (request.POST.get("rbac_sim_capability") or "").strip().lower()
    if capability not in SIMULATION_CAPABILITY_VALUES:
        return None, "Simulation capability is invalid."

    classroom = None
    class_id_raw = (request.POST.get("rbac_sim_class_id") or "").strip()
    if class_id_raw:
        classroom = staff_classroom_or_none(request.user, class_id_raw)
        if classroom is None:
            return None, "Simulation class not found."

    module_id = None
    module_id_raw = (request.POST.get("rbac_sim_module_id") or "").strip()
    if module_id_raw:
        module_id = _parse_positive_int(module_id_raw, min_value=1, max_value=2_147_483_647)
        if module_id is None:
            return None, "Simulation module id must be a positive integer."
        if classroom is None:
            return None, "Simulation module scope requires a class."
    return {
        "target_user": target_user,
        "capability": capability,
        "classroom": classroom,
        "module_id": module_id,
    }, ""


__all__ = [
    "CUSTOM_ROLE_CAPABILITY_VALUES",
    "CUSTOM_ROLE_SLUG_RE",
    "EFFECT_VALUES",
    "SCOPED_CAPABILITY_VALUES",
    "SIMULATION_CAPABILITY_VALUES",
    "parse_custom_role_assignment_payload",
    "parse_custom_role_capability_payload",
    "parse_custom_role_upsert_payload",
    "parse_scope_grant_payload",
    "parse_simulation_payload",
    "resolve_accessible_org_for_user",
    "resolve_staff_user",
    "target_user_has_org_membership",
]
