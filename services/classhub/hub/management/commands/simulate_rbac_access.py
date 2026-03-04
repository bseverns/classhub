from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ...models import Class
from ...services.org_access import evaluate_staff_capability


class Command(BaseCommand):
    help = "Simulate a staff RBAC capability decision for debugging and policy review."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--user-id", type=int, dest="user_id")
        target.add_argument("--username", dest="username")
        parser.add_argument("--capability", required=True, dest="capability")
        parser.add_argument("--class-id", type=int, dest="class_id")
        parser.add_argument("--module-id", type=int, dest="module_id")
        parser.add_argument("--json", action="store_true", dest="json_output")

    def handle(self, *args, **options):
        user = self._resolve_user(user_id=options.get("user_id"), username=options.get("username"))
        capability = str(options.get("capability") or "").strip().lower()
        if not capability:
            raise CommandError("capability is required")

        class_id = options.get("class_id")
        module_id = options.get("module_id")
        if module_id and not class_id:
            raise CommandError("module-id requires class-id")

        classroom = None
        if class_id:
            classroom = Class.objects.filter(id=class_id).first()
            if classroom is None:
                raise CommandError(f"class not found: {class_id}")

        decision = evaluate_staff_capability(
            user,
            capability,
            classroom=classroom,
            module_id=module_id,
        )
        payload = {
            "target_user": {
                "id": user.id,
                "username": user.get_username(),
                "is_staff": bool(user.is_staff),
                "is_superuser": bool(user.is_superuser),
            },
            "decision": {
                "allowed": bool(decision.allowed),
                "capability": decision.capability,
                "reason": decision.reason,
                "role": decision.role,
                "organization_id": decision.organization_id,
                "classroom_id": decision.classroom_id,
                "module_id": decision.module_id,
            },
        }

        if options.get("json_output"):
            self.stdout.write(json.dumps(payload, sort_keys=True))
            return

        decision_row = payload["decision"]
        self.stdout.write(
            "allowed={allowed} reason={reason} capability={capability} role={role}".format(
                allowed=decision_row["allowed"],
                reason=decision_row["reason"],
                capability=decision_row["capability"],
                role=decision_row["role"] or "-",
            )
        )
        self.stdout.write(f"user={user.get_username()} id={user.id}")
        if class_id:
            self.stdout.write(f"class_id={class_id}")
        if module_id:
            self.stdout.write(f"module_id={module_id}")

    def _resolve_user(self, *, user_id: int | None, username: str | None):
        User = get_user_model()
        if user_id:
            user = User.objects.filter(id=user_id).first()
            if user is None:
                raise CommandError(f"user not found: {user_id}")
            return user
        user = User.objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"user not found: {username}")
        return user
