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
)

# ----------------------------------------------------
# 0. RENDER FLASK SERVER
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
BOT_TOKEN = "8944862071:AAH5hwsxab2yTV4LwMRoAvU_8JtkZKWksvs"
ADMIN_ID = [7214612272, 607901580]

USD_RATE = 13000      # 1 USD = 13,000 UZS
RATES = {6: 0.30, 12: 0.45} # 6 oy: 30%, 12 oy: 45%

logging.basicConfig(level=logging.INFO)
router = Router()

users_db = set()
orders_db = []

# ----------------------------------------------------
# MATNLAR
# ----------------------------------------------------
TEXTS = {
    'uz': {
        'welcome': "👋 <b>Xush kelibsiz!</b>\n\nNasiya xizmatimizdan foydalanish uchun kerakli bo'limni tanlang 👇",
        'btn_nasiya': "📝 Nasiya rasmiylashtirish",
        'btn_about': "ℹ️ Bot haqida",
        'btn_lang': "🌐 Tilni o'zgartirish",
        'select_currency': "💱 <b>Summani qaysi valyutada kiritasiz?</b>",
        'enter_price': "💰 Summani <b>{symbol}</b>da kiriting:\n<i>(Masalan: {example})</i>",
        'enter_dp': "💵 Boshlang'ich to'lov summasini kiriting (<b>{symbol}</b>da):\n<i>(Agar boshlang'ich to'lov bo'lmasa, 0 kiriting)</i>",
        'dp_choice': "💵 Kiritilgan summa: <b>{price:,.0f} {symbol}</b>\n\nBoshlang'ich to'lov qilasizmi?",
        'select_duration': "Nasiya muddatini tanlang:",
        'passport_req': "📄 <b>Pasport yoki ID karta</b>\n\nIltimos, pasportingiz rasmini yoki PDF faylini yuboring:",
        'address_req': "📍 <b>Yashash manzilingizni kiriting:</b>\n<i>Namuna: Qo'qon shahar, Navoiy ko'chasi 15-uy</i>",
        'phone_req': "📞 <b>Telefon raqamingizni kiriting:</b>\n<i>Namuna: +998901234567</i>",
        'back': "⬅️ Orqaga",
        'cancel': "❌ Bekor qilish",
        'btn_dp_no': "🚫 Boshlang'ich to'lovsiz",
        'btn_dp_yes': "💵 Boshlang'ich to'lov bilan",
        'btn_continue': "✅ Davom etish",
        'btn_submit': "🚀 Arizani Yuborish",
        'about_text': (
            "✨ <b>NASIYA BOZOR BOTI HAQIDA TO'LIQ MA'LUMOT</b> ✨\n\n"
            "Siz istalgan do'kondan o'zingizga yoqqan buyumni tanlaysiz, "
            "biz uni siz uchun naqdga sotib olamiz va sizga halol nasiya savdo sharti bilan bo'lib-bo'lib to'lashga beramiz!\n\n"
            "📌 <b>Boshlang'ich to'lov:</b>\n"
            "• Boshlang'ich to'lovsiz yoki ixtiyoriy summa to'lagan holda rasmiylashtirishingiz mumkin.\n\n"
            "📄 <b>Talab qilinadigan hujjatlar:</b>\n"
            "• Faqatgina Pasport yoki ID karta va yashash manzilingiz kifoya."
        ),
        'cancelled': "❌ Bekor qilindi.",
        'success_sent': "🎉 <b>Arizangiz muvaffaqiyatli yuborildi!</b>\nTez orada adminlarimiz siz bilan bog'lanishadi."
    },
    'en': {
        'welcome': "👋 <b>Welcome!</b>\n\nPlease select a section 👇",
        'btn_nasiya': "📝 New Request",
        'btn_about': "ℹ️ About Bot",
        'btn_lang': "🌐 Change Language",
        'select_currency': "💱 <b>Select currency:</b>",
        'enter_price': "💰 Enter amount in <b>{symbol}</b>:\n<i>(Example: {example})</i>",
        'enter_dp': "💵 Enter down payment amount (in <b>{symbol}</b>):",
        'dp_choice': "💵 Amount: <b>{price:,.0f} {symbol}</b>\n\nWould you like to make a down payment?",
        'select_duration': "Select duration:",
        'passport_req': "📄 Send passport photo/PDF:",
        'address_req': "📍 Enter home address:",
        'phone_req': "📞 Enter phone number:",
        'back': "⬅️ Back",
        'cancel': "❌ Cancel",
        'btn_dp_no': "🚫 No down payment",
        'btn_dp_yes': "💵 With down payment",
        'btn_continue': "✅ Continue",
        'btn_submit': "🚀 Submit Application",
        'about_text': "✨ <b>NASIYA BOZOR BOT</b> ✨\n\nEasy monthly installments!",
        'cancelled': "❌ Cancelled.",
        'success_sent': "🎉 Application submitted successfully!"
    },
    'ru': {
        'welcome': "👋 <b>Добро пожаловать!</b>\n\nВыберите раздел 👇",
        'btn_nasiya': "📝 Оформить рассрочку",
        'btn_about': "ℹ️ О боте",
        'btn_lang': "🌐 Изменить язык",
        'select_currency': "💱 <b>Выберите валюту:</b>",
        'enter_price': "💰 Введите сумму в <b>{symbol}</b>:\n<i>(Пример: {example})</i>",
        'enter_dp': "💵 Введите сумму взноса (в <b>{symbol}</b>):",
        'dp_choice': "💵 Сумма: <b>{price:,.0f} {symbol}</b>\n\nПервоначальный взнос?",
        'select_duration': "Выберите срок:",
        'passport_req': "📄 Отправьте фото паспорта:",
        'address_req': "📍 Введите ваш адрес:",
        'phone_req': "📞 Введите номер телефона:",
        'back': "⬅️ Назад",
        'cancel': "❌ Отмена",
        'btn_dp_no': "🚫 Без взноса",
        'btn_dp_yes': "💵 Со взносом",
        'btn_continue': "✅ Продолжить",
        'btn_submit': "🚀 Отправить",
        'about_text': "✨ <b>NASIYA BOZOR BOT</b> ✨\n\nРассрочка!",
        'cancelled': "❌ Отменено.",
        'success_sent': "🎉 Заявка успешно отправлена!"
    }
}

# ----------------------------------------------------
# 1. FSM STATES
# ----------------------------------------------------
class NasiyaOrder(StatesGroup):
    waiting_for_lang = State()
    waiting_for_currency = State()
    waiting_for_price = State()
    waiting_for_down_payment_choice = State()
    waiting_for_down_payment_amount = State()
    waiting_for_duration = State()
    confirm_order = State()
    waiting_for_passport = State()
    waiting_for_address = State()
    waiting_for_phone = State()
    final_confirm = State()

class AdminBroadcast(StatesGroup):
    waiting_for_message = State()

# ----------------------------------------------------
# 2. HISOB-KITOB LOGIKASI (YANGI MATIQ)
# ----------------------------------------------------
def calculate_nasiya(input_price: float, input_dp: float, months: int, currency_type: str):
    # 1. Avval kiritilgan narx va boshlang'ich to'lovni so'mga o'giramiz
    if currency_type == "usd":
        price_uzs = input_price * USD_RATE
        dp_uzs = input_dp * USD_RATE
    else:
        price_uzs = input_price
        dp_uzs = input_dp

    # 2. Qoldiq summani topamiz
    remaining_uzs = price_uzs - dp_uzs

    # 3. So'mdagi qoldiqni oyga (6 yoki 12 ga) bo'lamiz
    base_monthly_uzs = remaining_uzs / months

    # 4. Bo'lingan bir oylik summani ustama foiziga ko'paytiramiz (masalan 12 oy uchun 1.45 ga)
    margin = RATES[months]
    monthly_uzs = base_monthly_uzs * (1 + margin)

    today = datetime.now()
    schedule = []
    for i in range(1, months + 1):
        due_date = today + relativedelta(months=i)
        schedule.append({
            "month": i,
            "date": due_date.strftime("%d.%m.%Y"),
            "amount": round(monthly_uzs)
        })

    return {
        "months": months,
        "monthly_uzs": round(monthly_uzs),
        "schedule": schedule,
        "price_uzs": round(price_uzs),
        "dp_uzs": round(dp_uzs),
        "input_price": input_price,
        "input_dp": input_dp,
        "currency_type": currency_type
    }

# ----------------------------------------------------
# 3. TUGMALAR (KEYBOARDS)
# ----------------------------------------------------
def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])

def get_main_menu(lang='uz'):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t['btn_nasiya'])],
            [KeyboardButton(text=t['btn_about']), KeyboardButton(text=t['btn_lang'])]
        ],
        resize_keyboard=True
    )

def get_back_keyboard(lang='uz'):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TEXTS[lang]['back'])]],
        resize_keyboard=True
    )

def get_currency_keyboard(lang='uz'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 Dollar ($)", callback_data="curr_usd"),
            InlineKeyboardButton(text="🇺🇿 So'm (UZS)", callback_data="curr_uzs")
        ],
        [InlineKeyboardButton(text=TEXTS[lang]['cancel'], callback_data="confirm_no")]
    ])

def get_dp_keyboard(lang='uz'):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['btn_dp_no'], callback_data="dp_no")],
        [InlineKeyboardButton(text=t['btn_dp_yes'], callback_data="dp_yes")],
        [InlineKeyboardButton(text=t['cancel'], callback_data="confirm_no")]
    ])

def get_duration_keyboard(lang='uz'):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="6 oy", callback_data="duration_6"),
            InlineKeyboardButton(text="12 oy", callback_data="duration_12")
        ],
        [InlineKeyboardButton(text=t['cancel'], callback_data="confirm_no")]
    ])

def get_confirm_keyboard(lang='uz'):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['btn_continue'], callback_data="confirm_yes")],
        [InlineKeyboardButton(text=t['cancel'], callback_data="confirm_no")]
    ])

def get_final_submit_keyboard(lang='uz'):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t['btn_submit'], callback_data="send_to_admin")],
        [InlineKeyboardButton(text=t['cancel'], callback_data="confirm_no")]
    ])

def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Tizim statistikasi"), KeyboardButton(text="📋 Arizalar ro'yxati")],
            [KeyboardButton(text="📨 Xabarnoma yuborish"), KeyboardButton(text="⚙️ Tizim Foizlari va Kursi")],
            [KeyboardButton(text="⬅️ Bosh menyuga qaytish")]
        ],
        resize_keyboard=True
    )

# ----------------------------------------------------
# 4. HANDLERS
# ----------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    users_db.add(message.from_user.id)
    
    await message.answer(
        "🌐 <b>Tilni tanlang / Select language / Выберите язык:</b>",
        reply_markup=get_lang_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_lang)

@router.callback_query(NasiyaOrder.waiting_for_lang, F.data.startswith("lang_"))
async def process_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]['welcome'],
        reply_markup=get_main_menu(lang),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.text.in_({"🌐 Tilni o'zgartirish", "🌐 Change Language", "🌐 Изменить язык"}))
async def change_lang(message: Message, state: FSMContext):
    await message.answer(
        "🌐 <b>Tilni tanlang / Select language / Выберите язык:</b>",
        reply_markup=get_lang_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_lang)

@router.message(F.text.in_({"ℹ️ Bot haqida", "ℹ️ About Bot", "ℹ️ О боте"}))
async def about_bot(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    await message.answer(TEXTS[lang]['about_text'], parse_mode="HTML")

@router.message(F.text.in_({"📝 Nasiya rasmiylashtirish", "📝 New Request", "📝 Оформить рассрочку"}))
async def start_nasiya(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')

    await message.answer(
        TEXTS[lang]['select_currency'],
        reply_markup=get_currency_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_currency)

@router.callback_query(NasiyaOrder.waiting_for_currency, F.data.startswith("curr_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    curr = callback.data.split("_")[1]
    data = await state.get_data()
    lang = data.get('lang', 'uz')

    symbol = "$" if curr == "usd" else "so'm"
    example = "500" if curr == "usd" else "6,500,000"

    await state.update_data(currency_type=curr, currency_symbol=symbol)

    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]['enter_price'].format(symbol=symbol, example=example),
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_price)
    await callback.answer()

@router.message(NasiyaOrder.waiting_for_price, F.text)
async def process_price(message: Message, state: FSMContext):
    if message.text in ["⬅️ Orqaga", "⬅️ Back", "⬅️ Назад"]:
        data = await state.get_data()
        lang = data.get('lang', 'uz')
        await message.answer("Bosh menyu", reply_markup=get_main_menu(lang))
        await state.clear()
        return

    clean_text = message.text.replace(" ", "").replace(",", "").replace(".", "")
    if not clean_text.isdigit():
        await message.answer("❌ Iltimos, faqat raqamlardan iborat summa kiriting:")
        return

    price = float(clean_text)
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    symbol = data.get('currency_symbol')

    await state.update_data(price=price)

    await message.answer(
        TEXTS[lang]['dp_choice'].format(price=price, symbol=symbol),
        reply_markup=get_dp_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_down_payment_choice)

@router.callback_query(NasiyaOrder.waiting_for_down_payment_choice, F.data == "dp_no")
async def process_dp_no(callback: CallbackQuery, state: FSMContext):
    await state.update_data(down_payment=0.0)
    data = await state.get_data()
    lang = data.get('lang', 'uz')

    await callback.message.edit_text(
        TEXTS[lang]['select_duration'],
        reply_markup=get_duration_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_duration)
    await callback.answer()

@router.callback_query(NasiyaOrder.waiting_for_down_payment_choice, F.data == "dp_yes")
async def process_dp_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    symbol = data.get('currency_symbol')

    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]['enter_dp'].format(symbol=symbol),
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_down_payment_amount)
    await callback.answer()

@router.message(NasiyaOrder.waiting_for_down_payment_amount, F.text)
async def process_dp_amount(message: Message, state: FSMContext):
    if message.text in ["⬅️ Orqaga", "⬅️ Back", "⬅️ Назад"]:
        data = await state.get_data()
        lang = data.get('lang', 'uz')
        await message.answer("Bosh menyu", reply_markup=get_main_menu(lang))
        await state.clear()
        return

    clean_text = message.text.replace(" ", "").replace(",", "").replace(".", "")
    if not clean_text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting:")
        return

    dp_amount = float(clean_text)
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    price = data.get('price')

    if dp_amount >= price:
        await message.answer("⚠️ Boshlang'ich to'lov umumiy summadan kichik bo'lishi kerak!")
        return

    await state.update_data(down_payment=dp_amount)

    await message.answer(
        TEXTS[lang]['select_duration'],
        reply_markup=get_duration_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_duration)

@router.callback_query(NasiyaOrder.waiting_for_duration, F.data.startswith("duration_"))
async def process_duration(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    price = data.get('price')
    dp = data.get('down_payment', 0.0)
    curr_type = data.get('currency_type')

    calc = calculate_nasiya(price, dp, months, curr_type)
    await state.update_data(calc_result=calc)

    schedule_text = "\n".join([f"   • {i['month']}-oy ({i['date']}): <b>{i['amount']:,} so'm</b>" for i in calc['schedule']])

    summary = (
        f"📋 <b>NASIYA HISOBI</b>\n\n"
        f"🔹 Boshlang'ich to'lov: <b>{calc['dp_uzs']:,} so'm</b>\n"
        f"🔹 Muddat: <b>{calc['months']} oy</b>\n"
        f"💳 Oylik to'lov: <b>{calc['monthly_uzs']:,} so'm/oy</b>\n\n"
        f"📅 <b>To'lovlar grafigi:</b>\n{schedule_text}"
    )

    await callback.message.edit_text(
        summary,
        reply_markup=get_confirm_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.confirm_order)
    await callback.answer()

@router.callback_query(NasiyaOrder.confirm_order, F.data == "confirm_yes")
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')

    await callback.message.delete()
    await callback.message.answer(
        TEXTS[lang]['passport_req'],
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_passport)
    await callback.answer()

@router.message(NasiyaOrder.waiting_for_passport, F.photo | F.document)
async def process_passport(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    file_type = "photo" if message.photo else "document"

    await state.update_data(passport_file=file_id, passport_type=file_type)

    data = await state.get_data()
    lang = data.get('lang', 'uz')

    await message.answer(
        TEXTS[lang]['address_req'],
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_address)

@router.message(NasiyaOrder.waiting_for_address, F.text)
async def process_address(message: Message, state: FSMContext):
    if message.text in ["⬅️ Orqaga", "⬅️ Back", "⬅️ Назад"]:
        data = await state.get_data()
        lang = data.get('lang', 'uz')
        await message.answer("Bosh menyu", reply_markup=get_main_menu(lang))
        await state.clear()
        return

    await state.update_data(user_address=message.text.strip())

    data = await state.get_data()
    lang = data.get('lang', 'uz')

    await message.answer(
        TEXTS[lang]['phone_req'],
        reply_markup=get_back_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.waiting_for_phone)

@router.message(NasiyaOrder.waiting_for_phone, F.text)
async def process_phone(message: Message, state: FSMContext):
    if message.text in ["⬅️ Orqaga", "⬅️ Back", "⬅️ Назад"]:
        data = await state.get_data()
        lang = data.get('lang', 'uz')
        await message.answer("Bosh menyu", reply_markup=get_main_menu(lang))
        await state.clear()
        return

    await state.update_data(user_phone=message.text.strip())

    data = await state.get_data()
    lang = data.get('lang', 'uz')
    calc = data.get('calc_result')

    final_text = (
        "📑 <b>ARIZA TAYYOR BO'LDI</b>\n\n"
        f"💵 Boshlang'ich: <b>{calc['dp_uzs']:,} so'm</b>\n"
        f"📅 Muddat: <b>{calc['months']} oy</b>\n"
        f"💳 Oylik to'lov: <b>{calc['monthly_uzs']:,} so'm/oy</b>\n"
        f"📍 Manzil: <b>{data.get('user_address')}</b>\n"
        f"📞 Tel: <b>{message.text}</b>\n"
    )

    await message.answer(
        final_text,
        reply_markup=get_final_submit_keyboard(lang),
        parse_mode="HTML"
    )
    await state.set_state(NasiyaOrder.final_confirm)

@router.callback_query(F.data == "confirm_no")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(TEXTS[lang]['cancelled'], reply_markup=get_main_menu(lang))
    await callback.answer()

@router.callback_query(NasiyaOrder.final_confirm, F.data == "send_to_admin")
async def send_order_to_admin(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    calc = data.get('calc_result')
    
    orders_db.append(calc)
    username = f"@{callback.from_user.username}" if callback.from_user.username else "Yo'q"

    admin_text = (
        f"📥 <b>YANGI NASIYA ARIZASI!</b>\n\n"
        f"👤 <b>Mijoz:</b> {callback.from_user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{callback.from_user.id}</code>\n"
        f"📱 <b>Username:</b> {username}\n"
        f"📞 <b>Telefon:</b> <code>{data.get('user_phone')}</code>\n"
        f"📍 <b>Manzil:</b> {data.get('user_address')}\n\n"
        f"💵 <b>Kiritgan valyutasi:</b> {calc['currency_type'].upper()}\n"
        f"💰 <b>Kiritgan summasi:</b> {calc['input_price']:,}\n"
        f"🔄 <b>So'mdagi miqdori:</b> {calc['price_uzs']:,} so'm\n"
        f"💵 <b>Boshlang'ich:</b> {calc['dp_uzs']:,} so'm\n"
        f"📅 <b>Muddat:</b> {calc['months']} oy\n"
        f"💳 <b>Oylik to'lov:</b> {calc['monthly_uzs']:,} so'm/oy\n"
    )

    for admin_id in ADMIN_ID:
        try:
            await callback.bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")
            if data.get("passport_type") == "photo":
                await callback.bot.send_photo(chat_id=admin_id, photo=data.get("passport_file"))
            else:
                await callback.bot.send_document(chat_id=admin_id, document=data.get("passport_file"))
        except Exception as e:
            logging.error(f"Admin Error: {e}")

    await callback.message.edit_text(TEXTS[lang]['success_sent'], parse_mode="HTML")
    await state.clear()
    await callback.message.answer("Bosh menyu", reply_markup=get_main_menu(lang))
    await callback.answer()

# ----------------------------------------------------
# 5. ADMIN PANEL
# ----------------------------------------------------
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        return
    await state.clear()
    await message.answer("⚙️ <b>Nasiya Bot Admin Paneliga xush kelibsiz!</b>", reply_markup=get_admin_menu(), parse_mode="HTML")

@router.message(F.text == "📊 Tizim statistikasi")
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(
        f"📊 <b>BOT TIZIMI STATISTIKASI</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{len(users_db)} ta</b>\n"
        f"📥 Arizalar soni: <b>{len(orders_db)} ta</b>",
        parse_mode="HTML"
    )

@router.message(F.text == "📋 Arizalar ro'yxati")
async def admin_orders(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(f"📋 Jami kelib tushgan arizalar: <b>{len(orders_db)} ta</b>", parse_mode="HTML")

@router.message(F.text == "⚙️ Tizim Foizlari va Kursi")
async def admin_rates(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(
        "⚙️ <b>MAXFIY TIZIM SOZLAMALARI:</b>\n\n"
        f"💵 <b>Hozirgi dollar kursi:</b> 1 USD = {USD_RATE:,} UZS\n"
        f"📈 <b>6 oylik ustama foizi:</b> {int(RATES[6]*100)}%\n"
        f"📈 <b>12 oylik ustama foizi:</b> {int(RATES[12]*100)}%",
        parse_mode="HTML"
    )

@router.message(F.text == "📨 Xabarnoma yuborish")
async def admin_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer("📝 Yubormoqchi bo'lgan xabaringizni kiriting:")
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

@router.message(F.text == "⬅️ Bosh menyuga qaytish")
async def back_to_user_menu(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    await message.answer("Asosiy menyuga qaytdingiz:", reply_markup=get_main_menu(lang))

# ----------------------------------------------------
# 6. RUN BOT
# ----------------------------------------------------
async def main():
    bot = Bot(token="8944862071:AAH5hwsxab2yTV4LwMRoAvU_8JtkZKWksvs")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())