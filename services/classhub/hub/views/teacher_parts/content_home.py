"""Teacher home and authoring template endpoints."""

from .content_operator_config import build_operator_config_snapshot
from .content_rbac_tools import (
    build_rbac_tools_context,
    rbac_tools_enabled_for_user,
    rbac_tools_requested,
)
from .content_syllabus_exports import build_syllabus_export_state
from .shared import (
    Class,
    ClassStaffAssignment,
    FileResponse,
    HttpResponse,
    Path,
    Organization,
    OrganizationRoleCapability,
    OrganizationMembership,
    Submission,
    _AUTHORING_TEMPLATE_SUFFIXES,
    _TEMPLATE_SLUG_RE,
    _audit,
    _authoring_template_output_dir,
    _build_class_digest_rows,
    _parse_positive_int,
    _resolve_authoring_template_download_path,
    _safe_internal_redirect,
    _with_notice,
    apply_download_safety,
    apply_no_store,
    generate_authoring_templates,
    get_user_model,
    render,
    require_POST,
    safe_attachment_filename,
    settings,
    models,
    staff_accessible_classes_ranked,
    staff_can_export_syllabi,
    staff_member_required,
    staff_has_explicit_memberships,
    timedelta,
    timezone,
)


def _read_org_admin_state(request):
    org_name = (request.GET.get("org_name") or "").strip()
    org_membership_org_id = (request.GET.get("org_membership_org_id") or "").strip()
    org_membership_user_id = (request.GET.get("org_membership_user_id") or "").strip()
    org_membership_role = (request.GET.get("org_membership_role") or "").strip()
    org_membership_active = (request.GET.get("org_membership_active") or "").strip()
    org_rolecap_org_id = (request.GET.get("org_rolecap_org_id") or "").strip()
    org_rolecap_role = (request.GET.get("org_rolecap_role") or "").strip()
    org_rolecap_capability = (request.GET.get("org_rolecap_capability") or "").strip()
    org_rolecap_active = (request.GET.get("org_rolecap_active") or "").strip()
    class_assignment_class_id = (request.GET.get("class_assignment_class_id") or "").strip()
    class_assignment_user_id = (request.GET.get("class_assignment_user_id") or "").strip()
    class_assignment_active = (request.GET.get("class_assignment_active") or "").strip()
    class_assignment_bulk_user_id = (request.GET.get("class_assignment_bulk_user_id") or "").strip()
    class_move_class_id = (request.GET.get("class_move_class_id") or "").strip()
    class_move_org_id = (request.GET.get("class_move_org_id") or "").strip()
    org_admin_active = (
        (request.GET.get("org_admin") or "").strip() == "1"
        or bool(
            org_name
            or org_membership_org_id
            or org_membership_user_id
            or org_membership_role
            or org_rolecap_org_id
            or org_rolecap_role
            or org_rolecap_capability
            or class_assignment_class_id
            or class_assignment_user_id
            or class_assignment_bulk_user_id
            or class_move_class_id
            or class_move_org_id
        )
    )
    return {
        "org_name": org_name,
        "org_membership_org_id": org_membership_org_id,
        "org_membership_user_id": org_membership_user_id,
        "org_membership_role": org_membership_role,
        "org_membership_active": org_membership_active if org_membership_active in {"0", "1"} else "1",
        "org_rolecap_org_id": org_rolecap_org_id,
        "org_rolecap_role": org_rolecap_role,
        "org_rolecap_capability": org_rolecap_capability,
        "org_rolecap_active": org_rolecap_active if org_rolecap_active in {"0", "1"} else "1",
        "class_assignment_class_id": class_assignment_class_id,
        "class_assignment_user_id": class_assignment_user_id,
        "class_assignment_active": class_assignment_active if class_assignment_active in {"0", "1"} else "1",
        "class_assignment_bulk_user_id": class_assignment_bulk_user_id,
        "class_move_class_id": class_move_class_id,
        "class_move_org_id": class_move_org_id,
        "org_admin_active": org_admin_active,
    }

def _read_profile_state(request, user):
    profile_first_name = (request.GET.get("profile_first_name") or "").strip()
    profile_last_name = (request.GET.get("profile_last_name") or "").strip()
    profile_email = (request.GET.get("profile_email") or "").strip()
    return {
        "profile_first_name": profile_first_name or (user.first_name or ""),
        "profile_last_name": profile_last_name or (user.last_name or ""),
        "profile_email": profile_email or (user.email or ""),
        "profile_tab_active": (request.GET.get("profile_tab") or "").strip() == "1" or bool(profile_first_name or profile_last_name or profile_email),
    }


def _read_teacher_invite_state(request):
    teacher_username = (request.GET.get("teacher_username") or "").strip()
    teacher_email = (request.GET.get("teacher_email") or "").strip()
    teacher_first_name = (request.GET.get("teacher_first_name") or "").strip()
    teacher_last_name = (request.GET.get("teacher_last_name") or "").strip()
    teacher_invite_open = (request.GET.get("teacher_invite") or "").strip() == "1"
    return {
        "teacher_username": teacher_username,
        "teacher_email": teacher_email,
        "teacher_first_name": teacher_first_name,
        "teacher_last_name": teacher_last_name,
        "teacher_invite_open": teacher_invite_open,
        "teacher_invite_active": bool(teacher_invite_open or teacher_username or teacher_email or teacher_first_name or teacher_last_name),
    }


def _resolve_initial_top_tab(*, user, profile_tab_active, org_admin_active, teacher_invite_active, rbac_tools_active):
    if profile_tab_active:
        return "profile"
    if rbac_tools_active:
        return "rbac-tools"
    if user.is_superuser and org_admin_active:
        return "org-admin"
    if user.is_superuser and teacher_invite_active:
        return "invite-teacher"
    return "quick-actions"


def _empty_class_assignment_context(org_state: dict):
    return {
        "class_staff_assignments": [],
        "org_classes": [],
        "class_assignment_class_id": org_state.get("class_assignment_class_id", ""),
        "class_assignment_user_id": org_state.get("class_assignment_user_id", ""),
        "class_assignment_active": org_state.get("class_assignment_active", "1"),
        "class_assignment_bulk_user_id": org_state.get("class_assignment_bulk_user_id", ""),
        "class_assignment_bulk_selected_class_ids": [],
        "class_move_class_id": org_state.get("class_move_class_id", ""),
        "class_move_org_id": org_state.get("class_move_org_id", ""),
    }


def _class_assignment_context(*, org_state: dict, classes: list):
    class_staff_assignments = list(
        ClassStaffAssignment.objects.select_related("classroom", "user")
        .order_by("classroom__name", "user__username", "id")
    )
    bulk_user_id = _parse_positive_int(org_state.get("class_assignment_bulk_user_id", ""), min_value=1, max_value=2_147_483_647)
    selected_bulk_class_ids: list[int] = []
    if bulk_user_id is not None:
        selected_bulk_class_ids = list(
            ClassStaffAssignment.objects.filter(
                user_id=bulk_user_id,
                is_active=True,
                classroom_id__in=[int(c.id) for c in classes],
            ).values_list("classroom_id", flat=True)
        )
    move_class_id = org_state.get("class_move_class_id", "")
    move_org_id = org_state.get("class_move_org_id", "")
    parsed_move_class_id = _parse_positive_int(move_class_id, min_value=1, max_value=2_147_483_647)
    if parsed_move_class_id is not None and not move_org_id:
        target_class = next((c for c in classes if int(c.id) == int(parsed_move_class_id)), None)
        if target_class is not None and target_class.organization_id:
            move_org_id = str(target_class.organization_id)
    return {
        "class_staff_assignments": class_staff_assignments,
        "org_classes": classes,
        "class_assignment_class_id": org_state["class_assignment_class_id"],
        "class_assignment_user_id": org_state["class_assignment_user_id"],
        "class_assignment_active": org_state["class_assignment_active"],
        "class_assignment_bulk_user_id": org_state["class_assignment_bulk_user_id"],
        "class_assignment_bulk_selected_class_ids": selected_bulk_class_ids,
        "class_move_class_id": move_class_id,
        "class_move_org_id": move_org_id,
    }


def _build_org_admin_context(*, user, user_model, org_state: dict, classes: list):
    if not user.is_superuser:
        return {
            "organizations": [],
            "org_memberships": [],
            "org_role_capabilities": [],
            "staff_users": [],
            **_empty_class_assignment_context(org_state),
            "org_role_choices": OrganizationMembership.ROLE_CHOICES,
            "org_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
        }
    organizations = list(Organization.objects.order_by("name", "id").only("id", "name", "is_active"))
    org_class_counts: dict[int, int] = {}
    if organizations:
        org_class_counts = {
            int(row["organization_id"]): int(row["count"])
            for row in (
                Class.objects.filter(organization_id__in=[int(org.id) for org in organizations])
                .values("organization_id")
                .annotate(count=models.Count("id"))
            )
        }
    for org in organizations:
        setattr(org, "class_count", org_class_counts.get(int(org.id), 0))
    org_memberships = list(
        OrganizationMembership.objects.select_related("organization", "user")
        .order_by("organization__name", "user__username", "id")
    )
    org_role_capabilities = list(
        OrganizationRoleCapability.objects.select_related("organization")
        .order_by("organization__name", "role", "capability", "id")
    )
    staff_users = list(
        user_model.objects.filter(is_staff=True)
        .order_by("username", "id")
        .only("id", "username", "is_active", "is_superuser")
    )
    return {
        "organizations": organizations,
        "org_memberships": org_memberships,
        "org_role_capabilities": org_role_capabilities,
        "staff_users": staff_users,
        **_class_assignment_context(org_state=org_state, classes=classes),
        "org_role_choices": OrganizationMembership.ROLE_CHOICES,
        "org_capability_choices": OrganizationRoleCapability.CAPABILITY_CHOICES,
    }

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


@staff_member_required
def teach_home(request):
    """Teacher landing page (outside /admin)."""
    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()
    template_slug = (request.GET.get("template_slug") or "").strip()
    template_title = (request.GET.get("template_title") or "").strip()
    template_sessions = (request.GET.get("template_sessions") or "").strip()
    template_duration = (request.GET.get("template_duration") or "").strip()
    import_course_slug = (request.GET.get("import_course_slug") or "").strip()
    import_course_title = (request.GET.get("import_course_title") or "").strip()
    import_default_ui_level = (request.GET.get("import_default_ui_level") or "secondary").strip().lower()
    import_session_parse_mode = (request.GET.get("import_session_parse_mode") or "auto").strip().lower()
    import_overwrite = (request.GET.get("import_overwrite") or "").strip() == "1"
    teacher_invite_state = _read_teacher_invite_state(request)
    org_state = _read_org_admin_state(request)
    profile_state = _read_profile_state(request, request.user)
    rbac_tools_enabled = rbac_tools_enabled_for_user(request.user)
    rbac_tools_active = rbac_tools_requested(request) and rbac_tools_enabled
    initial_tab = _resolve_initial_top_tab(
        user=request.user,
        profile_tab_active=profile_state["profile_tab_active"],
        org_admin_active=org_state["org_admin_active"],
        teacher_invite_active=teacher_invite_state["teacher_invite_active"],
        rbac_tools_active=rbac_tools_active,
    )
    classes, assigned_class_ids = staff_accessible_classes_ranked(request.user)
    assigned_classes = [c for c in classes if c.id in assigned_class_ids]
    digest_since = timezone.now() - timedelta(days=1)
    class_digest_rows = _build_class_digest_rows(classes, since=digest_since)
    User = get_user_model()
    teacher_accounts = (
        User.objects.filter(is_staff=True)
        .order_by("username", "id")
        .only("id", "username", "first_name", "last_name", "email", "is_active", "is_superuser")
    )
    class_ids = [int(c.id) for c in classes]
    recent_submissions = _recent_submissions_for_class_ids(class_ids)
    output_dir = _authoring_template_output_dir()
    template_download_rows = _build_template_download_rows(template_slug, output_dir)
    syllabus_export_state = build_syllabus_export_state(request)
    org_admin_context = _build_org_admin_context(user=request.user, user_model=User, org_state=org_state, classes=classes)
    rbac_tools_context = build_rbac_tools_context(request=request, classes=classes)
    operator_config_snapshot = build_operator_config_snapshot(user=request.user)
    response = render(
        request,
        "teach_home.html",
        {
            "classes": classes,
            "assigned_class_ids": assigned_class_ids,
            "assigned_classes": assigned_classes,
            "class_digest_rows": class_digest_rows,
            "digest_since": digest_since,
            "recent_submissions": recent_submissions,
            "notice": notice,
            "error": error,
            "template_slug": template_slug,
            "template_title": template_title,
            "template_sessions": template_sessions or "12",
            "template_duration": template_duration or "75",
            "import_course_slug": import_course_slug,
            "import_course_title": import_course_title,
            "import_default_ui_level": import_default_ui_level if import_default_ui_level in {"elementary", "secondary", "advanced"} else "secondary",
            "import_session_parse_mode": import_session_parse_mode if import_session_parse_mode in {"auto", "template", "verbose"} else "auto",
            "import_overwrite": import_overwrite,
            "template_output_dir": str(output_dir),
            "template_download_rows": template_download_rows,
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
            "org_rolecap_capability": (
                org_state["org_rolecap_capability"] or OrganizationRoleCapability.CAP_CLASS_VIEW
            ),
            "org_rolecap_active": org_state["org_rolecap_active"],
            "org_membership_mode": staff_has_explicit_memberships(request.user),
            **syllabus_export_state,
            **org_admin_context,
            **rbac_tools_context,
            **operator_config_snapshot,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response

@staff_member_required
@require_POST
def teach_generate_authoring_templates(request):
    slug = (request.POST.get("template_slug") or "").strip().lower()
    title = (request.POST.get("template_title") or "").strip()
    sessions_raw = (request.POST.get("template_sessions") or "").strip()
    duration_raw = (request.POST.get("template_duration") or "").strip()

    form_values = {
        "template_slug": slug,
        "template_title": title,
        "template_sessions": sessions_raw,
        "template_duration": duration_raw,
    }
    return_to = "/teach"

    if not slug:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Course slug is required.", extra=form_values),
            fallback=return_to,
        )
    if not _TEMPLATE_SLUG_RE.match(slug):
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Course slug can use lowercase letters, numbers, underscores, and dashes.", extra=form_values),
            fallback=return_to,
        )
    if not title:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Course title is required.", extra=form_values),
            fallback=return_to,
        )

    sessions = _parse_positive_int(sessions_raw, min_value=1, max_value=60)
    if sessions is None:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Sessions must be a whole number between 1 and 60.", extra=form_values),
            fallback=return_to,
        )

    duration = _parse_positive_int(duration_raw, min_value=15, max_value=240)
    if duration is None:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Session duration must be between 15 and 240 minutes.", extra=form_values),
            fallback=return_to,
        )

    age_band = (getattr(settings, "CLASSHUB_AUTHORING_TEMPLATE_AGE_BAND_DEFAULT", "5th-7th") or "5th-7th").strip()
    output_dir = Path(getattr(settings, "CLASSHUB_AUTHORING_TEMPLATE_DIR", "/uploads/authoring_templates"))

    try:
        result = generate_authoring_templates(
            slug=slug,
            title=title,
            sessions=sessions,
            duration=duration,
            age_band=age_band,
            out_dir=output_dir,
            overwrite=True,
        )
    except (OSError, ValueError) as exc:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error=f"Template generation failed: {exc}", extra=form_values),
            fallback=return_to,
        )

    _audit(
        request,
        action="teacher_templates.generate",
        target_type="AuthoringTemplates",
        target_id=slug,
        summary=f"Generated authoring templates for {slug}",
        metadata={
            "slug": slug,
            "title": title,
            "sessions": sessions,
            "duration": duration,
            "output_dir": str(output_dir),
            "files": [str(path) for path in result.output_paths],
        },
    )
    notice = f"Generated templates for {slug} in {output_dir}."
    return _safe_internal_redirect(
        request,
        _with_notice(return_to, notice=notice, extra=form_values),
        fallback=return_to,
    )


@staff_member_required
def teach_download_authoring_template(request):
    slug = (request.GET.get("slug") or "").strip().lower()
    kind = (request.GET.get("kind") or "").strip()

    if not slug or not _TEMPLATE_SLUG_RE.match(slug):
        return HttpResponse("Invalid template slug.", status=400)

    suffix = _AUTHORING_TEMPLATE_SUFFIXES.get(kind)
    if not suffix:
        return HttpResponse("Invalid template kind.", status=400)
    candidate = _resolve_authoring_template_download_path(slug, suffix)
    if candidate is None:
        return HttpResponse("Invalid template path.", status=400)
    if not candidate.exists() or not candidate.is_file():
        return HttpResponse("Template file not found.", status=404)

    _audit(
        request,
        action="teacher_templates.download",
        target_type="AuthoringTemplates",
        target_id=f"{slug}:{kind}",
        summary=f"Downloaded authoring template {candidate.name}",
        metadata={"slug": slug, "kind": kind, "path": str(candidate)},
    )
    response = FileResponse(
        candidate.open("rb"),
        as_attachment=True,
        filename=safe_attachment_filename(candidate.name),
        content_type="application/octet-stream",
    )
    apply_download_safety(response)
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = [
    "teach_home",
    "teach_generate_authoring_templates",
    "teach_download_authoring_template",
]
