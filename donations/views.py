# donations/views.py
from decimal import Decimal
from base64 import b64encode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from audit.services import log_action
from core.models import SiteSetting
from payments.models import PaymentTransaction
from payments.providers import get_provider
from payments.services import record_successful_transaction
from .forms import DonationForm
from .models import Campaign, Donation, Receipt


# ============================================================
# Helpers — read from SiteSetting, not settings.py
# ============================================================
def _bank_details(donation=None, amount="", reference="MAP-PENDING"):
    """
    Return bank details for the donation flow.

    Sourced from SiteSetting so staff can update them via
    /management/settings/ without touching code or redeploying.
    """
    site = SiteSetting.get()

    return {
        "bank_name":      site.bank_name or "",
        "account_name":   site.bank_account_name or "",
        "account_number": site.bank_account_number or "",
        "branch":         site.bank_branch or "",
        "swift":          site.bank_swift or "",
        "iban":           site.bank_iban or "",
        "sort_code":      site.bank_sort_code or "",
        "currency":       (donation.currency if donation
                           else site.currency or "ZMW"),
        "amount":         str(donation.amount) if donation else str(amount),
        "reference":      donation.reference if donation else reference,
    }


def _payment_instructions():
    """Custom instructions staff can set in settings."""
    site = SiteSetting.get()
    return site.bank_transfer_instructions or ""


def _confirmation_hours():
    """How long staff take to confirm a bank transfer."""
    # Not a SiteSetting field yet — use a sensible default
    return 24


def _qr_data_uri(bank):
    """Generate a base64-encoded PNG QR for the bank details."""
    from .utils.bank_qr import make_payment_qr_data, make_qr_png
    payload = make_payment_qr_data(bank)
    png = make_qr_png(payload)
    return f"data:image/png;base64,{b64encode(png).decode()}"


def _donation_context(form, donation=None, amount=""):
    """Shared context for donate + bank_instructions pages."""
    bank = _bank_details(donation=donation, amount=amount)
    return {
        "form": form,
        "donation": donation,                                    # ← ADDED
        "bank": bank,
        "qr_data_uri": _qr_data_uri(bank),
        "payment_instructions": _payment_instructions(),
        "confirmation_hours": _confirmation_hours(),
        "has_bank_details": SiteSetting.get().has_bank_details,
    }

# ============================================================
# Public — Campaigns
# ============================================================
class CampaignListView(ListView):
    model = Campaign
    template_name = "donations/campaigns_list.html"
    context_object_name = "campaigns"
    queryset = Campaign.objects.filter(status=Campaign.Status.ACTIVE)


class CampaignDetailView(DetailView):
    model = Campaign
    template_name = "donations/campaign_detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = Campaign.objects.filter(status=Campaign.Status.ACTIVE)


# ============================================================
# Public — Donate form
# ============================================================
class DonateView(View):
    template_name = "donations/donate.html"

    def get(self, request):
        initial = {}
        if request.GET.get("project"):
            initial["project"] = request.GET["project"]
        if request.GET.get("campaign"):
            initial["campaign"] = request.GET["campaign"]

        form = DonationForm(initial=initial, user=request.user)
        return render(request, self.template_name, _donation_context(form))

    def post(self, request):
        form = DonationForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(
                request, self.template_name, _donation_context(form), status=400,
            )

        d = form.cleaned_data

        # --- Amount guard ---
        try:
            amount = Decimal(str(d.get("amount") or "0"))
        except (ValueError, TypeError):
            amount = Decimal("0")
        if amount <= 0:
            form.add_error("amount", "Please enter an amount greater than zero.")
            return render(request, self.template_name, _donation_context(form))

        # --- Donor identity ---
        is_auth = request.user.is_authenticated
        donor_name = (d.get("donor_name") or "").strip()
        donor_email = (d.get("donor_email") or "").strip()
        donor_phone = (d.get("donor_phone") or "").strip()

        if is_auth:
            donor_name = donor_name or request.user.get_full_name() or request.user.get_username()
            donor_email = donor_email or request.user.email
            donor_phone = donor_phone or getattr(request.user, "phone", "") or ""

        donation = Donation.objects.create(
            donor=request.user if is_auth else None,
            donor_name=donor_name,
            donor_email=donor_email,
            donor_phone=donor_phone,
            is_anonymous=bool(d.get("is_anonymous")),
            kind=d["kind"],
            frequency=d["frequency"],
            amount=amount,
            currency=(SiteSetting.get().currency or "ZMW"),
            campaign=d.get("campaign"),
            project=d.get("project"),
            message=(d.get("message") or "").strip(),
            status=Donation.Status.PENDING,
        )

        donation.bank_reference = donation.reference
        donation.save(update_fields=["bank_reference"])

        log_action(
            request, "donation.create", target=donation,
            metadata={"amount": str(donation.amount), "kind": donation.kind},
        )

        messages.success(
            request,
            "Thank you! Please complete the bank transfer using the details below.",
        )
        return redirect("donations:bank_instructions", reference=donation.reference)


# ============================================================
# Public — Bank instructions after submit
# ============================================================
class BankInstructionsView(View):
    template_name = "donations/bank_instructions.html"

    def get(self, request, reference):
        donation = get_object_or_404(Donation, reference=reference)
        return render(
            request,
            self.template_name,
            _donation_context(form=None, donation=donation),
        )


# ============================================================
# Public — Submit proof of payment
# ============================================================
class SubmitProofView(View):
    template_name = "donations/submit_proof.html"

    def get(self, request, reference):
        donation = get_object_or_404(Donation, reference=reference)
        if donation.status == Donation.Status.RECEIVED:
            messages.info(request, "This donation has already been confirmed.")
            return redirect("donations:thank_you", reference=donation.reference)
        return render(request, self.template_name, {
            "donation": donation,
            "confirmation_hours": _confirmation_hours(),
        })

    def post(self, request, reference):
        donation = get_object_or_404(Donation, reference=reference)
        if donation.status == Donation.Status.RECEIVED:
            messages.info(request, "This donation has already been confirmed.")
            return redirect("donations:thank_you", reference=donation.reference)

        proof = request.FILES.get("proof_of_payment")
        notes = request.POST.get("proof_notes", "").strip()

        if not proof and not notes:
            messages.error(request, "Please upload a proof of payment or add a note.")
            return render(request, self.template_name, {
                "donation": donation,
                "confirmation_hours": _confirmation_hours(),
            })

        if proof:
            if proof.size > 5 * 1024 * 1024:
                messages.error(request, "File is too large (max 5 MB).")
                return render(request, self.template_name, {
                    "donation": donation,
                    "confirmation_hours": _confirmation_hours(),
                })
            ext = proof.name.rsplit(".", 1)[-1].lower() if "." in proof.name else ""
            if ext not in {"png", "jpg", "jpeg", "webp", "pdf"}:
                messages.error(request, "Allowed formats: PNG, JPG, JPEG, WEBP, PDF.")
                return render(request, self.template_name, {
                    "donation": donation,
                    "confirmation_hours": _confirmation_hours(),
                })
            donation.proof_of_payment = proof

        donation.proof_notes = notes
        donation.proof_submitted_at = timezone.now()
        donation.save(update_fields=[
            "proof_of_payment", "proof_notes",
            "proof_submitted_at", "updated_at",
        ])

        log_action(request, "donation.proof_submitted", target=donation)
        messages.success(
            request,
            f"Thank you! Your proof of payment has been received. "
            f"We'll confirm your donation within {_confirmation_hours()} hours.",
        )
        return redirect("donations:thank_you", reference=donation.reference)


# ============================================================
# Public — Thank you
# ============================================================
class ThankYouView(View):
    template_name = "donations/thank_you.html"

    def get(self, request, reference):
        donation = get_object_or_404(
            Donation.objects.select_related("campaign", "project", "donor"),
            reference=reference,
        )
        return render(request, self.template_name, {"donation": donation})


# ============================================================
# Dev — mock payment confirmation
# ============================================================
class ConfirmMockView(View):
    """Dev-only: simulate a successful provider callback for the mock provider."""
    def get(self, request):
        ref = request.GET.get("ref", "")
        txn = PaymentTransaction.objects.filter(provider="mock", provider_reference=ref).first()
        if not txn:
            raise Http404("Unknown payment reference.")
        record_successful_transaction(
            txn,
            raw_response={"status": "success", "provider_reference": ref},
        )
        messages.success(request, "Thank you! Your donation is confirmed.")
        return redirect("donations:thank_you", reference=txn.donation.reference)


# ============================================================
# Donor portal
# ============================================================
class DonorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "donations/portal_dashboard.html"

    def get_context_data(self, **kwargs):
        from datetime import timedelta
        from django.db.models import Sum

        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        donations = user.donations.select_related("campaign", "project")
        received = donations.filter(status=Donation.Status.RECEIVED)

        total_received = (
            received.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        )

        ctx["portal_root"] = "/portal/donor/"
        ctx["donations"] = donations.order_by("-created_at")[:10]
        ctx["total_received"] = total_received
        ctx["count_received"] = received.count()
        ctx["count_pending"] = donations.filter(status=Donation.Status.PENDING).count()

        # Chart 1 — last 6 calendar months
        now = timezone.now()
        buckets = []
        for i in range(5, -1, -1):
            year = now.year
            month = now.month - i
            while month <= 0:
                month += 12
                year -= 1
            start = timezone.datetime(year, month, 1, tzinfo=now.tzinfo)
            if month == 12:
                end = timezone.datetime(year + 1, 1, 1, tzinfo=now.tzinfo)
            else:
                end = timezone.datetime(year, month + 1, 1, tzinfo=now.tzinfo)

            subtotal = (
                received
                .filter(created_at__gte=start, created_at__lt=end)
                .aggregate(t=Sum("amount"))["t"]
                or 0
            )
            buckets.append({"label": start.strftime("%b"), "value": float(subtotal)})

        ctx["chart_donation_data"] = buckets

        # Chart 2 — top campaigns
        campaign_totals = list(
            received
            .values("campaign__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )
        ctx["chart_campaign_data"] = [
            {"label": row["campaign__name"] or "General fund", "value": float(row["total"])}
            for row in campaign_totals
        ] or [{"label": "No donations yet", "value": 0}]

        return ctx


class DonorHistoryView(LoginRequiredMixin, ListView):
    template_name = "donations/portal_history.html"
    context_object_name = "donations"
    paginate_by = 20

    def get_queryset(self):
        return (
            self.request.user.donations
            .select_related("campaign", "project")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["portal_root"] = "/portal/donor/"
        return ctx


# ============================================================
# Receipt download
# ============================================================
class ReceiptDownloadView(LoginRequiredMixin, View):
    """
    Serve a donation receipt as PDF.
    Auto-generates the PDF on first download if it doesn't exist yet.
    """

    def get(self, request, reference):
        donation = get_object_or_404(
            Donation.objects.select_related("donor", "campaign", "project"),
            reference=reference,
        )

        # Permission: owner or staff
        is_owner = donation.donor_id is not None and donation.donor_id == request.user.pk
        is_staff = request.user.is_staff or request.user.is_superuser
        if not (is_owner or is_staff):
            raise Http404("Receipt not found.")

        if donation.status != Donation.Status.RECEIVED:
            raise Http404("Receipt not available — donation has not been received yet.")

        try:
            receipt = donation.receipt
        except Receipt.DoesNotExist:
            raise Http404("Receipt not generated yet.")

        # Serve existing PDF
        if receipt.pdf_file:
            return FileResponse(
                receipt.pdf_file.open("rb"),
                as_attachment=True,
                filename=f"{receipt.number}.pdf",
                content_type="application/pdf",
            )

        # Generate on the fly, save, serve
        from django.core.files.base import ContentFile
        from .receipt_pdf import build_receipt_pdf

        pdf_bytes = build_receipt_pdf(donation, receipt)
        receipt.pdf_file.save(
            f"{receipt.number}.pdf",
            ContentFile(pdf_bytes),
            save=True,
        )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{receipt.number}.pdf"'
        return response