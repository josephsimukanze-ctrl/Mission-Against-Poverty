# partnerships/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView

from accounts.models import STAFF_ROLES, Role
from audit.services import log_action
from .forms import PartnershipApplicationForm
from .models import (
    PartnershipApplication, PartnerOrganization,
    PartnershipAgreement, PartnerProject,
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


# =========================================================
# PUBLIC
# =========================================================
class PartnershipApplyView(View):
    template_name = "partnerships/apply.html"

    def _get_types(self):
        """Resolve the partnership types choices safely."""
        # Try different attribute names your model might use
        for attr in ("PartnershipType", "Type", "PARTNERSHIP_TYPE_CHOICES"):
            choices = getattr(PartnershipApplication, attr, None)
            if choices is not None and hasattr(choices, "choices"):
                return choices.choices
            if isinstance(choices, (list, tuple)):
                return choices
        return []

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "contact_person": request.user.get_full_name() or request.user.get_username(),
                "email": request.user.email or "",
                "phone": getattr(request.user, "phone", "") or "",
            }
        form = PartnershipApplicationForm(initial=initial)
        return render(request, self.template_name, {
            "form": form,
            "types": self._get_types(),
        })

    def post(self, request):
        form = PartnershipApplicationForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "types": self._get_types(),
            })
        app = form.save(commit=False)
        if request.user.is_authenticated:
            app.user = request.user
        app.save()
        log_action(request, "partnership.application.submitted", target=app)
        messages.success(request, "Thank you! We'll review your proposal and be in touch.")
        return redirect("partnerships:apply_done")


class PartnershipApplyDoneView(TemplateView):
    template_name = "partnerships/apply_done.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Optional: recent 3 active projects to preview on the thank-you page
        try:
            from projects.models import Project
            ctx["featured_projects"] = (
                Project.objects.filter(status="active")
                .order_by("-created_at")[:3]
            )
        except Exception:
            ctx["featured_projects"] = []
        return ctx


# =========================================================
# COORDINATOR / MANAGEMENT
# =========================================================
class ApplicationListView(StaffRequiredMixin, ListView):
    template_name = "partnerships/management_applications.html"
    context_object_name = "applications"
    paginate_by = 30

    def get_queryset(self):
        qs = PartnershipApplication.objects.all().order_by("-created_at")

        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(organization_name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(email__icontains=q)
                | Q(location__icontains=q)
            )

        sort = self.request.GET.get("sort", "")
        if sort == "oldest":
            qs = qs.order_by("created_at")
        elif sort == "name":
            qs = qs.order_by("organization_name")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = PartnershipApplication.Status.choices
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "status": self.request.GET.get("status", ""),
            "sort": self.request.GET.get("sort", ""),
        }
        # Per-status counts for tab badges
        ctx["status_counts"] = dict(
            PartnershipApplication.objects
            .values_list("status")
            .annotate(c=Count("pk"))
        )
        return ctx


class ApplicationDetailView(StaffRequiredMixin, View):
    template_name = "partnerships/management_application_detail.html"

    def get(self, request, pk):
        app = get_object_or_404(PartnershipApplication, pk=pk)
        return render(request, self.template_name, {
            "app": app,
            "statuses": PartnershipApplication.Status.choices,
        })

    def post(self, request, pk):
        app = get_object_or_404(PartnershipApplication, pk=pk)
        action = request.POST.get("action", "")

        if action == "set_status":
            new_status = request.POST.get("status", "")
            if new_status in PartnershipApplication.Status.values:
                app.status = new_status
                app.reviewer_notes = request.POST.get("reviewer_notes", app.reviewer_notes)
                app.save(update_fields=["status", "reviewer_notes", "updated_at"])

                log_action(
                    request, "partnership.application.status_change",
                    target=app, metadata={"status": new_status},
                )
                messages.success(request, f"Status set to {app.get_status_display()}.")

                # On approval: create PartnerOrganization if needed
                if new_status == PartnershipApplication.Status.APPROVED:
                    self._ensure_partner_org(app, request)

        return redirect(f"/management/partnerships/applications/{app.pk}/")

    def _ensure_partner_org(self, app, request):
        """
        Create or link a PartnerOrganization on approval.
        Guarded so it doesn't crash if fields are missing.
        """
        # Check if the model even has partner_org
        has_partner_org = any(
            f.name == "partner_org" for f in PartnershipApplication._meta.fields
        )
        if not has_partner_org:
            return  # Model doesn't track this — skip silently

        if getattr(app, "partner_org", None):
            return  # Already linked

        try:
            org, _created = PartnerOrganization.objects.get_or_create(
                name=app.organization_name,
                defaults={
                    "type": getattr(app, "organization_type", ""),
                    "contact_person": app.contact_person,
                    "email": app.email,
                    "phone": app.phone or "",
                    "location": app.location or "",
                    "website": app.website or "",
                    "approved": True,
                    "user": app.user,
                },
            )
            app.partner_org = org
            app.save(update_fields=["partner_org"])

            # Promote user to Partner role
            if app.user and app.user.role != Role.PARTNER:
                app.user.role = Role.PARTNER
                app.user.save(update_fields=["role"])
                messages.info(
                    request,
                    f"{app.user.get_full_name() or app.user.username} is now a Partner.",
                )
        except Exception as exc:
            messages.warning(request, f"Could not create PartnerOrganization: {exc}")


class PartnershipBulkActionView(StaffRequiredMixin, View):
    """Bulk approve/reject from the applications list."""

    def post(self, request):
        ids = request.POST.getlist("application_ids")
        action = request.POST.get("bulk_action", "")

        if not ids:
            messages.warning(request, "No applications selected.")
            return redirect(request.META.get("HTTP_REFERER") or "partnerships:applications")

        apps = PartnershipApplication.objects.filter(pk__in=ids)
        count = 0

        if action == "approve":
            for app in apps:
                app.status = PartnershipApplication.Status.APPROVED
                app.save(update_fields=["status", "updated_at"])
                detail = ApplicationDetailView()
                detail._ensure_partner_org(app, request)
                count += 1
            messages.success(request, f"{count} application{'s' if count != 1 else ''} approved.")
        elif action == "reject":
            for app in apps:
                app.status = PartnershipApplication.Status.REJECTED
                app.save(update_fields=["status", "updated_at"])
                count += 1
            messages.success(request, f"{count} application{'s' if count != 1 else ''} rejected.")
        else:
            messages.warning(request, "Unknown bulk action.")

        return redirect(request.META.get("HTTP_REFERER") or "partnerships:applications")


# =========================================================
# PARTNER PORTAL
# =========================================================
class PartnerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "partnerships/portal_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if (
            request.user.role not in (Role.PARTNER, Role.ADMINISTRATOR)
            and not request.user.is_superuser
        ):
            raise PermissionDenied("Partner portal only.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        orgs = PartnerOrganization.objects.filter(user=user)
        apps = PartnershipApplication.objects.filter(user=user).order_by("-created_at")
        agreements = (
            PartnershipAgreement.objects.filter(partner_org__in=orgs)
            if orgs else PartnershipAgreement.objects.none()
        )
        projects = (
            PartnerProject.objects.filter(partner_org__in=orgs)
            if orgs else PartnerProject.objects.none()
        )

        ctx["portal_root"] = "/portal/partner/"
        ctx["orgs"] = orgs
        ctx["applications"] = apps[:10]
        ctx["agreements"] = agreements
        ctx["partner_projects"] = projects

        # KPIs for the dashboard header
        ctx["approved_count"] = apps.filter(
            Q(status="approved") | Q(status="active")
        ).count()

        return ctx


class PartnerApplicationsListView(LoginRequiredMixin, ListView):
    template_name = "partnerships/portal_applications.html"
    context_object_name = "applications"

    def get_queryset(self):
        return PartnershipApplication.objects.filter(user=self.request.user).order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/partner/"

        apps = ctx["applications"]
        # Status counts for the tab pills
        ctx["approved_count"] = sum(
            1 for a in apps if a.status in ("approved", "active")
        )
        ctx["submitted_count"] = sum(
            1 for a in apps if a.status in ("submitted", "pending")
        )
        ctx["rejected_count"] = sum(
            1 for a in apps if a.status == "rejected"
        )

        return ctx