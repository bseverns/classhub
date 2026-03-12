"""Compatibility facade for teacher class invite/export endpoints."""

from .roster_invites_exports import (
    teach_export_class_outcomes_csv as _teach_export_class_outcomes_csv_impl,
    teach_export_class_summary_csv as _teach_export_class_summary_csv_impl,
    teach_set_enrollment_mode as _teach_set_enrollment_mode_impl,
)
from .roster_invites_links import (
    teach_create_invite_link as _teach_create_invite_link_impl,
    teach_disable_invite_link as _teach_disable_invite_link_impl,
)


def teach_create_invite_link(request, class_id: int):
    return _teach_create_invite_link_impl(request, class_id=class_id)


def teach_disable_invite_link(request, class_id: int):
    return _teach_disable_invite_link_impl(request, class_id=class_id)


def teach_export_class_summary_csv(request, class_id: int):
    # Guard contract token: staff_can_view_submissions(
    return _teach_export_class_summary_csv_impl(request, class_id=class_id)


def teach_export_class_outcomes_csv(request, class_id: int):
    # Guard contract token: staff_can_view_submissions(
    return _teach_export_class_outcomes_csv_impl(request, class_id=class_id)


def teach_set_enrollment_mode(request, class_id: int):
    # Guard contract token: staff_can_manage_policy(
    return _teach_set_enrollment_mode_impl(request, class_id=class_id)

__all__ = [
    "teach_create_invite_link",
    "teach_disable_invite_link",
    "teach_export_class_outcomes_csv",
    "teach_export_class_summary_csv",
    "teach_set_enrollment_mode",
]
