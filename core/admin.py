# core/admin.py
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identity", {
            "fields": ("site_name", "tagline", "logo", "logo_light", "favicon"),
        }),
        ("Contact", {
            "fields": (
                "contact_email", "contact_phone", "contact_address",
                "office_hours", "google_maps_embed",
            ),
        }),
        ("Banking & Mobile Money", {
            "fields": (
                "bank_name", "bank_branch", "bank_account_name",
                "bank_account_number", "bank_sort_code",
                "bank_swift", "bank_iban",
                "mobile_money_name", "mobile_money_number",
                "bank_transfer_instructions",
            ),
            "classes": ("collapse",),
        }),
        ("Donation Settings", {
            "fields": ("currency", "currency_symbol", "min_donation", "preset_amounts"),
        }),
        ("Social Media", {
            "fields": (
                "facebook_url", "twitter_url", "instagram_url",
                "linkedin_url", "youtube_url",
            ),
            "classes": ("collapse",),
        }),
        ("Footer & SEO", {
            "fields": (
                "footer_description", "copyright_text",
                "default_meta_description", "google_analytics_id",
            ),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSetting.get()
        return redirect(reverse("admin:core_sitesetting_change", args=[obj.pk]))
from core.models import ContactEntry


@admin.register(ContactEntry)
class ContactEntryAdmin(admin.ModelAdmin):
    list_display = ("kind", "label", "value", "is_primary", "is_active", "order")
    list_filter = ("kind", "is_primary", "is_active")
    list_editable = ("order", "is_primary", "is_active")
    search_fields = ("label", "value")
