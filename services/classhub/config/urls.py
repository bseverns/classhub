from django.contrib import admin
from django.urls import path
from hub import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", views.healthz),

    # Student flow
    path("", views.index),
    path("join", views.join_class),
    path("student", views.student_home),
    path("logout", views.student_logout),

    # Upload dropbox
    path("material/<int:material_id>/upload", views.material_upload),
    path("submission/<int:submission_id>/download", views.submission_download),

    # Repo-authored course content (markdown)
    path("course/<slug:course_slug>", views.course_overview),
    path("course/<slug:course_slug>/<slug:lesson_slug>", views.course_lesson),
]
