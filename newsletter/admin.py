from django.contrib import admin
from .models import NewsletterSubscriber, NewsletterCampaign


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "status", "source", "created_at")
    list_filter = ("status", "source")
    search_fields = ("email", "name")
    readonly_fields = ("created_at", "updated_at", "unsubscribed_at")


@admin.register(NewsletterCampaign)
class NewsletterCampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "status", "scheduled_for", "sent_at", "recipients_count", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "preview_text", "body")
    readonly_fields = ("created_at", "updated_at", "sent_at")
