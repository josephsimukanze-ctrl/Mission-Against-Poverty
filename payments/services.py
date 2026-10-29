# payments/services.py
"""
All payment state transitions flow through this module.

Invariant enforced here (and only here):
    A Donation becomes RECEIVED if and only if a verified PaymentTransaction
    is recorded as SUCCESS with a matching amount & currency.
"""
import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction as db_tx
from django.utils import timezone

from .models import PaymentTransaction, PaymentWebhookEvent
from donations.models import Donation, Receipt

logger = logging.getLogger(__name__)


class PaymentVerificationError(Exception):
    """Raised when a transaction fails verification rules."""

    def __init__(self, message: str, *, code: str = "verification_failed"):
        super().__init__(message)
        self.code = code


# ============================================================
# Receipt generation
# ============================================================
def _issue_receipt(donation: Donation) -> Receipt:
    """
    Create a Receipt for `donation` if one doesn't exist.

    Idempotent — safe to call any number of times, including when the
    donation was already marked RECEIVED before this code existed.
    """
    existing = Receipt.objects.filter(donation=donation).first()
    if existing:
        return existing

    number = f"RCP-{donation.reference}"
    try:
        return Receipt.objects.create(donation=donation, number=number)
    except Exception:
        # Race condition: another worker created it between filter and create
        retry = Receipt.objects.filter(donation=donation).first()
        if retry:
            return retry
        raise


# ============================================================
# Success path
# ============================================================
def record_successful_transaction(
    txn: PaymentTransaction,
    *,
    raw_response: Optional[dict] = None,
) -> PaymentTransaction:
    """
    Called ONLY from a verified callback / webhook OR from an authorized
    manual reconciliation view. This is the sole path that can set
    Donation.status = RECEIVED.
    """
    with db_tx.atomic():
        # Lock order: txn → donation (matches FK direction; prevents deadlocks)
        txn = PaymentTransaction.objects.select_for_update().get(pk=txn.pk)
        donation = Donation.objects.select_for_update().get(pk=txn.donation_id)

        # ---- Idempotency ----
        if txn.status == PaymentTransaction.Status.SUCCESS:
            # Backfill guard: if a previous attempt marked the txn SUCCESS but
            # never created the receipt (e.g. code shipped after data existed),
            # create it now without touching the txn again.
            if not Receipt.objects.filter(donation=donation).exists():
                _issue_receipt(donation)
                logger.info(
                    "Backfilled missing receipt for donation %s",
                    donation.reference,
                )
            return txn

        # ---- Amount / currency verification ----
        txn_amount = txn.amount or Decimal("0")
        don_amount = donation.amount or Decimal("0")
        if txn_amount != don_amount:
            raise PaymentVerificationError(
                f"Amount mismatch for {donation.reference}: "
                f"txn={txn_amount} {txn.currency}, "
                f"donation={don_amount} {donation.currency}",
                code="amount_mismatch",
            )
        if (txn.currency or "").upper() != (donation.currency or "").upper():
            raise PaymentVerificationError(
                f"Currency mismatch for {donation.reference}: "
                f"txn={txn.currency}, donation={donation.currency}",
                code="currency_mismatch",
            )

        # ---- Transition transaction ----
        txn.status = PaymentTransaction.Status.SUCCESS
        txn.verified_at = timezone.now()
        if raw_response is not None:
            txn.raw_response = raw_response
        txn.save(update_fields=[
            "status", "verified_at", "raw_response", "updated_at",
        ])

        # ---- Transition donation ----
        if donation.status != Donation.Status.RECEIVED:
            donation.status = Donation.Status.RECEIVED
            donation.save(update_fields=["status", "updated_at"])

        # ---- Generate receipt ----
        _issue_receipt(donation)

        logger.info(
            "Donation %s marked RECEIVED via txn %s (provider=%s)",
            donation.reference, txn.pk, txn.provider,
        )
        return txn


# ============================================================
# Failure path
# ============================================================
def record_failed_transaction(
    txn: PaymentTransaction,
    *,
    reason: str = "",
    raw_response: Optional[dict] = None,
) -> PaymentTransaction:
    """
    Mark a transaction as FAILED. Will not downgrade a SUCCESS transaction,
    and will not downgrade a donation that's already RECEIVED.
    """
    with db_tx.atomic():
        txn = PaymentTransaction.objects.select_for_update().get(pk=txn.pk)

        # Never downgrade a successful transaction
        if txn.status == PaymentTransaction.Status.SUCCESS:
            logger.info(
                "Ignoring failure for txn %s — already SUCCESS", txn.pk,
            )
            return txn

        txn.status = PaymentTransaction.Status.FAILED
        if raw_response is not None:
            txn.raw_response = {**(raw_response or {}), "_reason": reason}
        txn.save(update_fields=["status", "raw_response", "updated_at"])

        # Only fail a donation that's still pending
        updated = (
            Donation.objects
            .filter(pk=txn.donation_id, status=Donation.Status.PENDING)
            .update(status=Donation.Status.FAILED)
        )

        logger.info(
            "Transaction %s marked FAILED (%s); donation updated=%s",
            txn.pk, reason or "unknown", bool(updated),
        )
        return txn


# ============================================================
# Webhook processing
# ============================================================
# Status vocabularies grouped by semantic meaning.
_SUCCESS_STATUSES = {"success", "succeeded", "completed", "paid", "captured"}
_FAILED_STATUSES  = {"failed", "cancelled", "canceled", "declined", "expired"}


def process_webhook(
    provider: str,
    event_type: str,
    idempotency_key: str,
    payload: dict,
) -> PaymentWebhookEvent:
    """
    Idempotent entry point for inbound webhooks.

    Returns the PaymentWebhookEvent instance. Idempotency is enforced by
    `idempotency_key` — a repeated call with the same key returns the
    existing event without re-processing.
    """
    event, created = PaymentWebhookEvent.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "provider": provider,
            "event_type": event_type,
            "payload": payload,
        },
    )

    if not created and event.processed:
        logger.debug(
            "Webhook %s already processed, skipping", idempotency_key,
        )
        return event

    try:
        provider_ref = payload.get("provider_reference", "")
        status = str(payload.get("status", "")).lower()

        if not provider_ref:
            raise PaymentVerificationError(
                "Webhook payload missing provider_reference",
                code="missing_reference",
            )

        txn = (
            PaymentTransaction.objects
            .filter(provider=provider, provider_reference=provider_ref)
            .first()
        )
        if not txn:
            raise PaymentVerificationError(
                f"No transaction found for provider={provider} ref={provider_ref}",
                code="unknown_transaction",
            )

        event.transaction = txn

        if status in _SUCCESS_STATUSES:
            record_successful_transaction(txn, raw_response=payload)
        elif status in _FAILED_STATUSES:
            record_failed_transaction(txn, reason=status, raw_response=payload)
        else:
            # Unknown status — log but don't fail. The webhook may be for a
            # state we don't care about (e.g. `authorized`, `processing`).
            logger.warning(
                "Webhook %s has unhandled status %r — marking processed",
                idempotency_key, status,
            )

        event.processed = True
        event.save(update_fields=[
            "processed", "transaction", "processing_error",
        ])

    except PaymentVerificationError as e:
        # Expected verification failures — record but don't crash the webhook
        logger.warning(
            "Webhook %s failed verification: %s (code=%s)",
            idempotency_key, e, getattr(e, "code", "?"),
        )
        event.processing_error = str(e)
        event.save(update_fields=["processing_error", "transaction"])
        raise

    except Exception as e:
        # Unexpected error — record, log with traceback, and re-raise so the
        # provider retries (or the caller can surface it).
        logger.exception(
            "Webhook %s failed unexpectedly", idempotency_key,
        )
        event.processing_error = str(e)
        event.save(update_fields=["processing_error", "transaction"])
        raise

    return event