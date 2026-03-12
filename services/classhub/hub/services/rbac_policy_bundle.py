"""RBAC policy-as-code bundle import/export helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .rbac_policy_bundle_apply import apply_normalized_policy_rows
from .rbac_policy_bundle_normalize import (
    POLICY_SCHEMA_VERSION,
    build_policy_export_payload,
    normalize_payload_for_actor,
)


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


def build_rbac_policy_export_payload(actor_user, *, exported_at: str) -> RbacPolicyExportResult:
    payload = build_policy_export_payload(actor_user, exported_at=exported_at)
    return RbacPolicyExportResult(
        payload=payload,
        organization_count=len(payload["organizations"]),
        scoped_grant_count=len(payload["scoped_grants"]),
        custom_role_count=len(payload["custom_roles"]),
        custom_role_assignment_count=len(payload["custom_role_assignments"]),
    )


def validate_rbac_policy_payload(*, actor_user, payload: dict) -> RbacPolicyValidationResult:
    normalized = normalize_payload_for_actor(actor_user=actor_user, payload=payload)
    return RbacPolicyValidationResult(
        org_rows=len(normalized.org_rows),
        grant_rows=len(normalized.grant_rows),
        custom_role_rows=len(normalized.custom_role_rows),
        custom_role_assignment_rows=len(normalized.custom_role_assignment_rows),
    )


def apply_rbac_policy_payload(*, actor_user, payload: dict, source_label: str) -> RbacPolicyImportResult:
    normalized = normalize_payload_for_actor(actor_user=actor_user, payload=payload)
    counts = apply_normalized_policy_rows(normalized)
    return RbacPolicyImportResult(
        source_label=source_label,
        org_rows=len(normalized.org_rows),
        grant_rows=len(normalized.grant_rows),
        custom_role_rows=len(normalized.custom_role_rows),
        custom_role_assignment_rows=len(normalized.custom_role_assignment_rows),
        org_created=counts["org_created"],
        org_updated=counts["org_updated"],
        grant_created=counts["grant_created"],
        grant_updated=counts["grant_updated"],
        custom_role_created=counts["custom_role_created"],
        custom_role_updated=counts["custom_role_updated"],
        custom_role_capability_created=counts["custom_role_capability_created"],
        custom_role_capability_updated=counts["custom_role_capability_updated"],
        custom_role_assignment_created=counts["custom_role_assignment_created"],
        custom_role_assignment_updated=counts["custom_role_assignment_updated"],
    )


__all__ = [
    "POLICY_SCHEMA_VERSION",
    "RbacPolicyExportResult",
    "RbacPolicyImportResult",
    "RbacPolicyValidationResult",
    "apply_rbac_policy_payload",
    "build_rbac_policy_export_payload",
    "validate_rbac_policy_payload",
]
