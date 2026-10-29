
from django.contrib import admin
from .models import (
    VolunteerProfile, VolunteerApplication, VolunteerAssignment,
    VolunteerAttendance, VolunteerHours, Certificate
)


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "approved", "total_hours", "location")
    list_filter = ("approved",)
    search_fields = ("user__username", "user__email", "skills")


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("full_name", "email")


@admin.register(VolunteerAssignment)
class VolunteerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "volunteer", "status", "scheduled_for")
    list_filter = ("status",)


@admin.register(VolunteerHours)
class VolunteerHoursAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "date", "hours")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("volunteer", "title", "issued_on")
