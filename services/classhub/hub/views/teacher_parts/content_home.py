"""Teacher home and authoring template endpoints."""

from django.conf import settings

from .content_home_context import (
    _build_org_admin_context,
    _build_teach_home_class_context,
    _build_teach_home_staff_context,
    _build_template_download_rows,
    _portal_mode_context,
    _read_advanced_tools_state,
    _read_org_admin_state,
    _read_portal_mode,
    _read_profile_state,
    _read_teacher_invite_state,
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
from ...services.teacher_home_context_data import build_teacher_home_context_data
from ...services.teacher_home_templates import generate_authoring_templates_from_form
from .shared import (
    FileResponse,
    HttpResponse,
    _AUTHORING_TEMPLATE_SUFFIXES,
    _TEMPLATE_SLUG_RE,
    _audit,
    _authoring_template_output_dir,
    _parse_positive_int,
    _resolve_authoring_template_download_path,
    _safe_internal_redirect,
    _with_notice,
    apply_download_safety,
    apply_no_store,
    generate_authoring_templates,
    render,
    require_POST,
    safe_attachment_filename,
    staff_member_required,
    staff_can_create_classes,
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
    registry_index = (request.GET.get("registry_index") or "").strip()
    registry_course_slug = (request.GET.get("registry_course_slug") or "").strip()
    registry_version = (request.GET.get("registry_version") or "").strip()
    registry_class_code = (request.GET.get("registry_class_code") or "").strip().upper()
    registry_class_name = (request.GET.get("registry_class_name") or "").strip()
    registry_create_class = (request.GET.get("registry_create_class") or "").strip().lower() in {"1", "true", "yes", "on"}
    registry_replace = (request.GET.get("registry_replace") or "").strip().lower() in {"1", "true", "yes", "on"}
    registry_overwrite_content = (
        (request.GET.get("registry_overwrite_content") or "").strip().lower() in {"1", "true", "yes", "on"}
    )
    teacher_invite_state = _read_teacher_invite_state(request)
    org_state = _read_org_admin_state(request)
    profile_state = _read_profile_state(request, request.user)
    rbac_tools_enabled = rbac_tools_enabled_for_user(request.user)
    rbac_tools_active = rbac_tools_requested(request) and rbac_tools_enabled
    advanced_tools_enabled = _read_advanced_tools_state(request, user=request.user)
    portal_mode = _read_portal_mode(
        request, user=request.user, advanced_tools_enabled=advanced_tools_enabled
    )
    portal_mode_context = _portal_mode_context(
        user=request.user, portal_mode=portal_mode, advanced_tools_enabled=advanced_tools_enabled
    )
    initial_tab = _resolve_initial_top_tab(
        user=request.user,
        profile_tab_active=profile_state["profile_tab_active"],
        org_admin_active=org_state["org_admin_active"],
        teacher_invite_active=teacher_invite_state["teacher_invite_active"],
        rbac_tools_active=rbac_tools_active,
    )
    initial_tab = _tab_for_portal_mode(
        initial_tab, portal_mode=portal_mode, user=request.user, advanced_tools_enabled=advanced_tools_enabled
    )
    context_data = build_teacher_home_context_data(user=request.user)
    classes = context_data["classes"]
    assigned_classes = context_data["assigned_classes"]
    recent_submissions = context_data["recent_submissions"]
    teacher_start_class = assigned_classes[0] if assigned_classes else (classes[0] if classes else None)
    first_submission = recent_submissions[0] if recent_submissions else None
    teacher_start_submission_material_id = int(getattr(getattr(first_submission, "material", None), "id", 0) or 0)
    output_dir = _authoring_template_output_dir()
    template_download_rows = _build_template_download_rows(template_slug, output_dir)
    syllabus_export_state = build_syllabus_export_state(request)
    org_admin_context = _build_org_admin_context(
        user=request.user,
        user_model=context_data["user_model"],
        org_state=org_state,
        classes=classes,
    )
    rbac_tools_context = build_rbac_tools_context(request=request, classes=classes)
    operator_config_snapshot = build_operator_config_snapshot(user=request.user)
    context = {
        **_build_teach_home_class_context(
            classes=classes,
            assigned_class_ids=context_data["assigned_class_ids"],
            assigned_classes=assigned_classes,
            teacher_start_class=teacher_start_class,
            teacher_start_submission_material_id=teacher_start_submission_material_id,
            class_digest_rows=context_data["class_digest_rows"],
            digest_since=context_data["digest_since"],
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
            registry_index=registry_index,
            registry_course_slug=registry_course_slug,
            registry_version=registry_version,
            registry_class_code=registry_class_code,
            registry_class_name=registry_class_name,
            registry_create_class=registry_create_class,
            registry_replace=registry_replace,
            registry_overwrite_content=registry_overwrite_content,
            output_dir=output_dir,
            template_download_rows=template_download_rows,
        ),
        **_build_teach_home_staff_context(
            request=request,
            teacher_accounts=context_data["teacher_accounts"],
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
        "org_membership_strict_mode": bool(getattr(settings, "REQUIRE_ORG_MEMBERSHIP_FOR_STAFF", False)),
        "can_compile_coursepack": bool(staff_can_create_classes(request.user)),
    }
    response = render(request, "teach_home.html", context)
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
