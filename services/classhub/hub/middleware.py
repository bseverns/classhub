"""Student session middleware.

This is the central trick that makes class-code auth feel like a real login.

- Teachers use Django auth.
- Students are tracked by a session cookie containing student_id + class_id.

Later, this becomes the access-control boundary for the helper and for content.
"""

from .models import StudentIdentity, Class

class StudentSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.student = None
        request.classroom = None

        sid = request.session.get("student_id")
        cid = request.session.get("class_id")

        if sid and cid:
            request.student = StudentIdentity.objects.filter(id=sid, classroom_id=cid).first()
            request.classroom = Class.objects.filter(id=cid).first()

        return self.get_response(request)
