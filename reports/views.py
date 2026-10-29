# reports/views.py — Mission Against Poverty management views
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import re

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from accounts.models import STAFF_ROLES, Role, User
from audit.models import AuditLog
from audit.services import log_action

from settings_app.forms import SiteConfigForm
from donations.models import Campaign, Donation
from events.models import Event
from news.models import Article, NewsCategory
from pages.models import HeroSlide, LeadershipMember, Page
from programs.models import Program
from projects.models import Project, ProjectCategory

import logging
logger = logging.getLogger(__name__)
# ============================================================
# Auth helpers
# ============================================================

def require_staff(request):
    if not request.user.is_authenticated:
        raise PermissionDenied("Login required.")
    if not (request.user.is_superuser or request.user.role in STAFF_ROLES):
        raise PermissionDenied("You do not have access to the management area.")


class StaffRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        require_staff(request)
        return super().dispatch(request, *args, **kwargs)


# ============================================================
# Dashboard
# ============================================================

class ManagementDashboardView(StaffRequiredMixin, View):
    template_name = "reports/management_dashboard.html"

    def get(self, request):
        now = timezone.now()
        last_30 = now - timedelta(days=30)

        donations = Donation.objects.all()
        received = donations.filter(status=Donation.Status.RECEIVED)

        ctx = {
            "stats": {
                "total_received": received.aggregate(t=Sum("amount"))["t"] or Decimal("0"),
                "received_last_30": received.filter(created_at__gte=last_30)
                                            .aggregate(t=Sum("amount"))["t"] or Decimal("0"),
                "donations_count": donations.count(),
                "donations_pending": donations.filter(status=Donation.Status.PENDING).count(),
                "active_campaigns": Campaign.objects.filter(status=Campaign.Status.ACTIVE).count(),
                "active_projects": Project.objects.filter(status=Project.Status.ACTIVE).count(),
                "active_programs": Program.objects.filter(published=True, archived=False).count(),
                "upcoming_events": Event.objects.filter(published=True, starts_at__gte=now).count(),
                "donors": User.objects.filter(role=Role.DONOR).count(),
                "volunteers": User.objects.filter(role=Role.VOLUNTEER).count(),
                "partners": User.objects.filter(role=Role.PARTNER).count(),
                "beneficiaries": User.objects.filter(role=Role.BENEFICIARY).count(),
                "staff": User.objects.filter(role__in=list(STAFF_ROLES)).count(),
            },
            "recent_donations": received.select_related("campaign", "project")
                                        .order_by("-created_at")[:8],
            "campaigns": Campaign.objects.filter(status=Campaign.Status.ACTIVE)
                                         .order_by("-created_at")[:5],
            "recent_activity": AuditLog.objects.order_by("-created_at")[:10],
        }

        # 6-month donation buckets
        buckets = []
        for i in range(6):
            start = (now.replace(day=1) - timedelta(days=30 * i)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end = (start + timedelta(days=32)).replace(day=1)
            total = received.filter(
                created_at__gte=start, created_at__lt=end
            ).aggregate(t=Sum("amount"))["t"] or 0
            buckets.append({"label": start.strftime("%b %Y"), "value": float(total)})
        ctx["chart_donation_data"] = list(reversed(buckets))
        ctx["chart_status_data"] = list(donations.values("status").annotate(count=Count("id")))

        return render(request, self.template_name, ctx)


# ============================================================
# Generic list base
# ============================================================

class ManagementListMixin(StaffRequiredMixin, ListView):
    """
    Base class for management list views.

    Provides:
      - Search (`?q=`) across `search_fields`
      - Status filter (`?status=`) when `statuses` is set
      - Automatic row building from `columns`
      - Image thumbnails via `image_field` OR a column with `"image"` lambda
      - Consistent row/cell shape for the shared template
    """

    template_name = "reports/management_list.html"
    paginate_by = 30

    # Presentation
    title = "Items"
    singular = "item"
    plural = "items"
    new_label = None

    # Columns
    columns = []
    search_fields = []

    # Actions
    add_url = None
    row_url = None
    edit_url = None
    delete_url = None

    # Image shortcut
    image_field = None
    image_alt_field = None

    # Status filter
    statuses = None
    status_param = "status"

    # ============================================================
    # Queryset
    # ============================================================
    def get_queryset(self):
        qs = super().get_queryset()

        # Search
        q = self.request.GET.get("q", "").strip()
        if q and self.search_fields:
            q_obj = Q()
            for f in self.search_fields:
                q_obj |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(q_obj)

        # Status filter
        status_value = self.request.GET.get(self.status_param, "").strip()
        if status_value and self.statuses:
            model_status_field = getattr(self.model, "status", None)
            if model_status_field is not None:
                try:
                    qs = qs.filter(status=status_value)
                except (ValueError, TypeError):
                    pass

        return qs

    # ============================================================
    # Cell helpers
    # ============================================================
    def _resolve(self, fn_or_val, row):
        if callable(fn_or_val):
            try:
                return fn_or_val(row)
            except Exception:
                return ""
        return fn_or_val if fn_or_val is not None else ""

    def _make_image_cell(self, obj, image_field, alt_field=None):
        img = getattr(obj, image_field, None)
        url = img.url if img else None
        alt = (getattr(obj, alt_field, None) if alt_field else None) or str(obj)
        return {
            "is_image": True,
            "image_url": url,
            "alt": str(alt),
            "align": "left",
            "muted": False,
            "is_status": False,
            "value": "",
            "status": "",
        }

    def _make_column_cell(self, obj, col):
        value = self._resolve(col.get("accessor", ""), obj)
        return {
            "is_image": False,
            "image_url": None,
            "value": str(value) if value is not None else "",
            "align": col.get("align", "left"),
            "muted": bool(col.get("muted", False)),
            "is_status": bool(col.get("status", False)),
            "status": getattr(obj, "status", "") or "",
        }

    # ============================================================
    # Context
    # ============================================================
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["title"] = self.title
        ctx["singular"] = self.singular
        ctx["plural"] = self.plural
        ctx["new_label"] = self.new_label
        ctx["columns"] = self.columns
        ctx["q"] = self.request.GET.get("q", "")
        ctx["add_url"] = self.add_url
        ctx["row_url"] = self.row_url
        ctx["edit_url"] = self.edit_url
        ctx["delete_url"] = self.delete_url
        ctx["statuses"] = self.statuses
        ctx["status_filter"] = self.request.GET.get(self.status_param, "")

        page_obj = ctx.get("page_obj")
        ctx["total"] = page_obj.paginator.count if page_obj is not None else len(
            ctx.get("object_list", [])
        )

        object_list = ctx.get("object_list", [])
        if hasattr(object_list, "object_list"):
            object_list = object_list.object_list
        try:
            object_list = list(object_list)
        except Exception:
            object_list = []

        rows = []
        for obj in object_list:
            cells = []

            if self.image_field:
                cells.append(
                    self._make_image_cell(obj, self.image_field, self.image_alt_field)
                )

            for col in self.columns:
                if col.get("image"):
                    try:
                        img_url = col["image"](obj)
                    except Exception:
                        img_url = None
                    cells.append({
                        "is_image": True,
                        "image_url": img_url,
                        "alt": str(obj),
                        "align": col.get("align", "left"),
                        "muted": bool(col.get("muted", False)),
                        "is_status": False,
                        "value": "",
                        "status": "",
                    })
                    continue

                cells.append(self._make_column_cell(obj, col))

            rows.append({
                "pk": getattr(obj, "pk", None),
                "cells": cells,
                "view_url": self._resolve(self.row_url, obj) if self.row_url else None,
                "edit_url": self._resolve(self.edit_url, obj) if self.edit_url else None,
                "delete_url": self._resolve(self.delete_url, obj) if self.delete_url else None,
            })

        ctx["rows"] = rows
        return ctx


# ============================================================
# Section list views
# ============================================================

class PageListView(ManagementListMixin):
    model = Page
    title = "Pages"
    singular = "page"
    plural = "pages"
    image_field = "hero_image"
    image_alt_field = "title"
    search_fields = ["title", "slug"]
    add_url = "/management/pages/new/"
    edit_url = staticmethod(lambda r: f"/management/pages/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/pages/{r.pk}/delete/")

    def get_queryset(self):
        return Page.objects.all().order_by("-updated_at")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Title", "accessor": lambda r: r.title},
            {"label": "Slug", "accessor": lambda r: r.slug, "muted": True},
            {"label": "Published", "accessor": lambda r: "Yes" if r.published else "No"},
            {"label": "Updated", "accessor": lambda r: r.updated_at.strftime("%Y-%m-%d")},
        ]
        return super().get_context_data(**kwargs)


class ProgramListView(ManagementListMixin):
    model = Program
    title = "Programs"
    singular = "program"
    plural = "programs"
    image_field = "cover_image"
    image_alt_field = "name"
    search_fields = ["name", "summary"]
    add_url = "/management/programs/new/"
    edit_url = staticmethod(lambda r: f"/management/programs/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/programs/{r.pk}/delete/")

    def get_queryset(self):
        return Program.objects.all().order_by("name")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Program", "accessor": lambda r: r.name},
            {
                "label": "Summary",
                "accessor": lambda r: (
                    (r.summary[:80] + "…")
                    if r.summary and len(r.summary) > 80
                    else (r.summary or "—")
                ),
                "muted": True,
            },
            {"label": "Published", "accessor": lambda r: "Yes" if r.published else "No"},
            {"label": "Archived", "accessor": lambda r: "Yes" if r.archived else "No"},
        ]
        return super().get_context_data(**kwargs)


class ProjectListView(ManagementListMixin):
    model = Project
    title = "Projects"
    singular = "project"
    plural = "projects"
    image_field = "cover_image"
    image_alt_field = "name"
    search_fields = ["name", "summary", "location"]
    add_url = "/management/projects/new/"
    edit_url = staticmethod(lambda r: f"/management/projects/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/projects/{r.pk}/delete/")
    row_url = staticmethod(lambda r: f"/management/projects/{r.pk}/edit/")

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("program", "category")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Project", "accessor": lambda r: r.name, "width": "auto"},
            {
                "label": "Program",
                "accessor": lambda r: r.program.name if r.program else "—",
                "muted": True,
                "width": "180px",
            },
            {
                "label": "Status",
                "accessor": lambda r: r.get_status_display(),
                "status": True,
                "width": "120px",
            },
            {
                "label": "Target",
                "accessor": lambda r: (
                    f"K {float(r.fundraising_target):,.0f}"
                    if r.fundraising_target else "—"
                ),
                "align": "right",
                "width": "140px",
            },
            {
                "label": "Beneficiaries",
                "accessor": lambda r: (
                    f"{r.beneficiaries_reached or 0:,} / {r.beneficiary_target or 0:,}"
                ),
                "align": "right",
                "width": "160px",
            },
        ]
        return super().get_context_data(**kwargs)


class ProjectCategoryListView(ManagementListMixin):
    model = ProjectCategory
    title = "Project Categories"
    singular = "project category"
    plural = "project categories"
    search_fields = ["name", "slug"]
    add_url = "/management/project-categories/new/"
    edit_url = staticmethod(lambda r: f"/management/project-categories/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/project-categories/{r.pk}/delete/")

    def get_queryset(self):
        return super().get_queryset().order_by("name")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Category", "accessor": lambda r: r.name, "width": "auto"},
            {"label": "Slug", "accessor": lambda r: r.slug, "muted": True, "width": "200px"},
            {
                "label": "Projects",
                "accessor": lambda r: str(r.project_set.count()),
                "align": "right",
                "width": "110px",
            },
        ]
        return super().get_context_data(**kwargs)


class ArticleListView(ManagementListMixin):
    model = Article
    title = "News"
    singular = "article"
    plural = "articles"
    image_field = "cover_image"
    image_alt_field = "title"
    search_fields = ["title", "summary", "body"]
    add_url = "/management/news/new/"
    edit_url = staticmethod(lambda r: f"/management/news/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/news/{r.pk}/delete/")

    def get_queryset(self):
        return super().get_queryset().select_related("category").order_by("-created_at")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Title", "accessor": lambda r: r.title, "width": "auto"},
            {
                "label": "Category",
                "accessor": lambda r: r.category.name if r.category else "—",
                "muted": True,
                "width": "180px",
            },
            {
                "label": "Published",
                "accessor": lambda r: "Yes" if r.published else "No",
                "width": "110px",
            },
            {
                "label": "Date",
                "accessor": lambda r: r.created_at.strftime("%Y-%m-%d"),
                "width": "130px",
            },
        ]
        return super().get_context_data(**kwargs)


class NewsCategoryListView(ManagementListMixin):
    model = NewsCategory
    title = "News Categories"
    singular = "news category"
    plural = "news categories"
    search_fields = ["name", "slug"]
    add_url = "/management/news-categories/new/"
    edit_url = staticmethod(lambda r: f"/management/news-categories/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/news-categories/{r.pk}/delete/")

    def get_queryset(self):
        return super().get_queryset().order_by("name")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Category", "accessor": lambda r: r.name, "width": "auto"},
            {"label": "Slug", "accessor": lambda r: r.slug, "muted": True, "width": "200px"},
            {
                "label": "Articles",
                "accessor": lambda r: str(r.articles.count()),
                "align": "right",
                "width": "110px",
            },
        ]
        return super().get_context_data(**kwargs)


class EventListView(ManagementListMixin):
    model = Event
    title = "Events"
    singular = "event"
    plural = "events"
    image_field = "cover_image"
    image_alt_field = "name"
    search_fields = ["name", "description", "location"]
    add_url = "/management/events/new/"
    edit_url = staticmethod(lambda r: f"/management/events/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/events/{r.pk}/delete/")

    def get_queryset(self):
        return super().get_queryset().order_by("-starts_at", "name")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Event", "accessor": lambda r: r.name, "width": "auto"},
            {
                "label": "Location",
                "accessor": lambda r: r.location or "—",
                "muted": True,
                "width": "180px",
            },
            {
                "label": "Starts",
                "accessor": lambda r: (
                    r.starts_at.strftime("%b %d, %Y · %H:%M") if r.starts_at else "—"
                ),
                "width": "180px",
            },
            {
                "label": "Registration",
                "accessor": lambda r: "Open" if r.registration_open else "Closed",
                "width": "120px",
            },
            {
                "label": "Published",
                "accessor": lambda r: "Yes" if r.published else "No",
                "width": "110px",
            },
        ]
        return super().get_context_data(**kwargs)


class UserListView(ManagementListMixin):
    model = User
    title = "Users & Roles"
    singular = "user"
    plural = "users"
    search_fields = ["username", "email", "first_name", "last_name"]
    row_url = staticmethod(lambda r: f"/management/users/{r.pk}/")

    def get_queryset(self):
        return super().get_queryset().order_by("-date_joined")

    def get_context_data(self, **kwargs):
        self.columns = [
            {
                "label": "Name",
                "accessor": lambda r: r.get_full_name() or r.username,
                "width": "auto",
            },
            {
                "label": "Email",
                "accessor": lambda r: r.email or "—",
                "muted": True,
                "width": "260px",
            },
            {
                "label": "Role",
                "accessor": lambda r: r.get_role_display(),
                "width": "140px",
            },
            {
                "label": "Joined",
                "accessor": lambda r: r.date_joined.strftime("%Y-%m-%d"),
                "width": "130px",
            },
        ]
        return super().get_context_data(**kwargs)


class DonationListView(ManagementListMixin):
    model = Donation
    title = "Donations"
    singular = "donation"
    plural = "donations"
    search_fields = ["reference", "donor_name", "donor_email"]
    add_url = "/management/donations/new/"
    edit_url = staticmethod(lambda r: f"/management/donations/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/donations/{r.pk}/delete/")
    row_url = staticmethod(lambda r: f"/management/donations/{r.pk}/")

    def get_queryset(self):
        return (
            Donation.objects.select_related("campaign", "project")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Reference", "accessor": lambda r: r.reference},
            {"label": "Donor", "accessor": lambda r: r.donor_name or "Anonymous"},
            {"label": "Amount", "accessor": lambda r: f"K {r.amount}", "align": "right"},
            {"label": "Status", "accessor": lambda r: r.get_status_display(), "status": True},
            {"label": "Date", "accessor": lambda r: r.created_at.strftime("%Y-%m-%d")},
        ]
        self.statuses = [
            ("", "All statuses"),
            ("pending", "Pending"),
            ("received", "Received"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
            ("cancelled", "Cancelled"),
        ]
        return super().get_context_data(**kwargs)


class CampaignListView(ManagementListMixin):
    model = Campaign
    title = "Campaigns"
    singular = "campaign"
    plural = "campaigns"
    image_field = "cover_image"
    image_alt_field = "name"
    search_fields = ["name", "summary"]
    add_url = "/management/campaigns/new/"
    edit_url = staticmethod(lambda r: f"/management/campaigns/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/campaigns/{r.pk}/delete/")

    def get_queryset(self):
        return super().get_queryset().order_by("-created_at")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Campaign", "accessor": lambda r: r.name, "width": "auto"},
            {
                "label": "Status",
                "accessor": lambda r: r.get_status_display(),
                "status": True,
                "width": "120px",
            },
            {
                "label": "Target",
                "accessor": lambda r: (
                    f"K {float(r.target_amount):,.0f}" if r.target_amount else "—"
                ),
                "align": "right",
                "width": "140px",
            },
            {
                "label": "Raised",
                "accessor": lambda r: f"K {float(r.raised_amount or 0):,.0f}",
                "align": "right",
                "width": "140px",
            },
            {
                "label": "Progress",
                "accessor": lambda r: f"{r.progress_percent}%",
                "align": "right",
                "width": "100px",
            },
        ]
        return super().get_context_data(**kwargs)


class AuditListView(ManagementListMixin):
    model = AuditLog
    title = "Audit Logs"
    singular = "log entry"
    plural = "log entries"
    search_fields = ["action", "target_type", "target_id"]
    paginate_by = 50
    row_url = staticmethod(lambda r: f"/management/audit/{r.pk}/")

    def get_queryset(self):
        qs = super().get_queryset().select_related("user").order_by("-created_at")
        action = self.request.GET.get("action", "").strip()
        if action:
            qs = qs.filter(action__startswith=action)
        return qs

    def get_context_data(self, **kwargs):
        # Resolve target labels for the current page
        logs = list(self.get_queryset()[:500])
        targets = self._bulk_resolve_targets(logs)

        def _target_label(r):
            return self._format_target(r, targets.get((r.target_type, str(r.target_id))))

        self.columns = [
            {
                "label": "When",
                "accessor": lambda r: r.created_at.strftime("%Y-%m-%d %H:%M"),
                "width": "140px",
            },
            {
                "label": "Action",
                "accessor": lambda r: self._humanize_action(r.action),
                "width": "auto",
            },
            {"label": "Target", "accessor": _target_label, "muted": True, "width": "280px"},
            {
                "label": "User",
                "accessor": lambda r: (
                    (r.user.get_full_name() or r.user.get_username()) if r.user else "system"
                ),
                "muted": True,
                "width": "140px",
            },
        ]

        ctx = super().get_context_data(**kwargs)
        ctx["action_filter"] = self.request.GET.get("action", "")
        ctx["action_options"] = (
            AuditLog.objects.values_list("action", flat=True)
            .distinct()
            .order_by("action")
        )
        return ctx

    # ---------- Humanizer ----------
    VERB_MAP = {
        "create": "Created",
        "create_management": "Created",
        "update": "Updated",
        "update_management": "Updated",
        "delete": "Deleted",
        "delete_management": "Deleted",
        "manually_received": "Marked received",
        "role_change": "Changed role",
        "proof_approved": "Approved proof",
        "proof_rejected": "Rejected proof",
        "proof_submitted": "Submitted proof",
        "status_change": "Changed status",
        "submitted": "Submitted",
        "login": "Signed in",
        "logout": "Signed out",
        "export_donations": "Exported donations CSV",
    }

    ENTITY_SPECIAL = {
        "sitesettings": "Site settings",
        "sitesetting": "Site setting",
        "contactmessage": "Message",
        "volunteerapplication": "Volunteer application",
        "partnershipapplication": "Partnership application",
        "eventregistration": "Event registration",
        "leadershipmember": "Leadership member",
        "news.category": "News category",
        "project.category": "Project category",
        "donations.campaign": "Campaign",
    }

    def _humanize_action(self, action):
        if not action:
            return "—"
        if "." not in action:
            return action.replace("_", " ").title()

        entity, verb = action.rsplit(".", 1)
        verb_label = self.VERB_MAP.get(verb, verb.replace("_", " ").title())

        entity_lower = entity.lower()
        if entity_lower in self.ENTITY_SPECIAL:
            entity_label = self.ENTITY_SPECIAL[entity_lower]
        else:
            spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", entity)
            entity_label = spaced.replace("_", " ").replace(".", " ").strip().title()

        return f"{verb_label} {entity_label}"

    # ---------- Bulk resolver ----------
    def _bulk_resolve_targets(self, logs):
        by_type = defaultdict(list)
        for log in logs:
            tt = (log.target_type or "").strip()
            tid = (str(log.target_id) if log.target_id else "").strip()
            if tt and tid:
                by_type[tt].append(tid)

        if not by_type:
            return {}

        name_to_model = {}
        for m in apps.get_models():
            name_to_model.setdefault(m.__name__.lower(), m)

        targets = {}
        for target_type, ids in by_type.items():
            model = None
            if "." in target_type:
                try:
                    app_label, model_name = target_type.split(".", 1)
                    model = apps.get_model(app_label, model_name)
                except (LookupError, ValueError):
                    model = None
            if model is None:
                model = name_to_model.get(target_type.lower())
            if model is None:
                continue
            try:
                for obj in model.objects.filter(pk__in=ids):
                    targets[(target_type, str(obj.pk))] = obj
            except Exception:
                continue
        return targets

    # ---------- Formatter ----------
    def _format_target(self, log, obj):
        if obj is None:
            short_id = (str(log.target_id) or "")[:8]
            label = (log.target_type or "Unknown").split(".")[-1]
            return f"{label} {short_id}"
        for attr in ("name", "title", "subject", "email", "username", "reference"):
            value = getattr(obj, attr, None)
            if value:
                return str(value)
        return str(obj)


class AuditLogDetailView(StaffRequiredMixin, View):
    template_name = "reports/audit_detail.html"

    def get(self, request, pk):
        log = get_object_or_404(AuditLog.objects.select_related("user"), pk=pk)
        return render(request, self.template_name, {"log": log})


# ============================================================
# Donation detail + form views
# ============================================================

class DonationDetailView(StaffRequiredMixin, View):
    template_name = "reports/management_donation_detail.html"

    def get(self, request, pk):
        donation = get_object_or_404(
            Donation.objects.select_related("campaign", "project", "donor"), pk=pk
        )
        return render(request, self.template_name, {
            "donation": donation,
            "receipt": getattr(donation, "receipt", None),
            "singular": "donation",
            "cancel_url": "/management/donations/",
        })

def post(self, request, pk):
    from django.db import transaction as db_transaction
    from payments.models import PaymentTransaction
    from payments.services import record_successful_transaction

    donation = get_object_or_404(Donation, pk=pk)
    action = request.POST.get("action", "")

    # ------------------------------------------------------------------
    # Mark received
    # ------------------------------------------------------------------
    if action == "mark_received":
        if donation.status == Donation.Status.RECEIVED:
            messages.info(request, "This donation is already marked as received.")
            return redirect(f"/management/donations/{donation.pk}/")

        try:
            with db_transaction.atomic():
                donation = Donation.objects.select_for_update().get(pk=pk)

                txn = PaymentTransaction.objects.filter(donation=donation).first()
                if not txn:
                    txn = PaymentTransaction.objects.create(
                        donation=donation,
                        provider="manual",
                        provider_reference=f"MANUAL-{donation.reference}",
                        amount=donation.amount,
                        currency=donation.currency,
                    )

                record_successful_transaction(
                    txn,
                    raw_response={
                        "source": "manual_reconciliation",
                        "by": request.user.username,
                    },
                )
        except Exception:
            logger.exception("Failed to mark donation %s as received", donation.reference)
            messages.error(
                request,
                f"Could not mark {donation.reference} as received. "
                f"Please retry or check the server logs.",
            )
            return redirect(f"/management/donations/{donation.pk}/")

        log_action(request, "donation.manually_received", target=donation)
        messages.success(request, f"Donation {donation.reference} marked received.")

    # ------------------------------------------------------------------
    # Approve proof of payment
    # ------------------------------------------------------------------
    elif action == "approve_proof":
        # Detect whether the model exposes a `proof_verified_by` FK
        has_verifier = any(
            f.name == "proof_verified_by"
            for f in donation._meta.get_fields()
        )

        if donation.proof_verified_at and not donation.proof_rejected:
            messages.info(request, "Proof of payment is already approved.")
            return redirect(f"/management/donations/{donation.pk}/")

        donation.proof_verified_at = timezone.now()
        donation.proof_rejected = False
        donation.proof_rejection_reason = ""

        update_fields = [
            "proof_verified_at",
            "proof_rejected",
            "proof_rejection_reason",
        ]
        if has_verifier:
            donation.proof_verified_by_id = request.user.pk
            update_fields.append("proof_verified_by_id")   # ← attname, not FK name

        donation.save(update_fields=update_fields)
        log_action(request, "donation.proof_approved", target=donation)
        messages.success(request, "Proof of payment approved.")

    # ------------------------------------------------------------------
    # Reject proof of payment
    # ------------------------------------------------------------------
    elif action == "reject_proof":
        reason = (request.POST.get("reason") or "").strip()[:500] or "No reason provided."

        has_verifier = any(
            f.name == "proof_verified_by"
            for f in donation._meta.get_fields()
        )

        donation.proof_rejected = True
        donation.proof_rejection_reason = reason
        donation.proof_verified_at = None

        update_fields = [
            "proof_rejected",
            "proof_rejection_reason",
            "proof_verified_at",
        ]
        if has_verifier:
            donation.proof_verified_by_id = None
            update_fields.append("proof_verified_by_id")   # ← attname, not FK name

        donation.save(update_fields=update_fields)
        log_action(
            request,
            "donation.proof_rejected",
            target=donation,
            metadata={"reason": reason},
        )
        messages.warning(request, f"Proof rejected: {reason}")

    # ------------------------------------------------------------------
    # Unknown action
    # ------------------------------------------------------------------
    else:
        messages.error(request, "Unknown action.")
        return redirect(f"/management/donations/{donation.pk}/")

    return redirect(f"/management/donations/{donation.pk}/")

class DonationManagementForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = (
            "donor_name", "donor_email", "donor_phone", "is_anonymous",
            "kind", "frequency", "amount", "currency",
            "campaign", "project", "message", "status",
        )
        widgets = {
            "donor_name": forms.TextInput(attrs={"class": "form-input"}),
            "donor_email": forms.EmailInput(attrs={"class": "form-input"}),
            "donor_phone": forms.TextInput(attrs={"class": "form-input"}),
            "kind": forms.Select(attrs={"class": "form-input"}),
            "frequency": forms.Select(attrs={"class": "form-input"}),
            "amount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01"}),
            "currency": forms.TextInput(attrs={"class": "form-input"}),
            "campaign": forms.Select(attrs={"class": "form-input"}),
            "project": forms.Select(attrs={"class": "form-input"}),
            "message": forms.Textarea(attrs={"class": "form-input", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["campaign"].queryset = Campaign.objects.all()
        self.fields["project"].queryset = Project.objects.all()
        self.fields["campaign"].required = False
        self.fields["project"].required = False


class DonationCreateView(StaffRequiredMixin, View):
    template_name = "reports/management_donation_form.html"

    def get(self, request):
        form = DonationManagementForm(initial={"currency": "ZMW", "status": "received"})
        return render(request, self.template_name, {"form": form, "mode": "create"})

    def post(self, request):
        from payments.models import PaymentTransaction
        from payments.services import record_successful_transaction

        form = DonationManagementForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "mode": "create"})

        donation = form.save(commit=False)
        donation.donor = None
        requested_status = donation.status
        donation.status = Donation.Status.PENDING
        donation.save()
        log_action(request, "donation.create_manual", target=donation)

        if requested_status == Donation.Status.RECEIVED:
            txn = PaymentTransaction.objects.create(
                donation=donation,
                provider="manual",
                provider_reference=f"MANUAL-{donation.reference}",
                amount=donation.amount,
                currency=donation.currency,
            )
            record_successful_transaction(
                txn,
                raw_response={"source": "management_add", "by": request.user.username},
            )
            messages.success(request, f"Donation {donation.reference} recorded and marked received.")
        else:
            messages.success(request, f"Donation {donation.reference} recorded.")

        return redirect(f"/management/donations/{donation.pk}/")


class DonationUpdateView(StaffRequiredMixin, View):
    template_name = "reports/management_donation_form.html"

    def get(self, request, pk):
        donation = get_object_or_404(Donation, pk=pk)
        return render(request, self.template_name, {
            "form": DonationManagementForm(instance=donation),
            "mode": "edit",
            "donation": donation,
        })

    def post(self, request, pk):
        donation = get_object_or_404(Donation, pk=pk)
        form = DonationManagementForm(request.POST, instance=donation)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form, "mode": "edit", "donation": donation,
            })
        if donation.status == Donation.Status.RECEIVED:
            form.instance.status = Donation.Status.RECEIVED
        form.save()
        log_action(request, "donation.update_manual", target=donation)
        messages.success(request, "Donation updated.")
        return redirect(f"/management/donations/{donation.pk}/")


class DonationDeleteView(StaffRequiredMixin, View):
    template_name = "reports/management_confirm_delete.html"

    def get(self, request, pk):
        donation = get_object_or_404(Donation, pk=pk)
        return render(request, self.template_name, {
            "object": donation,
            "object_type": "donation",
            "cancel_url": f"/management/donations/{donation.pk}/",
        })

    def post(self, request, pk):
        donation = get_object_or_404(Donation, pk=pk)
        if donation.status == Donation.Status.RECEIVED:
            messages.error(request, "Received donations cannot be deleted.")
            return redirect(f"/management/donations/{donation.pk}/")
        ref = donation.reference
        donation.delete()
        log_action(request, "donation.delete", metadata={"reference": ref})
        messages.success(request, f"Donation {ref} deleted.")
        return redirect("/management/donations/")


# ============================================================
# User detail
# ============================================================

class UserDetailView(StaffRequiredMixin, View):
    template_name = "reports/management_user_detail.html"

    def get(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {
            "object": u, "role_choices": Role.choices,
        })

    def post(self, request, pk):
        u = get_object_or_404(User, pk=pk)
        if not (request.user.is_superuser or request.user.role == Role.ADMINISTRATOR):
            raise PermissionDenied("Only administrators can change roles.")
        new_role = request.POST.get("role", "")
        if new_role in Role.values:
            old = u.role
            u.role = new_role
            u.save(update_fields=["role"])
            log_action(request, "user.role_change", target=u,
                       metadata={"from": old, "to": new_role})
            messages.success(request, f"Role updated to {u.get_role_display()}.")
        else:
            messages.error(request, "Invalid role.")
        return redirect(f"/management/users/{u.pk}/")


# ============================================================
# Generic forms + CRUD
# ============================================================

class BaseManagementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            cur = w.attrs.get("class", "")
            if "form-input" not in cur:
                w.attrs["class"] = (cur + " form-input").strip()


class PageForm(BaseManagementForm):
    class Meta:
        model = Page
        fields = ("title", "slug", "subtitle", "body", "hero_image", "published")


class ProgramForm(BaseManagementForm):
    class Meta:
        model = Program
        fields = ("name", "slug", "summary", "description", "icon",
                  "cover_image", "published", "archived")


class ProjectForm(BaseManagementForm):
    class Meta:
        model = Project
        fields = (
            "name", "slug", "program", "category", "summary", "description", "location",
            "manager", "start_date", "end_date", "budget", "fundraising_target",
            "beneficiary_target", "beneficiaries_reached", "status", "cover_image", "published",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class ProjectCategoryForm(BaseManagementForm):
    class Meta:
        model = ProjectCategory
        fields = ("name", "slug")


class ArticleForm(BaseManagementForm):
    class Meta:
        model = Article
        fields = ("title", "slug", "category", "summary", "body",
                  "cover_image", "published", "published_at")
        widgets = {"published_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class NewsCategoryForm(BaseManagementForm):
    class Meta:
        model = NewsCategory
        fields = ("name", "slug")


class EventForm(BaseManagementForm):
    class Meta:
        model = Event
        fields = ("name", "description", "location", "starts_at", "ends_at",
                  "cover_image", "registration_open", "published")
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class CampaignForm(BaseManagementForm):
    class Meta:
        model = Campaign
        fields = ("name", "slug", "summary", "description", "target_amount",
                  "start_date", "end_date", "cover_image", "project", "status")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class HeroSlideForm(BaseManagementForm):
    class Meta:
        model = HeroSlide
        fields = (
            "title", "subtitle", "image", "alt_text",
            "cta_label", "cta_url", "order", "is_active",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input"}),
            "subtitle": forms.TextInput(attrs={"class": "form-input"}),
            "alt_text": forms.TextInput(attrs={"class": "form-input"}),
            "cta_label": forms.TextInput(attrs={"class": "form-input"}),
            "cta_url": forms.TextInput(attrs={"class": "form-input"}),
            "order": forms.NumberInput(attrs={"class": "form-input"}),
        }


class LeadershipMemberForm(BaseManagementForm):
    class Meta:
        model = LeadershipMember
        fields = (
            "name", "position", "bio", "photo",
            "is_founder", "email", "linkedin",
            "order", "is_active",
        )


# ============================================================
# Generic create / update / delete
# ============================================================

class GenericCreateView(StaffRequiredMixin, View):
    template_name = "reports/management_form.html"
    model = None
    form_class = None
    singular = "record"
    success_url = None

    def get(self, request):
        return self._render(request, self.form_class(), mode="create")

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            return self._render(request, form, mode="create")
        obj = form.save()
        log_action(request, f"{self.singular}.create_management", target=obj)
        messages.success(request, f"{self.singular.capitalize()} created.")
        return redirect(self.success_url)

    def _render(self, request, form, mode, obj=None):
        return render(request, self.template_name, {
            "form": form, "mode": mode, "singular": self.singular,
            "object": obj, "cancel_url": self.success_url,
        })


class GenericUpdateView(StaffRequiredMixin, View):
    template_name = "reports/management_form.html"
    model = None
    form_class = None
    singular = "record"
    success_url = None

    def get(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        return self._render(request, self.form_class(instance=obj), mode="edit", obj=obj)

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        form = self.form_class(request.POST, request.FILES, instance=obj)
        if not form.is_valid():
            return self._render(request, form, mode="edit", obj=obj)
        form.save()
        log_action(request, f"{self.singular}.update_management", target=obj)
        messages.success(request, f"{self.singular.capitalize()} updated.")
        return redirect(self.success_url)

    def _render(self, request, form, mode, obj=None):
        return render(request, self.template_name, {
            "form": form, "mode": mode, "singular": self.singular,
            "object": obj, "cancel_url": self.success_url,
        })


class GenericDeleteView(StaffRequiredMixin, View):
    template_name = "reports/management_confirm_delete.html"
    model = None
    singular = "record"
    success_url = None

    def get(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        return render(request, self.template_name, {
            "object": obj, "object_type": self.singular, "cancel_url": self.success_url,
        })

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        label = str(obj)
        obj.delete()
        log_action(request, f"{self.singular}.delete_management",
                   metadata={"label": label})
        messages.success(request, f"{self.singular.capitalize()} deleted.")
        return redirect(self.success_url)


# ============================================================
# Concrete CRUD per model
# ============================================================

class PageCreateView(GenericCreateView):
    model = Page; form_class = PageForm; singular = "page"; success_url = "/management/pages/"

class PageUpdateView(GenericUpdateView):
    model = Page; form_class = PageForm; singular = "page"; success_url = "/management/pages/"

class PageDeleteView(GenericDeleteView):
    model = Page; singular = "page"; success_url = "/management/pages/"


class ProgramCreateView(GenericCreateView):
    model = Program; form_class = ProgramForm; singular = "program"; success_url = "/management/programs/"

class ProgramUpdateView(GenericUpdateView):
    model = Program; form_class = ProgramForm; singular = "program"; success_url = "/management/programs/"

class ProgramDeleteView(GenericDeleteView):
    model = Program; singular = "program"; success_url = "/management/programs/"


class ProjectCreateView(GenericCreateView):
    model = Project; form_class = ProjectForm; singular = "project"; success_url = "/management/projects/"

class ProjectUpdateView(GenericUpdateView):
    model = Project; form_class = ProjectForm; singular = "project"; success_url = "/management/projects/"

class ProjectDeleteView(GenericDeleteView):
    model = Project; singular = "project"; success_url = "/management/projects/"


class ProjectCategoryCreateView(GenericCreateView):
    model = ProjectCategory; form_class = ProjectCategoryForm
    singular = "project category"; success_url = "/management/project-categories/"

class ProjectCategoryUpdateView(GenericUpdateView):
    model = ProjectCategory; form_class = ProjectCategoryForm
    singular = "project category"; success_url = "/management/project-categories/"

class ProjectCategoryDeleteView(GenericDeleteView):
    model = ProjectCategory; singular = "project category"
    success_url = "/management/project-categories/"


class ArticleCreateView(GenericCreateView):
    model = Article; form_class = ArticleForm; singular = "article"; success_url = "/management/news/"

class ArticleUpdateView(GenericUpdateView):
    model = Article; form_class = ArticleForm; singular = "article"; success_url = "/management/news/"

class ArticleDeleteView(GenericDeleteView):
    model = Article; singular = "article"; success_url = "/management/news/"


class NewsCategoryCreateView(GenericCreateView):
    model = NewsCategory; form_class = NewsCategoryForm
    singular = "news category"; success_url = "/management/news-categories/"

class NewsCategoryUpdateView(GenericUpdateView):
    model = NewsCategory; form_class = NewsCategoryForm
    singular = "news category"; success_url = "/management/news-categories/"

class NewsCategoryDeleteView(GenericDeleteView):
    model = NewsCategory; singular = "news category"
    success_url = "/management/news-categories/"


class EventCreateView(GenericCreateView):
    model = Event; form_class = EventForm; singular = "event"; success_url = "/management/events/"

class EventUpdateView(GenericUpdateView):
    model = Event; form_class = EventForm; singular = "event"; success_url = "/management/events/"

class EventDeleteView(GenericDeleteView):
    model = Event; singular = "event"; success_url = "/management/events/"


class CampaignCreateView(GenericCreateView):
    model = Campaign; form_class = CampaignForm; singular = "campaign"; success_url = "/management/campaigns/"

class CampaignUpdateView(GenericUpdateView):
    model = Campaign; form_class = CampaignForm; singular = "campaign"; success_url = "/management/campaigns/"

class CampaignDeleteView(GenericDeleteView):
    model = Campaign; singular = "campaign"; success_url = "/management/campaigns/"


class HeroSlideListView(ManagementListMixin):
    from pages.models import HeroSlide as M
    model = M
    template_name = "reports/management_hero_slides_list.html"
    title = "Hero Slides"
    singular = "hero slide"
    plural = "hero slides"
    search_fields = ["title", "headline", "subheadline"]
    paginate_by = 30
    add_url = "/management/hero-slides/new/"
    row_url = staticmethod(lambda r: f"/management/hero-slides/{r.pk}/edit/")
    edit_url = staticmethod(lambda r: f"/management/hero-slides/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/hero-slides/{r.pk}/delete/")

    def get_queryset(self):
        from pages.models import HeroSlide
        return HeroSlide.objects.order_by("order", "-created_at")

    def get_context_data(self, **kwargs):
        from pages.models import HeroSlide

        self.columns = []  # overridden in template
        ctx = super().get_context_data(**kwargs)

        all_qs = HeroSlide.objects.all()
        ctx["stats"] = {
            "total": all_qs.count(),
            "active": all_qs.filter(is_active=True).count() if hasattr(HeroSlide, "is_active") else all_qs.filter(active=True).count(),
            "inactive": all_qs.count() - (all_qs.filter(is_active=True).count() if hasattr(HeroSlide, "is_active") else all_qs.filter(active=True).count()),
        }

        return ctx



class HeroSlideCreateView(GenericCreateView):
    model = HeroSlide; form_class = HeroSlideForm
    singular = "hero slide"; success_url = "/management/hero-slides/"

class HeroSlideUpdateView(GenericUpdateView):
    model = HeroSlide; form_class = HeroSlideForm
    singular = "hero slide"; success_url = "/management/hero-slides/"

class HeroSlideDeleteView(GenericDeleteView):
    model = HeroSlide; singular = "hero slide"; success_url = "/management/hero-slides/"


class LeadershipMemberListView(ManagementListMixin):
    from pages.models import LeadershipMember as M
    model = M
    template_name = "reports/management_leadership_list.html"
    title = "Leadership & Founders"
    singular = "leadership member"
    plural = "leadership members"
    search_fields = ["name", "position", "bio"]
    paginate_by = 30
    add_url = "/management/leadership/new/"
    row_url = staticmethod(lambda r: f"/management/leadership/{r.pk}/edit/")
    edit_url = staticmethod(lambda r: f"/management/leadership/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/leadership/{r.pk}/delete/")

    def get_queryset(self):
        from pages.models import LeadershipMember
        return LeadershipMember.objects.order_by("order", "name")

    def get_context_data(self, **kwargs):
        from pages.models import LeadershipMember

        self.columns = [
            {
                "label": "Name",
                "accessor": lambda r: r.name,
                "width": "auto",
            },
            {
                "label": "Position",
                "accessor": lambda r: r.position,
                "muted": True,
                "width": "240px",
            },
            {
                "label": "Role",
                "accessor": lambda r: "Founder" if r.is_founder else "Leader",
                "status": False,
                "width": "110px",
            },
            {
                "label": "Order",
                "accessor": lambda r: str(r.order),
                "align": "center",
                "width": "80px",
            },
            {
                "label": "Status",
                "accessor": lambda r: "Active" if r.is_active else "Inactive",
                "status": True,
                "width": "100px",
            },
        ]
        ctx = super().get_context_data(**kwargs)

        all_qs = LeadershipMember.objects.all()
        ctx["stats"] = {
            "total": all_qs.count(),
            "founders": all_qs.filter(is_founder=True).count(),
            "leaders": all_qs.filter(is_founder=False).count(),
            "active": all_qs.filter(is_active=True).count(),
            "inactive": all_qs.filter(is_active=False).count(),
        }

        return ctx



class LeadershipMemberCreateView(GenericCreateView):
    model = LeadershipMember; form_class = LeadershipMemberForm
    singular = "leadership member"; success_url = "/management/leadership/"

class LeadershipMemberUpdateView(GenericUpdateView):
    model = LeadershipMember; form_class = LeadershipMemberForm
    singular = "leadership member"; success_url = "/management/leadership/"

class LeadershipMemberDeleteView(GenericDeleteView):
    model = LeadershipMember; singular = "leadership member"
    success_url = "/management/leadership/"


# ============================================================
# Reports & Analytics
# ============================================================

class ReportsView(StaffRequiredMixin, View):
    template_name = "reports/management_reports.html"

    def get(self, request):
        from volunteers.models import VolunteerAssignment, VolunteerHours

        try:
            start = datetime.strptime(request.GET.get("start", ""), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start = (timezone.now() - timedelta(days=30)).date()
        try:
            end = datetime.strptime(request.GET.get("end", ""), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            end = timezone.now().date()

        donations = Donation.objects.filter(
            created_at__date__gte=start, created_at__date__lte=end
        )
        received = donations.filter(status=Donation.Status.RECEIVED)
        total_received = received.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        avg_gift = (total_received / received.count()) if received.count() else Decimal("0")

        by_status = list(donations.values("status").annotate(count=Count("id"), total=Sum("amount")))
        by_kind = list(donations.values("kind").annotate(count=Count("id"), total=Sum("amount")))
        by_campaign = list(
            received.values("campaign__name")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )
        by_day = list(
            received.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )

        projects = Project.objects.filter(published=True)

        return render(request, self.template_name, {
            "start": start,
            "end": end,
            "donations": {
                "total": total_received,
                "count": received.count(),
                "avg": avg_gift,
                "pending_count": donations.filter(status=Donation.Status.PENDING).count(),
                "failed_count": donations.filter(status=Donation.Status.FAILED).count(),
            },
            "by_status": by_status,
            "by_kind": by_kind,
            "by_campaign": by_campaign,
            "chart_daily": [
                {"label": r["day"].strftime("%b %d"), "value": float(r["total"])}
                for r in by_day
            ],
            "projects": {
                "active": projects.filter(status=Project.Status.ACTIVE).count(),
                "completed": projects.filter(status=Project.Status.COMPLETED).count(),
                "total_budget": projects.aggregate(t=Sum("budget"))["t"] or 0,
                "total_target": projects.aggregate(t=Sum("fundraising_target"))["t"] or 0,
                "total_raised": total_received,
            },
            "volunteers": {
                "total_assignments": VolunteerAssignment.objects.count(),
                "completed": VolunteerAssignment.objects.filter(
                    status=VolunteerAssignment.Status.COMPLETED
                ).count(),
                "accepted": VolunteerAssignment.objects.filter(
                    status=VolunteerAssignment.Status.ACCEPTED
                ).count(),
                "proposed": VolunteerAssignment.objects.filter(
                    status=VolunteerAssignment.Status.PROPOSED
                ).count(),
                "total_hours": VolunteerHours.objects.aggregate(t=Sum("hours"))["t"] or 0,
            },
        })


class ReportsExportCSVView(StaffRequiredMixin, View):
    def get(self, request):
        try:
            start = datetime.strptime(request.GET.get("start", ""), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            start = (timezone.now() - timedelta(days=30)).date()
        try:
            end = datetime.strptime(request.GET.get("end", ""), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            end = timezone.now().date()

        qs = (
            Donation.objects.filter(
                created_at__date__gte=start,
                created_at__date__lte=end,
                status=Donation.Status.RECEIVED,
            )
            .select_related("campaign", "project")
            .order_by("-created_at")
        )

        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = (
            f'attachment; filename="donations-{start}-to-{end}.csv"'
        )
        w = csv.writer(resp)
        w.writerow([
            "Reference", "Date", "Donor", "Email", "Amount",
            "Currency", "Campaign", "Project", "Status",
        ])
        for d in qs:
            w.writerow([
                d.reference,
                d.created_at.strftime("%Y-%m-%d %H:%M"),
                d.donor_name or "Anonymous",
                d.donor_email or "",
                str(d.amount),
                d.currency,
                d.campaign.name if d.campaign else "",
                d.project.name if d.project else "",
                d.get_status_display(),
            ])

        log_action(request, "report.export_donations_csv",
                   metadata={"start": str(start), "end": str(end)})
        return resp


# ============================================================
# Newsletter subscribers
# ============================================================

class NewsletterSubscriberListView(ManagementListMixin):
    model = None  # set below
    title = "Newsletter Subscribers"
    singular = "subscriber"
    plural = "subscribers"
    search_fields = ["email", "name"]
    add_url = "/management/newsletter/new/"
    edit_url = staticmethod(lambda r: f"/management/newsletter/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/newsletter/{r.pk}/delete/")

    def get_queryset(self):
        from newsletter.models import NewsletterSubscriber
        return NewsletterSubscriber.objects.order_by("-created_at")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Email", "accessor": lambda r: r.email},
            {"label": "Name", "accessor": lambda r: r.name or "—", "muted": True},
            {"label": "Status", "accessor": lambda r: r.get_status_display(), "status": True},
            {"label": "Source", "accessor": lambda r: r.source or "—", "muted": True},
            {"label": "Subscribed", "accessor": lambda r: r.created_at.strftime("%Y-%m-%d")},
        ]
        return super().get_context_data(**kwargs)


class NewsletterSubscriberForm(BaseManagementForm):
    class Meta:
        from newsletter.models import NewsletterSubscriber as M
        model = M
        fields = ("email", "name", "status", "source")


class SubscriberCreateView(GenericCreateView):
    model = None; form_class = NewsletterSubscriberForm
    singular = "subscriber"; success_url = "/management/newsletter/"

class SubscriberUpdateView(GenericUpdateView):
    model = None; form_class = NewsletterSubscriberForm
    singular = "subscriber"; success_url = "/management/newsletter/"

class SubscriberDeleteView(GenericDeleteView):
    model = None; singular = "subscriber"; success_url = "/management/newsletter/"


# ============================================================
# Newsletter campaigns
# ============================================================

class NewsletterCampaignListView(ManagementListMixin):
    model = None
    title = "Newsletters"
    singular = "newsletter"
    plural = "newsletters"
    new_label = "New newsletter"
    search_fields = ["subject", "preview_text"]
    add_url = "/management/newsletter/campaigns/new/"
    edit_url = staticmethod(lambda r: f"/management/newsletter/campaigns/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/newsletter/campaigns/{r.pk}/delete/")

    def get_queryset(self):
        from newsletter.models import NewsletterCampaign
        return NewsletterCampaign.objects.order_by("-created_at")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Subject", "accessor": lambda r: r.subject},
            {"label": "Status", "accessor": lambda r: r.get_status_display(), "status": True},
            {"label": "Recipients", "accessor": lambda r: str(r.recipients_count), "align": "right"},
            {"label": "Sent", "accessor": lambda r: r.sent_at.strftime("%Y-%m-%d") if r.sent_at else "—"},
            {"label": "Created", "accessor": lambda r: r.created_at.strftime("%Y-%m-%d")},
        ]
        return super().get_context_data(**kwargs)


class NewsletterCampaignForm(BaseManagementForm):
    class Meta:
        from newsletter.models import NewsletterCampaign as M
        model = M
        fields = ("subject", "preview_text", "body", "status", "scheduled_for")
        widgets = {"scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class NewsletterCampaignCreateView(GenericCreateView):
    model = None; form_class = NewsletterCampaignForm
    singular = "newsletter"; success_url = "/management/newsletter/campaigns/"

class NewsletterCampaignUpdateView(GenericUpdateView):
    model = None; form_class = NewsletterCampaignForm
    singular = "newsletter"; success_url = "/management/newsletter/campaigns/"

class NewsletterCampaignDeleteView(GenericDeleteView):
    model = None; singular = "newsletter"; success_url = "/management/newsletter/campaigns/"


# ============================================================
# Contact messages
# ============================================================

class ContactMessageListView(ManagementListMixin):
    model = None
    title = "Contact Messages"
    singular = "message"
    plural = "messages"
    search_fields = ["name", "email", "subject", "message"]
    row_url = staticmethod(lambda r: f"/management/contacts/{r.pk}/")

    def get_queryset(self):
        from contact.models import ContactMessage
        qs = ContactMessage.objects.order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "From", "accessor": lambda r: r.name},
            {"label": "Subject", "accessor": lambda r: r.subject},
            {"label": "Status", "accessor": lambda r: r.get_status_display(), "status": True},
            {"label": "Received", "accessor": lambda r: r.created_at.strftime("%Y-%m-%d")},
        ]
        self.statuses = [
            ("", "All statuses"),
            ("new", "New"),
            ("read", "Read"),
            ("replied", "Replied"),
            ("archived", "Archived"),
        ]
        return super().get_context_data(**kwargs)


class ContactMessageDetailView(StaffRequiredMixin, View):
    template_name = "reports/management_contact_detail.html"

    def get(self, request, pk):
        from contact.models import ContactMessage
        msg = get_object_or_404(ContactMessage, pk=pk)
        # Mark as read if it was "new" and the model uses a plain status field
        if getattr(msg, "status", "") == "new":
            msg.status = "read"
            msg.save(update_fields=["status"])
        statuses = [
            ("new", "New"),
            ("read", "Read"),
            ("replied", "Replied"),
            ("archived", "Archived"),
        ]
        return render(request, self.template_name, {
            "msg": msg,
            "statuses": statuses,
        })

    def post(self, request, pk):
        from contact.models import ContactMessage
        msg = get_object_or_404(ContactMessage, pk=pk)
        new_status = request.POST.get("status", "")
        valid_statuses = {"new", "read", "replied", "archived"}
        if new_status in valid_statuses:
            msg.status = new_status
            msg.reply_notes = request.POST.get("reply_notes", msg.reply_notes)
            if new_status == "replied" and hasattr(msg, "replied_at") and not msg.replied_at:
                msg.replied_at = timezone.now()
            msg.save()
            log_action(request, "contact.status_change", target=msg, metadata={"status": new_status})
            messages.success(request, f"Status set to {new_status}.")
        else:
            messages.error(request, "Invalid status.")
        return redirect(f"/management/contacts/{msg.pk}/")

class SiteSettingsView(StaffRequiredMixin, View):
    template_name = "management/settings.html"

    TEXT_FIELDS = [
        "site_name", "tagline",
        "contact_email", "contact_phone", "address", "office_hours", "google_maps_embed",
        "bank_name", "bank_branch", "bank_account_name", "bank_account_number",
        "bank_sort_code", "bank_swift", "bank_iban",
        "mobile_money_name", "mobile_money_number",
        "bank_transfer_instructions",
        "currency", "currency_symbol", "min_donation",
        "preset_amounts_csv", "preset_amounts",
        "facebook_url", "twitter_url", "instagram_url", "linkedin_url", "youtube_url",
        "footer_description", "copyright_text",
        "default_meta_description", "google_analytics_id",
        "about_hero_heading", "about_hero_subheading",
        "mission_heading", "mission_icon", "mission_text",
        "vision_heading", "vision_icon", "vision_text",
        "reach_heading", "reach_icon", "reach_text",
    ]

    FILE_FIELDS = [
        "logo", "logo_light", "favicon", "og_image",
        "about_hero_image", "mission_image", "vision_image", "reach_image",
    ]

    def get(self, request):
        from settings_app.models import SiteConfig
        config, _ = SiteConfig.objects.get_or_create(pk=1)
        return render(request, self.template_name, {
            "config": config,
            "site": config,
            "active_tab": request.GET.get("tab", "identity"),
        })

    def post(self, request):
        from settings_app.models import SiteConfig
        import logging
        logger = logging.getLogger(__name__)

        config, _ = SiteConfig.objects.get_or_create(pk=1)

        # DEBUG
        logger.error(f"[SETTINGS POST] FILES keys: {list(request.FILES.keys())}")
        logger.error(f"[SETTINGS POST] POST keys: {list(request.POST.keys())}")

        changed = []

        for field in self.TEXT_FIELDS:
            if field in request.POST:
                if field == "preset_amounts" and "preset_amounts_csv" in request.POST:
                    continue
                old = getattr(config, field, None)
                new = request.POST.get(field, "")
                if str(old) != str(new):
                    setattr(config, field, new)
                    changed.append(field)

        # FILES with detailed logging
        for field in self.FILE_FIELDS:
            if field in request.FILES:
                uploaded = request.FILES[field]
                logger.error(f"[SETTINGS POST] Saving file {field}: {uploaded.name} ({uploaded.size} bytes)")
                try:
                    setattr(config, field, uploaded)
                    changed.append(field)
                    logger.error(f"[SETTINGS POST] setattr OK for {field}")
                except Exception as e:
                    logger.error(f"[SETTINGS POST] setattr FAILED for {field}: {e}")
                    messages.error(request, f"Could not save {field}: {e}")

        new_maint = "maintenance_mode" in request.POST
        if config.maintenance_mode != new_maint:
            config.maintenance_mode = new_maint
            changed.append("maintenance_mode")

        try:
            config.save()
            logger.error(f"[SETTINGS POST] config.save() OK. Changed: {changed}")
            # Refresh from DB to confirm what's actually stored
            config.refresh_from_db()
            for field in self.FILE_FIELDS:
                val = getattr(config, field)
                logger.error(f"[SETTINGS POST] After save, {field}: {val.name if val else 'empty'}")
        except Exception as e:
            logger.error(f"[SETTINGS POST] config.save() FAILED: {e}")
            messages.error(request, f"Save failed: {e}")

        if changed:
            log_action(request, "settings.update", target=config, metadata={"changed": changed})
            messages.success(request, f"Settings saved. {len(changed)} field(s) updated.")
        else:
            messages.info(request, "No changes to save.")

        active_tab = request.POST.get("active_tab", "identity")
        return redirect(f"/management/settings/?tab={active_tab}")


class AssistanceRequestListView(ManagementListMixin):
    from beneficiaries.models import AssistanceRequest as M
    model = M
    template_name = "reports/management_assistance_list.html"
    title = "Assistance Requests"
    singular = "request"
    plural = "requests"
    search_fields = ["reference", "full_name", "email", "phone"]
    paginate_by = 30
    row_url = staticmethod(lambda r: f"/management/beneficiaries/{r.pk}/")

    def get_queryset(self):
        from beneficiaries.models import AssistanceRequest
        qs = AssistanceRequest.objects.order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        from beneficiaries.models import AssistanceRequest

        self.columns = [
            {"label": "Reference", "accessor": lambda r: r.reference},
            {"label": "Applicant", "accessor": lambda r: r.full_name},
            {"label": "Category", "accessor": lambda r: r.get_category_display(), "muted": True},
            {"label": "Household", "accessor": lambda r: str(r.household_size), "align": "center"},
            {"label": "Status", "accessor": lambda r: r.get_status_display(), "status": True},
            {"label": "Received", "accessor": lambda r: r.created_at.strftime("%Y-%m-%d")},
        ]
        ctx = super().get_context_data(**kwargs)

        # Rebuild rows with explicit URLs — do not rely on the mixin
        rebuilt = []
        for obj in ctx.get("object_list", []):
            cells = []
            for col in self.columns:
                try:
                    val = col["accessor"](obj) if callable(col["accessor"]) else col["accessor"]
                except Exception:
                    val = ""
                cells.append({
                    "value": str(val) if val is not None else "",
                    "align": col.get("align", "left"),
                    "muted": col.get("muted", False),
                    "is_status": col.get("status", False),
                    "status": getattr(obj, "status", ""),
                })
            rebuilt.append({
                "pk": obj.pk,
                "cells": cells,
                # Hardcoded — always a real URL
                "view_url": f"/management/beneficiaries/{obj.pk}/",
                "edit_url": None,
                "delete_url": None,
            })
        ctx["rows"] = rebuilt

        ctx["statuses"] = [("", "All statuses")] + list(AssistanceRequest.Status.choices)
        ctx["status_filter"] = self.request.GET.get("status", "")

        all_qs = AssistanceRequest.objects.all()
        ctx["stats"] = {
            "total": all_qs.count(),
            "submitted": all_qs.filter(status=AssistanceRequest.Status.SUBMITTED).count(),
            "under_review": all_qs.filter(status=AssistanceRequest.Status.UNDER_REVIEW).count(),
            "approved": all_qs.filter(status=AssistanceRequest.Status.APPROVED).count(),
            "delivered": all_qs.filter(status=AssistanceRequest.Status.DELIVERED).count(),
        }

        return ctx



class AssistanceRequestDetailView(StaffRequiredMixin, View):
    template_name = "reports/management_assistance_detail.html"

    def get(self, request, pk):
        from beneficiaries.models import AssistanceRequest
        req = get_object_or_404(AssistanceRequest, pk=pk)
        return render(request, self.template_name, {
            "req": req,
            "statuses": AssistanceRequest.Status.choices,
        })

    def post(self, request, pk):
        from beneficiaries.models import AssistanceRequest
        req = get_object_or_404(AssistanceRequest, pk=pk)
        new_status = request.POST.get("status", "")
        if new_status in AssistanceRequest.Status.values:
            req.status = new_status
            req.reviewer_notes = request.POST.get("reviewer_notes", req.reviewer_notes)
            req.reviewed_by = request.user if request.user.is_authenticated else req.reviewed_by
            req.save()
            log_action(request, "assistance.status_change", target=req,
                       metadata={"status": new_status})
            messages.success(request, f"Status set to {req.get_status_display()}.")
        return redirect(f"/management/beneficiaries/{req.pk}/")



# ============================================================
# Quick photo upload — from the list page
# ============================================================
class LeadershipPhotoUploadView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from pages.models import LeadershipMember
        member = get_object_or_404(LeadershipMember, pk=pk)

        photo = request.FILES.get("photo")
        if not photo:
            messages.error(request, "No file selected.")
            return redirect("/management/leadership/")

        # Basic validation
        if photo.size > 5 * 1024 * 1024:
            messages.error(request, "File too large (max 5 MB).")
            return redirect("/management/leadership/")

        ext = photo.name.rsplit(".", 1)[-1].lower() if "." in photo.name else ""
        if ext not in {"png", "jpg", "jpeg", "webp"}:
            messages.error(request, "Use PNG, JPG, or WEBP.")
            return redirect("/management/leadership/")

        member.photo = photo
        member.save(update_fields=["photo", "updated_at"])
        log_action(request, "leadership.photo_upload", target=member)
        messages.success(request, f"Photo updated for {member.name}.")
        return redirect("/management/leadership/")



# ============================================================
# Hero slide photo upload — from the list page
# ============================================================
class HeroSlidePhotoUploadView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from pages.models import HeroSlide
        slide = get_object_or_404(HeroSlide, pk=pk)

        photo = request.FILES.get("image")
        if not photo:
            messages.error(request, "No file selected.")
            return redirect("/management/hero-slides/")

        if photo.size > 8 * 1024 * 1024:
            messages.error(request, "File too large (max 8 MB).")
            return redirect("/management/hero-slides/")

        ext = photo.name.rsplit(".", 1)[-1].lower() if "." in photo.name else ""
        if ext not in {"png", "jpg", "jpeg", "webp"}:
            messages.error(request, "Use PNG, JPG, or WEBP.")
            return redirect("/management/hero-slides/")

        slide.image = photo
        slide.save(update_fields=["image", "updated_at"])
        log_action(request, "hero_slide.photo_upload", target=slide)
        messages.success(request, f"Image updated for slide '{slide.title or slide.headline or 'Untitled'}'.")
        return redirect("/management/hero-slides/")
