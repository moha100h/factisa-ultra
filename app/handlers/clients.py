from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Client
from app.keyboards.menus import client_list, client_detail, back_btn, main_menu, confirm_kb
from app.services.jalali import fmt, to_jalali

router = Router()

class ClientForm(StatesGroup):
    name = State(); phone = State(); company = State(); address = State()

@router.message(F.text == "👥 مشتریان")
async def clients_menu(msg: Message, session: AsyncSession):
    r = await session.execute(select(Client).order_by(Client.id.desc()))
    clients = r.scalars().all()
    await msg.answer(f"👥 <b>مشتریان</b> ({len(clients)} نفر)", reply_markup=client_list(clients))

@router.callback_query(F.data.startswith("cli:list:"))
async def cli_list_page(cb: CallbackQuery, session: AsyncSession):
    page = int(cb.data.split(":")[2])
    r = await session.execute(select(Client).order_by(Client.id.desc()))
    clients = r.scalars().all()
    await cb.message.edit_text(f"👥 <b>مشتریان</b> ({len(clients)} نفر)", reply_markup=client_list(clients, page))
    await cb.answer()

@router.callback_query(F.data.startswith("cli:view:"))
async def cli_view(cb: CallbackQuery, session: AsyncSession):
    cid = int(cb.data.split(":")[2])
    r = await session.execute(select(Client).where(Client.id == cid))
    c = r.scalar_one_or_none()
    if not c: await cb.answer("مشتری یافت نشد!", show_alert=True); return
    inv_count = len(c.invoices) if c.invoices else 0
    total_debt = sum(inv.remaining for inv in c.invoices if inv.remaining > 0) if c.invoices else 0
    await cb.message.edit_text(
        f"👤 <b>{c.name}</b>\n\n📞 تلفن: <code>{c.phone or '—'}</code>\n🏢 شرکت: {c.company or '—'}\n"
        f"📍 آدرس: {c.address or '—'}\n📅 ثبت: {to_jalali(c.created_at)}\n\n"
        f"📄 فاکتور: <b>{inv_count}</b> عدد\n💰 بدهی: <b>{fmt(total_debt)}</b>",
        reply_markup=client_detail(cid, c.phone or "")
    )
    await cb.answer()

@router.callback_query(F.data == "cli:new")
async def cli_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ClientForm.name)
    await cb.message.edit_text("👤 نام مشتری:", reply_markup=back_btn("cli:list:0"))
    await cb.answer()

@router.message(ClientForm.name)
async def cli_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text); await state.set_state(ClientForm.phone)
    await msg.answer("📞 شماره تلفن (یا — برای صرف نظر):", reply_markup=back_btn("cli:list:0"))

@router.message(ClientForm.phone)
async def cli_phone(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text if msg.text != "—" else None); await state.set_state(ClientForm.company)
    await msg.answer("🏢 نام شرکت (یا — برای صرف نظر):", reply_markup=back_btn("cli:list:0"))

@router.message(ClientForm.company)
async def cli_company(msg: Message, state: FSMContext):
    await state.update_data(company=msg.text if msg.text != "—" else None); await state.set_state(ClientForm.address)
    await msg.answer("📍 آدرس (یا — برای صرف نظر):", reply_markup=back_btn("cli:list:0"))

@router.message(ClientForm.address)
async def cli_address(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    data = await state.get_data()
    c = Client(name=data["name"], phone=data.get("phone"), company=data.get("company"), address=msg.text if msg.text != "—" else None)
    session.add(c); await session.commit(); await state.clear()
    await msg.answer(f"✅ مشتری <b>{c.name}</b> ثبت شد! 🎉", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("cli:del:"))
async def cli_del_confirm(cb: CallbackQuery, session: AsyncSession):
    cid = int(cb.data.split(":")[2])
    r = await session.execute(select(Client).where(Client.id == cid))
    c = r.scalar_one_or_none()
    if not c: await cb.answer("یافت نشد!", show_alert=True); return
    await cb.message.edit_text(f"⚠️ مشتری <b>{c.name}</b> حذف شود؟", reply_markup=confirm_kb("cli", cid))
    await cb.answer()

@router.callback_query(F.data.startswith("confirm:cli:"))
async def cli_del_exec(cb: CallbackQuery, session: AsyncSession):
    cid = int(cb.data.split(":")[2])
    r = await session.execute(select(Client).where(Client.id == cid))
    c = r.scalar_one_or_none()
    if c: await session.delete(c); await session.commit()
    await cb.answer("✅ حذف شد!", show_alert=True)
    r2 = await session.execute(select(Client).order_by(Client.id.desc()))
    clients = r2.scalars().all()
    await cb.message.edit_text(f"👥 <b>مشتریان</b> ({len(clients)} نفر)", reply_markup=client_list(clients))
