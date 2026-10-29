# programs/admin.py
from django.contrib import admin
from .models import Program


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "published", "archived", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("published", "archived")
    search_fields = ("name", "summary")