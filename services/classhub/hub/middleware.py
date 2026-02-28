"""Student session middleware.

This is the central trick that makes class-code auth feel like a real login.

- Teachers use Django auth.
- Students are tracked by a session cookie containing student_id + class_id.
- Mobile/headless clients can also use a signed bearer token (issued at join).

Later, this becomes the access-control boundary for the helper and for content.
"""

import logging

from .models import StudentIdentity

logger = logging.getLogger(__name__)

_SESSION_SKIP_PREFIXES = (
    "/static/",
    "/admin/",
    "/helper/",
)
_SESSION_SKIP_EXACT = {"/healthz"}


def _clear_student_session(session) -> None:
    session.pop("student_id", None)
    session.pop("class_id", None)
    session.pop("class_epoch", None)


def _resolve_bearer_token(request) -> bool:
    """Try to authenticate via Authorization: Bearer <token>.

    Returns True if request.student/classroom were set, False otherwise.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header[7:].strip()
    if not token:
        return False

    from .services.api_tokens import verify_student_token

    payload = verify_student_token(token)
    if payload is None:
        return False

    sid = payload.get("sid")
    cid = payload.get("cid")
    token_epoch = payload.get("epoch")
    if not sid or not cid:
        return False

    student = (
        StudentIdentity.objects.select_related("classroom")
        .filter(id=sid, classroom_id=cid)
        .first()
    )
    if student is None:
        return False

    classroom = getattr(student, "classroom", None)
    if classroom is None:
        return False

    current_epoch = int(getattr(classroom, "session_epoch", 1) or 1)
    if token_epoch is not None and int(token_epoch) != current_epoch:
        return False

    request.student = student
    request.classroom = classroom
    return True


class StudentSessionMiddleware:
    """Attach learner context to each request if a student session exists.

    Why this exists:
    - Django already attaches `request.user` for teacher/admin auth.
    - Student auth in this MVP is session-based (class code + display name),
      so we also attach:
      - `request.student`
      - `request.classroom`
    - For /api/ paths, a signed bearer token is also accepted.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Default state for anonymous/teacher requests.
        request.student = None
        request.classroom = None
        path = (getattr(request, "path", "") or "").strip()
        if path in _SESSION_SKIP_EXACT or any(path.startswith(prefix) for prefix in _SESSION_SKIP_PREFIXES):
            return self.get_response(request)

        # For API paths, try bearer token first.
        if path.startswith("/api/") and _resolve_bearer_token(request):
            return self.get_response(request)

        # Student identity is stored in the session after `/join`.
        sid = request.session.get("student_id")
        cid = request.session.get("class_id")
        class_epoch = request.session.get("class_epoch")

        if sid and cid:
            # Resolve both records in one query via select_related.
            student = (
                StudentIdentity.objects.select_related("classroom")
                .filter(id=sid, classroom_id=cid)
                .first()
            )
            classroom = getattr(student, "classroom", None) if student is not None else None
            if student is None or classroom is None:
                _clear_student_session(request.session)
                request.student = None
                request.classroom = None
            else:
                current_epoch = int(getattr(classroom, "session_epoch", 1) or 1)
                if class_epoch is None:
                    request.session["class_epoch"] = current_epoch
                    request.student = student
                    request.classroom = classroom
                else:
                    try:
                        session_epoch = int(class_epoch)
                    except Exception:
                        session_epoch = -1
                    if session_epoch != current_epoch:
                        _clear_student_session(request.session)
                        request.student = None
                        request.classroom = None
                    else:
                        request.student = student
                        request.classroom = classroom

        return self.get_response(request)

