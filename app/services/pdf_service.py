import io
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from bidi.algorithm import get_display
import arabic_reshaper

# Font paths — first check /app/fonts (Docker), then relative path
_BASE = os.path.dirname(__file__)
_CANDIDATES = [
    "/app/fonts",
    os.path.join(_BASE, "../../fonts"),
    os.path.join(_BASE, "../../../fonts"),
]

FONT = None
FONT_B = None
for _d in _CANDIDATES:
    _f = os.path.join(_d, "Vazir.ttf")
    _fb = os.path.join(_d, "Vazir-Bold.ttf")
    if os.path.exists(_f) and os.path.getsize(_f) > 10000:
        FONT = _f
    if os.path.exists(_fb) and os.path.getsize(_fb) > 10000:
        FONT_B = _fb
    if FONT and FONT_B:
        break

_FONTS_REGISTERED = False


def _reg():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    if FONT and FONT_B:
        try:
            pdfmetrics.registerFont(TTFont("Vazir", FONT))
            pdfmetrics.registerFont(TTFont("Vazir-Bold", FONT_B))
            _FONTS_REGISTERED = True
        except Exception as e:
            print(f"[PDF] Font registration failed: {e}")
    else:
        print(f"[PDF] Vazir fonts not found! Searched: {_CANDIDATES}")
        print(f"[PDF] FONT={FONT}, FONT_B={FONT_B}")


def rtl(t: str) -> str:
    if not t:
        return ""
    return get_display(arabic_reshaper.reshape(str(t)))


def _font(bold=False) -> str:
    """Return font name — Vazir if available, else Helvetica."""
    if _FONTS_REGISTERED:
        return "Vazir-Bold" if bold else "Vazir"
    return "Helvetica-Bold" if bold else "Helvetica"


def fmt(n) -> str:
    try:
        return f"{float(n):,.0f} \u062a"
    except Exception:
        return str(n)


def generate_invoice_pdf(inv, company_name: str = "") -> bytes:
    _reg()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm
    )
    fb = _font(bold=True)
    fn = _font(bold=False)
    story = []

    # Header
    ht = Table(
        [[rtl(company_name or "FacTisa Ultra"), rtl(f"شماره فاکتور: {inv.invoice_number}")]],
        colWidths=[9 * cm, 8 * cm]
    )
    ht.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), fb),
        ("FONTSIZE", (0, 0), (-1, -1), 14),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1a1a2e")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [ht, HRFlowable(width="100%", thickness=2, color=colors.HexColor("#4361ee")), Spacer(1, .4 * cm)]

    # Client info
    client_name = inv.client.name if inv.client else "—"
    date_str = str(inv.created_at)[:10] if inv.created_at else "—"
    it = Table([
        [rtl("مشتری:"), rtl(client_name)],
        [rtl("تاریخ:"), rtl(date_str)],
        [rtl("وضعیت:"), rtl(str(inv.status.value if hasattr(inv.status, 'value') else inv.status))],
    ], colWidths=[4 * cm, 13 * cm])
    it.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), fb),
        ("FONTNAME", (1, 0), (1, -1), fn),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [it, Spacer(1, .4 * cm)]

    # Items table
    headers = [rtl("ردیف"), rtl("شرح"), rtl("تعداد"), rtl("واحد"), rtl("قیمت واحد"), rtl("جمع کل")]
    rows = [headers]
    for idx, item in enumerate(inv.items or [], 1):
        rows.append([
            str(idx),
            rtl(item.description or ""),
            str(item.quantity),
            rtl(item.unit or "عدد"),
            fmt(item.unit_price),
            fmt(item.total),
        ])
    tbl = Table(rows, colWidths=[1.2 * cm, 5.5 * cm, 1.8 * cm, 1.8 * cm, 3.2 * cm, 3.5 * cm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), fb),
        ("FONTNAME", (0, 1), (-1, -1), fn),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4361ee")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [tbl, Spacer(1, .5 * cm)]

    # Totals
    subtotal = sum(i.total for i in (inv.items or []))
    discount = inv.discount or 0
    tax_rate = inv.tax_rate or 0
    tax_amount = (subtotal - discount) * tax_rate / 100
    total = subtotal - discount + tax_amount
    paid = sum(p.amount for p in (inv.payments or []))
    remaining = total - paid

    totals = Table([
        [rtl("جمع کل:"), fmt(subtotal)],
        [rtl("تخفیف:"), fmt(discount)],
        [rtl(f"مالیات ({tax_rate}%):"), fmt(tax_amount)],
        [rtl("مبلغ نهایی:"), fmt(total)],
        [rtl("پرداخت شده:"), fmt(paid)],
        [rtl("مانده:"), fmt(remaining)],
    ], colWidths=[5 * cm, 4 * cm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), fb),
        ("FONTNAME", (1, 0), (1, -1), fn),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8edff")),
        ("FONTNAME", (0, -1), (-1, -1), fb),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#4361ee")),
    ]))
    story.append(totals)

    doc.build(story)
    return buf.getvalue()
