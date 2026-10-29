# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin for the custom User model.

    Inherits from Django's UserAdmin for authentication features
    (password change, groups, permissions), plus our extra fields.
    """

    list_display = (
        "username", "email", "role",
        "is_staff", "is_active", "date_joined",
    )
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)


# If you have other models in accounts (e.g. roles, profiles), register them here too
# from .models import SomeOtherModel
# admin.site.register(SomeOtherModel)