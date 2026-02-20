"""Report or remove upload files not referenced by DB FileField rows."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from hub.models import LessonAsset, LessonVideo, Submission


def _iter_media_files(root: Path, prefixes: tuple[str, ...]):
    for prefix in prefixes:
        base = root / prefix
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                yield path


class Command(BaseCommand):
    help = "Report orphan files under MEDIA_ROOT not referenced by Submission/LessonAsset/LessonVideo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete orphan files after reporting. Default is report-only.",
        )
        parser.add_argument(
            "--show",
            type=int,
            default=50,
            help="How many orphan paths to print (default: 50).",
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        delete = bool(options["delete"])
        show = max(int(options["show"]), 0)
        prefixes = ("submissions", "lesson_assets", "lesson_videos")

        if not media_root.exists():
            self.stdout.write(self.style.WARNING(f"MEDIA_ROOT does not exist: {media_root}"))
            return

        referenced = set()
        referenced.update(
            name for name in Submission.objects.exclude(file="").values_list("file", flat=True) if name
        )
        referenced.update(
            name for name in LessonAsset.objects.exclude(file="").values_list("file", flat=True) if name
        )
        referenced.update(
            name
            for name in LessonVideo.objects.exclude(video_file="").values_list("video_file", flat=True)
            if name
        )

        total_files = 0
        orphan_paths: list[Path] = []
        for abs_path in _iter_media_files(media_root, prefixes):
            total_files += 1
            rel = abs_path.relative_to(media_root).as_posix()
            if rel not in referenced:
                orphan_paths.append(abs_path)

        self.stdout.write(f"MEDIA_ROOT: {media_root}")
        self.stdout.write(f"Scanned files: {total_files}")
        self.stdout.write(f"Referenced files: {len(referenced)}")
        self.stdout.write(f"Orphan files: {len(orphan_paths)}")

        for path in orphan_paths[:show]:
            self.stdout.write(f" - {path.relative_to(media_root).as_posix()}")
        if len(orphan_paths) > show:
            self.stdout.write(f"... ({len(orphan_paths) - show} more)")

        if not delete:
            self.stdout.write(self.style.WARNING("[report-only] Use --delete to remove orphan files."))
            return

        deleted = 0
        errors = 0
        for path in orphan_paths:
            try:
                path.unlink()
                deleted += 1
            except Exception:
                errors += 1
        self.stdout.write(self.style.SUCCESS(f"Deleted orphan files: {deleted}; errors: {errors}"))

