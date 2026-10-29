# donations/receipt_pdf.py
"""
Generate a professional PDF receipt for a Donation.

Uses ReportLab's Platypus layout — flowing content, automatic page breaks,
and proper structure for archival / tax purposes.
"""
import io
from decimal import Decimal

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ------------------------------------------------------------
# Amount in words
# ------------------------------------------------------------
_ONES = (
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen",
    "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
)
_TENS = (
    "", "", "Twenty", "Thirty", "Forty", "Fifty",
    "Sixty", "Seventy", "Eighty", "Ninety",
)

_CURRENCY_WORDS = {
    "ZMW": ("Kwacha", "Ngwee"),
    "USD": ("Dollar", "Cent"),
    "EUR": ("Euro", "Cent"),
    "GBP": ("Pound", "Penny"),
    "KES": ("Shilling", "Cent"),
    "ZAR": ("Rand", "Cent"),
}


def _number_to_words(n):
    """Convert an integer 0–999,999,999 to English words."""
    if n == 0:
        return "Zero"
    if n < 0:
        return "Minus " + _number_to_words(-n)

    parts = []

    if n >= 1_000_000:
        millions = n // 1_000_000
        parts.append(f"{_number_to_words(millions)} Million")
        n %= 1_000_000

    if n >= 1_000:
        thousands = n // 1_000
        parts.append(f"{_number_to_words(thousands)} Thousand")
        n %= 1_000

    if n >= 100:
        hundreds = n // 100
        parts.append(f"{_ONES[hundreds]} Hundred")
        n %= 100

    if n >= 20:
        tens, ones = divmod(n, 10)
        parts.append(f"{_TENS[tens]}{(' ' + _ONES[ones]) if ones else ''}")
    elif n > 0:
        parts.append(_ONES[n])

    return " ".join(parts)


def amount_to_words(amount, currency):
    """
    Convert a Decimal amount to natural language.

    Examples:
        250.00 ZMW   → "Two Hundred Fifty Kwacha Only"
        1250.50 USD  → "One Thousand Two Hundred Fifty Dollars and Fifty Cents"
    """
    major_word, minor_word = _CURRENCY_WORDS.get(
        (currency or "").upper(), (currency or "Units", "Cents")
    )

    try:
        amount = Decimal(str(amount))
    except Exception:
        return f"{amount} {currency}"

    integer_part = int(amount)
    fraction = int((amount - integer_part) * 100)

    words = f"{_number_to_words(integer_part)} {major_word}"
    if integer_part != 1 and not major_word.endswith("s"):
        words += "s"      # Kwacha → Kwachas, Dollar → Dollars

    if fraction > 0:
        words += f" and {_number_to_words(fraction)} {minor_word}"
        if fraction != 1 and not minor_word.endswith("s"):
            words += "s"
    else:
        words += " Only"

    return words


# ------------------------------------------------------------
# PDF builder
# ------------------------------------------------------------
# Brand colors — match your site
BRAND_NAVY  = colors.HexColor("#16253d")
BRAND_GREEN = colors.HexColor("#1e9e5f")
BRAND_GRAY  = colors.HexColor("#64748b")
BRAND_LIGHT = colors.HexColor("#f5f7fa")
BRAND_BORDER = colors.HexColor("#e5e9f0")


def _get_method_label(donation):
    """Determine how the donation was paid, from linked transactions."""
    txn = donation.transactions.order_by("-created_at").first()
    if not txn:
        return "Manual entry"

    provider = (txn.provider or "").lower()
    return {
        "manual":         "Bank transfer / Manual reconciliation",
        "bank":           "Bank transfer",
        "bank_transfer":  "Bank transfer",
        "mobile_money":   "Mobile money",
        "airtel":         "Airtel Money",
        "mtn":            "MTN Mobile Money",
        "zamtel":         "Zamtel Money",
        "cash":           "Cash",
        "stripe":         "Card (Stripe)",
        "paypal":         "PayPal",
    }.get(provider, provider.title() or "Unknown")


def build_receipt_pdf(donation, receipt):
    """
    Return the bytes of a fully formatted PDF receipt for `donation`.
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"Receipt {receipt.number}",
        author="Mission Against Poverty",
        subject="Official Donation Receipt",
    )

    styles = getSampleStyleSheet()

    # --- Styles ---
    org_style = ParagraphStyle(
        "org", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=18,
        textColor=BRAND_NAVY, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9.5,
        textColor=BRAND_GRAY, spaceAfter=12,
    )
    title_style = ParagraphStyle(
        "title", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=14,
        textColor=BRAND_NAVY, alignment=TA_CENTER, spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "subtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10,
        textColor=BRAND_GRAY, alignment=TA_CENTER, spaceAfter=14,
    )
    label_style = ParagraphStyle(
        "label", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=9,
        textColor=BRAND_GRAY, spaceAfter=2,
    )
    value_style = ParagraphStyle(
        "value", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10.5,
        textColor=BRAND_NAVY, spaceAfter=2,
    )
    amount_style = ParagraphStyle(
        "amount", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=22,
        textColor=BRAND_NAVY, spaceAfter=4,
    )
    words_style = ParagraphStyle(
        "words", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=10,
        textColor=BRAND_GRAY, spaceAfter=4,
    )
    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"],
        fontName="Helvetica", fontSize=8.5,
        textColor=BRAND_GRAY, alignment=TA_CENTER,
    )
    thanks_style = ParagraphStyle(
        "thanks", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=11,
        textColor=BRAND_GREEN, alignment=TA_CENTER, spaceAfter=8,
    )

    elements = []

    # --- Header: brand bar ---
    header = Table(
        [[
            Paragraph(
                '<font color="#ffffff"><b>♥</b></font>'
                '&nbsp;&nbsp;'
                '<font color="#ffffff"><b>MISSION AGAINST POVERTY</b></font>',
                ParagraphStyle(
                    "hdr", fontName="Helvetica-Bold", fontSize=13,
                    textColor=colors.white, alignment=TA_LEFT,
                ),
            ),
        ]],
        colWidths=[doc.width],
        rowHeights=[12 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
        ]),
    )
    elements.append(header)
    elements.append(Spacer(1, 6 * mm))

    # --- Title ---
    elements.append(Paragraph("Official Donation Receipt", title_style))
    elements.append(Paragraph(
        "This receipt acknowledges a charitable contribution "
        "to Mission Against Poverty.",
        subtitle_style,
    ))

    # --- Amount banner ---
    amount_display = f"{donation.amount:,.2f} {donation.currency}"
    words = amount_to_words(donation.amount, donation.currency)

    amount_table = Table(
        [[
            Paragraph(amount_display, amount_style),
        ], [
            Paragraph(words, words_style),
        ]],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ]),
    )
    elements.append(amount_table)
    elements.append(Spacer(1, 8 * mm))

    # --- Details grid (two columns) ---
    method = _get_method_label(donation)

    detail_rows = [
        ("Receipt Number", receipt.number),
        ("Reference",       donation.reference),
        ("Date Issued",     receipt.issued_at.strftime("%B %d, %Y · %H:%M")),
        ("Status",          donation.get_status_display()),
        ("Donation Type",   donation.get_kind_display()),
        ("Frequency",       donation.get_frequency_display()),
        ("Payment Method",  method),
    ]
    if donation.bank_reference:
        detail_rows.append(("Bank Reference", donation.bank_reference))

    detail_data = [
        [
            Paragraph(f"<b>{label}</b>", label_style),
            Paragraph(str(value), value_style),
        ]
        for label, value in detail_rows
    ]

    detail_table = Table(
        detail_data,
        colWidths=[45 * mm, doc.width - 45 * mm],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, -2), 0.25, BRAND_BORDER),
        ]),
    )
    elements.append(detail_table)
    elements.append(Spacer(1, 6 * mm))

    # --- Donor block ---
    elements.append(Paragraph("Donor", label_style))
    donor_lines = []
    if donation.is_anonymous:
        donor_lines.append("<i>Anonymous</i>")
    else:
        donor_lines.append(f"<b>{donation.donor_name or 'Not provided'}</b>")
        if donation.donor_email:
            donor_lines.append(donation.donor_email)
        if donation.donor_phone:
            donor_lines.append(donation.donor_phone)

    donor_table = Table(
        [[Paragraph("<br/>".join(donor_lines), value_style)]],
        colWidths=[doc.width],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]),
    )
    elements.append(donor_table)
    elements.append(Spacer(1, 6 * mm))

    # --- Allocation ---
    allocation_rows = []
    if donation.campaign:
        allocation_rows.append(("Campaign", donation.campaign.name))
    if donation.project:
        allocation_rows.append(("Project", donation.project.name))

    if allocation_rows:
        elements.append(Paragraph("Allocation", label_style))
        alloc_data = [
            [
                Paragraph(f"<b>{label}</b>", label_style),
                Paragraph(str(value), value_style),
            ]
            for label, value in allocation_rows
        ]
        alloc_table = Table(
            alloc_data,
            colWidths=[45 * mm, doc.width - 45 * mm],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]),
        )
        elements.append(alloc_table)
        elements.append(Spacer(1, 8 * mm))

    # --- Divider + thank you ---
    elements.append(HRFlowable(
        width="100%", thickness=0.5, color=BRAND_BORDER,
        spaceBefore=4 * mm, spaceAfter=6 * mm,
    ))
    elements.append(Paragraph(
        "Thank you for supporting our mission.", thanks_style,
    ))
    elements.append(Paragraph(
        "Mission Against Poverty · Lusaka, Zambia · info@map.org<br/>"
        "This is a computer-generated receipt. No signature required.",
        footer_style,
    ))

    doc.build(elements)
    return buf.getvalue()