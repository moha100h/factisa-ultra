import re
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.core.config import settings

router = Router()


class SettingsState(StatesGroup):
    waiting_company_name    = State()
    waiting_company_phone   = State()
    waiting_company_address = State()
    waiting_tax_rate        = State()


def settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text=f"🏢 نام شرکت: {settings.COMPANY_NAME or '—'}",
        callback_data="set:company_name"
    ))
    kb.row(InlineKeyboardButton(
        text=f"📞 تلفن: {settings.COMPANY_PHONE or '—'}",
        callback_data="set:company_phone"
    ))
    kb.row(InlineKeyboardButton(
        text=f"📍 آدرس: {(settings.COMPANY_ADDRESS or '—')[:30]}",
        callback_data="set:company_address"
    ))
    kb.row(InlineKeyboardButton(
        text=f"💹 نرخ مالیات: {settings.TAX_RATE}%",
        callback_data="set:tax_rate"
    ))
    kb.row(InlineKeyboardButton(
        text="🖼 لوگوی شرکت",
        callback_data="set:logo"
    ))
    kb.row(InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main"))
    return kb.as_markup()


def _update_env(key: str, value: str) -> bool:
    for env_path in ["/app/.env", ".env"]:
        if os.path.exists(env_path):
            break
    else:
        return False
    try:
        with open(env_path, "r") as f:
            lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if re.match(rf"^{re.escape(key)}\s*=", line):
                new_lines.append(f'{key}="{value}"\n')
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f'{key}="{value}"\n')
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        return True
    except Exception:
        return False


@router.message(F.text == "⚙️ تنظیمات")
async def settings_main(message: Message, is_admin: bool):
    if not is_admin:
        await message.answer("❌ دسترسی ندارید!")
        return
    await message.answer(
        "⚙️ <b>تنظیمات سیستم</b>\n\nروی هر گزینه کلیک کنید تا ویرایش کنید:",
        reply_markup=settings_menu()
    )


@router.callback_query(F.data == "set:main")
async def settings_back(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "⚙️ <b>تنظیمات سیستم</b>\n\nروی هر گزینه کلیک کنید تا ویرایش کنید:",
        reply_markup=settings_menu()
    )
    await cb.answer()


@router.callback_query(F.data == "set:company_name")
async def ask_company_name(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_company_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ لغو", callback_data="set:main")
    ]])
    await cb.message.edit_text(
        f"🏢 <b>نام شرکت</b>\n\nمقدار فعلی: <code>{settings.COMPANY_NAME or '—'}</code>\n\nنام جدید را وارد کنید:",
        reply_markup=kb
    )
    await cb.answer()


@router.message(SettingsState.waiting_company_name)
async def save_company_name(message: Message, state: FSMContext):
    value = message.text.strip()
    _update_env("COMPANY_NAME", value)
    settings.COMPANY_NAME = value
    await state.clear()
    await message.answer(f"✅ نام شرکت به <b>{value}</b> تغییر یافت.", reply_markup=settings_menu())


@router.callback_query(F.data == "set:company_phone")
async def ask_company_phone(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_company_phone)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ لغو", callback_data="set:main")
    ]])
    await cb.message.edit_text(
        f"📞 <b>تلفن شرکت</b>\n\nمقدار فعلی: <code>{settings.COMPANY_PHONE or '—'}</code>\n\nشماره جدید را وارد کنید:",
        reply_markup=kb
    )
    await cb.answer()


@router.message(SettingsState.waiting_company_phone)
async def save_company_phone(message: Message, state: FSMContext):
    value = message.text.strip()
    _update_env("COMPANY_PHONE", value)
    settings.COMPANY_PHONE = value
    await state.clear()
    await message.answer(f"✅ تلفن به <b>{value}</b> تغییر یافت.", reply_markup=settings_menu())


@router.callback_query(F.data == "set:company_address")
async def ask_company_address(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_company_address)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ لغو", callback_data="set:main")
    ]])
    await cb.message.edit_text(
        f"📍 <b>آدرس شرکت</b>\n\nمقدار فعلی: <code>{settings.COMPANY_ADDRESS or '—'}</code>\n\nآدرس جدید را وارد کنید:",
        reply_markup=kb
    )
    await cb.answer()


@router.message(SettingsState.waiting_company_address)
async def save_company_address(message: Message, state: FSMContext):
    value = message.text.strip()
    _update_env("COMPANY_ADDRESS", value)
    settings.COMPANY_ADDRESS = value
    await state.clear()
    await message.answer("✅ آدرس به‌روز شد.", reply_markup=settings_menu())


@router.callback_query(F.data == "set:tax_rate")
async def ask_tax_rate(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_tax_rate)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ لغو", callback_data="set:main")
    ]])
    await cb.message.edit_text(
        f"💹 <b>نرخ مالیات</b>\n\nمقدار فعلی: <code>{settings.TAX_RATE}%</code>\n\nعدد جدید را وارد کنید (مثلاً 9):",
        reply_markup=kb
    )
    await cb.answer()


@router.message(SettingsState.waiting_tax_rate)
async def save_tax_rate(message: Message, state: FSMContext):
    text = message.text.strip().replace("%", "")
    try:
        value = float(text)
        if not 0 <= value <= 100:
            raise ValueError
    except ValueError:
        await message.answer("❌ عدد معتبر وارد کنید (بین 0 تا 100):")
        return
    _update_env("TAX_RATE", str(value))
    settings.TAX_RATE = value
    await state.clear()
    await message.answer(f"✅ نرخ مالیات به <b>{value}%</b> تغییر یافت.", reply_markup=settings_menu())

# ─── Logo Upload ──────────────────────────────────────────────────────────────
class LogoState(StatesGroup):
    waiting_logo = State()


@router.callback_query(F.data == "set:logo")
async def ask_logo(cb: CallbackQuery, state: FSMContext):
    await state.set_state(LogoState.waiting_logo)
    has_logo = os.path.isfile(settings.LOGO_PATH)
    status = "✅ لوگو آپلود شده" if has_logo else "❌ لوگو ندارید"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ لغو", callback_data="set:main")
    ]])
    await cb.message.edit_text(
        f"🖼 <b>لوگوی شرکت</b>\n\nوضعیت: {status}\n\nتصویر لوگو را ارسال کنید (PNG/JPG):",
        reply_markup=kb
    )
    await cb.answer()


@router.message(LogoState.waiting_logo, F.photo)
async def save_logo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    os.makedirs(os.path.dirname(settings.LOGO_PATH), exist_ok=True)
    await message.bot.download_file(file.file_path, destination=settings.LOGO_PATH)
    await state.clear()
    await message.answer("✅ لوگو با موفقیت ذخیره شد و در فاکتورها اعمال می‌شود.", reply_markup=settings_menu())


@router.message(LogoState.waiting_logo)
async def logo_wrong_type(message: Message):
    await message.answer("❌ لطفاً یک تصویر (عکس) ارسال کنید.")
