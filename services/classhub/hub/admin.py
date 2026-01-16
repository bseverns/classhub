from django.contrib import admin
from .models import Class, Module, Material, StudentIdentity

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "join_code", "is_locked")
    search_fields = ("name", "join_code")
    list_filter = ("is_locked",)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "classroom", "order_index")
    list_filter = ("classroom",)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "type", "order_index")
    list_filter = ("type", "module__classroom")

@admin.register(StudentIdentity)
class StudentIdentityAdmin(admin.ModelAdmin):
    list_display = ("display_name", "classroom", "created_at", "last_seen_at")
    list_filter = ("classroom",)
    search_fields = ("display_name",)
