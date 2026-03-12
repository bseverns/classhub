"""Shared schema/constants/helpers for RBAC policy bundle normalization."""

from __future__ import annotations

from dataclasses import dataclass
import re

from ..models import (
    ClassStaffModuleScopeGrant,
    OrganizationMembership,
    OrganizationRoleCapability,
)

POLICY_SCHEMA_VERSION = "classhub.rbac_policy.v1"

ROLE_VALUES = {value for value, _label in OrganizationMembership.ROLE_CHOICES}
ORG_CAPABILITY_VALUES = {value for value, _label in OrganizationRoleCapability.CAPABILITY_CHOICES}
SCOPED_CAPABILITY_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.CAPABILITY_CHOICES}
SCOPED_EFFECT_VALUES = {value for value, _label in ClassStaffModuleScopeGrant.EFFECT_CHOICES}
CLASS_WIDE_SCOPED_CAPABILITIES = {
    ClassStaffModuleScopeGrant.CAP_ROSTER_MANAGE,
    ClassStaffModuleScopeGrant.CAP_POLICY_MANAGE,
}
SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class NormalizedPolicyRows:
    org_rows: list[dict]
    grant_rows: list[dict]
    custom_role_rows: list[dict]
    custom_role_assignment_rows: list[dict]


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_bool(value, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def join_errors(errors: list[str]) -> str:
    summary = "; ".join(errors[:3])
    if len(errors) > 3:
        summary += f" (+{len(errors) - 3} more)"
    return summary


__all__ = [
    "CLASS_WIDE_SCOPED_CAPABILITIES",
    "ORG_CAPABILITY_VALUES",
    "POLICY_SCHEMA_VERSION",
    "ROLE_VALUES",
    "SCOPED_CAPABILITY_VALUES",
    "SCOPED_EFFECT_VALUES",
    "SLUG_RE",
    "NormalizedPolicyRows",
    "as_bool",
    "join_errors",
    "safe_int",
]
