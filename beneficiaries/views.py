# beneficiaries/views.py
from django import forms
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views import View

from audit.services import log_action
from .models import AssistanceRequest


class AssistanceRequestForm(forms.ModelForm):
    class Meta:
        model = AssistanceRequest
        fields = (
            "full_name", "email", "phone", "location",
            "household_size", "category", "description",
            "supporting_document", "consent",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+260 …"}),
            "location": forms.TextInput(attrs={"class": "form-input", "placeholder": "Village / town"}),
            "household_size": forms.NumberInput(attrs={"class": "form-input", "min": 1}),
            "category": forms.Select(attrs={"class": "form-input"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 5,
                                                  "placeholder": "Tell us about your situation and what you need."}),
        }

    def clean_consent(self):
        consent = self.cleaned_data.get("consent")
        if not consent:
            raise forms.ValidationError("You must agree to the privacy notice.")
        return consent


class AssistanceRequestView(View):
    template_name = "beneficiaries/request_assistance.html"

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "full_name": request.user.get_full_name() or request.user.get_username(),
                "email": request.user.email,
                "phone": request.user.phone,
            }
        form = AssistanceRequestForm(initial=initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = AssistanceRequestForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        obj = form.save(commit=False)
        if request.user.is_authenticated:
            obj.applicant = request.user
        obj.save()
        log_action(request, "assistance.request.submitted", target=obj)
        messages.success(
            request,
            f"Your request has been received. Reference: {obj.reference}. "
            f"A case officer will review it and contact you."
        )
        return redirect("beneficiaries:apply_done")


class AssistanceRequestDoneView(TemplateView):
    template_name = "beneficiaries/apply_done.html"
