"""Teacher class dashboard/create/join-card endpoints."""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ...http.headers import apply_no_store
from ...models import Class, ClassInviteLink, ClassStaffAssignment
from ...services.coursepack_import import CoursepackImportError, import_content_upload_to_class
from ...services.teacher_roster_class import build_dashboard_context
from .roster_class_remote_compute import remote_compute_status_context
from .shared_auth import (
    staff_can_create_classes,
    staff_can_manage_policy,
    staff_classroom_or_none,
    staff_default_organization,
    staff_member_required,
)
from .shared_ordering import _next_unique_class_join_code, _normalize_order
from .shared_routing import _audit, _teach_class_path, _with_notice


def _class_assignment_panel_context(*, request, classroom):
    if not request.user.is_superuser:
        return {"class_staff_assignments": [], "class_assignment_staff_users": []}
    User = get_user_model()
    staff_users = list(
        User.objects.filter(is_staff=True, is_active=True, is_superuser=False)
        .order_by("username", "id")
        .only("id", "username")
    )
    assignments = list(
        ClassStaffAssignment.objects.select_related("user")
        .filter(classroom=classroom)
        .order_by("-is_active", "user__username", "id")
    )
    return {
        "class_staff_assignments": assignments,
        "class_assignment_staff_users": staff_users,
    }


from .roster_class_import import teach_create_class


@staff_member_required
def teach_class_dashboard(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)

    context = build_dashboard_context(
        request=request,
        classroom=classroom,
        normalize_order_fn=_normalize_order,
    )
    invite_links = list(
        ClassInviteLink.objects.filter(classroom=classroom)
        .select_related("created_by")
        .order_by("-created_at", "-id")
    )
    now = timezone.now()
    for invite in invite_links:
        invite.invite_url = request.build_absolute_uri(f"/invite/{invite.token}")
        invite.is_expired_now = invite.is_expired(at=now)
        invite.seats_remaining_value = invite.seats_remaining()

    notice = (request.GET.get("notice") or "").strip()
    error = (request.GET.get("error") or "").strip()
    class_assignment_panel = _class_assignment_panel_context(request=request, classroom=classroom)
    can_manage_remote_compute = bool(staff_can_manage_policy(request.user, classroom))
    get_token(request)

    response = render(
        request,
        "teach_class.html",
        {
            "classroom": classroom,
            **context,
            "invite_links": invite_links,
            "notice": notice,
            "error": error,
            "can_manage_helper_remote_compute": can_manage_remote_compute,
            **remote_compute_status_context(
                can_manage_remote_compute=can_manage_remote_compute,
                classroom=classroom,
            ),
            **class_assignment_panel,
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


@staff_member_required
def teach_class_join_card(request, class_id: int):
    classroom = staff_classroom_or_none(request.user, class_id)
    if not classroom:
        return HttpResponse("Not found", status=404)

    query = urlencode({"class_code": classroom.join_code})
    response = render(
        request,
        "teach_join_card.html",
        {
            "classroom": classroom,
            "join_url": request.build_absolute_uri("/"),
            "prefilled_join_url": request.build_absolute_uri(f"/?{query}"),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = [
    "teach_create_class",
    "teach_class_dashboard",
    "teach_class_join_card",
]
