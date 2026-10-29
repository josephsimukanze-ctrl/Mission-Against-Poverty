
# volunteers/models.py
import uuid
from django.conf import settings
from django.db import models
from core.models import TimeStampedModel, UUIDModel


class VolunteerProfile(TimeStampedModel, UUIDModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="volunteer_profile")
    location = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True, help_text="Skills and areas of interest")
    availability = models.CharField(max_length=120, blank=True, help_text="e.g., Weekends, Evenings")
    experience = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)
    approved = models.BooleanField(default=False)
    total_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"Volunteer<{self.user.get_username()}>"

    def recalc_hours(self):
        from django.db.models import Sum
        total = self.user.volunteer_hours.aggregate(t=Sum("hours"))["t"] or 0
        self.total_hours = total
        self.save(update_fields=["total_hours", "updated_at"])
        return total


class VolunteerApplication(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        INFO_REQUIRED = "info_required", "Additional Info Required"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    full_name = models.CharField(max_length=180)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    location = models.CharField(max_length=200, blank=True)
    skills = models.TextField(blank=True)
    availability = models.CharField(max_length=120, blank=True)
    areas_of_interest = models.CharField(max_length=300, blank=True)
    experience = models.TextField(blank=True)
    consent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="volunteer_applications")
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} → {self.get_status_display()}"


class VolunteerAssignment(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="volunteer_assignments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteer_assignments")
    event = models.ForeignKey("events.Event", on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteer_assignments")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)

    def __str__(self):
        return f"{self.volunteer.get_username()} → {self.title}"


class VolunteerAttendance(TimeStampedModel, UUIDModel):
    assignment = models.ForeignKey(VolunteerAssignment, on_delete=models.CASCADE, related_name="attendance")
    attended = models.BooleanField(default=False)
    notes = models.TextField(blank=True)


class VolunteerHours(TimeStampedModel, UUIDModel):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="volunteer_hours")
    assignment = models.ForeignKey(VolunteerAssignment, on_delete=models.SET_NULL, null=True, blank=True, related_name="hours")
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]


class Certificate(TimeStampedModel, UUIDModel):
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=200)
    issued_on = models.DateField()
    description = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to="certificates/", blank=True, null=True)

    class Meta:
        ordering = ["-issued_on"]
