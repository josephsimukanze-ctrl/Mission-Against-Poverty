# beneficiaries/models.py
import uuid
from django.conf import settings
from django.db import models
from core.models import TimeStampedModel, UUIDModel


class BeneficiaryProfile(TimeStampedModel, UUIDModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="beneficiary_profile")
    household_size = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Beneficiary<{self.user.get_username()}>"


class AssistanceRequest(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        INFO_REQUIRED = "info_required", "Additional Info Required"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        DELIVERED = "delivered", "Delivered"
        CLOSED = "closed", "Closed"

    class Category(models.TextChoices):
        FOOD = "food", "Food and basic necessities"
        EDUCATION = "education", "Educational support"
        SCHOOL_MATERIALS = "school_materials", "School materials and fees"
        HEALTHCARE = "healthcare", "Healthcare assistance"
        CLOTHING = "clothing", "Clothing"
        SHELTER = "shelter", "Shelter and emergency relief"
        SKILLS = "skills", "Skills training"
        LIVELIHOOD = "livelihood", "Livelihood and entrepreneurship support"
        OTHER = "other", "Other approved community support"

    reference = models.CharField(max_length=32, unique=True, editable=False)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name="assistance_requests")
    full_name = models.CharField(max_length=180)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    location = models.CharField(max_length=200, blank=True)
    household_size = models.PositiveIntegerField(default=1)
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.FOOD)
    description = models.TextField()
    supporting_document = models.FileField(upload_to="assistance/", blank=True, null=True)
    consent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.SUBMITTED, db_index=True)
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = "REQ-" + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)


class NeedsAssessment(TimeStampedModel, UUIDModel):
    request = models.OneToOneField(AssistanceRequest, on_delete=models.CASCADE, related_name="assessment")
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name="+")
    household_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    recommendation = models.TextField(blank=True)

    def __str__(self):
        return f"Assessment for {self.request.reference}"


class AssistanceRecord(TimeStampedModel, UUIDModel):
    request = models.ForeignKey(AssistanceRequest, on_delete=models.CASCADE, related_name="deliveries")
    description = models.CharField(max_length=250)
    delivered_on = models.DateField()
    delivered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="+")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.description} — {self.request.reference}"
