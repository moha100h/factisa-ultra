import io
import os
import logging
from datetime import date, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from bidi.algorithm import get_display
import arabic_reshaper
import jdatetime

logger = logging.getLogger(__name__)

# ---- Font paths (lazy — resolved at first call) ----
_SEARCH_DIRS = [
    "/app/fonts",
    os.path.join(os.path.dirname(__file__), "../../fonts"),
    os.path.join(os.path.dirname(__file__), "../../../fonts"),
    os.path.join(os.getcwd(), "fonts"),
]

_VAZIR: str | None = None
_VAZIR_BOLD: str | None = None
_REGISTERED = False


def _find_font(name: str) -> str | None:
    for d in _SEARCH_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.path.getsize(p) > 50_000:
            return p
    return None


def _register_fonts():
    global _VAZIR, _VAZIR_BOLD, _REGISTERED
    if _REGISTERED:
        return
    # Lazy font discovery
    _VAZIR = _find_font("Vazir.ttf")
    _VAZIR_BOLD = _find_font("Vazir-Bold.ttf")
    logger.info(f"[PDF] Vazir={_VAZIR}  Vazir-Bold={_VAZIR_BOLD}")
    if not _VAZIR or not _VAZIR_BOLD:
        logger.error(f"[PDF] Fonts NOT found! Searched: {_SEARCH_DIRS}")
        return
    try:
        pdfmetrics.registerFont(TTFont("Vazir", _VAZIR))
        pdfmetrics.registerFont(TTFont("Vazir-Bold", _VAZIR_BOLD))
        pdfmetrics.registerFontFamily("Vazir", normal="Vazir", bold="Vazir-Bold")
        _REGISTERED = True
        logger.info("[PDF] Vazir fonts registered OK")
    except Exception as e:
        logger.error(f"[PDF] Font registration error: {e}")


def _fn(bold=False) -> str:
    if _REGISTERED:
        return "Vazir-Bold" if bold else "Vazir"
    return "Helvetica-Bold" if bold else "Helvetica"


# ---- Helpers ----

def rtl(text) -> str:
    """Reshape + bidi for correct Persian/Arabic rendering in PDF."""
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_shamsi(d) -> str:
    """Convert date/datetime/str to Shamsi string like ۱۴۰۴/۰۳/۰۵"""
    try:
        if isinstance(d, str):
            d = d[:10]  # take YYYY-MM-DD part
            d = date.fromisoformat(d)
        elif isinstance(d, datetime):
            d = d.date()
        jd = jdatetime.date.fromgregorian(date=d)
        return jd.strftime("%Y/%m/%d")
    except Exception as e:
        logger.warning(f"[PDF] Shamsi conversion failed: {e}")
        return str(d)[:10] if d else "—"


def fmt_money(n) -> str:
    try:
        return f"{float(n):,.0f}"
    except Exception:
        return str(n)


def _style(bold=False, size=11, align="RIGHT") -> ParagraphStyle:
    _align = {"RIGHT": 2, "LEFT": 0, "CENTER": 1}.get(align, 2)
    return ParagraphStyle(
        name=f"fa_{'b' if bold else 'n'}_{size}_{align}",
        fontName=_fn(bold),
        fontSize=size,
        alignment=_align,
        leading=size * 1.6,
        wordWrap="RTL",
    )


# ---- Main generator ----

def generate_invoice_pdf(inv, company_name: str = "") -> bytes:
    _register_fonts()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    W = 17 * cm
    story = []

    # ── Header ──────────────────────────────────────────────
    hdr = Table([[
        Paragraph(rtl(f"شماره فاکتور: {inv.invoice_number}"), _style(bold=True, size=13, align="LEFT")),
        Paragraph(rtl(company_name or "FacTisa Ultra"), _style(bold=True, size=14, align="RIGHT")),
    ]], colWidths=[W * 0.45, W * 0.55])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(hdr)
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#4361ee"), spaceAfter=8))

    # ── Client info ─────────────────────────────────────────
    client_name = inv.client.name if inv.client else "—"
    date_shamsi = to_shamsi(inv.created_at)
    status_val = inv.status.value if hasattr(inv.status, "value") else str(inv.status)

    info = Table([
        [Paragraph(rtl(client_name), _style(size=11)), Paragraph(rtl("مشتری:"), _style(bold=True, size=11))],
        [Paragraph(rtl(date_shamsi), _style(size=11)),  Paragraph(rtl("تاریخ:"), _style(bold=True, size=11))],
        [Paragraph(rtl(status_val), _style(size=11)),   Paragraph(rtl("وضعیت:"), _style(bold=True, size=11))],
    ], colWidths=[W * 0.7, W * 0.3])
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info)
    story.append(Spacer(1, 0.4 * cm))

    # ── Items table ─────────────────────────────────────────
    col_headers = [
        Paragraph(rtl("جمع کل"),       _style(bold=True, size=10, align="CENTER")),
        Paragraph(rtl("قیمت واحد"),   _style(bold=True, size=10, align="CENTER")),
        Paragraph(rtl("واحد"),         _style(bold=True, size=10, align="CENTER")),
        Paragraph(rtl("تعداد"),        _style(bold=True, size=10, align="CENTER")),
        Paragraph(rtl("شرح"),          _style(bold=True, size=10, align="CENTER")),
        Paragraph(rtl("ردیف"),          _style(bold=True, size=10, align="CENTER")),
    ]
    rows = [col_headers]
    for idx, item in enumerate(inv.items or [], 1):
        rows.append([
            Paragraph(fmt_money(item.total),      _style(size=10, align="CENTER")),
            Paragraph(fmt_money(item.unit_price), _style(size=10, align="CENTER")),
            Paragraph(rtl(item.unit or "عدد"),   _style(size=10, align="CENTER")),
            Paragraph(str(item.quantity),         _style(size=10, align="CENTER")),
            Paragraph(rtl(item.description or ""),_style(size=10, align="RIGHT")),
            Paragraph(str(idx),                   _style(size=10, align="CENTER")),
        ])

    items_tbl = Table(
        rows,
        colWidths=[3.2*cm, 3.0*cm, 1.6*cm, 1.6*cm, 5.6*cm, 1.5*cm],
        repeatRows=1,
    )
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#4361ee")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # ── Totals ───────────────────────────────────────────────
    subtotal   = sum(i.total for i in (inv.items or []))
    discount   = inv.discount or 0
    tax_rate   = inv.tax_rate or 0
    tax_amount = (subtotal - discount) * tax_rate / 100
    total      = subtotal - discount + tax_amount
    paid       = sum(p.amount for p in (inv.payments or []))
    remaining  = total - paid

    totals_tbl = Table([
        [Paragraph(fmt_money(subtotal),   _style(size=11)),            Paragraph(rtl("جمع کل:"),              _style(bold=True, size=11))],
        [Paragraph(fmt_money(discount),   _style(size=11)),            Paragraph(rtl("تخفیف:"),              _style(bold=True, size=11))],
        [Paragraph(fmt_money(tax_amount), _style(size=11)),            Paragraph(rtl(f"مالیات ({tax_rate}%):"), _style(bold=True, size=11))],
        [Paragraph(fmt_money(total),      _style(bold=True, size=12)), Paragraph(rtl("مبلغ نهایی:"),         _style(bold=True, size=12))],
        [Paragraph(fmt_money(paid),       _style(size=11)),            Paragraph(rtl("پرداخت شده:"),        _style(bold=True, size=11))],
        [Paragraph(fmt_money(remaining),  _style(bold=True, size=12)), Paragraph(rtl("مانده:"),              _style(bold=True, size=12))],
    ], colWidths=[4*cm, 4*cm], hAlign="RIGHT")
    totals_tbl.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BACKGROUND",    (0, 3), (-1, 3),  colors.HexColor("#e8edff")),
        ("BACKGROUND",    (0, 5), (-1, 5),  colors.HexColor("#ffe8e8")),
        ("LINEABOVE",     (0, 3), (-1, 3),  1, colors.HexColor("#4361ee")),
        ("LINEBELOW",     (0, 3), (-1, 3),  1, colors.HexColor("#4361ee")),
    ]))
    story.append(totals_tbl)

    # ── Notes ────────────────────────────────────────────────
    if getattr(inv, "notes", None):
        story.append(Spacer(1, 0.4 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Paragraph(rtl(inv.notes), _style(size=10)))

    doc.build(story)
    return buf.getvalue()
