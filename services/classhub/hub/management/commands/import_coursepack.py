"""Import a repo-authored course pack into the DB as Modules + Materials."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from hub.models import Organization
from hub.services.coursepack_import import CoursepackImportError, import_coursepack_to_class


class Command(BaseCommand):
    help = "Import a repo-authored course pack into Modules + Materials."

    def add_arguments(self, parser):
        parser.add_argument("--course-slug", default="piper_scratch_12_session")

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
            result = import_coursepack_to_class(
                course_slug=opts["course_slug"],
                class_code=opts.get("class_code") or "",
                class_name=opts.get("class_name") or "",
                create_class=bool(opts.get("create_class")),
                replace=bool(opts.get("replace")),
                organization=organization,
            )
        except CoursepackImportError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported course '{result.course_slug}' into class "
                f"'{result.classroom.name}' ({result.classroom.join_code}). "
                f"Modules: {result.created_modules}, materials: {result.created_materials}, "
                f"support assets: {result.created_assets}."
            )
        )
