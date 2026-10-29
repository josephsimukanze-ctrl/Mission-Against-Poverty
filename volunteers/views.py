# volunteers/views.py
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from accounts.models import STAFF_ROLES, Role
from audit.services import log_action
from .forms import VolunteerApplicationForm
from .models import (
    Certificate,
    VolunteerApplication,
    VolunteerAssignment,
    VolunteerAttendance,
    VolunteerHours,
    VolunteerProfile,
)


# ---------- Public apply form ----------
class VolunteerApplyView(View):
    template_name = "volunteers/apply.html"

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "full_name": request.user.get_full_name() or request.user.get_username(),
                "email": request.user.email,
                "phone": getattr(request.user, "phone", "") or "",
            }
        form = VolunteerApplicationForm(initial=initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = VolunteerApplicationForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        app = form.save(commit=False)
        if request.user.is_authenticated:
            app.user = request.user
        app.save()

        log_action(request, "volunteer.application.submitted", target=app)
        messages.success(request, "Thank you! We'll review your application and be in touch.")
        return redirect("volunteers:apply_done")


class VolunteerApplyDoneView(TemplateView):
    template_name = "volunteers/apply_done.html"


# ---------- Coordinator / management ----------
def require_staff(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Login required.")
    if not (request.user.is_superuser or request.user.role in STAFF_ROLES):
        raise PermissionDenied("Staff access only.")


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        require_staff(request)
        return super().dispatch(request, *args, **kwargs)


class ApplicationListView(StaffRequiredMixin, ListView):
    template_name = "volunteers/management_applications.html"
    context_object_name = "applications"
    paginate_by = 30

    def get_queryset(self):
        qs = VolunteerApplication.objects.all().order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = VolunteerApplication.Status.choices
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


class ApplicationDetailView(StaffRequiredMixin, View):
    template_name = "volunteers/management_application_detail.html"

    def get(self, request, pk):
        app = get_object_or_404(VolunteerApplication, pk=pk)
        return render(request, self.template_name, {
            "app": app,
            "statuses": VolunteerApplication.Status.choices,
        })

    def post(self, request, pk):
        app = get_object_or_404(VolunteerApplication, pk=pk)
        action = request.POST.get("action", "")

        if action == "set_status":
            new_status = request.POST.get("status", "")
            if new_status in VolunteerApplication.Status.values:
                app.status = new_status
                app.reviewer_notes = request.POST.get("reviewer_notes", app.reviewer_notes)
                app.save(update_fields=["status", "reviewer_notes"])

                log_action(
                    request, "volunteer.application.status_change",
                    target=app, metadata={"status": new_status},
                )
                messages.success(request, f"Status set to {app.get_status_display()}.")

                # Auto-create/update profile on approval
                if new_status == VolunteerApplication.Status.APPROVED and app.user:
                    profile, _ = VolunteerProfile.objects.get_or_create(user=app.user)
                    profile.location = app.location
                    profile.skills = app.skills
                    profile.availability = app.availability
                    profile.experience = app.experience
                    profile.approved = True
                    profile.save()

                    if app.user.role != Role.VOLUNTEER:
                        app.user.role = Role.VOLUNTEER
                        app.user.save(update_fields=["role"])

        elif action == "assign":
            if not app.user:
                messages.error(request, "Application is not linked to a user — cannot assign.")
            else:
                title = request.POST.get("title", "").strip()
                if title:
                    VolunteerAssignment.objects.create(
                        volunteer=app.user,
                        title=title,
                        description=request.POST.get("description", ""),
                        status=VolunteerAssignment.Status.PROPOSED,
                    )
                    messages.success(request, "Assignment created.")

        return redirect(f"/management/volunteers/applications/{app.pk}/")


# ---------- Volunteer portal ----------
class VolunteerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "volunteers/portal_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        profile, _ = VolunteerProfile.objects.get_or_create(user=user)

        assignments = VolunteerAssignment.objects.filter(volunteer=user).order_by("-created_at")
        hours_qs = VolunteerHours.objects.filter(volunteer=user)

        ctx["portal_root"] = "/portal/volunteer/"
        ctx["profile"] = profile
        ctx["assignments"] = assignments[:10]
        ctx["hours"] = hours_qs[:10]
        ctx["total_hours"] = hours_qs.aggregate(t=Sum("hours"))["t"] or Decimal("0")
        ctx["completed_assignments"] = assignments.filter(
            status=VolunteerAssignment.Status.COMPLETED
        ).count()
        ctx["pending_assignments"] = assignments.filter(
            status=VolunteerAssignment.Status.PROPOSED
        ).count()
        ctx["certificates_count"] = Certificate.objects.filter(volunteer=user).count()
        return ctx


class VolunteerAssignmentsView(LoginRequiredMixin, ListView):
    template_name = "volunteers/portal_assignments.html"
    context_object_name = "assignments"
    paginate_by = 20

    def get_queryset(self):
        return (
            VolunteerAssignment.objects
            .filter(volunteer=self.request.user)
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/volunteer/"
        return ctx


@login_required
def respond_to_assignment(request, pk, action):
    a = get_object_or_404(VolunteerAssignment, pk=pk, volunteer=request.user)
    if action == "accept" and a.status == VolunteerAssignment.Status.PROPOSED:
        a.status = VolunteerAssignment.Status.ACCEPTED
    elif action == "decline" and a.status == VolunteerAssignment.Status.PROPOSED:
        a.status = VolunteerAssignment.Status.DECLINED
    elif action == "complete" and a.status == VolunteerAssignment.Status.ACCEPTED:
        a.status = VolunteerAssignment.Status.COMPLETED
    a.save()
    messages.success(request, f"Assignment {a.get_status_display().lower()}.")
    return redirect("volunteers:portal_assignments")


class VolunteerHoursView(LoginRequiredMixin, TemplateView):
    template_name = "volunteers/portal_hours.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/volunteer/"
        ctx["hours"] = (
            VolunteerHours.objects
            .filter(volunteer=self.request.user)
            .order_by("-date")
        )
        return ctx

    def post(self, request):
        date = request.POST.get("date")
        hours_val = request.POST.get("hours")
        if date and hours_val:
            VolunteerHours.objects.create(
                volunteer=request.user,
                date=date,
                hours=hours_val,
                notes=request.POST.get("notes", ""),
            )
            VolunteerProfile.objects.get_or_create(user=request.user).recalc_hours()
            messages.success(request, "Hours logged.")
        return redirect("volunteers:portal_hours")


class VolunteerCertificatesView(LoginRequiredMixin, ListView):
    template_name = "volunteers/portal_certificates.html"
    context_object_name = "certificates"

    def get_queryset(self):
        return Certificate.objects.filter(volunteer=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/volunteer/"
        return ctx


# ---------- Volunteer directory ----------
class VolunteerListView(StaffRequiredMixin, ListView):
    template_name = "volunteers/management_volunteers.html"
    context_object_name = "volunteers"
    paginate_by = 30

    def get_queryset(self):
        from accounts.models import User

        # Base queryset — approved profiles OR role=volunteer
        qs = (
            User.objects
            .filter(
                Q(volunteer_profile__approved=True) | Q(role="volunteer")
            )
            .select_related("volunteer_profile")
            .distinct()
            .order_by("-date_joined")
        )

        # Annotate stats in one query
        # NOTE: VolunteerHours.hours is DecimalField — must use Decimal + DecimalField output
        qs = qs.annotate(
            _assignments_count=Count(
                "volunteer_assignments",
                distinct=True,
            ),
            _completed_count=Count(
                "volunteer_assignments",
                filter=Q(volunteer_assignments__status=VolunteerAssignment.Status.COMPLETED),
                distinct=True,
            ),
            _hours_total=Coalesce(
                Sum("volunteer_hours__hours"),
                Value(Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2)),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
            _certificates_count=Count(
                "certificates",
                distinct=True,
            ),
        )

        # Search filter
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(username__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")

        # Expose annotated stats as clean attribute names
        for v in ctx["volunteers"]:
            v.assignments_count = getattr(v, "_assignments_count", 0) or 0
            v.completed_count = getattr(v, "_completed_count", 0) or 0
            v.hours_total = getattr(v, "_hours_total", Decimal("0")) or Decimal("0")
            v.certificates_count = getattr(v, "_certificates_count", 0) or 0
            v.profile_obj = getattr(v, "volunteer_profile", None)

        return ctx