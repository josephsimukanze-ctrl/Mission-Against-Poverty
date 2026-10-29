# donations/models.py
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from core.models import AuthoredModel, TimeStampedModel, UUIDModel


class Campaign(AuthoredModel, UUIDModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cover_image = models.ImageField(upload_to="campaigns/", blank=True, null=True)
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="campaigns")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("donations:campaign_detail", args=[self.slug])

    @property
    def raised_amount(self):
        total = self.donations.filter(status=Donation.Status.RECEIVED).aggregate(
            t=models.Sum("amount"))["t"]
        return total or Decimal("0")

    @property
    def progress_percent(self):
        if not self.target_amount:
            return 0
        return min(100, round(float(self.raised_amount) / float(self.target_amount) * 100))


class Donation(AuthoredModel, UUIDModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RECEIVED = "received", "Received"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    class Kind(models.TextChoices):
        CASH = "cash", "Cash"
        MATERIAL = "material", "Material / In-kind"

    class Frequency(models.TextChoices):
        ONE_TIME = "one_time", "One-time"
        MONTHLY = "monthly", "Monthly"

    # NOTE: unique + editable=False, no callable default. Value generated in save().
    reference = models.CharField(max_length=32, unique=True, editable=False)

    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="donations")
    donor_name = models.CharField(max_length=150, blank=True)
    donor_email = models.EmailField(blank=True)
    donor_phone = models.CharField(max_length=32, blank=True)
    is_anonymous = models.BooleanField(default=False)

    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.CASH)
    frequency = models.CharField(max_length=12, choices=Frequency.choices, default=Frequency.ONE_TIME)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="ZMW")

    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations")
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="donations")

    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.reference} · {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = "MAP-" + uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)


    # Bank-transfer proof-of-payment (no gateway API)
    bank_reference = models.CharField(
        max_length=64, blank=True,
        help_text="Reference number the donor should include with their transfer.",
    )
    proof_of_payment = models.FileField(
        upload_to="donations/proof/", blank=True, null=True,
        help_text="Screenshot or photo of the bank/mobile-money receipt.",
    )
    proof_notes = models.TextField(blank=True)
    proof_submitted_at = models.DateTimeField(null=True, blank=True)
    proof_verified_at = models.DateTimeField(null=True, blank=True)
    proof_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    proof_rejected = models.BooleanField(default=False)
    proof_rejection_reason = models.TextField(blank=True)


class DonationItem(TimeStampedModel, UUIDModel):
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=250)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return f"{self.quantity} × {self.description}"


class Pledge(TimeStampedModel, UUIDModel):
    donor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="pledges")
    donor_name = models.CharField(max_length=150)
    donor_email = models.EmailField()
    donor_phone = models.CharField(max_length=32, blank=True)
    kind = models.CharField(max_length=12, choices=Donation.Kind.choices, default=Donation.Kind.CASH)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    expected_on = models.DateField(null=True, blank=True)
    fulfilled = models.BooleanField(default=False)
    fulfilled_donation = models.ForeignKey(Donation, on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name="+")

    def __str__(self):
        return f"Pledge by {self.donor_name}"


class Receipt(TimeStampedModel, UUIDModel):
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name="receipt")
    number = models.CharField(max_length=32, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="receipts/", blank=True, null=True)

    def __str__(self):
        return f"Receipt {self.number}"
