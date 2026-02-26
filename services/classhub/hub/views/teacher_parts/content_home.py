"""Teacher home and authoring template endpoints."""

from .shared import (
    FileResponse,
    HttpResponse,
    Path,
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


@staff_member_required
def teach_home(request):
    """Teacher landing page (outside /admin)."""
    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()
    template_slug = (request.GET.get("template_slug") or "").strip()
    template_title = (request.GET.get("template_title") or "").strip()
    template_sessions = (request.GET.get("template_sessions") or "").strip()
    template_duration = (request.GET.get("template_duration") or "").strip()
    teacher_username = (request.GET.get("teacher_username") or "").strip()
    teacher_email = (request.GET.get("teacher_email") or "").strip()
    teacher_first_name = (request.GET.get("teacher_first_name") or "").strip()
    teacher_last_name = (request.GET.get("teacher_last_name") or "").strip()
    teacher_invite_active = bool(
        teacher_username or teacher_email or teacher_first_name or teacher_last_name
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
    recent_submissions = []
    if class_ids:
        recent_submissions = list(
            Submission.objects.select_related("student", "material__module__classroom")
            .filter(material__module__classroom_id__in=class_ids)[:20]
        )
    output_dir = _authoring_template_output_dir()
    template_download_rows: list[dict] = []
    if template_slug and _TEMPLATE_SLUG_RE.match(template_slug):
        existing_names: set[str] = set()
        try:
            existing_names = {
                item.name
                for item in output_dir.iterdir()
                if item.is_file()
            }
        except OSError:
            existing_names = set()
        for kind, suffix in _AUTHORING_TEMPLATE_SUFFIXES.items():
            expected_name = f"{template_slug}-{suffix}"
            exists = expected_name in existing_names
            template_download_rows.append(
                {
                    "kind": kind,
                    "label": expected_name,
                    "exists": exists,
                    "url": f"/teach/authoring-template/download?slug={template_slug}&kind={kind}",
                }
            )

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
            "template_output_dir": str(output_dir),
            "template_download_rows": template_download_rows,
            "teacher_accounts": teacher_accounts,
            "teacher_username": teacher_username,
            "teacher_email": teacher_email,
            "teacher_first_name": teacher_first_name,
            "teacher_last_name": teacher_last_name,
            "teacher_invite_active": teacher_invite_active,
            "org_membership_mode": staff_has_explicit_memberships(request.user),
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
