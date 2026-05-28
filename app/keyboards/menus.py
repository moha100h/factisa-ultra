from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def _btn(text: str, cb: str, color: str = None) -> InlineKeyboardButton:
    """Helper: ساخت دکمه با رنگ اختیاری."""
    kwargs = {"text": text, "callback_data": cb}
    if color:
        kwargs["color"] = color
    return InlineKeyboardButton(**kwargs)


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="📄 فاکتورها"), KeyboardButton(text="👥 مشتریان"))
    kb.row(KeyboardButton(text="🏗 پروژه‌ها"), KeyboardButton(text="👷 کارگران"))
    kb.row(KeyboardButton(text="💰 مالی"), KeyboardButton(text="📊 گزارش‌ها"))
    if is_admin:
        kb.row(KeyboardButton(text="⚙️ تنظیمات"), KeyboardButton(text="💾 بکاپ"))
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="یک گزینه انتخاب کنید...")


def back_btn(to: str = "nav:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        _btn("🔙 بازگشت", to)
    ]])


def invoice_list(invoices: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    S = {"draft": "📝", "sent": "📤", "paid": "✅", "partial": "⚠️", "cancelled": "❌"}
    for inv in invoices[start:start + per_page]:
        sv = inv.status.value if hasattr(inv.status, "value") else inv.status
        kb.row(_btn(
            f"{S.get(sv, '📄')} {inv.invoice_number}  •  {inv.total:,.0f} ت",
            f"inv:view:{inv.id}"
        ))
    nav = []
    if page > 0:
        nav.append(_btn("◀️", f"inv:list:{page - 1}"))
    nav.append(_btn(f"📄 {page + 1}", "noop"))
    if start + per_page < len(invoices):
        nav.append(_btn("▶️", f"inv:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(_btn("➕ فاکتور جدید", "inv:new", "success"))
    kb.row(_btn("🔙 منوی اصلی", "nav:main"))
    return kb.as_markup()


def invoice_detail(inv_id: int, status: str, inv_number: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status in ("draft", "sent", "partial"):
        kb.row(
            _btn("💳 پرداخت",    f"inv:pay:{inv_id}",  "success"),
            _btn("📤 ارسال شد",  f"inv:send:{inv_id}")
        )
    kb.row(
        _btn("📄 PDF",           f"inv:pdf:{inv_id}"),
        _btn("✅ پرداخت کامل",   f"inv:markpaid:{inv_id}", "success")
    )
    kb.row(
        _btn("🗑 حذف",           f"inv:del:{inv_id}",  "danger"),
        _btn("🔙 لیست",          "inv:list:0")
    )
    return kb.as_markup()


def client_list(clients: list, page: int = 0, per_page: int = 7) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    for c in clients[start:start + per_page]:
        label = f"👤 {c.name}" + (f"  ({c.company})" if c.company else "")
        kb.row(_btn(label, f"cli:view:{c.id}"))
    nav = []
    if page > 0:
        nav.append(_btn("◀️", f"cli:list:{page - 1}"))
    if start + per_page < len(clients):
        nav.append(_btn("▶️", f"cli:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(_btn("➕ مشتری جدید", "cli:new", "success"))
    kb.row(_btn("🔙 منوی اصلی",  "nav:main"))
    return kb.as_markup()


def client_detail(cid: int, phone: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("📄 فاکتورها", f"cli:invoices:{cid}"),
        _btn("🏗 پروژه‌ها", f"cli:projects:{cid}")
    )
    kb.row(
        _btn("✏️ ویرایش",  f"cli:edit:{cid}"),
        _btn("🗑 حذف",     f"cli:del:{cid}", "danger")
    )
    kb.row(_btn("🔙 لیست مشتریان", "cli:list:0"))
    return kb.as_markup()


def project_list(projects: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    S = {"active": "🟢", "completed": "✅", "paused": "⏸", "cancelled": "❌"}
    for p in projects[start:start + per_page]:
        sv = p.status.value if hasattr(p.status, "value") else p.status
        label = f"{S.get(sv, '⚪')} {p.title}" + (f"  •  {p.budget:,.0f} ت" if p.budget else "")
        kb.row(_btn(label, f"prj:view:{p.id}"))
    nav = []
    if page > 0:
        nav.append(_btn("◀️", f"prj:list:{page - 1}"))
    if start + per_page < len(projects):
        nav.append(_btn("▶️", f"prj:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(_btn("➕ پروژه جدید", "prj:new", "success"))
    kb.row(_btn("🔙 منوی اصلی",  "nav:main"))
    return kb.as_markup()


def project_detail(pid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("📄 فاکتورها",  f"prj:invoices:{pid}"),
        _btn("💸 هزینه‌ها",  f"prj:expenses:{pid}")
    )
    kb.row(
        _btn("👷 کارگران",   f"prj:workers:{pid}"),
        _btn("📊 گزارش PDF", f"prj:report:{pid}", "success")
    )
    kb.row(
        _btn("✏️ ویرایش",   f"prj:edit:{pid}"),
        _btn("🗑 حذف",      f"prj:del:{pid}", "danger")
    )
    kb.row(_btn("🔙 لیست پروژه‌ها", "prj:list:0"))
    return kb.as_markup()


def worker_list(workers: list, page: int = 0, per_page: int = 7) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    for w in workers[start:start + per_page]:
        icon = "🔴" if w.balance > 0 else "🟢"
        kb.row(_btn(
            f"{icon} {w.name}  •  {w.skill or 'عمومی'}",
            f"wrk:view:{w.id}"
        ))
    nav = []
    if page > 0:
        nav.append(_btn("◀️", f"wrk:list:{page - 1}"))
    if start + per_page < len(workers):
        nav.append(_btn("▶️", f"wrk:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(_btn("➕ کارگر جدید", "wrk:new", "success"))
    kb.row(_btn("🔙 منوی اصلی",  "nav:main"))
    return kb.as_markup()


def worker_detail(wid: int, phone: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("📋 ثبت کارکرد", f"wrk:log:{wid}", "success"),
        _btn("💳 پرداخت",     f"wrk:pay:{wid}", "success")
    )
    kb.row(
        _btn("✏️ ویرایش",    f"wrk:edit:{wid}"),
        _btn("🗑 حذف",       f"wrk:del:{wid}", "danger")
    )
    kb.row(_btn("🔙 لیست کارگران", "wrk:list:0"))
    return kb.as_markup()


def finance_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("💵 دریافتی‌ها", "fin:income"),
        _btn("💸 هزینه‌ها",   "fin:expenses")
    )
    kb.row(
        _btn("📊 سود/زیان",   "fin:profit"),
        _btn("📋 بدهکاران",   "fin:debtors")
    )
    kb.row(_btn("➕ ثبت هزینه", "exp:new:0", "success"))
    kb.row(_btn("🔙 منوی اصلی", "nav:main"))
    return kb.as_markup()


def report_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("📊 خلاصه مالی", "rep:summary"),
        _btn("📄 فاکتورها",   "rep:invoices")
    )
    kb.row(
        _btn("🏗 پروژه‌ها",   "rep:projects"),
        _btn("👷 کارگران",    "rep:workers")
    )
    kb.row(
        _btn("📅 ماهانه",     "rep:monthly"),
        _btn("📆 سالانه",     "rep:yearly")
    )
    kb.row(_btn("🔙 منوی اصلی", "nav:main"))
    return kb.as_markup()


def confirm_kb(action: str, item_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("✅ بله، حذف شود", f"confirm:{action}:{item_id}", "danger"),
        _btn("❌ خیر",          f"cancel:{action}:{item_id}",  "success")
    )
    return kb.as_markup()


def add_more_items() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("➕ اقلام بیشتر", "inv:addmore"),
        _btn("✅ اتمام و ذخیره", "inv:finish", "success")
    )
    return kb.as_markup()


def settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        _btn("🏢 نام شرکت",    "set:company"),
        _btn("📞 تلفن",        "set:phone")
    )
    kb.row(
        _btn("📍 آدرس",        "set:address"),
        _btn("🌐 وب‌سایت",     "set:website")
    )
    kb.row(_btn("🖼 لوگوی شرکت", "set:logo", "success"))
    kb.row(_btn("🔙 منوی اصلی",  "nav:main"))
    return kb.as_markup()
