# settings_app/models.py
import os
from decimal import Decimal, InvalidOperation

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, UUIDModel


DEFAULT_PRESET_AMOUNTS = "25,50,100,250,500,1000,2500,5000,10000,25000"


# ===============================================================
# Upload paths
#
# These MUST be module-level named functions — Django's migration
# writer serializes `upload_to` by importing the function from its
# module by name. Closures (e.g. `_upload("logo")`) can't be
# serialized and crash `makemigrations`.
# ===============================================================

def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower() or ".png"


def logo_upload_to(instance, filename):
    return f"site/logo{_ext(filename)}"


def logo_light_upload_to(instance, filename):
    return f"site/logo-light{_ext(filename)}"


def favicon_upload_to(instance, filename):
    return f"site/favicon{_ext(filename)}"


def og_image_upload_to(instance, filename):
    return f"site/og{_ext(filename)}"


# ===============================================================
# OrganizationSetting (unchanged)
# ===============================================================

class OrganizationSetting(UUIDModel, TimeStampedModel):
    """Singleton-per-key organization settings."""
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=200)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label


# ===============================================================
# SiteConfig
# ===============================================================

class SiteConfig(models.Model):
    """
    Single global config record (pk=1).

    All fields are optional — blank values fall back to defaults in
    templates (`{{ site.field|default:"..." }}`).
    """

    id = models.PositiveIntegerField(primary_key=True, default=1, editable=False)

    # ---------------------------------------------------------------
    # Identity
    # ---------------------------------------------------------------
    site_name = models.CharField(max_length=200, default="Mission Against Poverty")
    tagline = models.CharField(max_length=300, blank=True)

    logo = models.ImageField(
        upload_to=logo_upload_to, blank=True, null=True,
        help_text="Primary logo. Shown in the header on light backgrounds.",
    )
    logo_light = models.ImageField(
        upload_to=logo_light_upload_to, blank=True, null=True,
        help_text="Light version of the logo for dark backgrounds (footer).",
    )
    favicon = models.ImageField(
        upload_to=favicon_upload_to, blank=True, null=True,
        help_text="32×32 or 64×64 PNG/ICO. Shown in browser tabs.",
    )
    og_image = models.ImageField(
        upload_to=og_image_upload_to, blank=True, null=True,
        help_text="1200×630 px image shown when the site is shared on social media.",
    )

    # ---------------------------------------------------------------
    # Contact
    # ---------------------------------------------------------------
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(
        blank=True,
        help_text="Line breaks are preserved on the public site.",
    )
    office_hours = models.CharField(
        max_length=200, blank=True,
        help_text="e.g. Mon–Fri, 08:00–17:00 CAT",
    )
    google_maps_embed = models.TextField(
        blank=True,
        help_text="Paste the full <iframe …></iframe> from Google Maps → Share → Embed a map.",
    )

    # ---------------------------------------------------------------
    # Banking & mobile money
    # ---------------------------------------------------------------
    bank_name = models.CharField(max_length=120, blank=True)
    bank_branch = models.CharField(max_length=120, blank=True)
    bank_account_name = models.CharField(max_length=200, blank=True)
    bank_account_number = models.CharField(max_length=60, blank=True)
    bank_sort_code = models.CharField(max_length=40, blank=True)
    bank_swift = models.CharField(max_length=40, blank=True, verbose_name="SWIFT / BIC")
    bank_iban = models.CharField(max_length=60, blank=True, verbose_name="IBAN")
    about_hero_image = models.ImageField(upload_to="site/about/", blank=True, null=True, help_text="Hero background image for the About page (1600×900 recommended).")
    about_hero_heading = models.CharField(max_length=250, blank=True, help_text="Hero heading on the About page.")
    about_hero_subheading = models.TextField(blank=True, help_text="Hero subheading on the About page.")
    mission_heading = models.CharField(max_length=120, blank=True, default="Our Mission")
    mission_icon = models.CharField(max_length=20, blank=True, default="🎯", help_text="Emoji or single character icon.")
    vision_heading = models.CharField(max_length=120, blank=True, default="Our Vision")
    vision_icon = models.CharField(max_length=20, blank=True, default="🌅")
    reach_heading = models.CharField(max_length=120, blank=True, default="Our Reach")
    reach_icon = models.CharField(max_length=20, blank=True, default="📍")

    mission_image = models.ImageField(upload_to="site/about/", blank=True, null=True, help_text="Image shown below the Mission text (800×600 recommended).")
    vision_image = models.ImageField(upload_to="site/about/", blank=True, null=True, help_text="Image shown below the Vision text.")
    reach_image = models.ImageField(upload_to="site/about/", blank=True, null=True, help_text="Image shown below the Reach text.")

    # About page content
    mission_text = models.TextField(
        blank=True,
        help_text="Shown on the About page under 'Our Mission'.",
    )
    vision_text = models.TextField(
        blank=True,
        help_text="Shown on the About page under 'Our Vision'.",
    )
    reach_text = models.TextField(
        blank=True,
        help_text="Shown on the About page under 'Our Reach'.",
    )

    bank_transfer_instructions = models.TextField(
        blank=True,
        help_text="Shown above the bank details. e.g. 'Use your donation reference as the transfer note.'",
    )

    mobile_money_name = models.CharField(
        max_length=80, blank=True,
        help_text="e.g. Airtel Money, MTN MoMo",
    )
    mobile_money_number = models.CharField(max_length=40, blank=True)

    # ---------------------------------------------------------------
    # Donations
    # ---------------------------------------------------------------
    currency = models.CharField(
        max_length=8, default="ZMW",
        help_text="ISO code: ZMW, USD, EUR, GBP, KES, ZAR",
    )
    currency_symbol = models.CharField(
        max_length=8, default="K",
        help_text="Symbol shown before amounts (K, $, €, £). Not the ISO code.",
    )
    min_donation = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Smallest amount accepted by the donate form.",
    )
    preset_amounts_csv = models.CharField(
        max_length=255, blank=True, default=DEFAULT_PRESET_AMOUNTS,
        help_text="Comma-separated whole numbers. Shown as clickable chips on the donate page.",
    )

    # ---------------------------------------------------------------
    # Social
    # ---------------------------------------------------------------
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True, verbose_name="X / Twitter")
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    # ---------------------------------------------------------------
    # SEO, footer, analytics
    # ---------------------------------------------------------------
    footer_description = models.TextField(
        blank=True,
        help_text="2–3 sentences shown under the site name in the footer.",
    )
    copyright_text = models.CharField(
        max_length=200, blank=True,
        help_text="Leave blank to auto-generate: © <year> <site name>. All rights reserved.",
    )
    default_meta_description = models.TextField(
        blank=True,
        help_text="Aim for 150–160 characters. Appears in search results.",
    )
    google_analytics_id = models.CharField(
        max_length=40, blank=True,
        help_text="Format: G-XXXXXXXXXX. Leave blank to disable tracking.",
    )

    # ---------------------------------------------------------------
    # System
    # ---------------------------------------------------------------
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="When enabled, the public site shows a maintenance page.",
    )

    class Meta:
        verbose_name = "Site configuration"
        verbose_name_plural = "Site configuration"

    # ===============================================================
    # Singleton enforcement
    # ===============================================================
    def save(self, *args, **kwargs):
        self.id = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("SiteConfig is a singleton and cannot be deleted.")

    @classmethod
    def load(cls):
        """Return the singleton config, creating it if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    # ===============================================================
    # Helpers used by templates and donate page
    # ===============================================================
    @property
    def preset_amounts(self):
        """
        Parsed, de-duplicated, ordered list of positive integers.

        Invalid entries are silently dropped so a bad admin input never
        breaks the public donate page.
        """
        raw = (self.preset_amounts_csv or "").strip()
        if not raw:
            return []
        seen, out = set(), []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                n = int(chunk)
            except (ValueError, InvalidOperation):
                continue
            if n > 0 and n not in seen:
                seen.add(n)
                out.append(n)
        return out

    @property
    def preset_amounts_list(self):
        """Alias for preset_amounts — used by templates that expect a list name."""
        return self.preset_amounts

    @property
    def has_bank_details(self):
        return bool(self.bank_account_number and self.bank_account_name)

    @property
    def has_mobile_money(self):
        return bool(self.mobile_money_name and self.mobile_money_number)

    @property
    def social_links(self):
        """Return (name, url, icon) for non-empty social URLs."""
        rows = [
            ("Facebook",  self.facebook_url,  "f"),
            ("X",         self.twitter_url,   "𝕏"),
            ("Instagram", self.instagram_url, "📷"),
            ("LinkedIn",  self.linkedin_url,  "in"),
            ("YouTube",   self.youtube_url,   "▶"),
        ]
        return [(name, url, icon) for name, url, icon in rows if url]

    @property
    def has_social_links(self):
        return any([self.facebook_url, self.twitter_url, self.instagram_url,
                    self.linkedin_url, self.youtube_url])

    @property
    def copyright_line(self):
        """Explicit copyright text, or an auto-generated fallback."""
        if self.copyright_text:
            return self.copyright_text
        return f"© {timezone.now().year} {self.site_name}. All rights reserved."

    def __str__(self):
        return self.site_name