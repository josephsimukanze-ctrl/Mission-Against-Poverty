"""QR-code generator for bank transfer details (no gateway API available)."""
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def make_payment_qr_data(bank_details: dict) -> str:
    """Build the text payload that a banking app will read from the QR code.

    Format: a semi-structured string that Zambian banks and mobile-money apps
    (MTN MoMo, Airtel Money, ZANACO, Stanbic etc.) can parse. This is not the
    EMVCo standard QR (which requires merchant onboarding) — it's a
    widely-used pattern of "Account: xxx | Amount: yyy | Reference: zzz"
    that most apps display and let the user copy.
    """
    lines = [
        f"BANK:{bank_details.get('bank_name', '')}",
        f"ACCOUNT_NAME:{bank_details.get('account_name', '')}",
        f"ACCOUNT_NO:{bank_details.get('account_number', '')}",
        f"BRANCH:{bank_details.get('branch', '')}",
        f"AMOUNT:{bank_details.get('amount', '')}",
        f"CURRENCY:{bank_details.get('currency', 'ZMW')}",
        f"REFERENCE:{bank_details.get('reference', '')}",
    ]
    return "\n".join(lines)


def make_qr_png(payload: str, size: int = 280) -> bytes:
    """Return a PNG image as bytes for the given payload."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
