# settings_app/forms.py

from django import forms

from .models import SiteConfig, DEFAULT_PRESET_AMOUNTS


CURRENCY_SYMBOLS = {
    "ZMW": "K",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "KES": "KSh",
    "ZAR": "R",
    "NGN": "₦",
    "GHS": "₵",
    "TZS": "TSh",
    "UGX": "USh",
}


class SiteConfigForm(forms.ModelForm):
    # NOTE: preset_amounts_csv is a MODEL field (confirmed in output) —
    # do NOT redeclare it here. Configure via Meta.widgets instead.

    class Meta:
        model = SiteConfig
        # Confirmed against the model's actual field list.
        # If any of the "verify" rows below raise FieldError, adjust the
        # name to match the model (e.g. `physical_address` vs `address`).
        fields = [
            # Identity
            "site_name", "tagline",
            "logo", "logo_light", "favicon", "og_image",

            # Contact  — verify: 'address' was inferred from the
            # 'contact_address is unknown' error. Check the model.
            "contact_email", "contact_phone", "address",
            "office_hours", "google_maps_embed",

            # Banking  — verify these names exist on the model
            "bank_name", "bank_branch", "bank_account_name",
            "bank_account_number", "bank_sort_code",
            "bank_swift", "bank_iban",
            "mobile_money_name", "mobile_money_number",
            "bank_transfer_instructions",

            # Donations
            "currency", "currency_symbol", "min_donation",
            "preset_amounts_csv",

            # Social
            "facebook_url", "twitter_url", "instagram_url",
            "linkedin_url", "youtube_url",

            # SEO / Footer
            "footer_description", "copyright_text",
            "default_meta_description", "google_analytics_id",

            # Maintenance
            "maintenance_mode",
        ]
        widgets = {
            "preset_amounts_csv": forms.TextInput(attrs={
                "placeholder": DEFAULT_PRESET_AMOUNTS,
                "autocomplete": "off",
                "spellcheck": "false",
                "inputmode": "numeric",
            }),
            "address":                   forms.Textarea(attrs={"rows": 3}),
            "bank_transfer_instructions": forms.Textarea(attrs={"rows": 3}),
            "footer_description":        forms.Textarea(attrs={"rows": 3}),
            "default_meta_description":  forms.Textarea(attrs={"rows": 3}),
            "google_maps_embed":         forms.Textarea(attrs={"rows": 4}),
        
            "about_hero_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "mission_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "vision_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "reach_image": forms.ClearableFileInput(attrs={"class": "form-input", "accept": "image/*"}),
        }
        labels = {
            "address":          "Address",
            "preset_amounts_csv": "Preset amounts",
            "default_meta_description": "Default meta description",
        }
        help_texts = {
            "preset_amounts_csv":
                "Comma-separated whole numbers. These become clickable chips on the donate page.",
            "address": "Line breaks are preserved.",
            "google_maps_embed":
                "Paste the iframe HTML from Google Maps → Share → Embed a map.",
        }

    # ------------------------------------------------------------------ init
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Never block save on these being empty
        for name in ("preset_amounts_csv", "currency", "currency_symbol", "min_donation"):
            if name in self.fields:
                self.fields[name].required = False

        # Fill an empty preset field with the default so the operator
        # always sees a usable set of chips on first load.
        if (
            "preset_amounts_csv" in self.fields
            and not self.initial.get("preset_amounts_csv")
        ):
            self.initial["preset_amounts_csv"] = DEFAULT_PRESET_AMOUNTS

        self._apply_widget_classes()

    def _apply_widget_classes(self):
        """Attach consistent Tailwind classes to every widget."""
        file_classes = (
            "block w-full text-[13px] text-gray-700 "
            "file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 "
            "file:text-[12px] file:font-semibold "
            "file:bg-mapbg file:text-mapnavy hover:file:bg-mapborder"
        )
        text_classes = "form-input w-full text-[13px]"

        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if existing.startswith("form-input") or "font-mono" in existing:
                continue
            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = file_classes
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (
                    "h-4 w-4 rounded border-gray-300 text-mapgreen "
                    "focus:ring-mapgreen/40"
                )
            else:
                widget.attrs["class"] = text_classes

    # -------------------------------------------------------------- cleaning
    def clean_preset_amounts_csv(self):
        raw = (self.cleaned_data.get("preset_amounts_csv") or "").strip()
        if not raw:
            return ""
        seen, out = set(), []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if not chunk.isdigit():
                raise forms.ValidationError(f"'{chunk}' is not a whole number.")
            n = int(chunk)
            if n <= 0:
                raise forms.ValidationError("Preset amounts must be greater than zero.")
            if n not in seen:
                seen.add(n)
                out.append(n)
        return ",".join(str(n) for n in out)

    def clean_currency(self):
        return (self.cleaned_data.get("currency") or "").strip().upper()

    def clean_currency_symbol(self):
        symbol = (self.cleaned_data.get("currency_symbol") or "").strip()
        currency = (self.cleaned_data.get("currency") or "").strip().upper()

        if symbol and currency and symbol.upper() == currency:
            return CURRENCY_SYMBOLS.get(currency, currency)
        if not symbol and currency in CURRENCY_SYMBOLS:
            return CURRENCY_SYMBOLS[currency]
        return symbol

    def clean_min_donation(self):
        value = self.cleaned_data.get("min_donation")
        if value is not None and value < 0:
            raise forms.ValidationError("Minimum donation cannot be negative.")
        return value

    def clean(self):
        cleaned = super().clean()
        presets_raw = cleaned.get("preset_amounts_csv") or ""
        min_amt = cleaned.get("min_donation")

        if presets_raw and min_amt not in (None, ""):
            try:
                smallest = min(int(x) for x in presets_raw.split(",") if x)
            except ValueError:
                smallest = None
            if smallest is not None and min_amt > smallest:
                self.add_error(
                    "min_donation",
                    f"Minimum donation ({min_amt}) is higher than your smallest "
                    f"preset ({smallest}). Donors may be confused.",
                )
        return cleaned

    # -------------------------------------------------------------- helper
    @property
    def preset_amounts_list(self):
        """Parsed ints for template rendering."""
        if hasattr(self, "_preset_list"):
            return self._preset_list

        if self.is_bound:
            raw = (
                (self.cleaned_data.get("preset_amounts_csv")
                 if self.is_valid() else None)
                or self.data.get("preset_amounts_csv")
                or ""
            )
        else:
            raw = (self.initial.get("preset_amounts_csv")
                   or getattr(self.instance, "preset_amounts_csv", "")
                   or DEFAULT_PRESET_AMOUNTS)

        self._preset_list = [
            int(c) for c in str(raw).split(",")
            if c.strip().isdigit() and int(c) > 0
        ]
        return self._preset_list