from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Invoice, Payment, Expense, InvoiceStatus
from app.keyboards.menus import finance_menu
from app.services.jalali import fmt

router = Router()


@router.message(F.text == "💰 مالی")
async def fin_menu(msg: Message):
    await msg.answer("💰 <b>مدیریت مالی</b>", reply_markup=finance_menu())


@router.callback_query(F.data == "fin:income")
async def fin_income(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(select(func.sum(Payment.amount)))
    total = r.scalar() or 0
    r2 = await session.execute(select(Invoice).where(Invoice.status == InvoiceStatus.PAID))
    paid_invs = r2.scalars().all()
    await cb.message.edit_text(
        f"💵 <b>دریافتی‌ها</b>\n\n"
        f"💰 جمع کل: <b>{fmt(total)}</b>\n"
        f"✅ فاکتور پرداخت شده: <b>{len(paid_invs)}</b> عدد",
        reply_markup=finance_menu()
    )
    await cb.answer()


@router.callback_query(F.data == "fin:expenses")
async def fin_expenses(cb: CallbackQuery, session: AsyncSession):
    r = await session.execute(select(func.sum(Expense.amount)))
    total = r.scalar() or 0
    r2 = await session.execute(select(Expense).order_by(Expense.id.desc()).limit(5))
    recent = r2.scalars().all()
    text = f"💸 <b>هزینه‌ها</b>\n\nجمع کل: <b>{fmt(total)}</b>\n\n<b>آخرین هزینه‌ها:</b>\n"
    for e in recent:
        text += f"• {e.category} | {fmt(e.amount)}\n"
    await cb.message.edit_text(text, reply_markup=finance_menu())
    await cb.answer()


@router.callback_query(F.data == "fin:profit")
async def fin_profit(cb: CallbackQuery, session: AsyncSession):
    r1 = await session.execute(select(func.sum(Payment.amount)))
    income = r1.scalar() or 0
    r2 = await session.execute(select(func.sum(Expense.amount)))
    expense = r2.scalar() or 0
    profit = income - expense
    icon = "📈" if profit >= 0 else "📉"
    await cb.message.edit_text(
        f"{icon} <b>سود / زیان</b>\n\n"
        f"💵 درآمد: <b>{fmt(income)}</b>\n"
        f"💸 هزینه: <b>{fmt(expense)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{icon} <b>{'سود' if profit >= 0 else 'زیان'}: {fmt(abs(profit))}</b>",
        reply_markup=finance_menu()
    )
    await cb.answer()


@router.callback_query(F.data == "fin:debtors")
async def fin_debtors(cb: CallbackQuery, session: AsyncSession):
    from sqlalchemy.orm import selectinload
    r = await session.execute(
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.payments),
            selectinload(Invoice.client)
        )
        .where(Invoice.status.in_([
            InvoiceStatus.DRAFT,
            InvoiceStatus.SENT,
            InvoiceStatus.PARTIAL
        ]))
    )
    invs = r.scalars().all()
    debtors = sorted(
        [(inv, inv.remaining) for inv in invs if inv.remaining > 0],
        key=lambda x: x[1], reverse=True
    )
    text = f"📋 <b>بدهکاران</b> ({len(debtors)} نفر)\n\n"
    for inv, rem in debtors[:15]:
        name = inv.client.name if inv.client else "—"
        text += f"👤 {name} | {inv.invoice_number} | <b>{fmt(rem)}</b>\n"
    if not debtors:
        text += "✅ هیچ بدهی‌ای وجود ندارد!"
    await cb.message.edit_text(text, reply_markup=finance_menu())
    await cb.answer()
