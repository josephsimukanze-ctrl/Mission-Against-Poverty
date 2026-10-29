from django.contrib import admin
from .models import Donation, DonationItem, Campaign, Pledge, Receipt


class DonationItemInline(admin.TabularInline):
    model = DonationItem
    extra = 1


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "target_amount", "start_date", "end_date")
    list_filter = ("status",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "summary")


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("reference", "amount", "currency", "kind", "status", "donor_name", "created_at")
    list_filter = ("status", "kind", "frequency")
    search_fields = ("reference", "donor_name", "donor_email")
    readonly_fields = ("reference", "created_at", "updated_at")
    inlines = [DonationItemInline]
    date_hierarchy = "created_at"


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = ("donor_name", "kind", "amount", "expected_on", "fulfilled")
    list_filter = ("fulfilled", "kind")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("number", "donation", "issued_at")
    search_fields = ("number", "donation__reference")
