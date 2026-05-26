from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Invoice, Payment, Expense, Worker
from app.keyboards.menus import report_menu
from app.services.jalali import fmt
from datetime import datetime

router = Router()

@router.message(F.text == "📊 گزارش‌ها")
async def rep_menu(msg: Message):
    await msg.answer("📊 <b>گزارش‌ها</b>", reply_markup=report_menu())

@router.callback_query(F.data == "rep:summary")
async def rep_summary(cb: CallbackQuery, session: AsyncSession):
    r_inv = await session.execute(select(func.count(Invoice.id)))
    r_pay = await session.execute(select(func.sum(Payment.amount)))
    r_exp = await session.execute(select(func.sum(Expense.amount)))
    r_wrk = await session.execute(select(func.count(Worker.id)))
    inv_count = r_inv.scalar() or 0
    income = r_pay.scalar() or 0
    expense = r_exp.scalar() or 0
    workers = r_wrk.scalar() or 0
    profit = income - expense
    await cb.message.edit_text(
        f"📊 <b>خلاصه مالی کلی</b>\n\n📄 فاکتور: <b>{inv_count}</b>\n💵 درآمد: <b>{fmt(income)}</b>\n"
        f"💸 هزینه: <b>{fmt(expense)}</b>\n{'📈' if profit >= 0 else '📉'} <b>{'سود' if profit >= 0 else 'زیان'}: {fmt(abs(profit))}</b>\n👷 کارگر: <b>{workers}</b>",
        reply_markup=report_menu()
    )
    await cb.answer()

@router.callback_query(F.data == "rep:monthly")
async def rep_monthly(cb: CallbackQuery, session: AsyncSession):
    now = datetime.utcnow()
    r_pay = await session.execute(select(func.sum(Payment.amount)).where(extract("year",Payment.date)==now.year, extract("month",Payment.date)==now.month))
    r_exp = await session.execute(select(func.sum(Expense.amount)).where(extract("year",Expense.date)==now.year, extract("month",Expense.date)==now.month))
    r_inv = await session.execute(select(func.count(Invoice.id)).where(extract("year",Invoice.created_at)==now.year, extract("month",Invoice.created_at)==now.month))
    income = r_pay.scalar() or 0; expense = r_exp.scalar() or 0; inv_count = r_inv.scalar() or 0
    profit = income - expense
    await cb.message.edit_text(
        f"📅 <b>گزارش ماه جاری</b> ({now.strftime('%Y/%m')})\n\n📄 فاکتور: <b>{inv_count}</b>\n💵 درآمد: <b>{fmt(income)}</b>\n"
        f"💸 هزینه: <b>{fmt(expense)}</b>\n{'📈' if profit >= 0 else '📉'} <b>{'سود' if profit >= 0 else 'زیان'}: {fmt(abs(profit))}</b>",
        reply_markup=report_menu()
    )
    await cb.answer()

@router.callback_query(F.data == "rep:yearly")
async def rep_yearly(cb: CallbackQuery, session: AsyncSession):
    now = datetime.utcnow()
    r_pay = await session.execute(select(func.sum(Payment.amount)).where(extract("year",Payment.date)==now.year))
    r_exp = await session.execute(select(func.sum(Expense.amount)).where(extract("year",Expense.date)==now.year))
    r_inv = await session.execute(select(func.count(Invoice.id)).where(extract("year",Invoice.created_at)==now.year))
    income = r_pay.scalar() or 0; expense = r_exp.scalar() or 0; inv_count = r_inv.scalar() or 0
    profit = income - expense
    await cb.message.edit_text(
        f"📆 <b>گزارش سال جاری</b> ({now.year})\n\n📄 فاکتور: <b>{inv_count}</b>\n💵 درآمد: <b>{fmt(income)}</b>\n"
        f"💸 هزینه: <b>{fmt(expense)}</b>\n{'📈' if profit >= 0 else '📉'} <b>{'سود' if profit >= 0 else 'زیان'}: {fmt(abs(profit))}</b>",
        reply_markup=report_menu()
    )
    await cb.answer()

@router.callback_query(F.data == "rep:workers")
async def rep_workers(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(select(Worker).order_by(Worker.id.desc()))
    workers = r.scalars().all()
    text = f"👷 <b>گزارش کارگران</b>\n\n"
    total_debt = 0
    for w in workers:
        icon = "🔴" if w.balance > 0 else "🟢"
        text += f"{icon} {w.name} | کارکرد: {fmt(w.total_worked)} | پرداخت: {fmt(w.total_paid)} | مانده: <b>{fmt(w.balance)}</b>\n"
        total_debt += w.balance
    text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n💰 جمع بدهی: <b>{fmt(total_debt)}</b>"
    await cb.message.edit_text(text or "👷 هنوز کارگری ثبت نشده.", reply_markup=report_menu())
    await cb.answer()
