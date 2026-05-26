from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Invoice, InvoiceItem, Client, InvoiceStatus, Payment, PaymentMethod
from app.keyboards.menus import invoice_list, invoice_detail, back_btn, main_menu, confirm_kb, add_more_items
from app.services.jalali import fmt, to_jalali
from app.services.number_gen import gen_invoice_number

router = Router()

class InvoiceForm(StatesGroup):
    client = State(); item_desc = State(); item_qty = State(); item_unit = State(); item_price = State()
    discount = State(); tax = State(); notes = State()

async def _load(session, inv_id):
    r = await session.execute(select(Invoice).where(Invoice.id==inv_id).options(
        selectinload(Invoice.items), selectinload(Invoice.payments), selectinload(Invoice.client)))
    return r.scalar_one_or_none()

@router.message(F.text == "📄 فاکتورها")
async def inv_menu(msg: Message, session: AsyncSession):
    r = await session.execute(select(Invoice).options(selectinload(Invoice.items),selectinload(Invoice.payments)).order_by(Invoice.id.desc()))
    invs = r.scalars().all()
    await msg.answer(f"📄 <b>فاکتورها</b> ({len(invs)} عدد)", reply_markup=invoice_list(invs))

@router.callback_query(F.data.startswith("inv:list:"))
async def inv_list_page(cb: CallbackQuery, session: AsyncSession):
    page = int(cb.data.split(":")[2])
    r = await session.execute(select(Invoice).options(selectinload(Invoice.items),selectinload(Invoice.payments)).order_by(Invoice.id.desc()))
    invs = r.scalars().all()
    await cb.message.edit_text(f"📄 <b>فاکتورها</b> ({len(invs)} عدد)", reply_markup=invoice_list(invs, page))
    await cb.answer()

@router.callback_query(F.data.startswith("inv:view:"))
async def inv_view(cb: CallbackQuery, session: AsyncSession):
    inv_id = int(cb.data.split(":")[2])
    inv = await _load(session, inv_id)
    if not inv: await cb.answer("یافت نشد!", show_alert=True); return
    S = {"draft":"📝 پیش‌نویس","sent":"📤 ارسال شده","paid":"✅ پرداخت شده","partial":"⚠️ جزئی","cancelled":"❌ لغو"}
    sv = inv.status.value if hasattr(inv.status,"value") else inv.status
    items_text = "\n".join(f"  {i+1}. {it.description} | {it.quantity:g} {it.unit} × {it.unit_price:,.0f} = <b>{it.total:,.0f}</b>" for i,it in enumerate(inv.items))
    await cb.message.edit_text(
        f"📄 <b>فاکتور {inv.invoice_number}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 وضعیت: {S.get(sv,sv)}\n👤 مشتری: <b>{inv.client.name if inv.client else '—'}</b>\n"
        f"📅 تاریخ: {to_jalali(inv.created_at)}\n\n📋 <b>اقلام:</b>\n{items_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n💰 جمع: {fmt(inv.subtotal)}\n🎯 تخفیف: {fmt(inv.discount)}\n"
        f"💸 مالیات ({inv.tax_rate}%): {fmt(inv.tax_amount)}\n💵 <b>نهایی: {fmt(inv.total)}</b>\n"
        f"✅ پرداخت: {fmt(inv.paid_amount)}\n⚠️ <b>مانده: {fmt(inv.remaining)}</b>",
        reply_markup=invoice_detail(inv.id, sv, inv.invoice_number)
    )
    await cb.answer()

@router.callback_query(F.data == "inv:new")
async def inv_new(cb: CallbackQuery, state: FSMContext, session: AsyncSession):
    r = await session.execute(select(Client).order_by(Client.name))
    clients = r.scalars().all()
    if not clients: await cb.answer("⚠️ اول یک مشتری ثبت کنید!", show_alert=True); return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    kb = InlineKeyboardBuilder()
    for c in clients: kb.row(InlineKeyboardButton(text=f"👤 {c.name}", callback_data=f"inv_cli:{c.id}"))
    kb.row(InlineKeyboardButton(text="❌ لغو", callback_data="nav:main"))
    await state.set_state(InvoiceForm.client)
    await cb.message.edit_text("👤 مشتری را انتخاب کنید:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("inv_cli:"))
async def inv_sel_client(cb: CallbackQuery, state: FSMContext):
    cid = int(cb.data.split(":")[1])
    await state.update_data(client_id=cid, inv_number=gen_invoice_number(), items=[])
    await state.set_state(InvoiceForm.item_desc)
    await cb.message.edit_text("📋 شرح کالا/خدمت:", reply_markup=back_btn("inv:list:0"))
    await cb.answer()

@router.message(InvoiceForm.item_desc)
async def inv_item_desc(msg: Message, state: FSMContext):
    await state.update_data(cur_desc=msg.text); await state.set_state(InvoiceForm.item_qty)
    await msg.answer("📊 تعداد:", reply_markup=back_btn("inv:list:0"))

@router.message(InvoiceForm.item_qty)
async def inv_item_qty(msg: Message, state: FSMContext):
    try: qty = float(msg.text)
    except: qty = 1
    await state.update_data(cur_qty=qty); await state.set_state(InvoiceForm.item_unit)
    await msg.answer("📏 واحد (عدد / کیلو / ساعت):", reply_markup=back_btn("inv:list:0"))

@router.message(InvoiceForm.item_unit)
async def inv_item_unit(msg: Message, state: FSMContext):
    await state.update_data(cur_unit=msg.text); await state.set_state(InvoiceForm.item_price)
    await msg.answer("💰 قیمت واحد (تومان):", reply_markup=back_btn("inv:list:0"))

@router.message(InvoiceForm.item_price)
async def inv_item_price(msg: Message, state: FSMContext):
    try: price = float(msg.text.replace(",",""))
    except: await msg.answer("❌ قیمت را درست وارد کنید:"); return
    data = await state.get_data()
    items = data.get("items",[])
    items.append({"description":data["cur_desc"],"quantity":data["cur_qty"],"unit":data.get("cur_unit","عدد"),"unit_price":price})
    await state.update_data(items=items)
    total = sum(it["quantity"]*it["unit_price"] for it in items)
    await msg.answer(f"✅ قلم اضافه شد! ({len(items)} قلم | جمع: {total:,.0f} تومان)", reply_markup=add_more_items())

@router.callback_query(F.data == "inv:addmore")
async def inv_addmore(cb: CallbackQuery, state: FSMContext):
    await state.set_state(InvoiceForm.item_desc)
    await cb.message.edit_text("📋 شرح کالا/خدمت:", reply_markup=back_btn("inv:list:0"))
    await cb.answer()

@router.callback_query(F.data == "inv:finish")
async def inv_finish(cb: CallbackQuery, state: FSMContext):
    await state.set_state(InvoiceForm.discount)
    await cb.message.edit_text("🎯 مقدار تخفیف (تومان) — 0 برای بدون تخفیف:", reply_markup=back_btn("inv:list:0"))
    await cb.answer()

@router.message(InvoiceForm.discount)
async def inv_discount(msg: Message, state: FSMContext):
    try: d = float(msg.text.replace(",",""))
    except: d = 0
    await state.update_data(discount=d); await state.set_state(InvoiceForm.tax)
    await msg.answer("💸 نرخ مالیات (درصد) — 9 پیش‌فرض:", reply_markup=back_btn("inv:list:0"))

@router.message(InvoiceForm.tax)
async def inv_tax(msg: Message, state: FSMContext):
    try: t = float(msg.text)
    except: t = 9
    await state.update_data(tax_rate=t); await state.set_state(InvoiceForm.notes)
    await msg.answer("📝 توضیحات (یا — برای صرف نظر):", reply_markup=back_btn("inv:list:0"))

@router.message(InvoiceForm.notes)
async def inv_notes(msg: Message, state: FSMContext, session: AsyncSession, is_admin: bool):
    data = await state.get_data()
    inv = Invoice(invoice_number=data["inv_number"], client_id=data["client_id"],
                  discount=data.get("discount",0), tax_rate=data.get("tax_rate",9),
                  notes=msg.text if msg.text != "—" else None, status=InvoiceStatus.DRAFT)
    session.add(inv); await session.flush()
    for it in data["items"]:
        session.add(InvoiceItem(invoice_id=inv.id, description=it["description"], quantity=it["quantity"], unit=it["unit"], unit_price=it["unit_price"]))
    await session.commit(); await state.clear()
    await msg.answer(f"✅ فاکتور <b>{inv.invoice_number}</b> ساخته شد! 🎉", reply_markup=main_menu(is_admin=is_admin))

@router.callback_query(F.data.startswith("inv:markpaid:"))
async def inv_markpaid(cb: CallbackQuery, session: AsyncSession):
    inv_id = int(cb.data.split(":")[2])
    inv = await _load(session, inv_id)
    if inv:
        if inv.remaining > 0: session.add(Payment(invoice_id=inv.id, amount=inv.remaining, method=PaymentMethod.CASH, description="پرداخت کامل"))
        inv.paid_amount = inv.total; inv.status = InvoiceStatus.PAID
        await session.commit()
    await cb.answer("✅ پرداخت کامل ثبت شد!", show_alert=True)
    await inv_view(cb, session)

@router.callback_query(F.data.startswith("inv:send:"))
async def inv_send(cb: CallbackQuery, session: AsyncSession):
    inv_id = int(cb.data.split(":")[2])
    r = await session.execute(select(Invoice).where(Invoice.id==inv_id))
    inv = r.scalar_one_or_none()
    if inv: inv.status = InvoiceStatus.SENT; await session.commit()
    await cb.answer("✅ ارسال شده اعلام شد!", show_alert=True)
    await inv_view(cb, session)

@router.callback_query(F.data.startswith("inv:pdf:"))
async def inv_pdf(cb: CallbackQuery, session: AsyncSession):
    inv_id = int(cb.data.split(":")[2])
    inv = await _load(session, inv_id)
    if not inv: await cb.answer("یافت نشد!", show_alert=True); return
    from app.services.pdf_service import generate_invoice_pdf
    from app.core.config import settings
    pdf_bytes = generate_invoice_pdf(inv, settings.COMPANY_NAME, settings.LOGO_PATH)
    await cb.message.answer_document(BufferedInputFile(pdf_bytes, filename=f"{inv.invoice_number}.pdf"), caption=f"📄 فاکتور {inv.invoice_number}")
    await cb.answer()

@router.callback_query(F.data.startswith("inv:del:"))
async def inv_del_confirm(cb: CallbackQuery, session: AsyncSession):
    inv_id = int(cb.data.split(":")[2])
    r = await session.execute(select(Invoice).where(Invoice.id==inv_id))
    inv = r.scalar_one_or_none()
    if not inv: await cb.answer("یافت نشد!", show_alert=True); return
    await cb.message.edit_text(f"⚠️ فاکتور <b>{inv.invoice_number}</b> حذف شود؟", reply_markup=confirm_kb("inv", inv_id))
    await cb.answer()

@router.callback_query(F.data.startswith("confirm:inv:"))
async def inv_del_exec(cb: CallbackQuery, session: AsyncSession):
    inv_id = int(cb.data.split(":")[2])
    r = await session.execute(select(Invoice).where(Invoice.id==inv_id))
    inv = r.scalar_one_or_none()
    if inv: await session.delete(inv); await session.commit()
    await cb.answer("✅ حذف شد!", show_alert=True)
    r2 = await session.execute(select(Invoice).options(selectinload(Invoice.items),selectinload(Invoice.payments)).order_by(Invoice.id.desc()))
    invs = r2.scalars().all()
    await cb.message.edit_text(f"📄 <b>فاکتورها</b> ({len(invs)} عدد)", reply_markup=invoice_list(invs))
