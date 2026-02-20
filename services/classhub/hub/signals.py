"""File cleanup hooks for storage-backed model fields.

These handlers ensure uploaded files are removed when rows are deleted or when
file fields are replaced with new uploads.
"""

from __future__ import annotations

from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import LessonAsset, LessonVideo, Submission


def _remove_file_from_storage(field_file) -> None:
    """Delete a FieldFile safely without writing model updates."""
    if not field_file:
        return
    name = (getattr(field_file, "name", "") or "").strip()
    if not name:
        return
    try:
        field_file.delete(save=False)
    except Exception:
        # Best-effort cleanup; deletion failures should not break requests.
        return


def _cleanup_replaced_file(*, instance, model, field_name: str) -> None:
    """Delete old stored file when a file field is replaced."""
    if not instance.pk:
        return

    try:
        current = model.objects.only(field_name).get(pk=instance.pk)
    except model.DoesNotExist:
        return

    old_file = getattr(current, field_name, None)
    new_file = getattr(instance, field_name, None)
    old_name = (getattr(old_file, "name", "") or "").strip()
    new_name = (getattr(new_file, "name", "") or "").strip()

    if old_name and old_name != new_name:
        _remove_file_from_storage(old_file)


@receiver(pre_save, sender=Submission)
def _submission_file_replaced(sender, instance: Submission, **kwargs):
    _cleanup_replaced_file(instance=instance, model=Submission, field_name="file")


@receiver(post_delete, sender=Submission)
def _submission_file_deleted(sender, instance: Submission, **kwargs):
    _remove_file_from_storage(getattr(instance, "file", None))


@receiver(pre_save, sender=LessonAsset)
def _lesson_asset_file_replaced(sender, instance: LessonAsset, **kwargs):
    _cleanup_replaced_file(instance=instance, model=LessonAsset, field_name="file")


@receiver(post_delete, sender=LessonAsset)
def _lesson_asset_file_deleted(sender, instance: LessonAsset, **kwargs):
    _remove_file_from_storage(getattr(instance, "file", None))


@receiver(pre_save, sender=LessonVideo)
def _lesson_video_file_replaced(sender, instance: LessonVideo, **kwargs):
    _cleanup_replaced_file(instance=instance, model=LessonVideo, field_name="video_file")


@receiver(post_delete, sender=LessonVideo)
def _lesson_video_file_deleted(sender, instance: LessonVideo, **kwargs):
    _remove_file_from_storage(getattr(instance, "video_file", None))

