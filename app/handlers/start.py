from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Client, Invoice, Project, Worker
from app.keyboards.menus import main_menu
from app.core.config import settings
from app.services.jalali import jalali_now

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, is_admin: bool):
    await message.answer(
        f"╔══════════════════════════╗\n"
        f"║  🏢 <b>FacTisa Ultra v{settings.VERSION}</b>\n"
        f"║  سیستم مالی حرفه‌ای\n"
        f"╚══════════════════════════╝\n\n"
        f"سلام <b>{message.from_user.first_name}</b> 👋\n"
        f"📅 {jalali_now()}\n\n"
        f"از منوی زیر استفاده کنید:",
        reply_markup=main_menu(is_admin=is_admin)
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>راهنمای FacTisa Ultra</b>\n\n"
        "📄 <b>فاکتورها</b> — ساخت، ویرایش، PDF، پرداخت\n"
        "👥 <b>مشتریان</b> — ثبت و مدیریت\n"
        "🏗 <b>پروژه‌ها</b> — بودجه، هزینه، سود/زیان\n"
        "👷 <b>کارگران</b> — کارکرد، دستمزد، تسویه\n"
        "💰 <b>مالی</b> — دریافتی، هزینه، بدهکاران\n"
        "📊 <b>گزارش‌ها</b> — ماهانه، سالانه\n\n"
        "/stats — آمار کلی\n"
        "/backup — بکاپ دستی (ادمین)"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    c = (await session.execute(select(func.count(Client.id)))).scalar() or 0
    p = (await session.execute(select(func.count(Project.id)))).scalar() or 0
    i = (await session.execute(select(func.count(Invoice.id)))).scalar() or 0
    w = (await session.execute(select(func.count(Worker.id)))).scalar() or 0
    await message.answer(
        f"📊 <b>آمار کلی</b>\n\n"
        f"👥 مشتری: <b>{c}</b>\n"
        f"🏗 پروژه: <b>{p}</b>\n"
        f"📄 فاکتور: <b>{i}</b>\n"
        f"👷 کارگر: <b>{w}</b>"
    )


@router.message(Command("backup"))
async def cmd_backup(message: Message, is_admin: bool):
    if not is_admin:
        await message.answer("❌ دسترسی ندارید!")
        return
    from app.services.backup import create_backup, cleanup_backups
    await message.answer("⏳ در حال ساخت بکاپ...")
    fp = await create_backup()
    if fp:
        await cleanup_backups()
        await message.answer(f"✅ بکاپ ساخته شد!\n<code>{fp}</code>")
    else:
        await message.answer("❌ خطا در ساخت بکاپ!")


@router.callback_query(F.data == "nav:main")
async def nav_main(cb: CallbackQuery, is_admin: bool):
    await cb.message.delete()
    await cb.message.answer("🏠 منوی اصلی:", reply_markup=main_menu(is_admin=is_admin))
    await cb.answer()


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_action(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ لغو شد.")
    await cb.answer()

@router.message(F.text == "💾 بکاپ")
async def btn_backup(message: Message, is_admin: bool):
    if not is_admin:
        await message.answer("❌ دسترسی ندارید!")
        return
    from app.services.backup import create_backup, cleanup_backups
    await message.answer("⏳ در حال ساخت بکاپ...")
    fp = await create_backup()
    if fp:
        await cleanup_backups()
        await message.answer(f"✅ بکاپ ساخته شد!\n<code>{fp}</code>")
    else:
        await message.answer("❌ خطا در ساخت بکاپ!")
