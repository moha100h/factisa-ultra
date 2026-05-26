from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="📄 فاکتورها"), KeyboardButton(text="👥 مشتریان"))
    kb.row(KeyboardButton(text="🏗 پروژه‌ها"), KeyboardButton(text="👷 کارگران"))
    kb.row(KeyboardButton(text="💰 مالی"), KeyboardButton(text="📊 گزارش‌ها"))
    if is_admin:
        kb.row(KeyboardButton(text="⚙️ تنظیمات"), KeyboardButton(text="💾 بکاپ"))
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="یک گزینه انتخاب کنید...")


def back_btn(to: str = "nav:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data=to)]])


def invoice_list(invoices: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    S = {"draft": "📝", "sent": "📤", "paid": "✅", "partial": "⚠️", "cancelled": "❌"}
    for inv in invoices[start:start + per_page]:
        sv = inv.status.value if hasattr(inv.status, "value") else inv.status
        kb.row(InlineKeyboardButton(
            text=f"{S.get(sv, '📄')} {inv.invoice_number}  •  {inv.total:,.0f} ت",
            callback_data=f"inv:view:{inv.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"inv:list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}", callback_data="noop"))
    if start + per_page < len(invoices):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"inv:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="➕ فاکتور جدید", callback_data="inv:new"))
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def invoice_detail(inv_id: int, status: str, inv_number: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if status in ("draft", "sent", "partial"):
        kb.row(
            InlineKeyboardButton(text="💳 پرداخت", callback_data=f"inv:pay:{inv_id}"),
            InlineKeyboardButton(text="📤 ارسال شد", callback_data=f"inv:send:{inv_id}")
        )
    kb.row(
        InlineKeyboardButton(text="📄 PDF", callback_data=f"inv:pdf:{inv_id}"),
        InlineKeyboardButton(text="✅ پرداخت کامل", callback_data=f"inv:markpaid:{inv_id}")
    )
    kb.row(InlineKeyboardButton(text="🗑 حذف", callback_data=f"inv:del:{inv_id}"),
           InlineKeyboardButton(text="🔙 لیست", callback_data="inv:list:0"))
    return kb.as_markup()


def client_list(clients: list, page: int = 0, per_page: int = 7) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    for c in clients[start:start + per_page]:
        label = f"👤 {c.name}" + (f"  ({c.company})" if c.company else "")
        kb.row(InlineKeyboardButton(text=label, callback_data=f"cli:view:{c.id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"cli:list:{page - 1}"))
    if start + per_page < len(clients):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"cli:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="➕ مشتری جدید", callback_data="cli:new"))
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def client_detail(cid: int, phone: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📄 فاکتورها", callback_data=f"cli:invoices:{cid}"),
        InlineKeyboardButton(text="🏗 پروژه‌ها", callback_data=f"cli:projects:{cid}")
    )
    kb.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"cli:edit:{cid}"),
        InlineKeyboardButton(text="🗑 حذف", callback_data=f"cli:del:{cid}")
    )
    kb.row(InlineKeyboardButton(text="🔙 لیست مشتریان", callback_data="cli:list:0"))
    return kb.as_markup()


def project_list(projects: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    S = {"active": "🟢", "completed": "✅", "paused": "⏸", "cancelled": "❌"}
    for p in projects[start:start + per_page]:
        sv = p.status.value if hasattr(p.status, "value") else p.status
        label = f"{S.get(sv, '⚪')} {p.title}" + (f"  •  {p.budget:,.0f} ت" if p.budget else "")
        kb.row(InlineKeyboardButton(text=label, callback_data=f"prj:view:{p.id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"prj:list:{page - 1}"))
    if start + per_page < len(projects):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"prj:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="➕ پروژه جدید", callback_data="prj:new"))
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def project_detail(pid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📄 فاکتورها", callback_data=f"prj:invoices:{pid}"),
        InlineKeyboardButton(text="💸 هزینه‌ها", callback_data=f"prj:expenses:{pid}")
    )
    kb.row(
        InlineKeyboardButton(text="👷 کارگران", callback_data=f"prj:workers:{pid}"),
        InlineKeyboardButton(text="📊 گزارش PDF", callback_data=f"prj:report:{pid}")
    )
    kb.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"prj:edit:{pid}"),
        InlineKeyboardButton(text="🗑 حذف", callback_data=f"prj:del:{pid}")
    )
    kb.row(InlineKeyboardButton(text="🔙 لیست پروژه‌ها", callback_data="prj:list:0"))
    return kb.as_markup()


def worker_list(workers: list, page: int = 0, per_page: int = 7) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    for w in workers[start:start + per_page]:
        icon = "🔴" if w.balance > 0 else "🟢"
        kb.row(InlineKeyboardButton(
            text=f"{icon} {w.name}  •  {w.skill or 'عمومی'}",
            callback_data=f"wrk:view:{w.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"wrk:list:{page - 1}"))
    if start + per_page < len(workers):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"wrk:list:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="➕ کارگر جدید", callback_data="wrk:new"))
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def worker_detail(wid: int, phone: str = "") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 ثبت کارکرد", callback_data=f"wrk:log:{wid}"),
        InlineKeyboardButton(text="💳 پرداخت", callback_data=f"wrk:pay:{wid}")
    )
    kb.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"wrk:edit:{wid}"),
        InlineKeyboardButton(text="🗑 حذف", callback_data=f"wrk:del:{wid}")
    )
    kb.row(InlineKeyboardButton(text="🔙 لیست کارگران", callback_data="wrk:list:0"))
    return kb.as_markup()


def finance_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="💵 دریافتی‌ها", callback_data="fin:income"),
        InlineKeyboardButton(text="💸 هزینه‌ها", callback_data="fin:expenses")
    )
    kb.row(
        InlineKeyboardButton(text="📊 سود/زیان", callback_data="fin:profit"),
        InlineKeyboardButton(text="📋 بدهکاران", callback_data="fin:debtors")
    )
    kb.row(InlineKeyboardButton(text="➕ ثبت هزینه", callback_data="exp:new:0"))
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def report_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 خلاصه مالی", callback_data="rep:summary"),
        InlineKeyboardButton(text="📄 فاکتورها", callback_data="rep:invoices")
    )
    kb.row(
        InlineKeyboardButton(text="🏗 پروژه‌ها", callback_data="rep:projects"),
        InlineKeyboardButton(text="👷 کارگران", callback_data="rep:workers")
    )
    kb.row(
        InlineKeyboardButton(text="📅 ماهانه", callback_data="rep:monthly"),
        InlineKeyboardButton(text="📆 سالانه", callback_data="rep:yearly")
    )
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def confirm_kb(action: str, item_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ بله، حذف شود", callback_data=f"confirm:{action}:{item_id}"),
        InlineKeyboardButton(text="❌ خیر", callback_data=f"cancel:{action}:{item_id}")
    )
    return kb.as_markup()


def add_more_items() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="➕ اقلام بیشتر", callback_data="inv:addmore"),
        InlineKeyboardButton(text="✅ اتمام و ذخیره", callback_data="inv:finish")
    )
    return kb.as_markup()
