"""Service helpers for teacher-home data/query assembly."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import Submission
from .org_access import staff_accessible_classes_ranked
from .teacher_tracker import _build_class_digest_rows


def recent_submissions_for_class_ids(class_ids: list[int]) -> list[Submission]:
    if not class_ids:
        return []
    return list(
        Submission.objects.select_related("student", "material__module__classroom")
        .filter(material__module__classroom_id__in=class_ids)[:20]
    )


def build_teacher_home_context_data(*, user) -> dict:
    classes, assigned_class_ids = staff_accessible_classes_ranked(user)
    assigned_classes = [c for c in classes if c.id in assigned_class_ids]
    digest_since = timezone.now() - timedelta(days=1)
    class_digest_rows = _build_class_digest_rows(classes, since=digest_since)
    user_model = get_user_model()
    teacher_accounts = (
        user_model.objects.filter(is_staff=True)
        .order_by("username", "id")
        .only("id", "username", "first_name", "last_name", "email", "is_active", "is_superuser")
    )
    class_ids = [int(c.id) for c in classes]
    recent_submissions = recent_submissions_for_class_ids(class_ids)
    return {
        "classes": classes,
        "assigned_class_ids": assigned_class_ids,
        "assigned_classes": assigned_classes,
        "digest_since": digest_since,
        "class_digest_rows": class_digest_rows,
        "user_model": user_model,
        "teacher_accounts": teacher_accounts,
        "recent_submissions": recent_submissions,
    }


__all__ = [
    "build_teacher_home_context_data",
    "recent_submissions_for_class_ids",
]
