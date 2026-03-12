"""Apply normalized RBAC policy rows to persistence."""

from __future__ import annotations

from django.db import transaction

from ..models import (
    ClassStaffModuleScopeGrant,
    OrganizationCustomRole,
    OrganizationCustomRoleAssignment,
    OrganizationCustomRoleCapability,
    OrganizationRoleCapability,
)
from .rbac_policy_bundle_normalize import NormalizedPolicyRows


def apply_normalized_policy_rows(normalized: NormalizedPolicyRows) -> dict[str, int]:
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
        for row in normalized.org_rows:
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
        for row in normalized.custom_role_rows:
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
            for row in normalized.custom_role_assignment_rows
            if (int(row["organization"].id), row["role_slug"]) not in role_by_key
        }
        if assignment_missing_keys:
            existing_roles = OrganizationCustomRole.objects.filter(
                organization_id__in=[org_id for org_id, _slug in assignment_missing_keys],
                slug__in=[slug for _org_id, slug in assignment_missing_keys],
            )
            for role in existing_roles:
                role_by_key[(int(role.organization_id), str(role.slug))] = role
        for row in normalized.custom_role_assignment_rows:
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
        for row in normalized.grant_rows:
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
    return {
        "org_created": org_created,
        "org_updated": org_updated,
        "grant_created": grant_created,
        "grant_updated": grant_updated,
        "custom_role_created": custom_role_created,
        "custom_role_updated": custom_role_updated,
        "custom_role_capability_created": custom_role_capability_created,
        "custom_role_capability_updated": custom_role_capability_updated,
        "custom_role_assignment_created": custom_role_assignment_created,
        "custom_role_assignment_updated": custom_role_assignment_updated,
    }


__all__ = ["apply_normalized_policy_rows"]
