import asyncio
import logging
import os
from datetime import datetime
from threading import Thread
from dateutil.relativedelta import relativedelta
from flask import Flask

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ----------------------------------------------------
# 0. RENDER UCHUN FLASK PORT SERVER
# ----------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ----------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------
BOT_TOKEN = "8944862071:AAFcxHz0fIAMO3r6GLSXql7xrn_jzFk_Puc"

# IKKITA ADMIN ID-SI
ADMIN_ID = [7214612272, 607901580]  

logging.basicConfig(level=logging.INFO)
router = Router()

# Vaqtinchalik ma'lumotlar bazasi
users_db = set()
orders_db = []

# ----------------------------------------------------
# 1. FSM STATES (Bosqichlar)
# ----------------------------------------------------
class NasiyaOrder(StatesGroup):
    waiting_for_price = State()          # Narx kiritish
    waiting_for_down_payment_choice = State() # Oldindan to'lov bormi/yo'qmi
    waiting_for_down_payment_amount = State() # Oldindan to'lov summasi
    waiting_for_duration = State()       # Muddat tanlash
    confirm_order = State()              # To'lov grafigini tasdiqlash
    waiting_for_passport = State()       # Pasport rasm/PDF
    waiting_for_address = State()        # Yashash manzili
    waiting_for_phone = State()          # Telefon raqami (Matn ko'rinishida)
    final_confirm = State()              # Oxirgi qayta tasdiqlash

class AdminBroadcast(StatesGroup):
    waiting_for_message = State()        # Adminga xabar tarqatish holati

# ----------------------------------------------------
# 2. KALKULYATOR MANTIQLARI (6 oy: 30%, 12 oy: 45%)
# ----------------------------------------------------
RATES = {
    6: 0.30,   # 6 oyga 30%
    12: 0.45   # 12 oyga 45%
}

def calculate_nasiya(total_price: float, down_payment: float, months: int):
    remaining_amount = total_price - down_payment
    margin_rate = RATES[months]
    
    total_financed = remaining_amount * (1 + margin_rate)
    monthly_payment = total_financed / months
    
    today = datetime.now()
    schedule = []
    for i in range(1, months + 1):
        due_date = today + relativedelta(months=i)
        schedule.append({
            "month": i,
            "date": due_date.strftime("%d.%m.%Y"),
            "amount": round(monthly_payment)
        })
        
    return {
        "original_price": total_price,
        "down_payment": down_payment,
        "remaining_amount": remaining_amount,
        "months": months,
        "margin_percent": int(margin_rate * 100),
        "total_amount": round(total_financed + down_payment),
        "monthly_payment": round(monthly_payment),
        "schedule": schedule
    }

# ----------------------------------------------------
# 3. TUGMALAR (Keyboards)
# ----------------------------------------------------
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Nasiya rasmiylashtirish"),
                KeyboardButton(text="ℹ️ Bot haqida")
            ]
        ],
        resize_keyboard=True
    )

def get_back_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )

def get_down_payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚫 Boshlang'ich to'lovsiz", callback_data="dp_no")
        ],
        [
            InlineKeyboardButton(text="💵 Boshlang'ich to'lov bilan", callback_data="dp_yes")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="confirm_no")
        ]
    ])

def get_duration_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="6 oy", callback_data="duration_6"),
            InlineKeyboardButton(text="12 oy", callback_data="duration_12"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_dp_choice"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="confirm_no")
        ]
    ])

def get_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Davom etish", callback_data="confirm_yes"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_duration"),
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="confirm_no")
        ]
    ])

def get_final_submit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Arizani Adminga Yuborish", callback_data="send_to_admin"),
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="confirm_no"),
        ]
    ])

def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Tizim statistikasi"),
                KeyboardButton(text="📋 Arizalar ro'yxati")
            ],
            [
                KeyboardButton(text="📨 Xabarnoma yuborish"),
                KeyboardButton(text="➕ Majburiy kanallar")
            ],
            [
                KeyboardButton(text="📈 Foiz stavkalari")
            ],
            [
                KeyboardButton(text="⬅️ Bosh menyu")
            ]
        ],
        resize_keyboard=True
    )

# ----------------------------------------------------
# 4. USER HANDLERLARI
# ----------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    users_db.add(message.from_user.id)
    
    await message.answer(
        "👋 <b>Xush kelibsiz!</b>\n\n"
        "Ushbu bot orqali siz do'kondan sotib olmoqchi bo'lgan buyumingizni "
        "6 oy yoki 12 oy muddatga nasiyaga rasmiylashtirishingiz mumkin.\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "❓ <b>YORDAM VA BOT HAQIDA</b>\n\n"
        "• /start — Botni qayta ishga tushirish\n"
        "• /cancel — Har qanday amaliyotni bekor qilib, boshiga qaytish\n\n"
        "📩 Qo'shimcha savollar bo'lsa, ma'muriyat bilan bog'laning."
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Barcha amallaringiz bekor qilindi.", reply_markup=get_main_menu())

@router.message(F.text == "ℹ️ Bot haqida")
async def about_bot(message: Message):
    about_text = (
        "✨ <b>NASIYA BOT — ORZULARINGIZNI BUGUN RO'YOBGA CHIQARING!</b> ✨\n\n"
        "🛍️ <b>Bu bot nima qilib beradi?</b>\n"
        "Siz istalgan do'kondan o'zingizga yoqqan buyumni (gilam, mebel, maishiy texnika va h.k.) tanlaysiz, "
        "lekin pulingiz yetmayptimi? <b>Xavotir olmang!</b> Biz uni siz uchun sotib olamiz, siz esa bo'lib-bo'lib to'laysiz! 😉\n\n"
        "⚡️ <b>BIZNING AFZALLIKLARIMIZ:</b>\n"
        "└ ⏱️ <b>Tezkor:</b> 5 daqiqada hisob-kitob\n"
        "└ 📑 <b>Ortiqcha hujjatlarsiz:</b> Faqat pasport kifoya\n"
        "└ 📅 <b>Qulay muddat:</b> 6 yoki 12 oy\n"
        "└ 💸 <b>Hamyonbop:</b> Halol va aniq hisob-kitob\n\n"
        "🚀 <b>Qanday ishlaydi?</b>\n"
        "1️⃣ <b>📝 Nasiya rasmiylashtirish</b> tugmasini bosing\n"
        "2️⃣ Narxni kiriting va o'zingizga qulay muddatni tanlang\n"
        "3️⃣ Tayyor to'lov grafigi bilan tanishib, arizani yuboring!\n\n"
        "🤝 <i>Halollik va qulaylik — bizning bosh mezonimiz!</i>\n\n"
    )
    await message.answer(about_text, parse_mode="HTML")

@router.message(F.text == "📝 Nasiya rasmiylashtirish")
async def start_nasiya(message: Message, state: FSMContext):
    await message.answer(
        "💰 Sotib olmoqchi bo'lgan mahsulotingiz narxini so'mda kiriting:\n"
        "<i>(Masalan: 5000000)</i>",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_price)

@router.message(NasiyaOrder.waiting_for_price, F.text == "⬅️ Orqaga")
async def back_from_price(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=get_main_menu())

@router.message(NasiyaOrder.waiting_for_price, F.text)
async def process_price(message: Message, state: FSMContext):
    clean_text = message.text.replace(" ", "").replace(",", "")
    
    if not clean_text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamlardan iborat summa kiriting:")
        return

    price = float(clean_text)
    if price < 100000:
        await message.answer("⚠️ Eng kam nasiya summasi 100 000 so'm bo'lishi kerak.")
        return

    await state.update_data(price=price)
    
    await message.answer(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n\n"
        "Boshlang'ich to'lov qilasizmi?",
        reply_markup=get_down_payment_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_down_payment_choice)

@router.callback_query(NasiyaOrder.waiting_for_down_payment_choice, F.data == "dp_no")
async def process_dp_no(callback: CallbackQuery, state: FSMContext):
    await state.update_data(down_payment=0.0)
    user_data = await state.get_data()
    price = user_data.get("price")

    await callback.message.edit_text(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n"
        f"💳 Boshlang'ich to'lov: <b>0 so'm</b>\n\n"
        "Nasiya muddatini tanlang:",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_duration)
    await callback.answer()

@router.callback_query(NasiyaOrder.waiting_for_down_payment_choice, F.data == "dp_yes")
async def process_dp_yes(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "💵 Qancha boshlang'ich to'lov qilmoqchisiz? Summani kiriting:\n"
        "<i>(Masalan: 1000000)</i>",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_down_payment_amount)
    await callback.answer()

@router.message(NasiyaOrder.waiting_for_down_payment_amount, F.text == "⬅️ Orqaga")
async def back_from_dp_amount(message: Message, state: FSMContext):
    user_data = await state.get_data()
    price = user_data.get("price")
    
    await message.answer(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n\n"
        "Boshlang'ich to'lov qilasizmi?",
        reply_markup=get_down_payment_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_down_payment_choice)

@router.message(NasiyaOrder.waiting_for_down_payment_amount, F.text)
async def process_dp_amount(message: Message, state: FSMContext):
    clean_text = message.text.replace(" ", "").replace(",", "")
    
    if not clean_text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamlardan iborat summa kiriting:")
        return

    dp_amount = float(clean_text)
    user_data = await state.get_data()
    price = user_data.get("price")

    if dp_amount >= price:
        await message.answer("⚠️ Boshlang'ich to'lov mahsulot narxidan kamroq bo'lishi kerak!")
        return

    await state.update_data(down_payment=dp_amount)

    await message.answer(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n"
        f"💳 Boshlang'ich to'lov: <b>{dp_amount:,.0f} so'm</b>\n"
        f"🔹 Qolgan summa: <b>{(price - dp_amount):,.0f} so'm</b>\n\n"
        "Endi nasiya muddatini tanlang:",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_duration)

@router.callback_query(NasiyaOrder.waiting_for_duration, F.data == "back_to_dp_choice")
async def back_to_dp_choice_handler(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    price = user_data.get("price")

    await callback.message.edit_text(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n\n"
        "Boshlang'ich to'lov qilasizmi?",
        reply_markup=get_down_payment_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_down_payment_choice)
    await callback.answer()

@router.callback_query(NasiyaOrder.waiting_for_duration, F.data.startswith("duration_"))
async def process_duration(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    user_data = await state.get_data()
    price = user_data.get("price")
    down_payment = user_data.get("down_payment", 0.0)

    calc = calculate_nasiya(price, down_payment, months)
    await state.update_data(calc_result=calc)

    schedule_text = "\n".join(
        [f"   • {item['month']}-oy ({item['date']}): <b>{item['amount']:,} so'm</b>" for item in calc["schedule"]]
    )

    dp_text = f"🔹 Boshlang'ich to'lov: <b>{calc['down_payment']:,.0f} so'm</b>\n" if calc['down_payment'] > 0 else ""

    summary_text = (
        f"📋 <b>NASIYA HISOBI</b>\n\n"
        f"🔹 Mahsulot narxi: {calc['original_price']:,.0f} so'm\n"
        f"{dp_text}"
        f"🔹 Nasiya muddati: {calc['months']} oy\n"
        f"🔹 Oylik to'lov: <b>{calc['monthly_payment']:,.0f} so'm/oy</b>\n\n"
        f"📅 <b>To'lovlar grafigi:</b>\n{schedule_text}\n\n"
        f"Pasportni yuklashga o'tish uchun 'Davom etish' tugmasini bosing."
    )

    await callback.message.edit_text(
        summary_text,
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.confirm_order)
    await callback.answer()

@router.callback_query(NasiyaOrder.confirm_order, F.data == "back_to_duration")
async def back_to_duration_handler(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    price = user_data.get("price")
    dp = user_data.get("down_payment", 0.0)
    
    await callback.message.edit_text(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n"
        f"💳 Boshlang'ich to'lov: <b>{dp:,.0f} so'm</b>\n\n"
        "Nasiya muddatini qayta tanlang:",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_duration)
    await callback.answer()

@router.callback_query(NasiyaOrder.confirm_order, F.data == "confirm_yes")
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "📄 <b>Pasport yoki ID karta</b>\n\n"
        "Iltimos, pasportingiz (yoki ID kartangiz) rasmini yoki PDF faylini yuboring:",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_passport)
    await callback.answer()

@router.message(NasiyaOrder.waiting_for_passport, F.text == "⬅️ Orqaga")
async def back_from_passport(message: Message, state: FSMContext):
    user_data = await state.get_data()
    price = user_data.get("price")
    dp = user_data.get("down_payment", 0.0)
    
    await message.answer(
        f"💵 Mahsulot narxi: <b>{price:,.0f} so'm</b>\n"
        f"💳 Boshlang'ich to'lov: <b>{dp:,.0f} so'm</b>\n\n"
        "Nasiya muddatini tanlang:",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_duration)

@router.message(NasiyaOrder.waiting_for_passport, F.photo | F.document)
async def process_passport(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    file_type = "photo" if message.photo else "document"

    await state.update_data(passport_file=file_id, passport_type=file_type)

    await message.answer(
        "📍 <b>Yashash manzilingizni kiriting:</b>\n\n"
        "<i>Iltimos, shahar/tuman, mahalla va uy raqamingizni kiriting.</i>\n"
        "<b>Namuna:</b> <code>Qo'qon shahar, Charxiy MFY, Navoiy ko'chasi 15-uy</code>",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_address)

@router.message(NasiyaOrder.waiting_for_address, F.text == "⬅️ Orqaga")
async def back_from_address(message: Message, state: FSMContext):
    await message.answer(
        "📄 <b>Pasport yoki ID karta</b>\n\n"
        "Iltimos, pasportingiz (yoki ID kartangiz) rasmini qayta yuboring:",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_passport)

@router.message(NasiyaOrder.waiting_for_address, F.text)
async def process_address(message: Message, state: FSMContext):
    address = message.text.strip()
    await state.update_data(user_address=address)

    await message.answer(
        "📞 <b>Telefon raqamingizni kiriting:</b>\n\n"
        "<i>Siz bilan bog'lanishimiz uchun telefon raqamingizni yozib yuboring.</i>\n"
        "<b>Namuna:</b> <code>+998901234567</code>",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_phone)

@router.message(NasiyaOrder.waiting_for_phone, F.text == "⬅️ Orqaga")
async def back_from_phone(message: Message, state: FSMContext):
    await message.answer(
        "📍 <b>Yashash manzilingizni qayta kiriting:</b>\n\n"
        "<b>Namuna:</b> <code>Qo'qon shahar, Charxiy MFY, Navoiy ko'chasi 15-uy</code>",
        reply_markup=get_back_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_address)

@router.message(NasiyaOrder.waiting_for_phone, F.text)
async def process_phone(message: Message, state: FSMContext):
    phone_number = message.text.strip()
    await state.update_data(user_phone=phone_number)

    user_data = await state.get_data()
    calc = user_data.get("calc_result")
    address = user_data.get("user_address")

    dp_text = f"💵 Boshlang'ich to'lov: <b>{calc['down_payment']:,} so'm</b>\n" if calc['down_payment'] > 0 else ""

    final_text = (
        "📑 <b>ARIZA TAYYOR BO'LDI!</b>\n\n"
        f"💰 Mahsulot narxi: <b>{calc['original_price']:,} so'm</b>\n"
        f"{dp_text}"
        f"📅 Muddat: <b>{calc['months']} oy</b>\n"
        f"💳 Oylik to'lov: <b>{calc['monthly_payment']:,} so'm/oy</b>\n"
        f"📍 Manzil: <b>{address}</b>\n"
        f"📞 Telefon raqam: <b>{phone_number}</b>\n"
        f"📎 Hujjatlar: <b>Pasport yuklandi ✅</b>\n\n"
        "Barcha ma'lumotlar to'g'ri bo'lsa, 'Arizani Adminga Yuborish' tugmasini bosing:"
    )

    await message.answer(
        final_text,
        reply_markup=get_final_submit_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.final_confirm)

@router.callback_query(F.data == "confirm_no")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Ariza bekor qilindi.", reply_markup=get_main_menu())
    await callback.answer()

@router.callback_query(NasiyaOrder.final_confirm, F.data == "send_to_admin")
async def send_order_to_admin(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    calc = user_data.get("calc_result")
    user_address = user_data.get("user_address", "Ko'rsatilmadi")
    user_phone = user_data.get("user_phone", "Ko'rsatilmadi")
    
    orders_db.append(calc)

    username = f"@{callback.from_user.username}" if callback.from_user.username else "Yo'q"

    admin_text = (
        f"📥 <b>YANGI NASIYA ARIZASI!</b>\n\n"
        f"👤 <b>Mijoz:</b> {callback.from_user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{callback.from_user.id}</code>\n"
        f"📱 <b>Username:</b> {username}\n"
        f"📞 <b>Telefon raqami:</b> <code>{user_phone}</code>\n"
        f"📍 <b>Manzil:</b> {user_address}\n\n"
        f"💰 <b>Mahsulot narxi:</b> {calc['original_price']:,} so'm\n"
        f"💵 <b>Boshlang'ich to'lov:</b> {calc['down_payment']:,} so'm\n"
        f"🔹 <b>Nasiya qilingan summa:</b> {calc['remaining_amount']:,} so'm\n"
        f"📅 <b>Muddat:</b> {calc['months']} oy ({calc['margin_percent']}%)\n"
        f"💳 <b>Oylik to'lov:</b> {calc['monthly_payment']:,} so'm/oy"
    )

    try:
        for admin_id in ADMIN_ID:
            try:
                await callback.bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")

                await callback.bot.send_message(chat_id=admin_id, text="📄 <b>Mijoz pasporti:</b>", parse_mode="HTML")
                if user_data.get("passport_type") == "photo":
                    await callback.bot.send_photo(chat_id=admin_id, photo=user_data.get("passport_file"))
                else:
                    await callback.bot.send_document(chat_id=admin_id, document=user_data.get("passport_file"))

            except Exception as single_admin_error:
                logging.error(f"Admin {admin_id} ga xabar yuborishda xatolik: {single_admin_error}")

        await callback.message.edit_text(
            "🎉 <b>Arizangiz Adminga muvaffaqiyatli yuborildi!</b>\n\n"
            "Tez orada siz bilan bog'lanamiz.",
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Adminga yuborishda xatolik: {e}")
        await callback.message.edit_text("⚠️ Arizani yuborishda xatolik yuz berdi.")

    await state.clear()
    await callback.message.answer("Asosiy menyu:", reply_markup=get_main_menu())
    await callback.answer()

# ----------------------------------------------------
# 5. ADMIN PANEL HANDLERLARI
# ----------------------------------------------------
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(
        "⚙️ <b>Nasiya Bot Admin Paneliga xush kelibsiz!</b>\n\n"
        "Kerakli boshqaruv bo'limini tanlang 👇",
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "📊 Tizim statistikasi")
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    
    total_users = len(users_db) if users_db else 1
    total_orders = len(orders_db)

    stats_text = (
        "📊 <b>BOT TIZIMI STATISTIKASI</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
        f"📥 Kelib tushgan arizalar: <b>{total_orders} ta</b>\n"
    )
    await message.answer(stats_text, parse_mode="HTML")

@router.message(F.text == "📋 Arizalar ro'yxati")
async def admin_orders(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(f"📋 Jami arizalar soni: <b>{len(orders_db)} ta</b>", parse_mode="HTML")

@router.message(F.text == "📨 Xabarnoma yuborish")
async def admin_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer("📝 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni kiriting:")
    await state.set_state(AdminBroadcast.waiting_for_message)

@router.message(AdminBroadcast.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext):
    count = 0
    for user_id in users_db:
        try:
            await message.copy_to(chat_id=user_id)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Xabar <b>{count}</b> ta foydalanuvchiga yuborildi!", parse_mode="HTML")
    await state.clear()

@router.message(F.text == "➕ Majburiy kanallar")
async def admin_channels(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer("📢 Hozircha majburiy obuna kanallari sozlanmagan.")

@router.message(F.text == "📈 Foiz stavkalari")
async def admin_rates(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    rates_text = (
        "📈 <b>AMALDAGI FOIZ STAVKALARI:</b>\n\n"
        "• 6 oy: <b>30%</b>\n"
        "• 12 oy: <b>45%</b>"
    )
    await message.answer(rates_text, parse_mode="HTML")

@router.message(F.text == "⬅️ Bosh menyu")
async def back_to_user_menu(message: Message):
    await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=get_main_menu())

# ----------------------------------------------------
# 6. RUN BOT
# ----------------------------------------------------
async def main():
    bot = Bot(token="8944862071:AAFcxHz0fIAMO3r6GLSXql7xrn_jzFk_Puc")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()  # Render uchun portni fonda ochadi
    asyncio.run(main())