# core/views.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect
from django.views import View

from audit.services import log_action
from accounts.models import STAFF_ROLES


class StaffRequiredMixin(LoginRequiredMixin):
    """Requires login AND staff role (or superuser)."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_superuser or request.user.role in STAFF_ROLES):
            raise PermissionDenied("You do not have access to the management area.")
        return super().dispatch(request, *args, **kwargs)


class SiteSettingsView(StaffRequiredMixin, View):
    template_name = "management/settings.html"

    TEXT_FIELDS = [
        "site_name", "tagline",
        "contact_email", "contact_phone", "address", "office_hours", "google_maps_embed",
        "bank_name", "bank_branch", "bank_account_name", "bank_account_number",
        "bank_sort_code", "bank_swift", "bank_iban",
        "mobile_money_name", "mobile_money_number",
        "bank_transfer_instructions",
        "currency", "currency_symbol", "min_donation",
        "preset_amounts_csv",
        "facebook_url", "twitter_url", "instagram_url", "linkedin_url", "youtube_url",
        "footer_description", "copyright_text",
        "default_meta_description", "google_analytics_id",
        "about_hero_heading", "about_hero_subheading",
        "mission_heading", "mission_icon", "mission_text",
        "vision_heading", "vision_icon", "vision_text",
        "reach_heading", "reach_icon", "reach_text",
    ]

    FILE_FIELDS = [
        "logo", "logo_light", "favicon", "og_image",
        "about_hero_image", "mission_image", "vision_image", "reach_image",
    ]

    def _load_site(self):
        """Return the SiteConfig singleton — the model every page reads from."""
        from settings_app.models import SiteConfig
        return SiteConfig.load()

    def get(self, request):
        from settings_app.forms import SiteConfigForm
        from core.models import ContactEntry
        from core.forms import ContactEntryFormSet

        site = self._load_site()
        form = SiteConfigForm(instance=site)
        contact_formset = ContactEntryFormSet(queryset=ContactEntry.objects.all())

        return render(request, self.template_name, {
            "site": site,
            "config": site,
            "form": form,
            "contact_formset": contact_formset,
            "title": "Site Settings",
            "active_tab": request.GET.get("tab", "identity"),
        })

    def post(self, request):
        from core.models import ContactEntry
        from core.forms import ContactEntryFormSet

        site = self._load_site()
        changed = []

        with transaction.atomic():
            # ── Text fields ─────────────────────────────────────
            for field in self.TEXT_FIELDS:
                if field in request.POST:
                    old = getattr(site, field, None)
                    new = request.POST.get(field, "")
                    if str(old) != str(new):
                        setattr(site, field, new)
                        changed.append(field)

            # ── File uploads (logo, logo_light, favicon, og_image, about images) ──
            for field in self.FILE_FIELDS:
                if field in request.FILES:
                    try:
                        setattr(site, field, request.FILES[field])
                        changed.append(field)
                    except Exception as e:
                        messages.error(request, f"Could not save {field}: {e}")

            # ── Maintenance mode checkbox ───────────────────────
            new_maint = "maintenance_mode" in request.POST
            if hasattr(site, "maintenance_mode") and site.maintenance_mode != new_maint:
                site.maintenance_mode = new_maint
                changed.append("maintenance_mode")

            site.save()

            # ── Contact entries formset ─────────────────────────
            contact_formset = ContactEntryFormSet(
                request.POST, queryset=ContactEntry.objects.all()
            )
            if contact_formset.is_valid():
                contact_formset.save()
            else:
                messages.warning(request, "Some contact entries had errors.")

            log_action(
                request,
                "sitesettings.update",
                target=site,
                metadata={"changed_fields": changed},
            )

        if changed:
            messages.success(request, f"Settings saved. {len(changed)} field(s) updated.")
        else:
            messages.info(request, "No changes to save.")

        active_tab = request.POST.get("active_tab", "identity")
        return redirect(f"/management/settings/?tab={active_tab}")