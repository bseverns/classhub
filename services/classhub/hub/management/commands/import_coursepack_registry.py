"""Import a registry-indexed coursepack ZIP into the DB as Modules + Materials."""

from __future__ import annotations

from hub.models import AuditEvent
from django.core.management.base import BaseCommand, CommandError

from hub.models import Organization
from hub.services.coursepack_import import CoursepackImportError, import_coursepack_registry


class Command(BaseCommand):
    help = "Import a coursepack from a static registry index into Modules + Materials."

    def _record_audit(self, *, result, replace: bool, overwrite_content: bool) -> None:
        AuditEvent.objects.create(
            actor_user=None,
            action="coursepack.registry.import",
            target_type="Coursepack",
            target_id=result.course_slug,
            summary=f"Imported registry coursepack for {result.course_slug}",
            classroom=result.classroom,
            metadata={
                "import_channel": "management_command",
                "course_slug": result.course_slug,
                "course_title": result.course_title,
                "classroom_id": result.classroom.id,
                "join_code": result.classroom.join_code,
                "course_dir": str(result.course_dir),
                "created_modules": result.created_modules,
                "created_materials": result.created_materials,
                "created_assets": result.created_assets,
                "extracted_files": result.extracted_files,
                "source_kind": result.source_kind,
                "source_files": list(result.source_files),
                "source_metadata": result.source_metadata,
                "replace": replace,
                "overwrite_content": overwrite_content,
            },
        )

    def add_arguments(self, parser):
        parser.add_argument("--index", required=True, help="Registry index path or URL")
        parser.add_argument("--course-slug", required=True, help="Course slug from the registry index")
        parser.add_argument(
            "--registry-version",
            default="",
            help="Optional registry version (defaults to latest generated entry).",
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument("--class-code", default="")
        group.add_argument("--class-name", default="")

        parser.add_argument(
            "--create-class",
            action="store_true",
            help="Create a new Class if it does not exist (uses course title by default).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing modules/materials for the class before importing.",
        )
        parser.add_argument(
            "--overwrite-content",
            action="store_true",
            help="Replace existing extracted course content under CONTENT_ROOT/courses/<slug>.",
        )
        parser.add_argument(
            "--organization-id",
            type=int,
            default=None,
            help="Optional organization to attach when creating a class.",
        )

    def handle(self, *args, **opts):
        organization = None
        if opts.get("organization_id") is not None:
            organization = Organization.objects.filter(id=opts["organization_id"]).first()
            if organization is None:
                raise CommandError("No organization found for --organization-id.")

        try:
            result = import_coursepack_registry(
                index_location=opts["index"],
                course_slug=opts["course_slug"],
                version=opts.get("registry_version") or "",
                class_code=opts.get("class_code") or "",
                class_name=opts.get("class_name") or "",
                create_class=bool(opts.get("create_class")),
                replace=bool(opts.get("replace")),
                overwrite_content=bool(opts.get("overwrite_content")),
                organization=organization,
            )
        except CoursepackImportError as exc:
            raise CommandError(str(exc)) from exc

        self._record_audit(
            result=result,
            replace=bool(opts.get("replace")),
            overwrite_content=bool(opts.get("overwrite_content")),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported registry course '{result.course_slug}' into class "
                f"'{result.classroom.name}' ({result.classroom.join_code}). "
                f"Version: {result.source_files[2] or 'latest'}. "
                f"Modules: {result.created_modules}, materials: {result.created_materials}, "
                f"support assets: {result.created_assets}."
            )
        )
