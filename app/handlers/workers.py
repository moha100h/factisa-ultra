from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Worker, WorkLog, WorkerPayment
from app.keyboards.menus import worker_list, worker_detail, back_btn, confirm_kb
from app.services.jalali import fmt, to_jalali

router = Router()

class WorkerForm(StatesGroup):
    name = State(); phone = State(); skill = State(); daily_rate = State()

class WorkLogForm(StatesGroup):
    worker_id = State(); hours = State(); description = State()

class WorkerPayForm(StatesGroup):
    worker_id = State(); amount = State(); description = State()


async def _send_card(cb, card_bytes, reply_markup, caption=""):
    buf = BufferedInputFile(card_bytes, filename="card.png")
    try:
        if cb.message.photo:
            await cb.message.edit_media(
                media=InputMediaPhoto(media=buf, caption=caption, parse_mode="HTML"),
                reply_markup=reply_markup)
        else:
            await cb.message.delete()
            await cb.message.answer_photo(photo=buf, caption=caption,
                                          reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await cb.message.answer_photo(photo=buf, caption=caption,
                                      reply_markup=reply_markup, parse_mode="HTML")


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
    try:
        await cb.message.edit_text(f"👷 <b>کارگران</b> ({len(workers)} نفر)",
                                   reply_markup=worker_list(workers, page))
    except Exception:
        await cb.message.answer(f"👷 <b>کارگران</b> ({len(workers)} نفر)",
                                reply_markup=worker_list(workers, page))
    await cb.answer()


@router.callback_query(F.data.startswith("wrk:view:"))
async def wrk_view(cb: CallbackQuery, session: AsyncSession):
    wid = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    if not w:
        await cb.answer("کارگر یافت نشد!", show_alert=True); return
    from app.services.card_generator import make_worker_card
    card = make_worker_card(w)
    icon = "🔴" if (w.balance or 0) > 0 else "🟢"
    caption = (f"👷 <b>{w.name}</b>  |  {w.skill or 'عمومی'}\n"
               f"{icon} مانده: <b>{fmt(w.balance or 0)}</b>  |  ✅ پرداخت: {fmt(w.total_paid or 0)}")
    await _send_card(cb, card, worker_detail(wid, w.phone or ""), caption)
    await cb.answer()


@router.callback_query(F.data == "wrk:new")
async def wrk_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(WorkerForm.name)
    try:
        await cb.message.edit_text("👷 نام کارگر:", reply_markup=back_btn("wrk:list:0"))
    except Exception:
        await cb.message.answer("👷 نام کارگر:", reply_markup=back_btn("wrk:list:0"))
    await cb.answer()


@router.message(WorkerForm.name)
async def wrk_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(WorkerForm.phone)
    await msg.answer("📞 شماره تلفن (یا — برای صرف نظر):", reply_markup=back_btn("wrk:list:0"))


@router.message(WorkerForm.phone)
async def wrk_phone(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text if msg.text != "—" else None)
    await state.set_state(WorkerForm.skill)
    await msg.answer("🔧 تخصص (یا — برای صرف نظر):", reply_markup=back_btn("wrk:list:0"))


@router.message(WorkerForm.skill)
async def wrk_skill(msg: Message, state: FSMContext):
    await state.update_data(skill=msg.text if msg.text != "—" else None)
    await state.set_state(WorkerForm.daily_rate)
    await msg.answer("💰 نرخ روزانه (تومان):", reply_markup=back_btn("wrk:list:0"))


@router.message(WorkerForm.daily_rate)
async def wrk_rate(msg: Message, state: FSMContext, session: AsyncSession):
    try:
        rate = float(msg.text.replace(",",""))
    except ValueError:
        await msg.answer("❌ عدد وارد کنید:"); return
    d = await state.get_data()
    w = Worker(name=d["name"], phone=d.get("phone"), skill=d.get("skill"), daily_rate=rate)
    session.add(w)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ کارگر <b>{w.name}</b> ثبت شد!", reply_markup=back_btn("wrk:list:0"))


@router.callback_query(F.data.startswith("wrk:log:"))
async def wrk_log_start(cb: CallbackQuery, state: FSMContext):
    wid = int(cb.data.split(":")[2])
    await state.update_data(worker_id=wid)
    await state.set_state(WorkLogForm.hours)
    try:
        await cb.message.edit_text("⏱ تعداد ساعت کارکرد:", reply_markup=back_btn(f"wrk:view:{wid}"))
    except Exception:
        await cb.message.answer("⏱ تعداد ساعت کارکرد:", reply_markup=back_btn(f"wrk:view:{wid}"))
    await cb.answer()


@router.message(WorkLogForm.hours)
async def wrk_log_hours(msg: Message, state: FSMContext):
    try:
        hours = float(msg.text.replace(",",""))
    except ValueError:
        await msg.answer("❌ عدد وارد کنید:"); return
    await state.update_data(hours=hours)
    await state.set_state(WorkLogForm.description)
    await msg.answer("📝 شرح کار (یا — برای صرف نظر):")


@router.message(WorkLogForm.description)
async def wrk_log_desc(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    log = WorkLog(worker_id=d["worker_id"], hours=d["hours"],
                  description=msg.text if msg.text != "—" else None)
    session.add(log)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ کارکرد <b>{d['hours']}</b> ساعت ثبت شد!",
                     reply_markup=back_btn(f"wrk:view:{d['worker_id']}"))


@router.callback_query(F.data.startswith("wrk:pay:"))
async def wrk_pay_start(cb: CallbackQuery, state: FSMContext):
    wid = int(cb.data.split(":")[2])
    await state.update_data(worker_id=wid)
    await state.set_state(WorkerPayForm.amount)
    try:
        await cb.message.edit_text("💳 مبلغ پرداخت (تومان):", reply_markup=back_btn(f"wrk:view:{wid}"))
    except Exception:
        await cb.message.answer("💳 مبلغ پرداخت (تومان):", reply_markup=back_btn(f"wrk:view:{wid}"))
    await cb.answer()


@router.message(WorkerPayForm.amount)
async def wrk_pay_amount(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.replace(",",""))
    except ValueError:
        await msg.answer("❌ عدد وارد کنید:"); return
    await state.update_data(amount=amount)
    await state.set_state(WorkerPayForm.description)
    await msg.answer("📝 توضیح پرداخت (یا — برای صرف نظر):")


@router.message(WorkerPayForm.description)
async def wrk_pay_desc(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    pay = WorkerPayment(worker_id=d["worker_id"], amount=d["amount"],
                        description=msg.text if msg.text != "—" else None)
    session.add(pay)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ پرداخت <b>{fmt(d['amount'])}</b> ثبت شد!",
                     reply_markup=back_btn(f"wrk:view:{d['worker_id']}"))


@router.callback_query(F.data.startswith("wrk:del:"))
async def wrk_del_confirm(cb: CallbackQuery, session: AsyncSession):
    wid = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    if not w:
        await cb.answer("یافت نشد!", show_alert=True); return
    try:
        await cb.message.edit_text(f"⚠️ کارگر <b>{w.name}</b> حذف شود؟",
                                   reply_markup=confirm_kb("wrk", wid))
    except Exception:
        await cb.message.answer(f"⚠️ کارگر <b>{w.name}</b> حذف شود؟",
                                reply_markup=confirm_kb("wrk", wid))
    await cb.answer()


@router.callback_query(F.data.startswith("confirm:wrk:"))
async def wrk_del_exec(cb: CallbackQuery, session: AsyncSession):
    wid = int(cb.data.split(":")[2])
    r = await session.execute(select(Worker).where(Worker.id == wid))
    w = r.scalar_one_or_none()
    if w:
        await session.delete(w)
        await session.commit()
    await cb.answer("✅ حذف شد!", show_alert=True)
    r2 = await session.execute(select(Worker).order_by(Worker.id.desc()))
    workers = r2.scalars().all()
    try:
        await cb.message.edit_text(f"👷 <b>کارگران</b> ({len(workers)} نفر)",
                                   reply_markup=worker_list(workers))
    except Exception:
        await cb.message.answer(f"👷 <b>کارگران</b> ({len(workers)} نفر)",
                                reply_markup=worker_list(workers))
