"""Teacher lesson listing and release-tuning endpoints."""

from .shared import (
    LessonRelease,
    OperationalError,
    ProgrammingError,
    _audit,
    _build_lesson_tracker_rows,
    _normalize_helper_topics_text,
    _safe_internal_redirect,
    _safe_teacher_return_path,
    _with_notice,
    parse_release_date,
    render,
    require_POST,
    staff_accessible_classes_queryset,
    staff_can_manage_classroom,
    staff_classroom_or_none,
    staff_member_required,
)


@staff_member_required
def teach_lessons(request):
    classes = list(staff_accessible_classes_queryset(request.user).order_by("name", "id"))
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
        lesson_rows = _build_lesson_tracker_rows(
            request,
            classroom.id,
            modules,
            student_count,
            class_session_epoch=classroom.session_epoch,
        )
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

    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return _safe_internal_redirect(request, _with_notice(return_to, error="Class not found."), fallback=return_to)
    if not staff_can_manage_classroom(request.user, classroom):
        return _safe_internal_redirect(request, _with_notice(return_to, error="Class write access denied."), fallback=return_to)

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
    "teach_lessons",
    "teach_set_lesson_release",
]
