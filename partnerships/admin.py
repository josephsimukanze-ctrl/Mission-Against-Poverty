
from django.contrib import admin
from .models import PartnerOrganization, PartnershipApplication, PartnershipAgreement, PartnerProject


@admin.register(PartnerOrganization)
class PartnerOrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "approved", "email", "location")
    list_filter = ("approved",)
    search_fields = ("name", "email", "type")


@admin.register(PartnershipApplication)
class PartnershipApplicationAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "contact_person", "partnership_type", "status", "created_at")
    list_filter = ("status", "partnership_type")
    search_fields = ("organization_name", "contact_person", "email")


@admin.register(PartnershipAgreement)
class PartnershipAgreementAdmin(admin.ModelAdmin):
    list_display = ("title", "partner_org", "status", "start_date", "end_date")
    list_filter = ("status",)


@admin.register(PartnerProject)
class PartnerProjectAdmin(admin.ModelAdmin):
    list_display = ("partner_org", "project", "role")
