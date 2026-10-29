# contacts/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel, UUIDModel


class ContactMessage(TimeStampedModel, UUIDModel):
    STATUS_CHOICES = [
        ("new",       _("New")),
        ("read",      _("Read")),
        ("replied",   _("Replied")),
        ("archived",  _("Archived")),
        ("spam",      _("Spam")),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="new",
        db_index=True,
    )

    # Reply tracking
    replied_at = models.DateTimeField(null=True, blank=True)
    reply_notes = models.TextField(blank=True)

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="contact_messages",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Contact message")
        verbose_name_plural = _("Contact messages")
        indexes = [
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} — {self.subject}"