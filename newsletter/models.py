# newsletter/models.py
import uuid
from django.conf import settings
from django.db import models
from core.models import TimeStampedModel, UUIDModel


class NewsletterSubscriber(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
        BOUNCED = "bounced", "Bounced"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    source = models.CharField(max_length=80, blank=True, help_text="Where the subscriber signed up")
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class NewsletterCampaign(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"
        CANCELLED = "cancelled", "Cancelled"

    subject = models.CharField(max_length=250)
    preview_text = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, help_text="HTML or plain text")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject
