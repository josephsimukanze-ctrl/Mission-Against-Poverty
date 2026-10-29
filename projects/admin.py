# projects/admin.py
from django.contrib import admin
from .models import Project, ProjectCategory, ProjectMilestone, ProjectAssignment, ProjectUpdate


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class MilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "status", "published", "budget", "beneficiary_target")
    list_filter = ("status", "published", "program")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "summary")
    inlines = [MilestoneInline]


@admin.register(ProjectUpdate)
class ProjectUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "published", "created_at")
    list_filter = ("published",)


admin.site.register(ProjectAssignment)