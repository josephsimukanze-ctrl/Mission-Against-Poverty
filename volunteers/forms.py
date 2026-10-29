
from django import forms
from .models import VolunteerApplication


class VolunteerApplicationForm(forms.ModelForm):
    class Meta:
        model = VolunteerApplication
        fields = ("full_name", "email", "phone", "location", "skills",
                  "availability", "areas_of_interest", "experience", "consent")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+260 …"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "City / area"}),
            "skills": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Teaching, medical, construction, IT, …"}),
            "availability": forms.TextInput(attrs={"class": "form-input", "placeholder": "Weekends, evenings, full-time…"}),
            "areas_of_interest": forms.TextInput(attrs={"class": "form-input", "placeholder": "Education, health, food, …"}),
            "experience": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
        }

    def clean_consent(self):
        consent = self.cleaned_data.get("consent")
        if not consent:
            raise forms.ValidationError("You must agree to be contacted about volunteering.")
        return consent
