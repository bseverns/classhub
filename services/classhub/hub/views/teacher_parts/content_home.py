"""Teacher home and authoring template endpoints."""

from ...services.syllabus_ingest import (
    SyllabusIngestError,
    ingest_uploaded_syllabus_files,
)
from .content_syllabus_exports import build_syllabus_export_state
from .shared import (
    FileResponse,
    HttpResponse,
    Path,
    Organization,
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
    staff_accessible_classes_ranked,
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
    org_admin_active = (
        (request.GET.get("org_admin") or "").strip() == "1"
        or bool(org_name or org_membership_org_id or org_membership_user_id or org_membership_role)
    )
    return {
        "org_name": org_name,
        "org_membership_org_id": org_membership_org_id,
        "org_membership_user_id": org_membership_user_id,
        "org_membership_role": org_membership_role,
        "org_membership_active": org_membership_active if org_membership_active in {"0", "1"} else "1",
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
        "profile_tab_active": (request.GET.get("profile_tab") or "").strip() == "1"
        or bool(profile_first_name or profile_last_name or profile_email),
    }

def _resolve_initial_top_tab(*, user, profile_tab_active, org_admin_active, teacher_invite_active):
    if profile_tab_active:
        return "profile"
    if user.is_superuser and org_admin_active:
        return "org-admin"
    if user.is_superuser and teacher_invite_active:
        return "invite-teacher"
    return "quick-actions"

def _build_org_admin_context(*, user, user_model):
    if not user.is_superuser:
        return {
            "organizations": [],
            "org_memberships": [],
            "staff_users": [],
            "org_role_choices": OrganizationMembership.ROLE_CHOICES,
        }
    organizations = list(
        Organization.objects.order_by("name", "id").only("id", "name", "is_active")
    )
    org_memberships = list(
        OrganizationMembership.objects.select_related("organization", "user")
        .order_by("organization__name", "user__username", "id")
    )
    staff_users = list(
        user_model.objects.filter(is_staff=True)
        .order_by("username", "id")
        .only("id", "username", "is_active", "is_superuser")
    )
    return {
        "organizations": organizations,
        "org_memberships": org_memberships,
        "staff_users": staff_users,
        "org_role_choices": OrganizationMembership.ROLE_CHOICES,
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
    teacher_username = (request.GET.get("teacher_username") or "").strip()
    teacher_email = (request.GET.get("teacher_email") or "").strip()
    teacher_first_name = (request.GET.get("teacher_first_name") or "").strip()
    teacher_last_name = (request.GET.get("teacher_last_name") or "").strip()
    org_state = _read_org_admin_state(request)
    profile_state = _read_profile_state(request, request.user)
    teacher_invite_active = bool(
        teacher_username or teacher_email or teacher_first_name or teacher_last_name
    )
    initial_tab = _resolve_initial_top_tab(
        user=request.user,
        profile_tab_active=profile_state["profile_tab_active"],
        org_admin_active=org_state["org_admin_active"],
        teacher_invite_active=teacher_invite_active,
    )

    classes, assigned_class_ids = staff_accessible_classes_ranked(request.user)
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

    org_admin_context = _build_org_admin_context(user=request.user, user_model=User)

    response = render(
        request,
        "teach_home.html",
        {
            "classes": classes,
            "assigned_class_ids": assigned_class_ids,
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
            "teacher_username": teacher_username,
            "teacher_email": teacher_email,
            "teacher_first_name": teacher_first_name,
            "teacher_last_name": teacher_last_name,
            "teacher_invite_active": teacher_invite_active,
            "initial_top_tab": initial_tab,
            "profile_first_name": profile_state["profile_first_name"],
            "profile_last_name": profile_state["profile_last_name"],
            "profile_email": profile_state["profile_email"],
            "org_name": org_state["org_name"],
            "org_membership_org_id": org_state["org_membership_org_id"],
            "org_membership_user_id": org_state["org_membership_user_id"],
            "org_membership_role": org_state["org_membership_role"] or OrganizationMembership.ROLE_TEACHER,
            "org_membership_active": org_state["org_membership_active"],
            "org_membership_mode": staff_has_explicit_memberships(request.user),
            **syllabus_export_state,
            **org_admin_context,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response

def _syllabus_import_form_state(request):
    source_upload = request.FILES.get("syllabus_source")
    overview_upload = request.FILES.get("syllabus_overview")
    slug = (request.POST.get("import_course_slug") or "").strip().lower()
    title = (request.POST.get("import_course_title") or "").strip()
    default_ui_level = (request.POST.get("import_default_ui_level") or "secondary").strip().lower()
    session_parse_mode = (request.POST.get("import_session_parse_mode") or "auto").strip().lower()
    overwrite = (request.POST.get("import_overwrite") or "").strip() == "1"
    return {
        "source_upload": source_upload,
        "overview_upload": overview_upload,
        "slug": slug,
        "title": title,
        "default_ui_level": default_ui_level,
        "session_parse_mode": session_parse_mode,
        "overwrite": overwrite,
        "form_values": {
            "import_course_slug": slug,
            "import_course_title": title,
            "import_default_ui_level": default_ui_level,
            "import_session_parse_mode": session_parse_mode,
            "import_overwrite": "1" if overwrite else "0",
        },
    }


def _syllabus_import_error(request, *, form_values, message: str):
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", error=message, extra=form_values),
        fallback="/teach",
    )


def _validate_syllabus_import_state(state: dict) -> str:
    source_upload = state.get("source_upload")
    slug = state.get("slug") or ""
    default_ui_level = state.get("default_ui_level") or ""
    session_parse_mode = state.get("session_parse_mode") or ""
    if source_upload is None:
        return "Select a syllabus source file (.md, .docx, or .zip)."
    if slug and not _TEMPLATE_SLUG_RE.match(slug):
        return "Course slug can use lowercase letters, numbers, underscores, and dashes."
    if default_ui_level not in {"elementary", "secondary", "advanced"}:
        return "Default UI level must be elementary, secondary, or advanced."
    if session_parse_mode not in {"auto", "template", "verbose"}:
        return "Session parse mode must be auto, template, or verbose."
    return ""


def _audit_syllabus_import(request, *, result, overwrite: bool):
    _audit(
        request,
        action="teacher_syllabus_import.upload",
        target_type="CourseSyllabus",
        target_id=result.course_slug,
        summary=f"Imported syllabus source into {result.course_slug}",
        metadata={
            "course_slug": result.course_slug,
            "course_title": result.course_title,
            "course_dir": str(result.course_dir),
            "lesson_count": result.lesson_count,
            "source_kind": result.source_kind,
            "source_files": result.source_files,
            "ui_level": result.ui_level,
            "overwrite": overwrite,
        },
    )


@staff_member_required
@require_POST
def teach_import_syllabus_source(request):
    state = _syllabus_import_form_state(request)
    form_values = state["form_values"]
    error = _validate_syllabus_import_state(state)
    if error:
        return _syllabus_import_error(request, form_values=form_values, message=error)

    try:
        result = ingest_uploaded_syllabus_files(
            source_upload=state["source_upload"],
            course_slug=state["slug"],
            course_title=state["title"],
            overview_upload=state["overview_upload"],
            default_ui_level=state["default_ui_level"],
            session_parse_mode=state["session_parse_mode"],
            overwrite=state["overwrite"],
        )
    except (SyllabusIngestError, OSError, ValueError) as exc:
        return _syllabus_import_error(
            request,
            form_values=form_values,
            message=f"Syllabus import failed: {exc}",
        )

    _audit_syllabus_import(request, result=result, overwrite=state["overwrite"])
    notice = f"Imported course '{result.course_slug}' with {result.lesson_count} lessons."
    success_values = {
        "import_course_slug": result.course_slug,
        "import_course_title": result.course_title,
        "import_default_ui_level": state["default_ui_level"],
        "import_session_parse_mode": state["session_parse_mode"],
        "import_overwrite": "1" if state["overwrite"] else "0",
    }
    return _safe_internal_redirect(
        request,
        _with_notice("/teach", notice=notice, extra=success_values),
        fallback="/teach",
    )


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
    "teach_import_syllabus_source",
    "teach_generate_authoring_templates",
    "teach_download_authoring_template",
]
