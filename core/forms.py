# core/forms.py
from django import forms
from .models import SiteSetting


class SiteSettingForm(forms.ModelForm):
    """
    Full settings form. All fields on one form — the template groups
    them visually into tabs. The view doesn't care which tab the user
    is on; a single POST saves everything.
    """

    class Meta:
        model = SiteSetting
        fields = "__all__"

        widgets = {
            # Identity
            "site_name": forms.TextInput(attrs={"class": "form-input"}),
            "tagline": forms.TextInput(attrs={"class": "form-input"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "logo_light": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "favicon": forms.ClearableFileInput(attrs={"class": "form-input"}),

            # Contact
            "contact_email": forms.EmailInput(attrs={"class": "form-input"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-input"}),
            "contact_address": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "office_hours": forms.TextInput(attrs={"class": "form-input"}),
            "google_maps_embed": forms.Textarea(attrs={"class": "form-input", "rows": 3}),

            # Banking
            "bank_name": forms.TextInput(attrs={"class": "form-input"}),
            "bank_branch": forms.TextInput(attrs={"class": "form-input"}),
            "bank_account_name": forms.TextInput(attrs={"class": "form-input"}),
            "bank_account_number": forms.TextInput(attrs={"class": "form-input"}),
            "bank_sort_code": forms.TextInput(attrs={"class": "form-input"}),
            "bank_swift": forms.TextInput(attrs={"class": "form-input"}),
            "bank_iban": forms.TextInput(attrs={"class": "form-input"}),
            "mobile_money_name": forms.TextInput(attrs={"class": "form-input"}),
            "mobile_money_number": forms.TextInput(attrs={"class": "form-input"}),
            "bank_transfer_instructions": forms.Textarea(
                attrs={"class": "form-input", "rows": 4}
            ),

            # Donations
            "currency": forms.TextInput(attrs={"class": "form-input"}),
            "currency_symbol": forms.TextInput(attrs={"class": "form-input"}),
            "min_donation": forms.NumberInput(
                attrs={"class": "form-input", "step": "0.01"}
            ),
            "preset_amounts": forms.TextInput(attrs={"class": "form-input"}),

            # Social
            "facebook_url": forms.URLInput(attrs={"class": "form-input"}),
            "twitter_url": forms.URLInput(attrs={"class": "form-input"}),
            "instagram_url": forms.URLInput(attrs={"class": "form-input"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-input"}),
            "youtube_url": forms.URLInput(attrs={"class": "form-input"}),

            # Footer / SEO
            "footer_description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "copyright_text": forms.TextInput(attrs={"class": "form-input"}),
            "default_meta_description": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "google_analytics_id": forms.TextInput(attrs={"class": "form-input"}),
            "about_hero_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "mission_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "vision_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "reach_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
        }

    def clean_preset_amounts(self):
        """Validate the comma-separated preset amounts."""
        raw = self.cleaned_data.get("preset_amounts", "").strip()
        if not raw:
            return "50,100,250,500"

        try:
            values = [int(v.strip()) for v in raw.split(",") if v.strip()]
        except ValueError:
            raise forms.ValidationError(
                "Enter whole numbers separated by commas, e.g. 50,100,250."
            )

        if not values:
            raise forms.ValidationError("Provide at least one preset amount.")
        if any(v <= 0 for v in values):
            raise forms.ValidationError("Preset amounts must be greater than zero.")

        # Normalise back to CSV
        return ",".join(str(v) for v in values)

    def clean_min_donation(self):
        value = self.cleaned_data.get("min_donation")
        if value is not None and value <= 0:
            raise forms.ValidationError("Minimum donation must be greater than zero.")
        return value


# ============================================================
# Contact entry formset — allows adding/editing/deleting
# multiple contact entries from the Contact tab
# ============================================================
from django.forms import inlineformset_factory, modelformset_factory
from core.models import ContactEntry


class ContactEntryForm(forms.ModelForm):
    class Meta:
        model = ContactEntry
        fields = ("kind", "label", "value", "order", "is_primary", "is_active")
        widgets = {
            "kind": forms.Select(attrs={"class": "form-input"}),
            "label": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. General inquiries"}),
            "value": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "The contact info"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
        }


ContactEntryFormSet = modelformset_factory(
    ContactEntry,
    form=ContactEntryForm,
    extra=1,
    can_delete=True,
)
