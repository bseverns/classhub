"""Read-only operator dashboard for retention/lifecycle visibility."""

from ...services.data_lifespan import build_data_lifespan_snapshot
from .shared import HttpResponse, apply_no_store, render, staff_can_export_syllabi, staff_member_required


@staff_member_required
def teach_data_lifespan(request):
    can_export_syllabus = bool(staff_can_export_syllabi(request.user))
    if not (request.user.is_superuser or can_export_syllabus):
        return HttpResponse("Forbidden", status=403)

    response = render(
        request,
        "teach_data_lifespan.html",
        {
            "snapshot": build_data_lifespan_snapshot(),
        },
    )
    apply_no_store(response, private=True, pragma=True)
    return response


__all__ = ["teach_data_lifespan"]
