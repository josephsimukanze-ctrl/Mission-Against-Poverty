# newsletter/views.py
from django.contrib import messages
from django.shortcuts import redirect
from django.views import View

from .models import NewsletterSubscriber
from .forms import CampaignForm, SubscriberForm

class SubscribeView(View):
    """
    Handle POST from the public footer signup form.
    Also accepts ?redirect=... to return to a custom URL after subscribing.
    """

    def post(self, request):
        email = (request.POST.get("email") or "").strip().lower()
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

        if not email:
            messages.error(request, "Please enter your email address.")
            return redirect(next_url)

        sub, created = NewsletterSubscriber.objects.get_or_create(
            email=email,
            defaults={
                "status": "active",
                "source": request.POST.get("source", "footer"),
                "ip_address": self._client_ip(request),
                "user": request.user if request.user.is_authenticated else None,
            },
        )

        if created:
            messages.success(request, "Thanks for subscribing! You'll hear from us soon.")
        elif sub.status == "unsubscribed":
            sub.reactivate()
            messages.success(request, "Welcome back — you're subscribed again.")
        elif sub.status == "active":
            messages.info(request, "You're already on our list.")
        else:
            messages.info(request, "We already have your email on file.")

        return redirect(next_url)

    @staticmethod
    def _client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


# newsletter/management_views.py
from reports.views import (
    ManagementListMixin,
    GenericCreateView,
    GenericUpdateView,
    GenericDeleteView,
)
from .models import NewsletterSubscriber, NewsletterCampaign
from .forms import CampaignForm


# ============================================================
# Subscribers
# ============================================================
class SubscriberListView(ManagementListMixin):
    model = NewsletterSubscriber
    title = "Newsletter Subscribers"
    singular = "subscriber"
    plural = "subscribers"
    search_fields = ["email", "name", "source"]
    add_url = None
    delete_url = staticmethod(lambda r: f"/management/newsletter/{r.pk}/delete/")

    def get_queryset(self):
        qs = super().get_queryset().order_by("-created_at")
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "Email", "accessor": lambda r: r.email, "width": "auto"},
            {"label": "Name", "accessor": lambda r: r.name or "—", "muted": True, "width": "180px"},
            {"label": "Source", "accessor": lambda r: r.source or "—", "muted": True, "width": "140px"},
            {
                "label": "Status",
                "accessor": lambda r: r.get_status_display(),
                "status": True,
                "width": "140px",
            },
            {
                "label": "Subscribed",
                "accessor": lambda r: r.created_at.strftime("%Y-%m-%d"),
                "width": "130px",
            },
        ]
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = [("", "All statuses")] + list(NewsletterSubscriber.STATUS_CHOICES)
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


class SubscriberDeleteView(GenericDeleteView):
    model = NewsletterSubscriber
    singular = "subscriber"
    success_url = "/management/newsletter/"


# ============================================================
# Campaigns
# ============================================================
class CampaignListView(ManagementListMixin):
    model = NewsletterCampaign
    title = "Newsletter Campaigns"
    singular = "campaign"
    plural = "campaigns"
    search_fields = ["name", "subject"]
    add_url = "/management/newsletter/campaigns/new/"
    edit_url = staticmethod(lambda r: f"/management/newsletter/campaigns/{r.pk}/edit/")
    delete_url = staticmethod(lambda r: f"/management/newsletter/campaigns/{r.pk}/delete/")

    def get_queryset(self):
        return super().get_queryset().order_by("-created_at")

    def get_context_data(self, **kwargs):
        self.columns = [
            {"label": "NewsletterCampaign", "accessor": lambda r: r.name, "width": "auto"},
            {"label": "Subject", "accessor": lambda r: r.subject or "—", "muted": True, "width": "260px"},
            {
                "label": "Status",
                "accessor": lambda r: r.get_status_display(),
                "status": True,
                "width": "120px",
            },
            {
                "label": "Recipients",
                "accessor": lambda r: str(r.recipient_count),
                "align": "right",
                "width": "110px",
            },
            {
                "label": "Sent",
                "accessor": lambda r: r.sent_at.strftime("%Y-%m-%d") if r.sent_at else "—",
                "width": "130px",
            },
        ]
        return super().get_context_data(**kwargs)


class CampaignCreateView(GenericCreateView):
    model = NewsletterCampaign
    form_class = CampaignForm
    singular = "campaign"
    success_url = "/management/newsletter/campaigns/"


class CampaignUpdateView(GenericUpdateView):
    model = NewsletterCampaign
    form_class = CampaignForm
    singular = "campaign"
    success_url = "/management/newsletter/campaigns/"


class CampaignDeleteView(GenericDeleteView):
    model = NewsletterCampaign
    singular = "campaign"
    success_url = "/management/newsletter/campaigns/"