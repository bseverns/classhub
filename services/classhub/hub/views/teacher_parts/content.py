"""Teacher dashboard, lessons, and authoring template endpoints."""

from .shared import *  # noqa: F401,F403,F405


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

    classes = list(Class.objects.all().order_by("name", "id"))
    digest_since = timezone.now() - timedelta(days=1)
    class_digest_rows = _build_class_digest_rows(classes, since=digest_since)
    User = get_user_model()
    teacher_accounts = (
        User.objects.filter(is_staff=True)
        .order_by("username", "id")
        .only("id", "username", "first_name", "last_name", "email", "is_active", "is_superuser")
    )
    recent_submissions = list(
        Submission.objects.select_related("student", "material__module__classroom")
        .all()[:20]
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


@staff_member_required
def teach_lessons(request):
    classes = list(Class.objects.all().order_by("name", "id"))
    try:
        class_id = int((request.GET.get("class_id") or "0").strip())
    except Exception:
        class_id = 0
    selected_class = next((c for c in classes if c.id == class_id), None)
    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()

    target_classes = [selected_class] if selected_class else classes
    class_rows = []
    for classroom in target_classes:
        if not classroom:
            continue
        student_count = classroom.students.count()
        modules = list(classroom.modules.prefetch_related("materials").all())
        modules.sort(key=lambda m: (m.order_index, m.id))
        lesson_rows = _build_lesson_tracker_rows(request, classroom.id, modules, student_count)
        class_rows.append(
            {
                "classroom": classroom,
                "student_count": student_count,
                "lesson_rows": lesson_rows,
            }
        )

    return render(
        request,
        "teach_lessons.html",
        {
            "classes": classes,
            "selected_class_id": selected_class.id if selected_class else 0,
            "class_rows": class_rows,
            "notice": notice,
            "error": error,
        },
    )


@staff_member_required
@require_POST
def teach_set_lesson_release(request):
    try:
        class_id = int((request.POST.get("class_id") or "0").strip())
    except Exception:
        class_id = 0

    default_return = f"/teach/lessons?class_id={class_id}" if class_id else "/teach/lessons"
    return_to = _safe_teacher_return_path((request.POST.get("return_to") or "").strip(), default_return)

    classroom = Class.objects.filter(id=class_id).first()
    if not classroom:
        return _safe_internal_redirect(request, _with_notice(return_to, error="Class not found."), fallback=return_to)

    course_slug = (request.POST.get("course_slug") or "").strip()
    lesson_slug = (request.POST.get("lesson_slug") or "").strip()
    if not course_slug or not lesson_slug:
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, error="Missing course or lesson slug."),
            fallback=return_to,
        )

    action = (request.POST.get("action") or "").strip()
    try:
        LessonRelease.objects.only("id").first()
    except (OperationalError, ProgrammingError) as exc:
        if "hub_lessonrelease" in str(exc).lower():
            return _safe_internal_redirect(
                request,
                _with_notice(return_to, error="Lesson release table is missing. Run `python manage.py migrate`."),
                fallback=return_to,
            )
        raise

    release = LessonRelease.objects.filter(
        classroom_id=classroom.id,
        course_slug=course_slug,
        lesson_slug=lesson_slug,
    ).first()

    if action == "set_date":
        raw_date = (request.POST.get("available_on") or "").strip()
        parsed_date = parse_release_date(raw_date)
        if parsed_date is None:
            return _safe_internal_redirect(
                request,
                _with_notice(return_to, error="Enter a valid date (YYYY-MM-DD)."),
                fallback=return_to,
            )
        if release is None:
            release = LessonRelease(
                classroom=classroom,
                course_slug=course_slug,
                lesson_slug=lesson_slug,
            )
        release.available_on = parsed_date
        release.force_locked = False
        release.save()
        _audit(
            request,
            action="lesson_release.set_date",
            classroom=classroom,
            target_type="LessonRelease",
            target_id=f"{course_slug}/{lesson_slug}",
            summary=f"Set lesson release date {parsed_date.isoformat()}",
            metadata={"course_slug": course_slug, "lesson_slug": lesson_slug, "available_on": parsed_date.isoformat()},
        )
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, notice=f"Release date set to {parsed_date.isoformat()}."),
            fallback=return_to,
        )

    if action == "toggle_lock":
        if release is None:
            release = LessonRelease.objects.create(
                classroom=classroom,
                course_slug=course_slug,
                lesson_slug=lesson_slug,
                force_locked=True,
            )
            _audit(
                request,
                action="lesson_release.lock",
                classroom=classroom,
                target_type="LessonRelease",
                target_id=f"{course_slug}/{lesson_slug}",
                summary="Locked lesson",
                metadata={"course_slug": course_slug, "lesson_slug": lesson_slug, "force_locked": True},
            )
            return _safe_internal_redirect(
                request,
                _with_notice(return_to, notice="Lesson locked."),
                fallback=return_to,
            )
        release.force_locked = not release.force_locked
        release.save(update_fields=["force_locked", "updated_at"])
        _audit(
            request,
            action="lesson_release.toggle_lock",
            classroom=classroom,
            target_type="LessonRelease",
            target_id=f"{course_slug}/{lesson_slug}",
            summary=f"Toggled lesson lock to {release.force_locked}",
            metadata={"course_slug": course_slug, "lesson_slug": lesson_slug, "force_locked": release.force_locked},
        )
        if release.force_locked:
            return _safe_internal_redirect(
                request,
                _with_notice(return_to, notice="Lesson locked."),
                fallback=return_to,
            )
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, notice="Lesson lock removed."),
            fallback=return_to,
        )

    if action == "unlock_now":
        if release is None:
            release = LessonRelease(
                classroom=classroom,
                course_slug=course_slug,
                lesson_slug=lesson_slug,
            )
        release.available_on = None
        release.force_locked = False
        release.save()
        _audit(
            request,
            action="lesson_release.unlock_now",
            classroom=classroom,
            target_type="LessonRelease",
            target_id=f"{course_slug}/{lesson_slug}",
            summary="Opened lesson now",
            metadata={"course_slug": course_slug, "lesson_slug": lesson_slug},
        )
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, notice="Lesson opened now for this class."),
            fallback=return_to,
        )

    if action == "set_helper_scope":
        helper_context_override = (request.POST.get("helper_context_override") or "").strip()[:200]
        helper_topics_override = _normalize_helper_topics_text(request.POST.get("helper_topics_override") or "")
        helper_allowed_topics_override = _normalize_helper_topics_text(
            request.POST.get("helper_allowed_topics_override") or ""
        )
        helper_reference_override = (request.POST.get("helper_reference_override") or "").strip()[:200]
        has_helper_override = bool(
            helper_context_override
            or helper_topics_override
            or helper_allowed_topics_override
            or helper_reference_override
        )

        if release is None:
            if not has_helper_override:
                return _safe_internal_redirect(
                    request,
                    _with_notice(return_to, notice="Helper tuning is using lesson defaults."),
                    fallback=return_to,
                )
            release = LessonRelease(
                classroom=classroom,
                course_slug=course_slug,
                lesson_slug=lesson_slug,
            )

        release.helper_context_override = helper_context_override
        release.helper_topics_override = helper_topics_override
        release.helper_allowed_topics_override = helper_allowed_topics_override
        release.helper_reference_override = helper_reference_override

        if (
            not has_helper_override
            and release.available_on is None
            and not release.force_locked
            and release.id is not None
        ):
            release.delete()
        else:
            release.save()

        _audit(
            request,
            action="lesson_release.set_helper_scope",
            classroom=classroom,
            target_type="LessonRelease",
            target_id=f"{course_slug}/{lesson_slug}",
            summary="Updated lesson helper tuning",
            metadata={
                "course_slug": course_slug,
                "lesson_slug": lesson_slug,
                "helper_context_override": helper_context_override,
                "helper_topics_override": helper_topics_override,
                "helper_allowed_topics_override": helper_allowed_topics_override,
                "helper_reference_override": helper_reference_override,
            },
        )
        if has_helper_override:
            return _safe_internal_redirect(
                request,
                _with_notice(return_to, notice="Helper tuning saved for this lesson."),
                fallback=return_to,
            )
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, notice="Helper tuning reset to lesson defaults."),
            fallback=return_to,
        )

    if action == "reset_default":
        LessonRelease.objects.filter(
            classroom_id=classroom.id,
            course_slug=course_slug,
            lesson_slug=lesson_slug,
        ).delete()
        _audit(
            request,
            action="lesson_release.reset_default",
            classroom=classroom,
            target_type="LessonRelease",
            target_id=f"{course_slug}/{lesson_slug}",
            summary="Reset lesson release override",
            metadata={"course_slug": course_slug, "lesson_slug": lesson_slug},
        )
        return _safe_internal_redirect(
            request,
            _with_notice(return_to, notice="Lesson release reset to content default."),
            fallback=return_to,
        )

    return _safe_internal_redirect(
        request,
        _with_notice(return_to, error="Unknown release action."),
        fallback=return_to,
    )

__all__ = [
    "teach_home",
    "teach_generate_authoring_templates",
    "teach_download_authoring_template",
    "teach_lessons",
    "teach_set_lesson_release",
]
