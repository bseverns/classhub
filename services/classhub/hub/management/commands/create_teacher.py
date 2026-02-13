"""Create or update a teacher account.

Usage examples:
  python manage.py create_teacher --username teacher1 --password 'CHANGE_ME'
  python manage.py create_teacher --username teacher1 --email teacher1@example.org --password 'NEW' --update
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a teacher account (staff user)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Teacher username")
        parser.add_argument("--email", default=None, help="Email address")
        parser.add_argument("--password", default=None, help="Password (required for new users)")
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update an existing user instead of failing if username already exists.",
        )
        parser.add_argument(
            "--clear-email",
            action="store_true",
            help="Clear email on update/create.",
        )

        superuser_group = parser.add_mutually_exclusive_group()
        superuser_group.add_argument(
            "--superuser",
            action="store_true",
            help="Grant superuser access (default: false for new users).",
        )
        superuser_group.add_argument(
            "--no-superuser",
            action="store_true",
            help="Explicitly revoke superuser on update.",
        )

        active_group = parser.add_mutually_exclusive_group()
        active_group.add_argument(
            "--active",
            action="store_true",
            help="Mark account active.",
        )
        active_group.add_argument(
            "--inactive",
            action="store_true",
            help="Mark account inactive.",
        )

    def handle(self, *args, **opts):
        username = (opts.get("username") or "").strip()
        email = opts.get("email")
        password = opts.get("password")
        update = bool(opts.get("update"))
        clear_email = bool(opts.get("clear_email"))

        if not username:
            raise CommandError("--username is required.")
        if clear_email and email is not None:
            raise CommandError("Use either --email or --clear-email, not both.")

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        exists = user is not None

        if exists and not update:
            raise CommandError(f"User '{username}' already exists. Re-run with --update.")
        if not exists and update:
            raise CommandError(f"User '{username}' does not exist. Remove --update to create.")

        # Resolve target flags.
        if opts.get("superuser"):
            target_superuser = True
            explicit_superuser = True
        elif opts.get("no_superuser"):
            target_superuser = False
            explicit_superuser = True
        else:
            target_superuser = False
            explicit_superuser = False

        if opts.get("active"):
            target_active = True
            explicit_active = True
        elif opts.get("inactive"):
            target_active = False
            explicit_active = True
        else:
            target_active = True
            explicit_active = False

        if not exists:
            if not password:
                raise CommandError("--password is required when creating a new teacher.")

            target_email = "" if clear_email else ((email or "").strip())
            user = User.objects.create_user(
                username=username,
                email=target_email,
                password=password,
            )
            user.is_staff = True
            user.is_superuser = target_superuser
            user.is_active = target_active
            user.save(update_fields=["is_staff", "is_superuser", "is_active"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created teacher '{username}' (is_staff={user.is_staff}, "
                    f"is_superuser={user.is_superuser}, is_active={user.is_active})."
                )
            )
            return

        # Update existing user.
        changed_fields: list[str] = []
        password_updated = False

        if not user.is_staff:
            user.is_staff = True
            changed_fields.append("is_staff")

        if explicit_superuser and user.is_superuser != target_superuser:
            user.is_superuser = target_superuser
            changed_fields.append("is_superuser")

        if explicit_active and user.is_active != target_active:
            user.is_active = target_active
            changed_fields.append("is_active")

        if clear_email and user.email:
            user.email = ""
            changed_fields.append("email")
        elif email is not None:
            new_email = email.strip()
            if user.email != new_email:
                user.email = new_email
                changed_fields.append("email")

        if password:
            user.set_password(password)
            password_updated = True

        if changed_fields:
            user.save(update_fields=changed_fields)
        if password_updated:
            user.save(update_fields=["password"])

        if changed_fields or password_updated:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated teacher '{username}' (changed: "
                    f"{', '.join(changed_fields + (['password'] if password_updated else []))})."
                )
            )
        else:
            self.stdout.write(self.style.WARNING(f"No changes for teacher '{username}'."))
