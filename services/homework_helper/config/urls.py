from django.contrib import admin
from django.urls import path
from tutor import views
from tutor import views_remote_compute

urlpatterns = [
    path("admin/", admin.site.urls),
    path("helper/healthz", views.healthz),
    path("helper/chat", views.chat),
    path("helper/internal/reset-class-conversations", views.reset_class_conversations),
    path("helper/internal/rag-status", views.internal_rag_status),
    path("helper/internal/remote-compute-status", views_remote_compute.internal_remote_compute_status),
    path("helper/internal/remote-compute-evidence", views_remote_compute.internal_remote_compute_evidence),
    path("helper/internal/remote-compute-control", views_remote_compute.internal_remote_compute_control),
]
