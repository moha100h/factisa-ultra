"""
Dynamic card generator using Pillow + Vazir font.
Produces 800x420 PNG cards for each section.
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

_FONT_DIRS = ["/app/fonts", os.path.join(os.getcwd(), "fonts")]

def _font_path(name: str):
    for d in _FONT_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None

_VAZIR_PATH      = _font_path("Vazir.ttf")
_VAZIR_BOLD_PATH = _font_path("Vazir-Bold.ttf")

def _font(size: int, bold: bool = False):
    path = _VAZIR_BOLD_PATH if bold else _VAZIR_PATH
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def rtl(text: str) -> str:
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(str(text)))

C = {
    "bg":      "#0f0f1a", "card":    "#1a1a2e", "accent":  "#4361ee",
    "accent2": "#7209b7", "text":    "#e0e0e0", "muted":   "#888899",
    "success": "#06d6a0", "warning": "#ffd166", "danger":  "#ef476f",
    "white":   "#ffffff", "sep":     "#2a2a3e",
}
W, H = 800, 420

def _base(title: str, icon: str, accent: str = None):
    accent = accent or C["accent"]
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([10,10,W-10,H-10], radius=20, fill=C["card"])
    d.rounded_rectangle([10,10,W-10,58],   radius=20, fill=accent)
    d.rectangle([10,38,W-10,58], fill=accent)
    d.text((W//2, 34), rtl(f"{icon}  {title}"),
           font=_font(22, True), fill=C["white"], anchor="mm")
    d.line([(30,68),(W-30,68)], fill=C["sep"], width=1)
    return img, d

def _row(d, y, label, value, vc=None):
    vc = vc or C["text"]
    d.text((W-40, y), rtl(label), font=_font(16, True), fill=C["muted"], anchor="ra")
    d.text((40,   y), rtl(value), font=_font(16),       fill=vc,         anchor="la")

def _box(d, x, y, w, h, label, value, color):
    d.rounded_rectangle([x,y,x+w,y+h], radius=10, fill=color+"33")
    d.rounded_rectangle([x,y,x+w,y+4], radius=2,  fill=color)
    d.text((x+w//2, y+h//2-10), rtl(value), font=_font(18,True), fill=color,     anchor="mm")
    d.text((x+w//2, y+h//2+14), rtl(label), font=_font(13),      fill=C["muted"], anchor="mm")

def _png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def make_client_card(client) -> bytes:
    from app.services.jalali import fmt, to_jalali
    img, d = _base("مشتری", "👤", C["accent"])
    inv_count  = len(client.invoices) if client.invoices else 0
    total_debt = sum(i.remaining for i in client.invoices if i.remaining > 0) if client.invoices else 0
    total_paid = sum(p.amount for inv in client.invoices for p in (inv.payments or [])) if client.invoices else 0
    for i,(lbl,val) in enumerate([
        ("نام:",       client.name or "—"),
        ("تلفن:",      client.phone or "—"),
        ("شرکت:",      client.company or "—"),
        ("آدرس:",      (client.address or "—")[:35]),
        ("تاریخ ثبت:", to_jalali(client.created_at)),
    ]):
        _row(d, 90+i*38, lbl, val)
    bw = 220
    _box(d,  40, 285, bw, 90, "تعداد فاکتور", str(inv_count),  C["accent"])
    _box(d, 290, 285, bw, 90, "پرداخت شده",   fmt(total_paid), C["success"])
    _box(d, 540, 285, bw, 90, "بدهی",          fmt(total_debt),
         C["danger"] if total_debt > 0 else C["success"])
    return _png(img)


def make_invoice_card(inv) -> bytes:
    from app.services.jalali import fmt, to_jalali
    SC = {"draft":C["muted"],"sent":C["accent"],"paid":C["success"],
          "partial":C["warning"],"cancelled":C["danger"]}
    sv = inv.status.value if hasattr(inv.status,"value") else str(inv.status)
    img, d = _base(f"فاکتور {inv.invoice_number}", "📄", SC.get(sv, C["accent"]))
    subtotal   = sum(i.total for i in (inv.items or []))
    discount   = inv.discount or 0
    tax_rate   = inv.tax_rate or 0
    tax_amount = (subtotal - discount) * tax_rate / 100
    total      = subtotal - discount + tax_amount
    paid       = sum(p.amount for p in (inv.payments or []))
    remaining  = total - paid
    for i,(lbl,val) in enumerate([
        ("مشتری:",           inv.client.name if inv.client else "—"),
        ("تاریخ:",           to_jalali(inv.created_at)),
        ("تعداد اقلام:",     str(len(inv.items or []))),
        ("تخفیف:",           fmt(discount)),
        (f"مالیات ({tax_rate}%):", fmt(tax_amount)),
    ]):
        _row(d, 90+i*38, lbl, val)
    bw = 220
    _box(d,  40, 285, bw, 90, "جمع کل",     fmt(total),     C["accent"])
    _box(d, 290, 285, bw, 90, "پرداخت شده", fmt(paid),      C["success"])
    _box(d, 540, 285, bw, 90, "مانده",       fmt(remaining),
         C["danger"] if remaining > 0 else C["success"])
    return _png(img)


def make_project_card(project) -> bytes:
    from app.services.jalali import fmt, to_jalali
    SC = {"active":C["success"],"completed":C["accent"],
          "paused":C["warning"],"cancelled":C["danger"]}
    sv = project.status.value if hasattr(project.status,"value") else str(project.status)
    img, d = _base(project.title[:35], "🏗", SC.get(sv, C["accent"]))
    inv_total = sum(i.total for i in project.invoices) if project.invoices else 0
    exp_total = sum(e.amount for e in project.expenses) if project.expenses else 0
    profit    = inv_total - exp_total
    for i,(lbl,val) in enumerate([
        ("وضعیت:",    sv),
        ("بودجه:",    fmt(project.budget or 0)),
        ("شروع:",     to_jalali(project.created_at)),
        ("توضیحات:", (project.description or "—")[:35]),
    ]):
        _row(d, 90+i*38, lbl, val)
    bw = 220
    _box(d,  40, 285, bw, 90, "درآمد",    fmt(inv_total), C["success"])
    _box(d, 290, 285, bw, 90, "هزینه",    fmt(exp_total), C["warning"])
    _box(d, 540, 285, bw, 90, "سود/زیان", fmt(profit),
         C["success"] if profit >= 0 else C["danger"])
    return _png(img)


def make_worker_card(worker) -> bytes:
    from app.services.jalali import fmt, to_jalali
    img, d = _base(worker.name, "👷", C["accent2"])
    for i,(lbl,val) in enumerate([
        ("تخصص:",       worker.skill or "عمومی"),
        ("تلفن:",        worker.phone or "—"),
        ("نرخ روزانه:", fmt(worker.daily_rate or 0)),
        ("تاریخ ثبت:",  to_jalali(worker.created_at)),
    ]):
        _row(d, 90+i*38, lbl, val)
    bw = 220
    _box(d,  40, 285, bw, 90, "کارکرد",     fmt(worker.total_worked or 0), C["accent"])
    _box(d, 290, 285, bw, 90, "پرداخت شده", fmt(worker.total_paid or 0),   C["success"])
    _box(d, 540, 285, bw, 90, "مانده",       fmt(worker.balance or 0),
         C["danger"] if (worker.balance or 0) > 0 else C["success"])
    return _png(img)


def make_dashboard_card(stats: dict) -> bytes:
    from app.services.jalali import fmt, jalali_now
    img, d = _base("داشبورد FacTisa Ultra", "📊", C["accent"])
    bw, bh, gap = 170, 95, 10
    for idx,(lbl,key,color) in enumerate([
        ("مشتریان",  "clients",  C["accent"]),
        ("پروژه‌ها", "projects", C["accent2"]),
        ("فاکتورها", "invoices", C["success"]),
        ("کارگران",  "workers",  C["warning"]),
    ]):
        _box(d, 30+idx*(bw+gap), 85, bw, bh, lbl, str(stats.get(key,0)), color)
    _box(d,  30, 210, 365, 90, "کل درآمد", fmt(stats.get("income",0)), C["success"])
    _box(d, 405, 210, 365, 90, "کل بدهی",  fmt(stats.get("debt",0)),   C["danger"])
    d.text((W//2, H-18), rtl(jalali_now()), font=_font(13), fill=C["muted"], anchor="mm")
    return _png(img)
