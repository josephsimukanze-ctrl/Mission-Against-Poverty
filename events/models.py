# events/models.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import AuthoredModel, TimeStampedModel, UUIDModel


# ============================================================
# Validator (migration-safe)
# ============================================================
from django.utils.deconstruct import deconstructible


@deconstructible
class MaxFileSizeValidator:
    def __init__(self, limit_mb=5):
        self.limit_mb = limit_mb

    def __call__(self, file):
        if file.size > self.limit_mb * 1024 * 1024:
            raise ValidationError(
                _("File must be under %(mb)s MB.") % {"mb": self.limit_mb}
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and self.limit_mb == other.limit_mb

    def deconstruct(self):
        path = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
        kwargs = {} if self.limit_mb == 5 else {"limit_mb": self.limit_mb}
        return path, [], kwargs


validate_file_size = MaxFileSizeValidator()


# ============================================================
# Event
# ============================================================
class Event(AuthoredModel, UUIDModel):
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    location    = models.CharField(max_length=250, blank=True)

    starts_at   = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at     = models.DateTimeField(null=True, blank=True)

    cover_image = models.ImageField(
        upload_to="events/",
        blank=True, null=True,
        validators=[validate_file_size],
    )

    # Registration controls
    registration_open = models.BooleanField(default=False, db_index=True)
    capacity          = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("Maximum registrations. Leave blank for unlimited."),
    )

    # Publishing
    published = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["starts_at", "name"]
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        indexes = [
            models.Index(fields=["published", "starts_at"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug(slugify(self.name)[:220])
        super().save(*args, **kwargs)

    def _unique_slug(self, base):
        slug = base or "event"
        n = 1
        while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
            n += 1
            suffix = f"-{n}"
            slug = f"{base[:220 - len(suffix)]}{suffix}"
        return slug

    # ---------- State helpers ----------
    @property
    def is_upcoming(self):
        return self.starts_at and self.starts_at >= timezone.now()

    @property
    def is_ongoing(self):
        now = timezone.now()
        if not self.starts_at:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return self.starts_at <= now

    @property
    def is_past(self):
        if self.ends_at:
            return self.ends_at < timezone.now()
        if self.starts_at:
            return self.starts_at < timezone.now()
        return False

    @property
    def is_visible(self):
        return self.published

    # ---------- Registration helpers ----------
    @property
    def registrations_count(self):
        return self.registrations.filter(status=EventRegistration.Status.CONFIRMED).count()

    @property
    def is_full(self):
        if not self.capacity:
            return False
        return self.registrations_count >= self.capacity

    @property
    def spots_left(self):
        if not self.capacity:
            return None
        return max(0, self.capacity - self.registrations_count)

    @property
    def can_register(self):
        return (
            self.published
            and self.registration_open
            and not self.is_past
            and not self.is_full
        )


# ============================================================
# Event registration
# ============================================================
class EventRegistration(TimeStampedModel, UUIDModel):
    class Status(models.TextChoices):
        PENDING   = "pending",   _("Pending")
        CONFIRMED = "confirmed", _("Confirmed")
        CANCELLED = "cancelled", _("Cancelled")
        WAITLIST  = "waitlist",  _("Waitlisted")

    event      = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="registrations",
    )
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="event_registrations",
    )
    full_name  = models.CharField(max_length=180)
    email      = models.EmailField()
    phone      = models.CharField(max_length=32, blank=True)
    notes      = models.TextField(blank=True)

    status     = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CONFIRMED, db_index=True,
    )
    attended   = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Event registration")
        verbose_name_plural = _("Event registrations")
        constraints = [
            models.UniqueConstraint(
                fields=["event", "email"],
                name="unique_event_email",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} → {self.event.name}"