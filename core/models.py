# core/models.py
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================================
# Abstract base models
# ============================================================
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AuthoredModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True


# ============================================================
# Site settings (singleton)
# ============================================================
class SiteSetting(models.Model):
    """
    Global site configuration. Singleton — only one row exists (pk=1).

    Access from views:
        from core.models import SiteSetting
        site = SiteSetting.get()

    Access from templates (via context processor):
        {{ site.site_name }}
        {{ site.contact_email }}
        {{ site.bank_account_number }}

    Cached for 1 hour. Cache cleared automatically on save().
    """

    CACHE_KEY = "site_settings_singleton"
    CACHE_TIMEOUT = 60 * 60  # 1 hour

    # ============================================================
    # Identity
    # ============================================================
    site_name = models.CharField(
        max_length=120,
        default="Mission Against Poverty",
        help_text=_("Displayed in the header, footer, and page titles."),
    )
    tagline = models.CharField(
        max_length=200,
        blank=True,
        default="Together we can end poverty.",
        help_text=_("Short phrase shown under the site name."),
    )
    logo = models.ImageField(
        upload_to="settings/",
        blank=True,
        null=True,
        help_text=_("Main logo shown in the site header."),
    )
    logo_light = models.ImageField(
        upload_to="settings/",
        blank=True,
        null=True,
        help_text=_("Light version for dark backgrounds (footer, hero)."),
    )
    favicon = models.ImageField(
        upload_to="settings/",
        blank=True,
        null=True,
        help_text=_("32×32 or 64×64 ICO/PNG shown in browser tabs."),
    )
    og_image = models.ImageField(
        upload_to="settings/",
        blank=True,
        null=True,
        verbose_name=_("Social share image"),
        help_text=_(
            "Shown when the site is shared on WhatsApp, Facebook, X, or LinkedIn. "
            "Recommended size: 1200×630 pixels."
        ),
    )

    # ============================================================
    # Contact
    # ============================================================
    contact_email = models.EmailField(
        blank=True,
        default="josephsimukanze@gmail.com",
        help_text=_("Primary contact email shown in the footer and on the contact page."),
    )
    contact_phone = models.CharField(
        max_length=32,
        blank=True,
        default="+260 777 672 440",
        help_text=_("Main phone line for donors and partners."),
    )
    contact_address = models.TextField(
        blank=True,
        default="Lusaka, Zambia",
        help_text=_("Physical office address. Line breaks are preserved."),
    )
    office_hours = models.CharField(
        max_length=200,
        blank=True,
        default="Mon–Fri, 08:00–17:00 (CAT)",
        help_text=_("When the office is open for calls and visits."),
    )
    google_maps_embed = models.TextField(
        blank=True,
        help_text=_("Paste the iframe embed code from Google Maps."),
    )

    # ============================================================
    # Banking / Donations
    # ============================================================
    bank_name = models.CharField(
        max_length=120,
        blank=True,
        default="Zanaco",
        help_text=_("e.g. Zanaco, Stanbic, Absa, FNB"),
    )
    bank_branch = models.CharField(
        max_length=120,
        blank=True,
        help_text=_("e.g. Cairo Road Branch"),
    )
    bank_account_name = models.CharField(
        max_length=200,
        blank=True,
        default="Mission Against Poverty",
        help_text=_("Account name as it appears on bank statements."),
    )
    bank_account_number = models.CharField(
        max_length=60,
        blank=True,
        help_text=_("Shown to donors who choose bank transfer."),
    )
    bank_sort_code = models.CharField(
        max_length=30,
        blank=True,
        help_text=_("Branch or sort code, if applicable."),
    )
    bank_swift = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("SWIFT / BIC"),
        help_text=_("For international transfers."),
    )
    bank_iban = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("IBAN"),
    )
    mobile_money_name = models.CharField(
        max_length=60,
        blank=True,
        help_text=_("e.g. Airtel Money, MTN MoMo"),
    )
    mobile_money_number = models.CharField(
        max_length=32,
        blank=True,
        help_text=_("Phone number registered for mobile money."),
    )
    bank_transfer_instructions = models.TextField(
        blank=True,
        help_text=_(
            "Shown to donors who choose bank transfer. "
            "Include reference instructions, e.g. 'Use your name as reference'."
        ),
    )

    # Donation defaults
    currency = models.CharField(
        max_length=8,
        default="ZMW",
        help_text=_("Default currency code, e.g. ZMW, USD, EUR."),
    )
    currency_symbol = models.CharField(
        max_length=8,
        default="K",
        help_text=_("Symbol shown before amounts, e.g. K, $, €."),
    )
    min_donation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10,
        help_text=_("Minimum allowed donation amount."),
    )
    preset_amounts = models.CharField(
        max_length=200,
        default="50,100,250,500,1000",
        help_text=_(
            "Comma-separated preset amounts for donation buttons, e.g. 50,100,250,500."
        ),
    )

    # ============================================================
    # Social
    # ============================================================
    facebook_url = models.URLField(blank=True, verbose_name=_("Facebook"))
    twitter_url = models.URLField(blank=True, verbose_name=_("X / Twitter"))
    instagram_url = models.URLField(blank=True, verbose_name=_("Instagram"))
    linkedin_url = models.URLField(blank=True, verbose_name=_("LinkedIn"))
    youtube_url = models.URLField(blank=True, verbose_name=_("YouTube"))

    # ============================================================
    # Footer / SEO
    # ============================================================
    footer_description = models.TextField(
        blank=True,
        default=(
            "Mission Against Poverty is a community-driven organization "
            "committed to reducing poverty in Zambia through education, "
            "healthcare, skills development and sustainable community support."
        ),
        help_text=_(
            "Shown in the footer of every page. Keep it to 2–3 sentences "
            "describing what your organization does."
        ),
    )
    copyright_text = models.CharField(
        max_length=200,
        blank=True,
        help_text=_(
            "The copyright line at the bottom of the site, e.g. "
            "'© 2026 Mission Against Poverty'. Leave blank to auto-generate "
            "from the current year and site name."
        ),
    )
    default_meta_description = models.TextField(
        blank=True,
        default=(
            "Mission Against Poverty reduces poverty in Zambia through "
            "education, healthcare, skills development and sustainable "
            "community support."
        ),
        help_text=_(
            "Default description used by search engines and social media "
            "when a page doesn't specify its own. Aim for 150–160 characters."
        ),
    )
    google_analytics_id = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_("Google Analytics ID"),
        help_text=_(
            "Optional. Format: G-XXXXXXXXXX. Leave blank to disable "
            "analytics tracking. Get this from analytics.google.com."
        ),
    )

    # ============================================================
    # Metadata
    # ============================================================
    updated_at = models.DateTimeField(auto_now=True)

    about_hero_image = models.ImageField(upload_to="site/about/", blank=True, null=True)
    about_hero_heading = models.CharField(max_length=250, blank=True)
    about_hero_subheading = models.TextField(blank=True)
    mission_heading = models.CharField(max_length=120, blank=True)
    mission_icon = models.CharField(max_length=20, blank=True, default="🎯")
    mission_text = models.TextField(blank=True)
    mission_image = models.ImageField(upload_to="site/about/", blank=True, null=True)
    vision_heading = models.CharField(max_length=120, blank=True)
    vision_icon = models.CharField(max_length=20, blank=True, default="🌅")
    vision_text = models.TextField(blank=True)
    vision_image = models.ImageField(upload_to="site/about/", blank=True, null=True)
    reach_heading = models.CharField(max_length=120, blank=True)
    reach_icon = models.CharField(max_length=20, blank=True, default="📍")
    reach_text = models.TextField(blank=True)
    reach_image = models.ImageField(upload_to="site/about/", blank=True, null=True)

    class Meta:
        verbose_name = _("Site settings")
        verbose_name_plural = _("Site settings")

    def __str__(self):
        return f"Site settings — {self.site_name}"

    # ---------- Singleton enforcement ----------
    def save(self, *args, **kwargs):
        self.pk = 1                       # always single row
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)      # invalidate cache

    def delete(self, *args, **kwargs):
        pass                              # never allow deletion

    @classmethod
    def get(cls):
        """Return the singleton instance, cached for 1 hour."""
        cached = cache.get(cls.CACHE_KEY)
        if cached is not None:
            return cached

        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set(cls.CACHE_KEY, obj, cls.CACHE_TIMEOUT)
        return obj

    # ---------- Template helpers ----------
    @property
    def preset_amounts_list(self):
        """Parse `preset_amounts` into a list of integers."""
        try:
            return [int(a.strip()) for a in self.preset_amounts.split(",") if a.strip()]
        except (ValueError, AttributeError):
            return [50, 100, 250, 500]

    @property
    def social_links(self):
        """List of (name, url, icon) tuples for templates."""
        return [
            ("facebook", self.facebook_url, "f"),
            ("twitter", self.twitter_url, "𝕏"),
            ("instagram", self.instagram_url, "📷"),
            ("linkedin", self.linkedin_url, "in"),
            ("youtube", self.youtube_url, "▶"),
        ]

    @property
    def has_bank_details(self):
        return bool(self.bank_name and self.bank_account_number)

    @property
    def has_social_links(self):
        return any(url for _, url, _ in self.social_links)

    @property
    def copyright_line(self):
        """
        The full copyright line for the footer.

        Uses `copyright_text` if set, otherwise auto-generates:
            © {current_year} {site_name}. All rights reserved.
        """
        if self.copyright_text:
            return self.copyright_text
        from django.utils import timezone
        year = timezone.now().year
        return f"© {year} {self.site_name}. All rights reserved."

    @property
    def og_image_url(self):
        """
        URL to the social share image, with sensible fallbacks:
          1. `og_image` if uploaded
          2. `logo` if uploaded
          3. Empty string (templates render the default)
        """
        if self.og_image:
            return self.og_image.url
        if self.logo:
            return self.logo.url
        return ""

    @property
    def favicon_url(self):
        """URL to the favicon (or logo fallback, or empty)."""
        if self.favicon:
            return self.favicon.url
        if self.logo:
            return self.logo.url
        return ""

    @property
    def full_address(self):
        """`contact_address` with line breaks collapsed to a single line."""
        return " ".join((self.contact_address or "").split())

    @property
    def primary_contact(self):
        """
        Convenience tuple: (email, phone) — whichever are set.
        Templates can do:
            {% with email=site.primary_contact.0 phone=site.primary_contact.1 %}
        """
        return (self.contact_email or "", self.contact_phone or "")


class ContactEntry(models.Model):
    """Flexible contact info — supports many emails/phones/addresses."""
    class Kind(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        ADDRESS = "address", "Address"
        WHATSAPP = "whatsapp", "WhatsApp"
        SOCIAL = "social", "Social link"
        OTHER = "other", "Other"

    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.EMAIL)
    label = models.CharField(max_length=80, blank=True, help_text="e.g. 'General inquiries', 'Donations team'")
    value = models.TextField(help_text="The contact info itself")
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False, help_text="Show this one first / in compact places")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "Contact entry"
        verbose_name_plural = "Contact entries"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.value[:40]}"
