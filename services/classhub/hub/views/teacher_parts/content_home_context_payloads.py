"""Payload builder helpers for teacher home context assembly."""

from .content_home_context_payloads_class_forms import _build_teach_home_class_context
from .shared import (
    OrganizationMembership,
    OrganizationRoleCapability,
    Path,
    Submission,
    _AUTHORING_TEMPLATE_SUFFIXES,
    _TEMPLATE_SLUG_RE,
    staff_can_export_syllabi,
    staff_has_explicit_memberships,
)


def _recent_submissions_for_class_ids(class_ids):
    if not class_ids:
        return []
    return list(
        Submission.objects.select_related("student", "material__module__classroom")
        .filter(material__module__classroom_id__in=class_ids)[:20]
    )


def _build_template_download_rows(template_slug: str, output_dir: Path):
    rows: list[dict] = []
    if not template_slug or not _TEMPLATE_SLUG_RE.match(template_slug):
        return rows

    existing_names: set[str] = set()
    try:
        existing_names = {item.name for item in output_dir.iterdir() if item.is_file()}
    except OSError:
        existing_names = set()
    for kind, suffix in _AUTHORING_TEMPLATE_SUFFIXES.items():
        expected_name = f"{template_slug}-{suffix}"
        rows.append(
            {
                "kind": kind,
                "label": expected_name,
                "exists": expected_name in existing_names,
                "url": f"/teach/authoring-template/download?slug={template_slug}&kind={kind}",
            }
        )
    return rows


def _build_teach_home_staff_context(
    *,
    request,
    teacher_accounts,
    teacher_invite_state: dict,
    profile_state: dict,
    org_state: dict,
    initial_tab: str,
) -> dict:
    return {
        "teacher_accounts": teacher_accounts,
        "teacher_username": teacher_invite_state["teacher_username"],
        "teacher_email": teacher_invite_state["teacher_email"],
        "teacher_first_name": teacher_invite_state["teacher_first_name"],
        "teacher_last_name": teacher_invite_state["teacher_last_name"],
        "teacher_invite_active": teacher_invite_state["teacher_invite_active"],
        "data_lifespan_enabled": bool(request.user.is_superuser or staff_can_export_syllabi(request.user)),
        "initial_top_tab": initial_tab,
        "profile_first_name": profile_state["profile_first_name"],
        "profile_last_name": profile_state["profile_last_name"],
        "profile_email": profile_state["profile_email"],
        "org_name": org_state["org_name"],
        "org_membership_org_id": org_state["org_membership_org_id"],
        "org_membership_user_id": org_state["org_membership_user_id"],
        "org_membership_role": org_state["org_membership_role"] or OrganizationMembership.ROLE_TEACHER,
        "org_membership_active": org_state["org_membership_active"],
        "org_rolecap_org_id": org_state["org_rolecap_org_id"],
        "org_rolecap_role": org_state["org_rolecap_role"] or OrganizationMembership.ROLE_TEACHER,
        "org_rolecap_capability": (org_state["org_rolecap_capability"] or OrganizationRoleCapability.CAP_CLASS_VIEW),
        "org_rolecap_active": org_state["org_rolecap_active"],
        "org_membership_mode": staff_has_explicit_memberships(request.user),
    }


__all__ = [
    "_build_teach_home_class_context",
    "_build_teach_home_staff_context",
    "_build_template_download_rows",
    "_recent_submissions_for_class_ids",
]
