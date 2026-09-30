from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import BaseUser


@admin.register(BaseUser)
class BaseUserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_admin", "is_active", "created_at")
    list_filter = ("is_admin", "is_active")
    search_fields = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_admin", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
    readonly_fields = ("created_at", "updated_at", "last_login")
