"""Teacher home and authoring template endpoints."""

from .content_home_context import (
    _build_org_admin_context,
    _build_teach_home_class_context,
    _build_teach_home_staff_context,
    _build_template_download_rows,
    _portal_mode_context,
    _read_org_admin_state,
    _read_portal_mode,
    _read_profile_state,
    _read_teacher_invite_state,
    _recent_submissions_for_class_ids,
    _resolve_initial_top_tab,
    _tab_for_portal_mode,
)
from .content_operator_config import build_operator_config_snapshot
from .content_rbac_tools import (
    build_rbac_tools_context,
    rbac_tools_enabled_for_user,
    rbac_tools_requested,
)
from .content_syllabus_exports import build_syllabus_export_state
from ...services.teacher_home_templates import generate_authoring_templates_from_form
from .shared import (
    FileResponse,
    HttpResponse,
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
    staff_accessible_classes_ranked,
    staff_member_required,
    timedelta,
    timezone,
)


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
    portal_mode = _read_portal_mode(request, user=request.user, rbac_tools_enabled=rbac_tools_enabled)
    portal_mode_context = _portal_mode_context(
        user=request.user,
        portal_mode=portal_mode,
        rbac_tools_enabled=rbac_tools_enabled,
    )
    initial_tab = _resolve_initial_top_tab(
        user=request.user,
        profile_tab_active=profile_state["profile_tab_active"],
        org_admin_active=org_state["org_admin_active"],
        teacher_invite_active=teacher_invite_state["teacher_invite_active"],
        rbac_tools_active=rbac_tools_active,
    )
    initial_tab = _tab_for_portal_mode(
        initial_tab,
        portal_mode=portal_mode,
        user=request.user,
        rbac_tools_enabled=rbac_tools_enabled,
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
    context = {
        **_build_teach_home_class_context(
            classes=classes,
            assigned_class_ids=assigned_class_ids,
            assigned_classes=assigned_classes,
            class_digest_rows=class_digest_rows,
            digest_since=digest_since,
            recent_submissions=recent_submissions,
            notice=notice,
            error=error,
            template_slug=template_slug,
            template_title=template_title,
            template_sessions=template_sessions,
            template_duration=template_duration,
            import_course_slug=import_course_slug,
            import_course_title=import_course_title,
            import_default_ui_level=import_default_ui_level,
            import_session_parse_mode=import_session_parse_mode,
            import_overwrite=import_overwrite,
            output_dir=output_dir,
            template_download_rows=template_download_rows,
        ),
        **_build_teach_home_staff_context(
            request=request,
            teacher_accounts=teacher_accounts,
            teacher_invite_state=teacher_invite_state,
            profile_state=profile_state,
            org_state=org_state,
            initial_tab=initial_tab,
        ),
        **syllabus_export_state,
        **org_admin_context,
        **rbac_tools_context,
        **operator_config_snapshot,
        **portal_mode_context,
    }
    response = render(
        request,
        "teach_home.html",
        context,
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
@require_POST
def teach_generate_authoring_templates(request):
    return_to = "/teach"
    generation_result = generate_authoring_templates_from_form(
        post_data=request.POST,
        template_slug_re=_TEMPLATE_SLUG_RE,
        parse_positive_int_fn=_parse_positive_int,
        generate_authoring_templates_fn=generate_authoring_templates,
    )
    if generation_result.error:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error=generation_result.error, extra=generation_result.form_values),
            fallback=return_to,
        )

    _audit(
        request,
        action="teacher_templates.generate",
        target_type="AuthoringTemplates",
        target_id=generation_result.slug,
        summary=f"Generated authoring templates for {generation_result.slug}",
        metadata={
            "slug": generation_result.slug,
            "title": generation_result.title,
            "sessions": generation_result.sessions,
            "duration": generation_result.duration,
            "output_dir": str(generation_result.output_dir),
            "files": list(generation_result.output_paths),
        },
    )
    return _safe_internal_redirect(
        request,
        _with_notice(return_to, notice=generation_result.notice, extra=generation_result.form_values),
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
