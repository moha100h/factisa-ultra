from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Project, Expense, Invoice
from app.keyboards.menus import project_list, project_detail, back_btn, confirm_kb
from app.services.jalali import fmt, to_jalali

router = Router()

class ProjectForm(StatesGroup):
    title = State(); budget = State(); description = State()

class ExpenseForm(StatesGroup):
    project_id = State(); category = State(); description = State(); amount = State()


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
    try:
        await cb.message.edit_text(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)",
                                   reply_markup=project_list(projects, page))
    except Exception:
        await cb.message.answer(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)",
                                reply_markup=project_list(projects, page))
    await cb.answer()


@router.callback_query(F.data.startswith("prj:view:"))
async def prj_view(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(
        select(Project).where(Project.id == pid)
        .options(selectinload(Project.invoices), selectinload(Project.expenses))
    )
    p = r.scalar_one_or_none()
    if not p:
        await cb.answer("پروژه یافت نشد!", show_alert=True); return
    from app.services.card_generator import make_project_card
    card = make_project_card(p)
    sv = p.status.value if hasattr(p.status,"value") else str(p.status)
    S = {"active":"🟢 فعال","completed":"✅ تکمیل","paused":"⏸ متوقف","cancelled":"❌ لغو"}
    inv_total = sum(i.total for i in p.invoices) if p.invoices else 0
    exp_total = sum(e.amount for e in p.expenses) if p.expenses else 0
    caption = (f"🏗 <b>{p.title}</b>  |  {S.get(sv,sv)}\n"
               f"💰 بودجه: {fmt(p.budget or 0)}  |  📈 سود: <b>{fmt(inv_total-exp_total)}</b>")
    await _send_card(cb, card, project_detail(pid), caption)
    await cb.answer()


@router.callback_query(F.data == "prj:new")
async def prj_new(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ProjectForm.title)
    try:
        await cb.message.edit_text("🏗 نام پروژه:", reply_markup=back_btn("prj:list:0"))
    except Exception:
        await cb.message.answer("🏗 نام پروژه:", reply_markup=back_btn("prj:list:0"))
    await cb.answer()


@router.message(ProjectForm.title)
async def prj_title(msg: Message, state: FSMContext):
    await state.update_data(title=msg.text)
    await state.set_state(ProjectForm.budget)
    await msg.answer("💰 بودجه (تومان) — 0 برای نامشخص:", reply_markup=back_btn("prj:list:0"))


@router.message(ProjectForm.budget)
async def prj_budget(msg: Message, state: FSMContext):
    try:
        budget = float(msg.text.replace(",",""))
    except ValueError:
        await msg.answer("❌ عدد وارد کنید:"); return
    await state.update_data(budget=budget)
    await state.set_state(ProjectForm.description)
    await msg.answer("📝 توضیحات (یا — برای صرف نظر):", reply_markup=back_btn("prj:list:0"))


@router.message(ProjectForm.description)
async def prj_desc(msg: Message, state: FSMContext, session: AsyncSession):
    d = await state.get_data()
    p = Project(title=d["title"], budget=d.get("budget",0),
                description=msg.text if msg.text != "—" else None)
    session.add(p)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ پروژه <b>{p.title}</b> ثبت شد!", reply_markup=back_btn("prj:list:0"))


@router.callback_query(F.data.startswith("prj:del:"))
async def prj_del_confirm(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(select(Project).where(Project.id == pid))
    p = r.scalar_one_or_none()
    if not p:
        await cb.answer("یافت نشد!", show_alert=True); return
    try:
        await cb.message.edit_text(f"⚠️ پروژه <b>{p.title}</b> حذف شود؟",
                                   reply_markup=confirm_kb("prj", pid))
    except Exception:
        await cb.message.answer(f"⚠️ پروژه <b>{p.title}</b> حذف شود؟",
                                reply_markup=confirm_kb("prj", pid))
    await cb.answer()


@router.callback_query(F.data.startswith("confirm:prj:"))
async def prj_del_exec(cb: CallbackQuery, session: AsyncSession):
    pid = int(cb.data.split(":")[2])
    r = await session.execute(select(Project).where(Project.id == pid))
    p = r.scalar_one_or_none()
    if p:
        await session.delete(p)
        await session.commit()
    await cb.answer("✅ حذف شد!", show_alert=True)
    r2 = await session.execute(select(Project).order_by(Project.id.desc()))
    projects = r2.scalars().all()
    try:
        await cb.message.edit_text(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)",
                                   reply_markup=project_list(projects))
    except Exception:
        await cb.message.answer(f"🏗 <b>پروژه‌ها</b> ({len(projects)} عدد)",
                                reply_markup=project_list(projects))


@router.callback_query(F.data.startswith("exp:new:"))
async def exp_new(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split(":")[2])
    await state.update_data(project_id=pid)
    await state.set_state(ExpenseForm.category)
    try:
        await cb.message.edit_text("💸 دسته‌بندی هزینه:", reply_markup=back_btn(f"prj:view:{pid}"))
    except Exception:
        await cb.message.answer("💸 دسته‌بندی هزینه:", reply_markup=back_btn(f"prj:view:{pid}"))
    await cb.answer()


@router.message(ExpenseForm.category)
async def exp_cat(msg: Message, state: FSMContext):
    await state.update_data(category=msg.text)
    await state.set_state(ExpenseForm.description)
    await msg.answer("📝 شرح هزینه:")


@router.message(ExpenseForm.description)
async def exp_desc(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text)
    await state.set_state(ExpenseForm.amount)
    await msg.answer("💰 مبلغ (تومان):")


@router.message(ExpenseForm.amount)
async def exp_amount(msg: Message, state: FSMContext, session: AsyncSession):
    try:
        amount = float(msg.text.replace(",",""))
    except ValueError:
        await msg.answer("❌ عدد وارد کنید:"); return
    d = await state.get_data()
    e = Expense(project_id=d["project_id"], category=d["category"],
                description=d["description"], amount=amount)
    session.add(e)
    await session.commit()
    await state.clear()
    await msg.answer(f"✅ هزینه <b>{fmt(amount)}</b> ثبت شد!",
                     reply_markup=back_btn(f"prj:view:{d['project_id']}"))
