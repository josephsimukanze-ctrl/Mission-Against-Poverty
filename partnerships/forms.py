
from django import forms
from .models import PartnershipApplication


class PartnershipApplicationForm(forms.ModelForm):
    class Meta:
        model = PartnershipApplication
        fields = (
            "organization_name", "organization_type", "contact_person",
            "email", "phone", "location", "website",
            "partnership_type", "proposed_contribution",
            "proposed_project", "supporting_document", "additional_comments",
        )
        widgets = {
            "organization_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Organization name"}),
            "organization_type": forms.TextInput(attrs={"class": "form-input", "placeholder": "NGO, Business, Church, Government…"}),
            "contact_person": forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "official@org.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+260 …"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "City / area"}),
            "website": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://…"}),
            "partnership_type": forms.Select(attrs={"class": "form-input"}),
            "proposed_contribution": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "What you'd like to contribute"}),
            "proposed_project": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "A project or area you'd like to work on"}),
            "additional_comments": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }
