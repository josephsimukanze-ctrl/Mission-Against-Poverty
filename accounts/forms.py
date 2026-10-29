from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User, UserProfile, Role


class RegisterForm(UserCreationForm):
    PUBLIC_ROLES = [
        (Role.DONOR, "Donor — I want to support the mission"),
        (Role.VOLUNTEER, "Volunteer — I want to give my time"),
        (Role.PARTNER, "Partner — I represent an organization"),
        (Role.BENEFICIARY, "Beneficiary — I am requesting assistance"),
    ]

    role = forms.ChoiceField(
        choices=PUBLIC_ROLES,
        widget=forms.RadioSelect(attrs={"class": "role-radio"}),
        label="I am registering as",
    )
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False, max_length=32)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "phone", "role", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-input class to all text-like inputs
        for name, field in self.fields.items():
            if name == "role":
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-input").strip()

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower().strip()
        user.phone = self.cleaned_data.get("phone", "")
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Username or email", "autofocus": True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"})
    )

    def clean_username(self):
        value = self.cleaned_data["username"].strip()
        if "@" in value:
            try:
                return User.objects.get(email__iexact=value).username
            except User.DoesNotExist:
                pass
        return value


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "form-input")


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("photo", "address", "city", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            if name != "photo":
                f.widget.attrs.setdefault("class", "form-input")
