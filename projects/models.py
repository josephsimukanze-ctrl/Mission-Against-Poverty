# projects/models.py
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.models import AuthoredModel, TimeStampedModel, UUIDModel


class ProjectCategory(TimeStampedModel, UUIDModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Project categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)


class Project(AuthoredModel, UUIDModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    program = models.ForeignKey(
        "programs.Program", on_delete=models.PROTECT, related_name="project_set"
    )
    category = models.ForeignKey(
        ProjectCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_projects"
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fundraising_target = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    beneficiary_target = models.PositiveIntegerField(default=0)
    beneficiaries_reached = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED, db_index=True)
    cover_image = models.ImageField(upload_to="projects/", blank=True, null=True)
    published = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "published"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:220]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("projects:detail", args=[self.slug])

    # ============================================================
    # Fundraising helpers — the ONLY place donation sums are computed
    # ============================================================

    def _raised_total(self):
        """
        Sum of *received* donations allocated to this project.
        Returns Decimal('0.00') when none exist.
        """
        return (
            self.donations.filter(status="received").aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

    @property
    def raised_amount(self):
        """
        Total of received donations for this project.
        Templates: {{ project.raised_amount|floatformat:0|intcomma }}
        """
        return self._raised_total()

    @property
    def progress_percent(self):
        """0–100. Shares `_raised_total()` with `raised_amount` so they never disagree."""
        if not self.fundraising_target or self.fundraising_target == 0:
            return 0
        pct = (float(self._raised_total()) / float(self.fundraising_target)) * 100
        return min(100, round(pct))

    @property
    def remaining_amount(self):
        """Target − raised, floored at 0. Useful for 'X left to go' copy."""
        remaining = self.fundraising_target - self.raised_amount
        return remaining if remaining > 0 else Decimal("0.00")


class ProjectMilestone(TimeStampedModel, UUIDModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    completed_on = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "target_date"]

    def __str__(self):
        return f"{self.project.name} — {self.title}"


class ProjectAssignment(TimeStampedModel, UUIDModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_assignments")
    role = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = [("project", "user")]

    def __str__(self):
        return f"{self.user} on {self.project}"


class ProjectUpdate(TimeStampedModel, UUIDModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="updates")
    title = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]