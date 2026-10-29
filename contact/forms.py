# contacts/forms.py
from django import forms
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """
    Public-facing contact form — visitors submit through this.
    No `status` or `reply_notes` — those are staff-only fields.
    """

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "Optional"}),
            "subject": forms.TextInput(attrs={"class": "form-input", "placeholder": "What's this about?"}),
            "message": forms.Textarea(attrs={"class": "form-input", "rows": 6, "placeholder": "How can we help?"}),
        }


class ContactMessageForm(forms.ModelForm):
    """
    Staff-facing form — used to log a message manually
    (phone call, email, walk-in) and set its initial status.
    """

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message", "status")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "subject": forms.TextInput(attrs={"class": "form-input"}),
            "message": forms.Textarea(attrs={"class": "form-input", "rows": 6}),
            "status": forms.Select(attrs={"class": "form-input"}),
        }


class ContactMessageEditForm(forms.ModelForm):
    """
    Staff-facing edit form — only for triaging an existing message:
    change status, add reply notes.
    """

    class Meta:
        model = ContactMessage
        fields = ("status", "reply_notes")
        widgets = {
            "status": forms.Select(attrs={"class": "form-input"}),
            "reply_notes": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 4,
                    "placeholder": "Internal notes about how this was handled (not visible to the sender)",
                }
            ),
        }