import io
import os
import logging
from datetime import date
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

# ---- Font discovery ----
_SEARCH_DIRS = [
    "/app/fonts",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../fonts"),
    os.path.join(os.getcwd(), "fonts"),
]

def _find(name: str):
    for d in _SEARCH_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.path.getsize(p) > 50_000:
            logger.info(f"[PDF] Found {name} at {p} ({os.path.getsize(p)} bytes)")
            return p
    logger.error(f"[PDF] {name} NOT found in {_SEARCH_DIRS}")
    return None

_VAZIR      = _find("Vazir.ttf")
_VAZIR_BOLD = _find("Vazir-Bold.ttf")
_REGISTERED = False


def _register():
    global _REGISTERED
    if _REGISTERED:
        return True
    if not _VAZIR or not _VAZIR_BOLD:
        logger.error("[PDF] Cannot register fonts — files missing")
        return False
    try:
        pdfmetrics.registerFont(TTFont("Vazir",      _VAZIR))
        pdfmetrics.registerFont(TTFont("Vazir-Bold", _VAZIR_BOLD))
        pdfmetrics.registerFontFamily("Vazir", normal="Vazir", bold="Vazir-Bold")
        _REGISTERED = True
        logger.info("[PDF] Vazir fonts registered OK")
        return True
    except Exception as e:
        logger.error(f"[PDF] Font registration failed: {e}")
        return False


def _fn(bold=False) -> str:
    if _REGISTERED:
        return "Vazir-Bold" if bold else "Vazir"
    return "Helvetica-Bold" if bold else "Helvetica"


def rtl(text) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_jalali(d) -> str:
    """Convert date/datetime/str to Jalali string like 1403/02/15"""
    try:
        if isinstance(d, str):
            d = date.fromisoformat(d[:10])
        jd = jdatetime.date.fromgregorian(date=d)
        return jd.strftime("%Y/%m/%d")
    except Exception:
        return str(d)[:10] if d else "—"


def fmt_money(n) -> str:
    try:
        return f"{float(n):,.0f}"
    except Exception:
        return str(n)


def _style(bold=False, size=11, align="RIGHT") -> ParagraphStyle:
    al = {"RIGHT": 2, "LEFT": 0, "CENTER": 1}.get(align, 2)
    return ParagraphStyle(
        name=f"fa_{bold}_{size}_{align}",
        fontName=_fn(bold),
        fontSize=size,
        alignment=al,
        leading=size * 1.7,
        wordWrap="RTL",
        textColor=colors.HexColor("#1a1a2e"),
    )


def P(text, bold=False, size=11, align="RIGHT") -> Paragraph:
    return Paragraph(rtl(str(text)), _style(bold, size, align))


def generate_invoice_pdf(inv, company_name: str = "") -> bytes:
    ok = _register()
    if not ok:
        logger.warning("[PDF] Generating with fallback Helvetica font")

    buf = io.BytesIO()
    W = 17 * cm
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []

    # ── Header ──────────────────────────────────────────────────
    h = Table([[
        P(f"شماره فاکتور: {inv.invoice_number}", bold=True, size=12, align="LEFT"),
        P(company_name or "FacTisa Ultra", bold=True, size=14, align="RIGHT"),
    ]], colWidths=[W*0.45, W*0.55])
    h.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story += [
        h,
        HRFlowable(width="100%", thickness=2,
                   color=colors.HexColor("#4361ee"), spaceAfter=8),
    ]

    # ── Client info ─────────────────────────────────────────────
    client_name = inv.client.name if inv.client else "—"
    date_jalali = to_jalali(inv.created_at)
    status_val  = inv.status.value if hasattr(inv.status, "value") else str(inv.status)

    info = Table([
        [P(client_name, size=11),   P("مشتری:",  bold=True, size=11)],
        [P(date_jalali, size=11),   P("تاریخ:",  bold=True, size=11)],
        [P(status_val,  size=11),   P("وضعیت:",  bold=True, size=11)],
    ], colWidths=[W*0.72, W*0.28])
    info.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
    ]))
    story += [info, Spacer(1, 0.4*cm)]

    # ── Items table ─────────────────────────────────────────────
    headers = [
        P("جمع کل",      bold=True, size=10, align="CENTER"),
        P("قیمت واحد",  bold=True, size=10, align="CENTER"),
        P("واحد",        bold=True, size=10, align="CENTER"),
        P("تعداد",       bold=True, size=10, align="CENTER"),
        P("شرح",         bold=True, size=10, align="CENTER"),
        P("ردیف",         bold=True, size=10, align="CENTER"),
    ]
    rows = [headers]
    for i, item in enumerate(inv.items or [], 1):
        rows.append([
            P(fmt_money(item.total),      size=10, align="CENTER"),
            P(fmt_money(item.unit_price), size=10, align="CENTER"),
            P(item.unit or "عدد",        size=10, align="CENTER"),
            P(str(item.quantity),         size=10, align="CENTER"),
            P(item.description or "",     size=10, align="RIGHT"),
            P(str(i),                     size=10, align="CENTER"),
        ])

    tbl = Table(rows,
                colWidths=[3.2*cm, 3.0*cm, 1.6*cm, 1.6*cm, 5.6*cm, 1.5*cm],
                repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#4361ee")),
        ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0f4ff")]),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
    ]))
    story += [tbl, Spacer(1, 0.5*cm)]

    # ── Totals ───────────────────────────────────────────────────
    subtotal   = sum(i.total for i in (inv.items or []))
    discount   = inv.discount  or 0
    tax_rate   = inv.tax_rate  or 0
    tax_amount = (subtotal - discount) * tax_rate / 100
    total      = subtotal - discount + tax_amount
    paid       = sum(p.amount for p in (inv.payments or []))
    remaining  = total - paid

    tot = Table([
        [P(fmt_money(subtotal),   size=11),        P("جمع کل:",              bold=True, size=11)],
        [P(fmt_money(discount),   size=11),        P("تخفیف:",              bold=True, size=11)],
        [P(fmt_money(tax_amount), size=11),        P(f"مالیات ({tax_rate}%):", bold=True, size=11)],
        [P(fmt_money(total),      bold=True, size=12), P("مبلغ نهایی:",       bold=True, size=12)],
        [P(fmt_money(paid),       size=11),        P("پرداخت شده:",       bold=True, size=11)],
        [P(fmt_money(remaining),  bold=True, size=12), P("مانده:",              bold=True, size=12)],
    ], colWidths=[4*cm, 4.5*cm], hAlign="RIGHT")
    tot.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "RIGHT"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BACKGROUND",    (0,3),(-1,3),  colors.HexColor("#e8edff")),
        ("BACKGROUND",    (0,5),(-1,5),  colors.HexColor("#ffe8e8")),
        ("LINEABOVE",     (0,3),(-1,3),  1, colors.HexColor("#4361ee")),
        ("LINEBELOW",     (0,3),(-1,3),  1, colors.HexColor("#4361ee")),
    ]))
    story.append(tot)

    if getattr(inv, "notes", None):
        story += [
            Spacer(1, 0.4*cm),
            HRFlowable(width="100%", thickness=0.5, color=colors.grey),
            P(inv.notes, size=10),
        ]

    doc.build(story)
    return buf.getvalue()
