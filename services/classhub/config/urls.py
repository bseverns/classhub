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
]
