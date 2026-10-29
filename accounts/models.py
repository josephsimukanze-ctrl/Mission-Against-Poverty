# accounts/models.py
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    DONOR = "donor", "Donor"
    VOLUNTEER = "volunteer", "Volunteer"
    PARTNER = "partner", "Partner"
    BENEFICIARY = "beneficiary", "Beneficiary"
    CASE_OFFICER = "case_officer", "Case Officer"
    VOLUNTEER_COORDINATOR = "volunteer_coordinator", "Volunteer Coordinator"
    FUNDRAISING_OFFICER = "fundraising_officer", "Fundraising Officer"
    FINANCE_OFFICER = "finance_officer", "Finance Officer"
    PROJECT_MANAGER = "project_manager", "Project Manager"
    COMMUNICATIONS_OFFICER = "communications_officer", "Communications Officer"
    ADMINISTRATOR = "administrator", "Administrator"


STAFF_ROLES = {
    Role.CASE_OFFICER,
    Role.VOLUNTEER_COORDINATOR,
    Role.FUNDRAISING_OFFICER,
    Role.FINANCE_OFFICER,
    Role.PROJECT_MANAGER,
    Role.COMMUNICATIONS_OFFICER,
    Role.ADMINISTRATOR,
}


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.DONOR)
    phone = models.CharField(max_length=32, blank=True)
    email_verified = models.BooleanField(default=False)

    def is_staff_member(self) -> bool:
        return self.role in STAFF_ROLES or self.is_superuser

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    photo = models.ImageField(upload_to="profiles/", blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"
