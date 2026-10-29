# payments/providers.py
"""
Provider interface. Real providers (mobile money / bank) implement this
same interface and are wired through settings.PAYMENT_PROVIDER.
"""
import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class InitResult:
    provider_reference: str
    redirect_url: str | None = None
    instructions: str = ""


class BaseProvider:
    name = "base"

    def initiate(self, *, donation, amount: Decimal, currency: str, return_url: str) -> InitResult:
        raise NotImplementedError

    def verify(self, *, provider_reference: str) -> dict:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """Deterministic mock. 'Success' simulated via the return URL."""
    name = "mock"

    def initiate(self, *, donation, amount: Decimal, currency: str, return_url: str) -> InitResult:
        ref = "MOCK-" + uuid.uuid4().hex[:12].upper()
        return InitResult(
            provider_reference=ref,
            redirect_url=return_url + f"?ref={ref}",
            instructions="This is a development mock. No real money is moved.",
        )

    def verify(self, *, provider_reference: str) -> dict:
        return {"provider_reference": provider_reference, "status": "success", "raw": {"provider": "mock"}}


class ManualProvider(BaseProvider):
    """Bank transfer / manual confirmation — a staff member reconciles."""
    name = "manual"

    def initiate(self, *, donation, amount: Decimal, currency: str, return_url: str) -> InitResult:
        ref = donation.reference
        return InitResult(
            provider_reference=ref,
            redirect_url=None,
            instructions=(
                "Bank Transfer: Mission Against Poverty, Account #XXXXXXXX, "
                f"Reference: {ref}. Please send proof of payment to finance@map.org. "
                "A staff member will confirm and issue a receipt."
            ),
        )

    def verify(self, *, provider_reference: str) -> dict:
        raise NotImplementedError("Manual transfers require staff verification in the admin.")


def get_provider(name: str) -> BaseProvider:
    from django.conf import settings
    name = name or settings.PAYMENT_PROVIDER
    if name == "mock":
        return MockProvider()
    if name == "manual":
        return ManualProvider()
    raise ValueError(f"Unknown payment provider: {name}")
