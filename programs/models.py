# programs/models.py
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import AuthoredModel, UUIDModel


# ============================================================
# Validators (migration-safe — deconstructible classes)
# ============================================================
@deconstructible
class MaxFileSizeValidator:
    """Reject files larger than `limit_mb` megabytes."""

    def __init__(self, limit_mb=5):
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
        kwargs = {} if self.limit_mb == 5 else {"limit_mb": self.limit_mb}
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
            # Non-image or unreadable — ImageField will handle rejection
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


validate_file_size   = MaxFileSizeValidator()
validate_cover_image = MinImageDimensionsValidator(1200, 600)


# ============================================================
# Queryset
# ============================================================
class ProgramQuerySet(models.QuerySet):
    def visible(self):
        """Programs to show on the public site (published, not archived)."""
        return self.filter(published=True, archived=False)


# ============================================================
# Program
# ============================================================
class Program(AuthoredModel, UUIDModel):
    name        = models.CharField(max_length=180, unique=True)
    slug        = models.SlugField(max_length=200, unique=True, blank=True)
    summary     = models.CharField(
        max_length=300,
        blank=True,
        help_text=_("Short description shown on cards and listings."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Full description. Supports plain text or HTML."),
    )
    icon = models.CharField(
        max_length=80,
        blank=True,
        help_text=_("CSS class or emoji (e.g. 📚 or fa-solid fa-book)."),
    )
    cover_image = models.ImageField(
        upload_to="programs/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_cover_image],
    )

    # Curator controls
    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text=_("Lower number = shown first on the homepage."),
    )
    published = models.BooleanField(default=True, db_index=True)
    archived  = models.BooleanField(default=False, db_index=True)

    objects = ProgramQuerySet.as_manager()

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("Program")
        verbose_name_plural = _("Programs")
        indexes = [
            # Composite index for the most common filter:
            # Program.objects.visible().order_by("order", "name")
            models.Index(
                fields=["published", "archived", "order", "name"],
                name="program_visible_order_idx",
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("programs:detail", args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug(slugify(self.name)[:200])
        super().save(*args, **kwargs)

    def _unique_slug(self, base):
        slug = base or "program"
        n = 1
        while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
            n += 1
            suffix = f"-{n}"
            slug = f"{base[:200 - len(suffix)]}{suffix}"
        return slug

    @property
    def is_visible(self):
        """Convenience property for templates: on the public site or not."""
        return self.published and not self.archived