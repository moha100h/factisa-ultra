from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Worker, WorkLog, WorkerPayment, PaymentMethod
from app.keyboards.menus import worker_list, worker_detail, back_btn, main_menu, confirm_kb
from app.services.jalali import fmt, to_jalali

router = Router()

class WorkerForm(StatesGroup):
    name = State(); phone = State(); skill = State(); daily_rate = State()

class WorkLogForm(StatesGroup):
    worker_id = State(); hours = State(); description = State()

class WorkerPayForm(StatesGroup):
    worker_id = State(); amount = State(); description = State()

@router.message(F.text == "👷 کارگران")
async def wrk_menu(msg: Message, session: AsyncSession):
    r = await session.execute(select(Worker).order_by(Worker.id.desc()))
    workers = r.scalars().all()
    await msg.answer(f"👷 <b>کارگران</b> ({len(workers)} نفر)", reply_markup=worker_list(workers))

@router.callback_query(F.data.startswith("wrk:list:"))
async def wrk_list_page(cb: CallbackQuery, session: AsyncSession):
    page = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).order_by(Worker.id.desc()))
    workers = r.scalars().all()
    await cb.message.edit_text(f"👷 <b>کارگران</b> ({len(workers)} نفر)", reply_markup=worker_list(workers, page))
    await cb.answer()

@router.callback_query(F.data.startswith("wrk:view:"))
async def wrk_view(cb: CallbackQuery, session: AsyncSession):
    wid = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    if not w: await cb.answer("کارگر یافت نشد!", show_alert=True); return
    await cb.message.edit_text(
        f"👷 <b>{w.name}</b>\n\n📞 تلفن: <code>{w.phone or '—'}</code>\n🔧 تخصص: {w.skill or '—'}\n"
        f"💰 نرخ روزانه: <b>{fmt(w.daily_rate)}</b>\n📅 ثبت: {to_jalali(w.created_at)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n📋 کارکرد: {fmt(w.total_worked)}\n✅ پرداخت: {fmt(w.total_paid)}\n"
        f"⚠️ <b>مانده: {fmt(w.balance)}</b>",
        reply_markup=worker_detail(wid, w.phone or "")
    )
    await cb.answer()

@router.callback_query(F.data == "wrk:new")
async def wrk_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(WorkerForm.name)
    await cb.message.edit_text("👷 نام کارگر:", reply_markup=back_btn("wrk:list:0"))
    await cb.answer()

@router.message(WorkerForm.name)
async def wrk_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text); await state.set_state(WorkerForm.phone)
    await msg.answer("📞 شماره تلفن (یا — برای صرف نظر):", reply_markup=back_btn("wrk:list:0"))

@router.message(WorkerForm.phone)
async def wrk_phone(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text if msg.text != "—" else None); await state.set_state(WorkerForm.skill)
    await msg.answer("🔧 تخصص (یا — برای صرف نظر):", reply_markup=back_btn("wrk:list:0"))

@router.message(WorkerForm.skill)
async def wrk_skill(msg: Message, state: FSMContext):
    await state.update_data(skill=msg.text if msg.text != "—" else None); await state.set_state(WorkerForm.daily_rate)
    await msg.answer("💰 نرخ روزانه (تومان):", reply_markup=back_btn("wrk:list:0"))

@router.message(WorkerForm.daily_rate)
async def wrk_rate(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    try: rate = float(msg.text.replace(",",""))
    except: rate = 0
    data = await state.get_data()
    w = Worker(name=data["name"], phone=data.get("phone"), skill=data.get("skill"), daily_rate=rate)
    session.add(w); await session.commit(); await state.clear()
    await msg.answer(f"✅ کارگر <b>{w.name}</b> ثبت شد! 🎉", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("wrk:log:"))
async def wrk_log_start(cb: CallbackQuery, state: FSMContext):
    wid = int(cb.data.split(":")[2])
    await state.update_data(worker_id=wid); await state.set_state(WorkLogForm.hours)
    await cb.message.edit_text("⏰ تعداد ساعت کارکرد (8 = یک روز کامل):", reply_markup=back_btn(f"wrk:view:{wid}"))
    await cb.answer()

@router.message(WorkLogForm.hours)
async def wrk_log_hours(msg: Message, state: FSMContext):
    try: h = float(msg.text)
    except: h = 8
    await state.update_data(hours=h); await state.set_state(WorkLogForm.description)
    await msg.answer("📝 شرح کار (یا — برای صرف نظر):", reply_markup=back_btn("wrk:list:0"))

@router.message(WorkLogForm.description)
async def wrk_log_desc(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    data = await state.get_data()
    wid = data["worker_id"]
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    log = WorkLog(worker_id=wid, hours=data["hours"], description=msg.text if msg.text != "—" else None, daily_rate=w.daily_rate if w else 0)
    session.add(log); await session.commit(); await state.clear()
    await msg.answer(f"✅ کارکرد ثبت شد!\n⏰ {data['hours']} ساعت | 💰 {fmt(log.total_pay)}", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("wrk:pay:"))
async def wrk_pay_start(cb: CallbackQuery, state: FSMContext):
    wid = int(cb.data.split(":")[2])
    await state.update_data(worker_id=wid); await state.set_state(WorkerPayForm.amount)
    await cb.message.edit_text("💳 مبلغ پرداخت (تومان):", reply_markup=back_btn(f"wrk:view:{wid}"))
    await cb.answer()

@router.message(WorkerPayForm.amount)
async def wrk_pay_amount(msg: Message, state: FSMContext):
    try: amount = float(msg.text.replace(",",""))
    except: await msg.answer("❌ مبلغ را درست وارد کنید:"); return
    await state.update_data(amount=amount); await state.set_state(WorkerPayForm.description)
    await msg.answer("📝 توضیحات (یا — برای صرف نظر):", reply_markup=back_btn("wrk:list:0"))

@router.message(WorkerPayForm.description)
async def wrk_pay_desc(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    data = await state.get_data()
    session.add(WorkerPayment(worker_id=data["worker_id"], amount=data["amount"], method=PaymentMethod.CASH, description=msg.text if msg.text != "—" else None))
    await session.commit(); await state.clear()
    await msg.answer(f"✅ پرداخت <b>{fmt(data['amount'])}</b> ثبت شد!", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("wrk:del:"))
async def wrk_del_confirm(cb: CallbackQuery, session: AsyncSession):
    wid = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    if not w: await cb.answer("یافت نشد!", show_alert=True); return
    await cb.message.edit_text(f"⚠️ کارگر <b>{w.name}</b> حذف شود؟", reply_markup=confirm_kb("wrk", wid))
    await cb.answer()

@router.callback_query(F.data.startswith("confirm:wrk:"))
async def wrk_del_exec(cb: CallbackQuery, session: AsyncSession):
    wid = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    if w: await session.delete(w); await session.commit()
    await cb.answer("✅ حذف شد!", show_alert=True)
    r2 = await session.execute(select(Worker).order_by(Worker.id.desc()))
    workers = r2.scalars().all()
    await cb.message.edit_text(f"👷 <b>کارگران</b> ({len(workers)} نفر)", reply_markup=worker_list(workers))
