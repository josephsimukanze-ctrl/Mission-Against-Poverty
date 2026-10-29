# payments/models.py
import uuid
from django.db import models
from core.models import TimeStampedModel, UUIDModel


class PaymentTransaction(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    donation = models.ForeignKey("donations.Donation", on_delete=models.PROTECT, related_name="transactions")
    provider = models.CharField(max_length=40, default="mock")
    provider_reference = models.CharField(max_length=120, blank=True, db_index=True)
    provider_status = models.CharField(max_length=60, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="ZMW")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    raw_response = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_reference"],
                condition=~models.Q(provider_reference=""),
                name="uniq_provider_ref",
            )
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_reference or self.pk} → {self.status}"


class PaymentWebhookEvent(TimeStampedModel, UUIDModel):
    """Every inbound webhook recorded once. Duplicate processing is prevented by idempotency_key."""
    provider = models.CharField(max_length=40)
    event_type = models.CharField(max_length=80)
    idempotency_key = models.CharField(max_length=200, unique=True)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="webhook_events")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}:{self.event_type} [{self.idempotency_key}]"


class Refund(TimeStampedModel, UUIDModel):
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="+")
    refunded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund {self.amount} on {self.transaction}"
