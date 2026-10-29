# newsletter/forms.py
from django import forms

from .models import NewsletterCampaign, NewsletterSubscriber


# ============================================================
# NewsletterSubscriber form — manual add / edit
# ============================================================
class SubscriberForm(forms.ModelForm):
    """
    Create or edit a subscriber manually.

    Email is normalized to lowercase and checked for uniqueness
    (excluding the instance being edited). Status defaults to "active"
    so manually-added subscribers receive campaigns immediately.
    """

    class Meta:
        model = NewsletterSubscriber
        fields = ("email", "name", "status", "source")
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "someone@example.com",
                "autocomplete": "email",
            }),
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Full name (optional)",
            }),
            "status": forms.Select(attrs={"class": "form-input"}),
            "source": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g. event, walk-in, mailing list",
            }),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")

        qs = NewsletterSubscriber.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This email is already subscribed.")

        return email


# ============================================================
# NewsletterCampaign form
# ============================================================
class CampaignForm(forms.ModelForm):
    class Meta:
        model = NewsletterCampaign
        fields = (
            "subject", "preview_text", "body",
            "status", "scheduled_for",
        )
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-input"}),
            "preview_text": forms.TextInput(attrs={"class": "form-input"}),
            "body": forms.Textarea(attrs={"class": "form-input", "rows": 20}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "scheduled_for": forms.DateTimeInput(
                attrs={"class": "form-input", "type": "datetime-local"}
            ),
        }


