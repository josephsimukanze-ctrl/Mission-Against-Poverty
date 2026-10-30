# volunteers/views.py
from datetime import date, timedelta
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
from django.views.decorators.http import require_http_methods
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


# =========================================================
# PUBLIC — Volunteer apply form
# =========================================================
class VolunteerApplyView(View):
    template_name = "volunteers/apply.html"

    def _opportunities(self):
        """Upcoming published events — shown in the sidebar of the apply page."""
        try:
            from events.models import Event
            return (
                Event.objects
                .filter(published=True, starts_at__gte=timezone.now())
                .order_by("starts_at")[:3]
            )
        except Exception:
            return []

    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "full_name": request.user.get_full_name() or request.user.get_username(),
                "email": request.user.email,
                "phone": getattr(request.user, "phone", "") or "",
            }
        form = VolunteerApplicationForm(initial=initial)
        return render(request, self.template_name, {
            "form": form,
            "opportunities": self._opportunities(),
        })

    def post(self, request):
        form = VolunteerApplicationForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "opportunities": self._opportunities(),
            })

        app = form.save(commit=False)
        if request.user.is_authenticated:
            app.user = request.user
        app.save()

        log_action(request, "volunteer.application.submitted", target=app)
        messages.success(request, "Thank you! We'll review your application and be in touch.")
        return redirect("volunteers:apply_done")


class VolunteerApplyDoneView(TemplateView):
    template_name = "volunteers/apply_done.html"


# =========================================================
# COORDINATOR / MANAGEMENT
# =========================================================
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
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(location__icontains=q)
                | Q(skills__icontains=q)
            )
        sort = self.request.GET.get("sort", "")
        if sort == "oldest":
            qs = qs.order_by("created_at")
        elif sort == "name":
            qs = qs.order_by("full_name")
        # default already -created_at
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = VolunteerApplication.Status.choices
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "status": self.request.GET.get("status", ""),
            "sort": self.request.GET.get("sort", ""),
        }
        # Counts per status for tab pills
        ctx["status_counts"] = {
            s[0]: VolunteerApplication.objects.filter(status=s[0]).count()
            for s in VolunteerApplication.Status.choices
        }
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
                app.save(update_fields=["status", "reviewer_notes", "updated_at"])

                log_action(
                    request, "volunteer.application.status_change",
                    target=app, metadata={"status": new_status},
                )
                messages.success(request, f"Status set to {app.get_status_display()}.")

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


class BulkApplicationActionView(StaffRequiredMixin, View):
    """Bulk approve/reject from the applications list page."""

    def post(self, request):
        ids = request.POST.getlist("application_ids")
        action = request.POST.get("bulk_action") or request.POST.get("quick_action", "")

        # Quick action format: "approve:<pk>"
        if ":" in action:
            action, pk = action.split(":", 1)
            ids = [pk]

        if not ids:
            messages.warning(request, "No applications selected.")
            return redirect(request.META.get("HTTP_REFERER") or "volunteers:applications")

        apps = VolunteerApplication.objects.filter(pk__in=ids)
        count = 0

        if action == "approve":
            for app in apps:
                app.status = VolunteerApplication.Status.APPROVED
                app.save(update_fields=["status", "updated_at"])
                if app.user:
                    profile, _ = VolunteerProfile.objects.get_or_create(user=app.user)
                    profile.approved = True
                    profile.save()
                count += 1
            messages.success(request, f"{count} application{'s' if count != 1 else ''} approved.")
        elif action == "reject":
            for app in apps:
                app.status = VolunteerApplication.Status.REJECTED
                app.save(update_fields=["status", "updated_at"])
                count += 1
            messages.success(request, f"{count} application{'s' if count != 1 else ''} rejected.")
        else:
            messages.warning(request, "Unknown bulk action.")

        return redirect(request.META.get("HTTP_REFERER") or "volunteers:applications")


# =========================================================
# VOLUNTEER PORTAL
# =========================================================
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

        # Optional: milestone progress
        milestones = [10, 25, 50, 100, 250, 500, 1000]
        total = float(ctx["total_hours"])
        next_ms = next((m for m in milestones if m > total), None)
        if next_ms:
            prev_ms = max([m for m in milestones if m <= total], default=0)
            span = next_ms - prev_ms
            ctx["next_milestone"] = next_ms
            ctx["milestone_progress"] = round(((total - prev_ms) / span) * 100) if span else 0
            ctx["milestone_remaining"] = round(next_ms - total, 1)

        # Optional: upcoming events
        try:
            from events.models import Event
            ctx["upcoming_events"] = Event.objects.filter(
                published=True, starts_at__gte=timezone.now()
            ).order_by("starts_at")[:2]
        except Exception:
            ctx["upcoming_events"] = []

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
        # Status counts for tab pills
        qs = VolunteerAssignment.objects.filter(volunteer=self.request.user)
        ctx["proposed_count"] = qs.filter(status=VolunteerAssignment.Status.PROPOSED).count()
        ctx["accepted_count"] = qs.filter(status=VolunteerAssignment.Status.ACCEPTED).count()
        ctx["completed_count"] = qs.filter(status=VolunteerAssignment.Status.COMPLETED).count()
        ctx["declined_count"] = qs.filter(status=VolunteerAssignment.Status.DECLINED).count()
        return ctx


@login_required
@require_http_methods(["GET", "POST"])
def respond_to_assignment(request, pk, action):
    """Accept / decline / complete an assignment."""
    a = get_object_or_404(VolunteerAssignment, pk=pk, volunteer=request.user)

    if action == "accept" and a.status == VolunteerAssignment.Status.PROPOSED:
        a.status = VolunteerAssignment.Status.ACCEPTED
    elif action == "decline" and a.status == VolunteerAssignment.Status.PROPOSED:
        a.status = VolunteerAssignment.Status.DECLINED
    elif action == "complete" and a.status == VolunteerAssignment.Status.ACCEPTED:
        a.status = VolunteerAssignment.Status.COMPLETED
    else:
        messages.warning(request, "That action isn't allowed right now.")
        return redirect("volunteers:portal_assignments")

    a.save()
    messages.success(request, f"Assignment {a.get_status_display().lower()}.")
    return redirect("volunteers:portal_assignments")


@login_required
@require_http_methods(["POST"])
def bulk_respond_to_assignments(request):
    """Bulk accept/decline proposed assignments."""
    action = request.POST.get("action")
    raw_ids = request.POST.get("ids", "")
    ids = [i for i in raw_ids.split(",") if i.strip().isdigit()]

    if not ids or action not in ("accept", "decline"):
        messages.warning(request, "No assignments selected.")
        return redirect("volunteer_portal:portal_assignments")

    qs = VolunteerAssignment.objects.filter(
        pk__in=ids,
        volunteer=request.user,
        status=VolunteerAssignment.Status.PROPOSED,
    )

    new_status = (
        VolunteerAssignment.Status.ACCEPTED if action == "accept"
        else VolunteerAssignment.Status.DECLINED
    )
    count = qs.update(status=new_status)

    messages.success(request, f"{count} assignment{'s' if count != 1 else ''} {action}ed.")
    return redirect("volunteer_portal:portal_assignments")


class VolunteerHoursView(LoginRequiredMixin, TemplateView):
    template_name = "volunteers/portal_hours.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/volunteer/"
        hours_qs = VolunteerHours.objects.filter(volunteer=self.request.user).order_by("-date")
        ctx["hours"] = hours_qs

        # Summary
        ctx["total_hours"] = hours_qs.aggregate(t=Sum("hours"))["t"] or Decimal("0")
        today = date.today()
        ctx["hours_this_month"] = hours_qs.filter(
            date__year=today.year, date__month=today.month
        ).aggregate(t=Sum("hours"))["t"] or Decimal("0")

        # Last 8 weeks bar data
        weeks = []
        for i in range(7, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * i)
            week_end = week_start + timedelta(days=7)
            h = hours_qs.filter(
                date__gte=week_start, date__lt=week_end
            ).aggregate(t=Sum("hours"))["t"] or Decimal("0")
            weeks.append({"week_start": week_start, "hours": float(h)})
        ctx["weekly_hours"] = weeks
        ctx["weekly_max"] = max((w["hours"] for w in weeks), default=1) or 1

        return ctx

    def post(self, request):
        # Delete
        delete_id = request.GET.get("delete")
        if delete_id:
            VolunteerHours.objects.filter(
                pk=delete_id, volunteer=request.user
            ).delete()
            VolunteerProfile.objects.get_or_create(user=request.user).recalc_hours()
            messages.success(request, "Entry removed.")
            return redirect("volunteer_portal:portal_hours")

        # Create
        date_val = request.POST.get("date")
        hours_val = request.POST.get("hours")
        if date_val and hours_val:
            try:
                VolunteerHours.objects.create(
                    volunteer=request.user,
                    date=date_val,
                    hours=hours_val,
                    notes=request.POST.get("notes", ""),
                )
                VolunteerProfile.objects.get_or_create(user=request.user).recalc_hours()
                messages.success(request, "Hours logged.")
            except Exception as e:
                messages.error(request, f"Could not log hours: {e}")
        return redirect("volunteer_portal:portal_hours")


class VolunteerCertificatesView(LoginRequiredMixin, ListView):
    template_name = "volunteers/portal_certificates.html"
    context_object_name = "certificates"

    def get_queryset(self):
        return Certificate.objects.filter(volunteer=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/volunteer/"
        profile, _ = VolunteerProfile.objects.get_or_create(user=self.request.user)
        ctx["profile"] = profile
        return ctx


# =========================================================
# VOLUNTEER DIRECTORY (staff)
# =========================================================
class VolunteerListView(StaffRequiredMixin, ListView):
    template_name = "volunteers/management_volunteers.html"
    context_object_name = "volunteers"
    paginate_by = 30

    def get_queryset(self):
        from accounts.models import User

        qs = (
            User.objects
            .filter(
                Q(volunteer_profile__approved=True) | Q(role="volunteer")
            )
            .select_related("volunteer_profile")
            .distinct()
        )

        # Annotate stats in one query
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

        # Search
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(username__icontains=q)
                | Q(phone__icontains=q)
            )

        # Status filter
        status = self.request.GET.get("status", "").strip()
        if status == "approved":
            qs = qs.filter(volunteer_profile__approved=True)
        elif status == "pending":
            qs = qs.filter(
                Q(volunteer_profile__approved=False)
                | Q(volunteer_profile__isnull=True)
            )

        # Sort
        sort = self.request.GET.get("sort", "")
        if sort == "hours":
            qs = qs.order_by("-_hours_total")
        elif sort == "assignments":
            qs = qs.order_by("-_assignments_count")
        elif sort == "name":
            qs = qs.order_by("first_name", "last_name")
        else:
            qs = qs.order_by("-date_joined")

        return qs

    def get_context_data(self, **kwargs):
        from accounts.models import User

        ctx = super().get_context_data(**kwargs)
        ctx["filters"] = {
            "q": self.request.GET.get("q", ""),
            "status": self.request.GET.get("status", ""),
            "sort": self.request.GET.get("sort", ""),
        }
        ctx["pending_count"] = User.objects.filter(
            Q(volunteer_profile__approved=False)
            | Q(volunteer_profile__isnull=True),
            role="volunteer",
        ).distinct().count()

        for v in ctx["volunteers"]:
            v.assignments_count = getattr(v, "_assignments_count", 0) or 0
            v.completed_count = getattr(v, "_completed_count", 0) or 0
            v.hours_total = getattr(v, "_hours_total", Decimal("0")) or Decimal("0")
            v.certificates_count = getattr(v, "_certificates_count", 0) or 0
            v.profile_obj = getattr(v, "volunteer_profile", None)

        return ctx