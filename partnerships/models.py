
# partnerships/models.py
import uuid
from django.conf import settings
from django.db import models
from core.models import TimeStampedModel, UUIDModel


class PartnerOrganization(TimeStampedModel, UUIDModel):
    name = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=80, blank=True, help_text="NGO, Business, Church, Government, School, …")
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    location = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="partners/", blank=True, null=True)
    about = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="partner_orgs")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PartnershipApplication(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        INFO_REQUIRED = "info_required", "Additional Info Required"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        TERMINATED = "terminated", "Terminated"

    class Type(models.TextChoices):
        FINANCIAL = "financial", "Financial sponsorship"
        MATERIAL = "material", "Material & equipment donations"
        PROJECT = "project", "Project implementation"
        SERVICES = "services", "Skills & professional services"
        TRAINING = "training", "Training & mentorship"
        EDUCATION = "education", "Educational support"
        HEALTHCARE = "healthcare", "Healthcare support"
        TECHNOLOGY = "technology", "Technology support"
        OUTREACH = "outreach", "Community outreach"
        RESEARCH = "research", "Research & institutional collaboration"

    organization_name = models.CharField(max_length=200)
    organization_type = models.CharField(max_length=80, blank=True)
    contact_person = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    location = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    partnership_type = models.CharField(max_length=20, choices=Type.choices, default=Type.FINANCIAL)
    proposed_contribution = models.TextField(blank=True)
    proposed_project = models.TextField(blank=True)
    supporting_document = models.FileField(upload_to="partnerships/documents/", blank=True, null=True)
    additional_comments = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="partnership_applications")
    partner_org = models.ForeignKey(PartnerOrganization, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="applications")
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization_name} → {self.get_status_display()}"


class PartnershipAgreement(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        TERMINATED = "terminated", "Terminated"

    partner_org = models.ForeignKey(PartnerOrganization, on_delete=models.CASCADE, related_name="agreements")
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    document = models.FileField(upload_to="partnerships/agreements/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    def __str__(self):
        return self.title


class PartnerProject(TimeStampedModel, UUIDModel):
    """Link between a partner and a MAP project they're contributing to."""
    partner_org = models.ForeignKey(PartnerOrganization, on_delete=models.CASCADE, related_name="partner_projects")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="partner_links")
    role = models.CharField(max_length=200, blank=True, help_text="e.g., Funder, Implementer, Technical advisor")
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("partner_org", "project")]
