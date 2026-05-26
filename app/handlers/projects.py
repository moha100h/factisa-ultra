from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Project, Expense
from app.keyboards.menus import project_list, project_detail, back_btn, main_menu, confirm_kb
from app.services.jalali import fmt, to_jalali

router = Router()

class ProjectForm(StatesGroup):
    title = State(); budget = State(); description = State()

class ExpenseForm(StatesGroup):
    project_id = State(); category = State(); description = State(); amount = State()

@router.message(F.text == "🏗 پروژه‌ها")
async def prj_menu(msg: Message, session: AsyncSession):
    r = await session.execute(select(Project).order_by(Project.id.desc()))
    projects = r.scalars().all()
    await msg.answer(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)", reply_markup=project_list(projects))

@router.callback_query(F.data.startswith("prj:list:"))
async def prj_list_page(cb: CallbackQuery, session: AsyncSession):
    page = int(cb.data.split(":")[2])
    r = await session.execute(select(Project).order_by(Project.id.desc()))
    projects = r.scalars().all()
    await cb.message.edit_text(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)", reply_markup=project_list(projects, page))
    await cb.answer()

@router.callback_query(F.data.startswith("prj:view:"))
async def prj_view(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(select(Project).where(Project.id == pid))
    p = r.scalar_one_or_none()
    if not p: await cb.answer("پروژه یافت نشد!", show_alert=True); return
    sv = p.status.value if hasattr(p.status,"value") else p.status
    S = {"active":"🟢 فعال","completed":"✅ تکمیل","paused":"⏸ متوقف","cancelled":"❌ لغو"}
    inv_total = sum(i.total for i in p.invoices) if p.invoices else 0
    exp_total = sum(e.amount for e in p.expenses) if p.expenses else 0
    await cb.message.edit_text(
        f"🏗 <b>{p.title}</b>\n\n📊 وضعیت: {S.get(sv,sv)}\n💰 بودجه: <b>{fmt(p.budget)}</b>\n"
        f"📅 شروع: {to_jalali(p.created_at)}\n📝 توضیح: {p.description or '—'}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n📄 فاکتور: {fmt(inv_total)}\n💸 هزینه: {fmt(exp_total)}\n"
        f"📈 <b>سود/زیان: {fmt(inv_total - exp_total)}</b>",
        reply_markup=project_detail(pid)
    )
    await cb.answer()

@router.callback_query(F.data == "prj:new")
async def prj_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ProjectForm.title)
    await cb.message.edit_text("🏗 نام پروژه:", reply_markup=back_btn("prj:list:0"))
    await cb.answer()

@router.message(ProjectForm.title)
async def prj_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text); await state.set_state(ProjectForm.budget)
    await msg.answer("💰 بودجه (تومان) — 0 برای نامشخص:", reply_markup=back_btn("prj:list:0"))

@router.message(ProjectForm.budget)
async def prj_budget(msg: Message, state: FSMContext):
    try: b = float(msg.text.replace(",",""))
    except: b = 0
    await state.update_data(budget=b); await state.set_state(ProjectForm.description)
    await msg.answer("📝 توضیحات (یا — برای صرف نظر):", reply_markup=back_btn("prj:list:0"))

@router.message(ProjectForm.description)
async def prj_desc(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    data = await state.get_data()
    p = Project(title=data["title"], budget=data.get("budget",0), description=msg.text if msg.text != "—" else None)
    session.add(p); await session.commit(); await state.clear()
    await msg.answer(f"✅ پروژه <b>{p.title}</b> ثبت شد! 🎉", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("prj:expenses:"))
async def prj_expenses(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(select(Expense).where(Expense.project_id == pid).order_by(Expense.id.desc()))
    expenses = r.scalars().all()
    total = sum(e.amount for e in expenses)
    text = f"💸 <b>هزینه‌ها</b>\nجمع: <b>{fmt(total)}</b>\n\n"
    for e in expenses: text += f"• {e.category} | {e.description or '—'} | <b>{fmt(e.amount)}</b>\n"
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ هزینه جدید", callback_data=f"exp:new:{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 پروژه", callback_data=f"prj:view:{pid}"))
    await cb.message.edit_text(text or "💸 هنوز هزینه‌ای ثبت نشده.", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("exp:new:"))
async def exp_new(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split(":")[2])
    await state.update_data(project_id=pid); await state.set_state(ExpenseForm.category)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for cat in ["مصالح","دستمزد","حمل‌ونقل","ابزار","اداری","سایر"]:
        kb.row(InlineKeyboardButton(text=cat, callback_data=f"exp_cat:{cat}"))
    await cb.message.edit_text("📋 دسته‌بندی هزینه:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("exp_cat:"))
async def exp_cat(cb: CallbackQuery, state: FSMContext):
    cat = cb.data.split(":")[1]
    await state.update_data(category=cat); await state.set_state(ExpenseForm.description)
    await cb.message.edit_text("📝 شرح هزینه:", reply_markup=back_btn("prj:list:0"))
    await cb.answer()

@router.message(ExpenseForm.description)
async def exp_desc(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text); await state.set_state(ExpenseForm.amount)
    await msg.answer("💰 مبلغ (تومان):", reply_markup=back_btn("prj:list:0"))

@router.message(ExpenseForm.amount)
async def exp_amount(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    try: amount = float(msg.text.replace(",",""))
    except: await msg.answer("❌ مبلغ را درست وارد کنید:"); return
    data = await state.get_data()
    session.add(Expense(project_id=data["project_id"], category=data["category"], description=data.get("description"), amount=amount))
    await session.commit(); await state.clear()
    await msg.answer(f"✅ هزینه <b>{fmt(amount)}</b> ثبت شد!", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("prj:del:"))
async def prj_del_confirm(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(select(Project).where(Project.id == pid))
    p = r.scalar_one_or_none()
    if not p: await cb.answer("یافت نشد!", show_alert=True); return
    await cb.message.edit_text(f"⚠️ پروژه <b>{p.title}</b> حذف شود؟", reply_markup=confirm_kb("prj", pid))
    await cb.answer()

@router.callback_query(F.data.startswith("confirm:prj:"))
async def prj_del_exec(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(select(Project).where(Project.id == pid))
    p = r.scalar_one_or_none()
    if p: await session.delete(p); await session.commit()
    await cb.answer("✅ حذف شد!", show_alert=True)
    r2 = await session.execute(select(Project).order_by(Project.id.desc()))
    projects = r2.scalars().all()
    await cb.message.edit_text(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)", reply_markup=project_list(projects))
