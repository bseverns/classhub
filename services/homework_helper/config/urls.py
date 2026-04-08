from django.contrib import admin
from django.urls import path
from tutor import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("helper/healthz", views.healthz),
    path("helper/chat", views.chat),
    path("helper/internal/reset-class-conversations", views.reset_class_conversations),
    path("helper/internal/rag-status", views.internal_rag_status),
    path("helper/internal/remote-compute-status", views.internal_remote_compute_status),
    path("helper/internal/remote-compute-control", views.internal_remote_compute_control),
]
