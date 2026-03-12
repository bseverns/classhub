"""Compatibility facade for superuser org-management endpoints."""

from .roster_orgs_membership_policy import (
    teach_upsert_org_role_capability,
    teach_upsert_organization_membership,
)
from .roster_orgs_organizations import (
    teach_create_organization,
    teach_set_organization_active,
)

__all__ = [
    "teach_create_organization",
    "teach_set_organization_active",
    "teach_upsert_org_role_capability",
    "teach_upsert_organization_membership",
]
