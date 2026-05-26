import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from bidi.algorithm import get_display
import arabic_reshaper, os

FONT = os.path.join(os.path.dirname(__file__), "../../fonts/Vazir.ttf")
FONT_B = os.path.join(os.path.dirname(__file__), "../../fonts/Vazir-Bold.ttf")

def _reg():
    try:
        pdfmetrics.registerFont(TTFont("Vazir", FONT))
        pdfmetrics.registerFont(TTFont("Vazir-Bold", FONT_B))
    except: pass

def rtl(t: str) -> str:
    if not t: return ""
    return get_display(arabic_reshaper.reshape(str(t)))

def generate_invoice_pdf(inv, company_name: str = "") -> bytes:
    _reg()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    f = "Vazir" if os.path.exists(FONT) else "Helvetica"
    fb = "Vazir-Bold" if os.path.exists(FONT_B) else "Helvetica-Bold"
    story = []
    ht = Table([[rtl(company_name or "FacTisa Ultra"), rtl(f"فاکتور: {inv.invoice_number}")]], colWidths=[9*cm,8*cm])
    ht.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),fb),("FONTSIZE",(0,0),(-1,-1),14),
        ("ALIGN",(0,0),(0,0),"LEFT"),("ALIGN",(1,0),(1,0),"RIGHT"),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor("#1a1a2e")),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    story += [ht, HRFlowable(width="100%", thickness=2, color=colors.HexColor("#4361ee")), Spacer(1,.4*cm)]
    it = Table([[rtl("مشتری:"), rtl(inv.client.name if inv.client else "—")],
                [rtl("تاریخ:"), rtl(str(inv.created_at)[:10] if inv.created_at else "—")],
                [rtl("وضعیت:"), rtl(inv.status.value if hasattr(inv.status,"value") else str(inv.status))]],
               colWidths=[4*cm,13*cm])
    it.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),f),("FONTSIZE",(0,0),(-1,-1),11),
        ("ALIGN",(0,0),(-1,-1),"RIGHT"),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story += [it, Spacer(1,.5*cm)]
    rows = [[rtl("ردیف"),rtl("شرح"),rtl("تعداد"),rtl("واحد"),rtl("قیمت"),rtl("جمع")]]
    for i,item in enumerate(inv.items,1):
        rows.append([str(i),rtl(item.description),f"{item.quantity:g}",rtl(item.unit or "عدد"),f"{item.unit_price:,.0f}",f"{item.total:,.0f}"])
    tbl = Table(rows, colWidths=[1.2*cm,7*cm,1.8*cm,1.8*cm,3*cm,3*cm])
    tbl.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),f),("FONTNAME",(0,0),(-1,0),fb),
        ("FONTSIZE",(0,0),(-1,-1),10),("ALIGN",(0,0),(-1,-1),"CENTER"),("ALIGN",(1,1),(1,-1),"RIGHT"),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#4361ee")),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8f9fa")]),
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#dee2e6")),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
    story += [tbl, Spacer(1,.5*cm)]
    tot = Table([[rtl("جمع اقلام:"),f"{inv.subtotal:,.0f}"],[rtl(f"مالیات ({inv.tax_rate}%):"),f"{inv.tax_amount:,.0f}"],
                 [rtl("تخفیف:"),f"{inv.discount:,.0f}"],[rtl("مبلغ نهایی:"),f"{inv.total:,.0f}"],
                 [rtl("پرداخت شده:"),f"{inv.paid_amount:,.0f}"],[rtl("مانده:"),f"{inv.remaining:,.0f}"]],
                colWidths=[5*cm,5*cm], hAlign="RIGHT")
    tot.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),f),("FONTNAME",(0,3),(-1,3),fb),("FONTNAME",(0,5),(-1,5),fb),
        ("FONTSIZE",(0,0),(-1,-1),11),("FONTSIZE",(0,3),(-1,3),13),("ALIGN",(0,0),(-1,-1),"RIGHT"),
        ("BACKGROUND",(0,3),(-1,3),colors.HexColor("#4361ee")),("TEXTCOLOR",(0,3),(-1,3),colors.white),
        ("BACKGROUND",(0,5),(-1,5),colors.HexColor("#e63946")),("TEXTCOLOR",(0,5),(-1,5),colors.white),
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#dee2e6")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story.append(tot)
    doc.build(story)
    return buf.getvalue()
