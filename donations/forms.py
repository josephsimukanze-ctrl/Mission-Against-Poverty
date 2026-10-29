# donations/forms.py
from decimal import Decimal
from django import forms
from .models import Donation, Campaign


class DonationForm(forms.Form):
    AMOUNT_PRESETS = [Decimal("50"), Decimal("100"), Decimal("250"), Decimal("500")]

    kind = forms.ChoiceField(
        choices=Donation.Kind.choices, initial=Donation.Kind.CASH,
        widget=forms.RadioSelect(attrs={"class": "inline-radio"}),
        label="Donation type",
    )
    amount = forms.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("1"),
        widget=forms.NumberInput(attrs={"class": "form-input", "placeholder": "Enter amount", "step": "0.01"}),
        label="Amount (ZMW)",
    )
    frequency = forms.ChoiceField(
        choices=Donation.Frequency.choices, initial=Donation.Frequency.ONE_TIME,
        widget=forms.RadioSelect(attrs={"class": "inline-radio"}),
        label="Frequency",
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.filter(status=Campaign.Status.ACTIVE),
        required=False, empty_label="General fund",
        widget=forms.Select(attrs={"class": "form-input"}),
        label="Support a campaign (optional)",
    )
    project = forms.ModelChoiceField(
        queryset=None, required=False, empty_label="No specific project",
        widget=forms.Select(attrs={"class": "form-input"}),
        label="Support a project (optional)",
    )

    donor_name = forms.CharField(max_length=150, required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Full name"}))
    donor_email = forms.EmailField(required=False,
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}))
    donor_phone = forms.CharField(max_length=32, required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+260 …"}))
    is_anonymous = forms.BooleanField(required=False, label="Show my donation as anonymous")
    message = forms.CharField(required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Optional message of support"}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        from projects.models import Project
        self.fields["project"].queryset = Project.objects.filter(published=True)
        if user and user.is_authenticated:
            self.fields["donor_name"].initial = user.get_full_name()
            self.fields["donor_email"].initial = user.email
            self.fields["donor_phone"].initial = user.phone

    def clean(self):
        data = super().clean()
        if data.get("kind") == Donation.Kind.MATERIAL:
            if data.get("amount", 0) <= 0:
                data["amount"] = Decimal("0")
        if data.get("donor_email") and not data.get("donor_name"):
            self.add_error("donor_name", "Please provide your name.")
        return data
