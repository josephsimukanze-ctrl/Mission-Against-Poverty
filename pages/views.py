# pages/views.py

from django.db.models import Q, Sum
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from .models import HeroSlide, LeadershipMember, Page
from donations.models import Donation
from events.models import Event
from news.models import Article
from programs.models import Program
from projects.models import Project


# ============================================================
# Helpers
# ============================================================
def _active_project_statuses():
    """
    Return every Project.Status value that should count as "active".

    Adjust this list once you decide the canonical "in-flight" states
    for your workflow (e.g. only `ACTIVE`, or `ACTIVE` + `ONGOING`).
    """
    return [Project.Status.ACTIVE]


def _active_volunteer_count():
    """
    Return the number of active volunteers.

    Tries the volunteers app in order of preference, falls back to 0
    so the homepage never crashes when the app is missing.
    """
    # Try VolunteerAssignment (assignments currently in-flight)
    try:
        from volunteers.models import VolunteerAssignment as Assignment
        active_states = [
            s for s in ("accepted", "in_progress", "scheduled")
            if hasattr(Assignment, "Status") and s in [v for v, _ in Assignment.Status.choices]
        ]
        if active_states:
            return Assignment.objects.filter(status__in=active_states).values("volunteer").distinct().count()
        return Assignment.objects.values("volunteer").distinct().count()
    except Exception:
        pass

    # Try Volunteer profile model
    try:
        from volunteers.models import Volunteer
        return Volunteer.objects.filter(is_active=True).count()
    except Exception:
        return 0


# ============================================================
# Home
# ============================================================
class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # ---------- Hero carousel ----------
        ctx["hero_slides"] = (
            HeroSlide.objects
            .filter(is_active=True)
            .order_by("order", "id")
        )

        # ---------- Impact stats ----------
        donations_received = (
            Donation.objects
            .filter(status=Donation.Status.RECEIVED)
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Sum of beneficiary_target; fall back to beneficiaries_reached if 0
        people_targeted = (
            Project.objects
            .aggregate(total=Sum("beneficiary_target"))["total"]
            or 0
        )
        people_reached = (
            Project.objects
            .aggregate(total=Sum("beneficiaries_reached"))["total"]
            or 0
        )

        active_statuses = _active_project_statuses()

        ctx["stats"] = {
            # Prefer people_reached if any project has it; otherwise use target
            "people_helped": people_reached or people_targeted,
            "donations_received": donations_received,
            "active_projects": Project.objects.filter(status__in=active_statuses).count(),
            "active_volunteers": _active_volunteer_count(),
        }

        # ---------- Featured programs ----------
        ctx["programs"] = (
            Program.objects
            .filter(published=True, archived=False)
            .order_by("order", "name")[:4]
        )

        # ---------- Featured projects ----------
        # Fetch full objects (no .only()) so properties like progress_percent,
        # raised_amount, and beneficiaries_reached all work in the template.
        ctx["projects"] = (
            Project.objects
            .filter(
                status__in=active_statuses,
                published=True,
            )
            .order_by("-created_at", "-id")[:3]
        )

        # ---------- Latest articles ----------
        ctx["articles"] = (
            Article.objects
            .filter(published=True)
            .order_by("-published_at", "-id")[:3]
        )

        # ---------- Upcoming events ----------
        ctx["events"] = (
            Event.objects
            .filter(
                published=True,
                starts_at__gte=timezone.now(),
            )
            .order_by("starts_at", "id")[:3]
        )

        # ---------- Leadership ----------
        ctx["leaders"] = (
            LeadershipMember.objects
            .filter(is_active=True)
            .order_by("order", "name")[:4]
        )

        return ctx


# ============================================================
# About
# ============================================================
class AboutView(TemplateView):
    template_name = "pages/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["founders"] = (
            LeadershipMember.objects
            .filter(is_active=True, is_founder=True)
            .order_by("order", "name")
        )

        ctx["leaders"] = (
            LeadershipMember.objects
            .filter(is_active=True, is_founder=False)
            .order_by("order", "name")
        )

        return ctx


# ============================================================
# Page detail
# ============================================================
class PageDetailView(DetailView):
    model = Page
    template_name = "pages/page_detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = Page.objects.filter(published=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["leaders"] = (
            LeadershipMember.objects
            .filter(is_active=True)
            .order_by("order", "name")[:4]
        )

        return ctx