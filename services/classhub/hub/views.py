import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.middleware.csrf import get_token

from .models import Class, StudentIdentity


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def index(request):
    """Landing page.

    - If student session exists, send them to /student
    - Otherwise, show join form

    Teachers/admins can use /admin for now.
    """
    if getattr(request, "student", None) is not None:
        return redirect("/student")
    get_token(request)
    return render(request, "student_join.html", {})


@require_POST
def join_class(request):
    """Join via class code + display name.

    Body (JSON): {"class_code": "ABCD1234", "display_name": "Ada"}

    Stores student identity in session cookie.
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad_json"}, status=400)

    code = (payload.get("class_code") or "").strip().upper()
    name = (payload.get("display_name") or "").strip()[:80]

    if not code or not name:
        return JsonResponse({"error": "missing_fields"}, status=400)

    classroom = Class.objects.filter(join_code=code).first()
    if not classroom:
        return JsonResponse({"error": "invalid_code"}, status=404)
    if classroom.is_locked:
        return JsonResponse({"error": "class_locked"}, status=403)

    student = StudentIdentity.objects.create(classroom=classroom, display_name=name)
    student.last_seen_at = timezone.now()
    student.save(update_fields=["last_seen_at"])

    request.session["student_id"] = student.id
    request.session["class_id"] = classroom.id

    return JsonResponse({"ok": True})


def student_home(request):
    if getattr(request, "student", None) is None or getattr(request, "classroom", None) is None:
        return redirect("/")

    # Update last seen (cheap pulse; later do this asynchronously)
    request.student.last_seen_at = timezone.now()
    request.student.save(update_fields=["last_seen_at"])

    classroom = request.classroom
    modules = classroom.modules.prefetch_related("materials").all()

    return render(
        request,
        "student_class.html",
        {
            "student": request.student,
            "classroom": classroom,
            "modules": modules,
        },
    )


def student_logout(request):
    request.session.flush()
    return redirect("/")
