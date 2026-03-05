"""RBAC policy-as-code bundle import/export helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re

from django.contrib.auth import get_user_model
from django.db import transaction

from ..models import (
    ClassStaffModuleScopeGrant,
    Organization,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationCustomRoleCapability,
    OrganizationMembership,
    OrganizationRoleCapability,
)
from .org_access import staff_accessible_classes_ranked


POLICY_SCHEMA_VERSION = "classhub.rbac_policy.v1"

_ROLE_VALUES = {value for value, _label in OrganizationMembership.ROLE_CHOICES}
_ORG_CAPABILITY_VALUES = {value for value, _label in OrganizationRoleCapability.CAPABILITY_CHOICES}
_SCOPED_CAPABILITY_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.CAPABILITY_CHOICES}
_SCOPED_EFFECT_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.EFFECT_CHOICES}
_CLASS_WIDE_SCOPED_CAPABILITIES = {
    ClassStaffModuleScopeGrant.CAP_ROSTER_MANAGE,
    ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
}
_SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class RbacPolicyExportResult:
    payload: dict
    organization_count: int
    scoped_grant_count: int
    custom_role_count: int
    custom_role_assignment_count: int


@dataclass(frozen=True)
class RbacPolicyImportResult:
    source_label: str
    org_rows: int
    grant_rows: int
    custom_role_rows: int
    custom_role_assignment_rows: int
    org_created: int
    org_updated: int
    grant_created: int
    grant_updated: int
    custom_role_created: int
    custom_role_updated: int
    custom_role_capability_created: int
    custom_role_capability_updated: int
    custom_role_assignment_created: int
    custom_role_assignment_updated: int


@dataclass(frozen=True)
class RbacPolicyValidationResult:
    org_rows: int
    grant_rows: int
    custom_role_rows: int
    custom_role_assignment_rows: int


@dataclass(frozen=True)
class _NormalizedPolicyRows:
    org_rows: list[dict]
    grant_rows: list[dict]
    custom_role_rows: list[dict]
    custom_role_assignment_rows: list[dict]


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _allowed_orgs_for_actor(user):
    if user.is_superuser:
        return list(Organization.objects.filter(is_active=True).only("id", "name").order_by("name", "id"))
    return list(
        Organization.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
            is_active=True,
        )
        .distinct()
        .only("id", "name")
        .order_by("name", "id")
    )


def _class_map_for_actor(user):
    classes, _assigned = staff_accessible_classes_ranked(user)
    return {str(c.join_code or "").upper(): c for c in classes if c.join_code}


def _target_user_has_org_membership(user, *, classroom) -> bool:
    if user.is_superuser:
        return True
    if not classroom.organization_id:
        return True
    return OrganizationMembership.objects.filter(
        user=user,
        organization_id=classroom.organization_id,
        is_active=True,
        organization__is_active=True,
    ).exists()


def _target_user_has_org_membership_by_org_id(user, *, organization_id: int | None) -> bool:
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


def _role_capability_payload(org_rows):
    grouped: dict[int, dict] = {}
    for row in org_rows:
        bucket = grouped.setdefault(
            int(row.organization_id),
            {
                "name": row.organization.name,
                "role_capabilities": [],
            },
        )
        bucket["role_capabilities"].append(
            {
                "role": row.role,
                "capability": row.capability,
                "is_active": bool(row.is_active),
            }
        )
    return list(grouped.values())


def _scoped_grant_payload(grant_rows):
    payload = []
    for row in grant_rows:
        payload.append(
            {
                "class_join_code": row.classroom.join_code,
                "class_name": row.classroom.name,
                "username": row.user.username,
                "capability": row.capability,
                "effect": row.effect,
                "module_order_start": int(row.module_order_start),
                "module_order_end": int(row.module_order_end),
                "is_active": bool(row.is_active),
            }
        )
    return payload


def _custom_role_payload(rows):
    payload = []
    for row in rows:
        payload.append(
            {
                "organization_name": row.organization.name,
                "slug": row.slug,
                "name": row.name,
                "description": row.description,
                "is_active": bool(row.is_active),
                "capabilities": [
                    {
                        "capability": cap.capability,
                        "is_active": bool(cap.is_active),
                    }
                    for cap in row.capabilities.all()
                ],
            }
        )
    return payload


def _custom_role_assignment_payload(rows):
    payload = []
    for row in rows:
        payload.append(
            {
                "organization_name": row.organization.name,
                "role_slug": row.role.slug,
                "username": row.user.username,
                "is_active": bool(row.is_active),
            }
        )
    return payload


def build_rbac_policy_export_payload(actor_user, *, exported_at: str) -> RbacPolicyExportResult:
    classes, _assigned = staff_accessible_classes_ranked(actor_user)
    class_ids = [int(c.id) for c in classes]
    org_ids = sorted({int(c.organization_id) for c in classes if c.organization_id})
    role_caps = list(
        OrganizationRoleCapability.objects.select_related("organization")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "role", "capability", "id")
    )
    scope_grants = list(
        ClassStaffModuleScopeGrant.objects.select_related("classroom", "user")
        .filter(classroom_id__in=class_ids)
        .order_by(
            "classroom__name",
            "user__username",
            "capability",
            "effect",
            "module_order_start",
            "module_order_end",
            "id",
        )
    )
    custom_roles = list(
        OrganizationCustomRole.objects.select_related("organization")
        .prefetch_related("capabilities")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "slug", "id")
    )
    custom_role_assignments = list(
        OrganizationCustomRoleAssignment.objects.select_related("organization", "role", "user")
        .filter(organization_id__in=org_ids)
        .order_by("organization__name", "role__slug", "user__username", "id")
    )
    payload = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "exported_at": exported_at,
        "exported_by": actor_user.username,
        "organizations": _role_capability_payload(role_caps),
        "scoped_grants": _scoped_grant_payload(scope_grants),
        "custom_roles": _custom_role_payload(custom_roles),
        "custom_role_assignments": _custom_role_assignment_payload(custom_role_assignments),
    }
    return RbacPolicyExportResult(
        payload=payload,
        organization_count=len(payload["organizations"]),
        scoped_grant_count=len(payload["scoped_grants"]),
        custom_role_count=len(payload["custom_roles"]),
        custom_role_assignment_count=len(payload["custom_role_assignments"]),
    )


def _normalized_org_rows(*, payload: dict, allowed_orgs_by_name: dict[str, Organization]):
    rows = payload.get("organizations") or []
    if not isinstance(rows, list):
        raise ValueError("organizations must be a list.")
    normalized = []
    errors: list[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            errors.append(f"organizations[{index}] must be an object.")
            continue
        org_name = str(item.get("name") or "").strip()
        if not org_name:
            errors.append(f"organizations[{index}].name is required.")
            continue
        org = allowed_orgs_by_name.get(org_name.lower())
        if org is None:
            errors.append(f"organizations[{index}] is not accessible: {org_name}.")
            continue
        caps = item.get("role_capabilities") or []
        if not isinstance(caps, list):
            errors.append(f"organizations[{index}].role_capabilities must be a list.")
            continue
        for cap_idx, cap_row in enumerate(caps):
            if not isinstance(cap_row, dict):
                errors.append(f"organizations[{index}].role_capabilities[{cap_idx}] must be an object.")
                continue
            role = str(cap_row.get("role") or "").strip()
            capability = str(cap_row.get("capability") or "").strip().lower()
            is_active = _as_bool(cap_row.get("is_active"), default=True)
            if role not in _ROLE_VALUES:
                errors.append(f"organizations[{index}].role_capabilities[{cap_idx}] invalid role {role!r}.")
                continue
            if capability not in _ORG_CAPABILITY_VALUES:
                errors.append(
                    f"organizations[{index}].role_capabilities[{cap_idx}] invalid capability {capability!r}."
                )
                continue
            normalized.append(
                {
                    "organization": org,
                    "role": role,
                    "capability": capability,
                    "is_active": is_active,
                }
            )
    if errors:
        raise ValueError(_join_errors(errors))
    return normalized


def _normalized_scope_rows(*, payload: dict, class_by_join: dict[str, object], user_by_username: dict[str, object]):
    rows = payload.get("scoped_grants") or []
    if not isinstance(rows, list):
        raise ValueError("scoped_grants must be a list.")
    normalized = []
    errors: list[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            errors.append(f"scoped_grants[{index}] must be an object.")
            continue
        join_code = str(item.get("class_join_code") or "").strip().upper()
        username = str(item.get("username") or "").strip()
        capability = str(item.get("capability") or "").strip().lower()
        effect = str(item.get("effect") or "").strip().lower()
        module_start = _safe_int(item.get("module_order_start"))
        module_end = _safe_int(item.get("module_order_end"))
        is_active = _as_bool(item.get("is_active"), default=True)
        classroom = class_by_join.get(join_code)
        if classroom is None:
            errors.append(f"scoped_grants[{index}] class_join_code is unknown/inaccessible: {join_code!r}.")
            continue
        user = user_by_username.get(username)
        if user is None:
            errors.append(f"scoped_grants[{index}] username not found: {username!r}.")
            continue
        if not _target_user_has_org_membership(user, classroom=classroom):
            errors.append(f"scoped_grants[{index}] user {username!r} lacks active org membership for class {join_code}.")
            continue
        if capability not in _SCOPED_CAPABILITY_VALUES:
            errors.append(f"scoped_grants[{index}] invalid capability {capability!r}.")
            continue
        if effect not in _SCOPED_EFFECT_VALUES:
            errors.append(f"scoped_grants[{index}] invalid effect {effect!r}.")
            continue
        if module_start is None or module_end is None or module_start < 0 or module_end < 0 or module_end < module_start:
            errors.append(f"scoped_grants[{index}] invalid module range.")
            continue
        if capability in _CLASS_WIDE_SCOPED_CAPABILITIES and (module_start != 0 or module_end != 0):
            errors.append(
                f"scoped_grants[{index}] {capability} must use module_order_start=0 and module_order_end=0."
            )
            continue
        normalized.append(
            {
                "classroom": classroom,
                "user": user,
                "capability": capability,
                "effect": effect,
                "module_order_start": module_start,
                "module_order_end": module_end,
                "is_active": is_active,
            }
        )
    if errors:
        raise ValueError(_join_errors(errors))
    return normalized


def _normalized_custom_role_rows(*, payload: dict, allowed_orgs_by_name: dict[str, Organization]):
    rows = payload.get("custom_roles") or []
    if not isinstance(rows, list):
        raise ValueError("custom_roles must be a list.")
    normalized = []
    errors: list[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            errors.append(f"custom_roles[{index}] must be an object.")
            continue
        org_name = str(item.get("organization_name") or "").strip()
        org = allowed_orgs_by_name.get(org_name.lower())
        if org is None:
            errors.append(f"custom_roles[{index}] organization_name is unknown/inaccessible: {org_name!r}.")
            continue
        slug = str(item.get("slug") or "").strip().lower()
        if not _SLUG_RE.match(slug):
            errors.append(f"custom_roles[{index}] slug must match [a-z0-9_-] and be <=64 chars.")
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            errors.append(f"custom_roles[{index}] name is required.")
            continue
        description = str(item.get("description") or "").strip()
        is_active = _as_bool(item.get("is_active"), default=True)
        caps = item.get("capabilities") or []
        if not isinstance(caps, list):
            errors.append(f"custom_roles[{index}].capabilities must be a list.")
            continue
        normalized_caps = []
        for cap_index, cap in enumerate(caps):
            if not isinstance(cap, dict):
                errors.append(f"custom_roles[{index}].capabilities[{cap_index}] must be an object.")
                continue
            capability = str(cap.get("capability") or "").strip().lower()
            if capability not in _ORG_CAPABILITY_VALUES:
                errors.append(f"custom_roles[{index}].capabilities[{cap_index}] invalid capability {capability!r}.")
                continue
            normalized_caps.append(
                {
                    "capability": capability,
                    "is_active": _as_bool(cap.get("is_active"), default=True),
                }
            )
        normalized.append(
            {
                "organization": org,
                "slug": slug,
                "name": name[:120],
                "description": description[:500],
                "is_active": is_active,
                "capabilities": normalized_caps,
            }
        )
    if errors:
        raise ValueError(_join_errors(errors))
    return normalized


def _normalized_custom_role_assignment_rows(
    *,
    payload: dict,
    allowed_orgs_by_name: dict[str, Organization],
    user_by_username: dict[str, object],
    custom_role_rows: list[dict],
):
    rows = payload.get("custom_role_assignments") or []
    if not isinstance(rows, list):
        raise ValueError("custom_role_assignments must be a list.")
    imported_role_keys = {
        (int(row["organization"].id), str(row["slug"]))
        for row in custom_role_rows
    }
    needed_role_keys = set(imported_role_keys)
    staged: list[dict] = []
    errors: list[str] = []
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            errors.append(f"custom_role_assignments[{index}] must be an object.")
            continue
        org_name = str(item.get("organization_name") or "").strip()
        org = allowed_orgs_by_name.get(org_name.lower())
        if org is None:
            errors.append(
                f"custom_role_assignments[{index}] organization_name is unknown/inaccessible: {org_name!r}."
            )
            continue
        role_slug = str(item.get("role_slug") or "").strip().lower()
        if not _SLUG_RE.match(role_slug):
            errors.append(f"custom_role_assignments[{index}] role_slug must match [a-z0-9_-] and be <=64 chars.")
            continue
        username = str(item.get("username") or "").strip()
        user = user_by_username.get(username)
        if user is None:
            errors.append(f"custom_role_assignments[{index}] username not found: {username!r}.")
            continue
        if not _target_user_has_org_membership_by_org_id(user, organization_id=int(org.id)):
            errors.append(
                f"custom_role_assignments[{index}] user {username!r} lacks active org membership for {org_name!r}."
            )
            continue
        role_key = (int(org.id), role_slug)
        needed_role_keys.add(role_key)
        staged.append(
            {
                "organization": org,
                "role_slug": role_slug,
                "user": user,
                "is_active": _as_bool(item.get("is_active"), default=True),
            }
        )
    existing_rows = OrganizationCustomRole.objects.filter(
        organization_id__in=[org_id for org_id, _slug in needed_role_keys]
    ).values_list("organization_id", "slug")
    existing_role_keys = {(int(org_id), str(slug)) for org_id, slug in existing_rows}
    normalized = []
    for index, row in enumerate(staged):
        role_key = (int(row["organization"].id), row["role_slug"])
        if role_key not in imported_role_keys and role_key not in existing_role_keys:
            errors.append(
                f"custom_role_assignments[{index}] role not found for organization/slug: {row['role_slug']!r}."
            )
            continue
        normalized.append(row)
    if errors:
        raise ValueError(_join_errors(errors))
    return normalized


def _join_errors(errors: list[str]) -> str:
    summary = "; ".join(errors[:3])
    if len(errors) > 3:
        summary += f" (+{len(errors) - 3} more)"
    return summary


def _normalize_payload_for_actor(*, actor_user, payload: dict) -> _NormalizedPolicyRows:
    if not isinstance(payload, dict):
        raise ValueError("Policy JSON root must be an object.")
    schema_version = str(payload.get("schema_version") or "").strip()
    if schema_version and schema_version != POLICY_SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version {schema_version!r}.")

    allowed_orgs = _allowed_orgs_for_actor(actor_user)
    allowed_orgs_by_name = {str(org.name).strip().lower(): org for org in allowed_orgs}
    User = get_user_model()
    users = User.objects.filter(is_staff=True).only("id", "username", "is_superuser")
    user_by_username = {str(u.username): u for u in users}
    class_by_join = _class_map_for_actor(actor_user)

    org_rows = _normalized_org_rows(payload=payload, allowed_orgs_by_name=allowed_orgs_by_name)
    custom_role_rows = _normalized_custom_role_rows(payload=payload, allowed_orgs_by_name=allowed_orgs_by_name)
    grant_rows = _normalized_scope_rows(
        payload=payload,
        class_by_join=class_by_join,
        user_by_username=user_by_username,
    )
    custom_role_assignment_rows = _normalized_custom_role_assignment_rows(
        payload=payload,
        allowed_orgs_by_name=allowed_orgs_by_name,
        user_by_username=user_by_username,
        custom_role_rows=custom_role_rows,
    )
    return _NormalizedPolicyRows(
        org_rows=org_rows,
        grant_rows=grant_rows,
        custom_role_rows=custom_role_rows,
        custom_role_assignment_rows=custom_role_assignment_rows,
    )


def validate_rbac_policy_payload(*, actor_user, payload: dict) -> RbacPolicyValidationResult:
    normalized = _normalize_payload_for_actor(actor_user=actor_user, payload=payload)
    return RbacPolicyValidationResult(
        org_rows=len(normalized.org_rows),
        grant_rows=len(normalized.grant_rows),
        custom_role_rows=len(normalized.custom_role_rows),
        custom_role_assignment_rows=len(normalized.custom_role_assignment_rows),
    )


def apply_rbac_policy_payload(*, actor_user, payload: dict, source_label: str) -> RbacPolicyImportResult:
    normalized = _normalize_payload_for_actor(actor_user=actor_user, payload=payload)
    org_rows = normalized.org_rows
    grant_rows = normalized.grant_rows
    custom_role_rows = normalized.custom_role_rows
    custom_role_assignment_rows = normalized.custom_role_assignment_rows

    org_created = 0
    org_updated = 0
    grant_created = 0
    grant_updated = 0
    custom_role_created = 0
    custom_role_updated = 0
    custom_role_capability_created = 0
    custom_role_capability_updated = 0
    custom_role_assignment_created = 0
    custom_role_assignment_updated = 0
    with transaction.atomic():
        for row in org_rows:
            obj, created = OrganizationRoleCapability.objects.get_or_create(
                organization=row["organization"],
                role=row["role"],
                capability=row["capability"],
                defaults={"is_active": row["is_active"]},
            )
            if created:
                org_created += 1
                continue
            if obj.is_active != row["is_active"]:
                obj.is_active = row["is_active"]
                obj.save(update_fields=["is_active", "updated_at"])
                org_updated += 1
        role_by_key: dict[tuple[int, str], OrganizationCustomRole] = {}
        for row in custom_role_rows:
            role_obj, created = OrganizationCustomRole.objects.get_or_create(
                organization=row["organization"],
                slug=row["slug"],
                defaults={
                    "name": row["name"],
                    "description": row["description"],
                    "is_active": row["is_active"],
                },
            )
            role_by_key[(int(role_obj.organization_id), str(role_obj.slug))] = role_obj
            if created:
                custom_role_created += 1
            else:
                changed_fields: list[str] = []
                if role_obj.name != row["name"]:
                    role_obj.name = row["name"]
                    changed_fields.append("name")
                if role_obj.description != row["description"]:
                    role_obj.description = row["description"]
                    changed_fields.append("description")
                if role_obj.is_active != row["is_active"]:
                    role_obj.is_active = row["is_active"]
                    changed_fields.append("is_active")
                if changed_fields:
                    role_obj.save(update_fields=changed_fields + ["updated_at"])
                    custom_role_updated += 1
            for capability_row in row["capabilities"]:
                cap_obj, cap_created = OrganizationCustomRoleCapability.objects.get_or_create(
                    role=role_obj,
                    capability=capability_row["capability"],
                    defaults={"is_active": capability_row["is_active"]},
                )
                if cap_created:
                    custom_role_capability_created += 1
                    continue
                if cap_obj.is_active != capability_row["is_active"]:
                    cap_obj.is_active = capability_row["is_active"]
                    cap_obj.save(update_fields=["is_active", "updated_at"])
                    custom_role_capability_updated += 1
        assignment_missing_keys = {
            (int(row["organization"].id), row["role_slug"])
            for row in custom_role_assignment_rows
            if (int(row["organization"].id), row["role_slug"]) not in role_by_key
        }
        if assignment_missing_keys:
            existing_roles = OrganizationCustomRole.objects.filter(
                organization_id__in=[org_id for org_id, _slug in assignment_missing_keys],
                slug__in=[slug for _org_id, slug in assignment_missing_keys],
            )
            for role in existing_roles:
                role_by_key[(int(role.organization_id), str(role.slug))] = role
        for row in custom_role_assignment_rows:
            role_obj = role_by_key.get((int(row["organization"].id), row["role_slug"]))
            if role_obj is None:
                raise ValueError(f"Role missing for assignment: {row['organization'].name}/{row['role_slug']}.")
            assignment_obj, assignment_created = OrganizationCustomRoleAssignment.objects.get_or_create(
                organization=row["organization"],
                user=row["user"],
                role=role_obj,
                defaults={"is_active": row["is_active"]},
            )
            if assignment_created:
                custom_role_assignment_created += 1
                continue
            if assignment_obj.is_active != row["is_active"]:
                assignment_obj.is_active = row["is_active"]
                assignment_obj.save(update_fields=["is_active", "updated_at"])
                custom_role_assignment_updated += 1
        for row in grant_rows:
            obj, created = ClassStaffModuleScopeGrant.objects.get_or_create(
                classroom=row["classroom"],
                user=row["user"],
                capability=row["capability"],
                effect=row["effect"],
                module_order_start=row["module_order_start"],
                module_order_end=row["module_order_end"],
                defaults={"is_active": row["is_active"]},
            )
            if created:
                grant_created += 1
                continue
            if obj.is_active != row["is_active"]:
                obj.is_active = row["is_active"]
                obj.save(update_fields=["is_active", "updated_at"])
                grant_updated += 1
    return RbacPolicyImportResult(
        source_label=source_label,
        org_rows=len(org_rows),
        grant_rows=len(grant_rows),
        custom_role_rows=len(custom_role_rows),
        custom_role_assignment_rows=len(custom_role_assignment_rows),
        org_created=org_created,
        org_updated=org_updated,
        grant_created=grant_created,
        grant_updated=grant_updated,
        custom_role_created=custom_role_created,
        custom_role_updated=custom_role_updated,
        custom_role_capability_created=custom_role_capability_created,
        custom_role_capability_updated=custom_role_capability_updated,
        custom_role_assignment_created=custom_role_assignment_created,
        custom_role_assignment_updated=custom_role_assignment_updated,
    )
