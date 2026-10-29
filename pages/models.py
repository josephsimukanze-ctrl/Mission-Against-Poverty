# pages/models.py
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel, UUIDModel, AuthoredModel


# ============================================================
# Validators (migration-safe — deconstructible classes)
# ============================================================
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


@deconstructible
class MaxFileSizeValidator:
    """Reject files larger than `limit_mb` megabytes."""

    def __init__(self, limit_mb=MAX_IMAGE_SIZE_MB):
        self.limit_mb = limit_mb
        self.limit_bytes = limit_mb * 1024 * 1024

    def __call__(self, file):
        if file.size > self.limit_bytes:
            raise ValidationError(
                _("File must be under %(mb)s MB.") % {"mb": self.limit_mb}
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and self.limit_mb == other.limit_mb

    def deconstruct(self):
        path = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
        kwargs = {} if self.limit_mb == MAX_IMAGE_SIZE_MB else {"limit_mb": self.limit_mb}
        return path, [], kwargs


@deconstructible
class MinImageDimensionsValidator:
    """Ensure an image is at least width×height pixels."""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __call__(self, file):
        try:
            from PIL import Image
            with Image.open(file) as img:
                if img.width < self.width or img.height < self.height:
                    raise ValidationError(
                        _("Image must be at least %(w)s×%(h)s px.") % {
                            "w": self.width, "h": self.height,
                        }
                    )
        except ValidationError:
            raise
        except Exception:
            # Non-image or unreadable — let ImageField handle rejection
            pass

    def __eq__(self, other):
        return (
            isinstance(other, MinImageDimensionsValidator)
            and self.width == other.width
            and self.height == other.height
        )

    def deconstruct(self):
        path = f"{self.__class__.__module__}.{self.__class__.__qualname__}"
        return path, [self.width, self.height], {}


validate_file_size = MaxFileSizeValidator()               # 5 MB
validate_page_hero = MinImageDimensionsValidator(1200, 600)
validate_hero_slide = MinImageDimensionsValidator(1200, 900)
validate_portrait = MinImageDimensionsValidator(400, 400)


# ============================================================
# Pages
# ============================================================
class Page(AuthoredModel, UUIDModel):
    """Static-ish CMS pages editable by the communications team."""

    slug = models.SlugField(max_length=180, unique=True, blank=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    body = models.TextField(help_text="Supports plain text or HTML.")
    hero_image = models.ImageField(
        upload_to="pages/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_page_hero],
    )

    # SEO
    meta_title = models.CharField(
        max_length=70,
        blank=True,
        help_text=_("Optional. Defaults to the page title."),
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text=_("Optional. Recommended: 150–160 characters."),
    )

    published = models.BooleanField(default=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["published", "slug"]),
        ]
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("pages:detail", args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug(slugify(self.title)[:180])
        super().save(*args, **kwargs)

    def _unique_slug(self, base):
        slug = base or "page"
        n = 1
        while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
            n += 1
            suffix = f"-{n}"
            slug = f"{base[:180 - len(suffix)]}{suffix}"
        return slug

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        return self.meta_description or self.subtitle or ""


# ============================================================
# Homepage hero carousel
# ============================================================
class HeroSlide(TimeStampedModel, UUIDModel):
    """Images shown in the homepage hero carousel.

    Staff can add, reorder, and toggle slides from the management dashboard.
    """

    title = models.CharField(
        max_length=120,
        blank=True,
        help_text=_("Optional headline shown over the image."),
    )
    subtitle = models.CharField(
        max_length=160,
        blank=True,
        help_text=_("Optional caption shown below the title."),
    )
    image = models.ImageField(
        upload_to="hero/",
        help_text=_("Landscape image, 1600×1200 or larger."),
        validators=[validate_file_size, validate_hero_slide],
    )
    alt_text = models.CharField(
        max_length=160,
        blank=True,
        help_text=_("Describes the image for screen readers."),
    )

    # Optional CTA
    cta_label = models.CharField(max_length=60, blank=True)
    cta_url = models.CharField(
        max_length=200,
        blank=True,
        help_text=_("Relative (e.g. /donate/) or absolute URL."),
    )

    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text=_("Lower number = shown first."),
    )

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("Hero slide")
        verbose_name_plural = _("Hero slides")
        indexes = [
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self):
        return self.title or f"Slide #{self.pk or '—'}"

    def get_absolute_url(self):
        return self.image.url if self.image else "#"

    @property
    def display_title(self):
        return self.title or ""


# ============================================================
# Leadership
# ============================================================
class LeadershipMember(TimeStampedModel, UUIDModel):
    """
    Team members, founders, and advisors.

    Founders are the same model with `is_founder=True` — the About page
    renders them in a dedicated section above the general leadership grid.
    """

    name = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    bio = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="leadership/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_portrait],
    )

    # ---- Roles / categorization ----
    is_founder = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Check to display this person in the Founders section on the About page."),
    )

    # ---- Contact ----
    email = models.EmailField(blank=True)
    linkedin = models.URLField(blank=True)

    # ---- Presentation ----
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("Leadership member")
        verbose_name_plural = _("Leadership members")
        indexes = [
            models.Index(fields=["is_active", "is_founder", "order"]),
        ]

    def __str__(self):
        suffix = " (Founder)" if self.is_founder else ""
        return f"{self.name} — {self.position}{suffix}"

    @property
    def initials(self):
        parts = [p for p in self.name.split() if p]
        return "".join(p[0].upper() for p in parts[:2]) or "?"


# ============================================================
# Media library
# ============================================================
class MediaAsset(TimeStampedModel, UUIDModel):
    """Central media library (images / documents) referenced elsewhere."""

    CATEGORY_CHOICES = [
        ("image", _("Image")),
        ("document", _("Document")),
        ("video", _("Video")),
        ("other", _("Other")),
    ]

    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to="media_library/%Y/%m/",
        validators=[validate_file_size],
    )
    category = models.CharField(
        max_length=16,
        choices=CATEGORY_CHOICES,
        default="image",
        db_index=True,
    )
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_media",
    )

    # Auto-populated metadata
    file_size = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text=_("Bytes — filled automatically on save."),
    )
    mime_type = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Media asset")
        verbose_name_plural = _("Media library")
        indexes = [
            models.Index(fields=["category", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file:
            try:
                self.file_size = self.file.size
            except (OSError, ValueError):
                self.file_size = None
            ext = Path(self.file.name).suffix.lower().lstrip(".")
            self.mime_type = ext
        super().save(*args, **kwargs)

    @property
    def size_display(self):
        if not self.file_size:
            return "—"
        kb = self.file_size / 1024
        if kb < 1024:
            return f"{kb:.0f} KB"
        return f"{kb / 1024:.1f} MB"

    @property
    def is_image(self):
        return self.category == "image"