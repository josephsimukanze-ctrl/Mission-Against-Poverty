
# partnerships/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView

from accounts.models import STAFF_ROLES, Role
from audit.services import log_action
from .forms import PartnershipApplicationForm
from .models import (
    PartnershipApplication, PartnerOrganization,
    PartnershipAgreement, PartnerProject
)


def require_staff(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Login required.")
    if not (request.user.is_superuser or request.user.role in STAFF_ROLES):
        raise PermissionDenied("Staff access only.")


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        require_staff(request)
        return super().dispatch(request, *args, **kwargs)


# ---------- Public ----------
class PartnershipApplyView(View):
    template_name = "partnerships/apply.html"

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "contact_person": request.user.get_full_name() or request.user.get_username(),
                "email": request.user.email,
                "phone": request.user.phone,
            }
        form = PartnershipApplicationForm(initial=initial)
        return render(request, self.template_name, {"form": form, "types": PartnershipApplication.Type.choices})

    def post(self, request):
        form = PartnershipApplicationForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "types": PartnershipApplication.Type.choices})
        app = form.save(commit=False)
        if request.user.is_authenticated:
            app.user = request.user
        app.save()
        log_action(request, "partnership.application.submitted", target=app)
        messages.success(request, "Thank you! We'll review your proposal and be in touch.")
        return redirect("partnerships:apply_done")


class PartnershipApplyDoneView(TemplateView):
    template_name = "partnerships/apply_done.html"


# ---------- Coordinator ----------
class ApplicationListView(StaffRequiredMixin, ListView):
    template_name = "partnerships/management_applications.html"
    context_object_name = "applications"
    paginate_by = 30

    def get_queryset(self):
        qs = PartnershipApplication.objects.all().order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = PartnershipApplication.Status.choices
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


class ApplicationDetailView(StaffRequiredMixin, View):
    template_name = "partnerships/management_application_detail.html"

    def get(self, request, pk):
        app = get_object_or_404(PartnershipApplication, pk=pk)
        return render(request, self.template_name, {
            "app": app, "statuses": PartnershipApplication.Status.choices,
        })

    def post(self, request, pk):
        app = get_object_or_404(PartnershipApplication, pk=pk)
        action = request.POST.get("action", "")

        if action == "set_status":
            new_status = request.POST.get("status", "")
            if new_status in PartnershipApplication.Status.values:
                app.status = new_status
                app.reviewer_notes = request.POST.get("reviewer_notes", app.reviewer_notes)
                app.save()
                log_action(request, "partnership.application.status_change", target=app, metadata={"status": new_status})
                messages.success(request, f"Status set to {app.get_status_display()}.")

                # On approval, create/link a PartnerOrganization
                if new_status == PartnershipApplication.Status.APPROVED and not app.partner_org:
                    org, _ = PartnerOrganization.objects.get_or_create(
                        name=app.organization_name,
                        defaults={
                            "type": app.organization_type,
                            "contact_person": app.contact_person,
                            "email": app.email,
                            "phone": app.phone,
                            "location": app.location,
                            "website": app.website,
                            "approved": True,
                            "user": app.user,
                        },
                    )
                    app.partner_org = org
                    app.save()
                    if app.user and app.user.role != Role.PARTNER:
                        app.user.role = Role.PARTNER
                        app.user.save(update_fields=["role"])

        return redirect(f"/management/partnerships/applications/{app.pk}/")


# ---------- Partner portal ----------
class PartnerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "partnerships/portal_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in (Role.PARTNER, Role.ADMINISTRATOR) and not request.user.is_superuser:
            raise PermissionDenied("Partner portal only.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        orgs = PartnerOrganization.objects.filter(user=user)
        apps = PartnershipApplication.objects.filter(user=user).order_by("-created_at")
        agreements = PartnershipAgreement.objects.filter(partner_org__in=orgs) if orgs else PartnershipAgreement.objects.none()
        projects = PartnerProject.objects.filter(partner_org__in=orgs) if orgs else PartnerProject.objects.none()

        ctx["portal_root"] = "/portal/partner/"
        ctx["orgs"] = orgs
        ctx["applications"] = apps[:10]
        ctx["agreements"] = agreements
        ctx["partner_projects"] = projects
        return ctx


class PartnerApplicationsListView(LoginRequiredMixin, ListView):
    template_name = "partnerships/portal_applications.html"
    context_object_name = "applications"

    def get_queryset(self):
        return PartnershipApplication.objects.filter(user=self.request.user).order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/partner/"
        return ctx
