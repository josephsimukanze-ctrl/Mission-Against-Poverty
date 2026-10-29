from django.contrib import admin
from .models import PaymentTransaction, PaymentWebhookEvent, Refund


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("provider", "provider_reference", "donation", "amount", "status", "verified_at")
    list_filter = ("provider", "status")
    search_fields = ("provider_reference", "donation__reference")
    readonly_fields = ("provider_reference", "raw_response", "verified_at", "created_at", "updated_at")


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("provider", "event_type", "idempotency_key", "processed", "created_at")
    list_filter = ("provider", "processed")
    search_fields = ("idempotency_key",)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("transaction", "amount", "approved_by", "refunded_at")
