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
# 0. RENDER FLASK SERVER (24/7 ishlatish uchun)
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
ADMIN_ID = [7214612272, 607901580]  # Ikkita admin ID
USD_RATE = 13000                    # Doimiy fixed kurs: 1 USD = 13,000 UZS

logging.basicConfig(level=logging.INFO)
router = Router()

users_db = set()
orders_db = []

# ----------------------------------------------------
# KOP TILLILIK MATNLARI (MULTILANGUAGE TEXTS)
# ----------------------------------------------------
TEXTS = {
    'uz': {
        'welcome': "👋 <b>Xush kelibsiz!</b>\n\nNasiya xizmatimizdan foydalanish uchun kerakli bo'limni tanlang 👇",
        'btn_nasiya': "📝 Nasiya rasmiylashtirish",
        'btn_about': "ℹ️ Bot haqida",
        'btn_lang': "🌐 Tilni o'zgartirish",
        'select_currency': "💱 <b>Valyutani tanlang:</b>\n<i>(Belgilangan fixed kurs: 1 USD = 13,000 UZS)</i>",
        'enter_price': "💰 Mahsulot narxini <b>{symbol}</b>da kiriting:\n<i>(Masalan: {example})</i>",
        'enter_dp': "💵 Boshlang'ich to'lov summasini <b>{symbol}</b>da kiriting:",
        'dp_choice': "💵 Mahsulot narxi: <b>{price:,.0f} {symbol}</b>\n\nBoshlang'ich to'lov qilasizmi?",
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
            "Siz istalgan do'kondan o'zingizga yoqqan buyumni (telefon, maishiy texnika, kompyuter va h.k.) tanlaysiz, "
            "biz uni siz uchun naqdga sotib olamiz va sizga halol nasiya savdo sharti bilan bo'lib-bo'lib to'lashga beramiz!\n\n"
            "💱 <b>Valyuta va Kurs:</b>\n"
            "• Hisob-kitoblar So'm yoki Dollarda olib boriladi.\n"
            "• Belgilangan o'zgarmas kurs: <b>1 USD = 13,000 UZS</b>\n\n"
            "⏱️ <b>Nasiya muddatlari va ustama foizlari:</b>\n"
            "• <b>6 oy</b> — 30% ustama bilan\n"
            "• <b>12 oy</b> — 45% ustama bilan\n\n"
            "📌 <b>Boshlang'ich to'lov:</b>\n"
            "• Boshlang'ich to'lovsiz yoki ixtiyoriy summa to'lagan holda rasmiylashtirishingiz mumkin.\n\n"
            "📄 <b>Talab qilinadigan hujjatlar:</b>\n"
            "• Faqatgina Pasport yoki ID karta va yashash manzilingiz kifoya."
        ),
        'cancelled': "❌ Bekor qilindi.",
        'success_sent': "🎉 <b>Arizangiz muvaffaqiyatli yuborildi!</b>\nTez orada adminlarimiz siz bilan bog'lanishadi."
    },
    'en': {
        'welcome': "👋 <b>Welcome!</b>\n\nPlease select a section to use our installment service 👇",
        'btn_nasiya': "📝 New Installment Request",
        'btn_about': "ℹ️ About Bot",
        'btn_lang': "🌐 Change Language",
        'select_currency': "💱 <b>Select currency:</b>\n<i>(Fixed rate: 1 USD = 13,000 UZS)</i>",
        'enter_price': "💰 Enter the product price in <b>{symbol}</b>:\n<i>(Example: {example})</i>",
        'enter_dp': "💵 Enter the down payment amount in <b>{symbol}</b>:",
        'dp_choice': "💵 Product price: <b>{price:,.0f} {symbol}</b>\n\nWould you like to make a down payment?",
        'select_duration': "Select installment duration:",
        'passport_req': "📄 <b>Passport or ID card</b>\n\nPlease send a photo or PDF file of your passport:",
        'address_req': "📍 <b>Enter your home address:</b>\n<i>Example: Tashkent city, Amir Timur street 10</i>",
        'phone_req': "📞 <b>Enter your phone number:</b>\n<i>Example: +998901234567</i>",
        'back': "⬅️ Back",
        'cancel': "❌ Cancel",
        'btn_dp_no': "🚫 No down payment",
        'btn_dp_yes': "💵 With down payment",
        'btn_continue': "✅ Continue",
        'btn_submit': "🚀 Submit Application",
        'about_text': (
            "✨ <b>ABOUT NASIYA BOZOR BOT</b> ✨\n\n"
            "Choose any item you like from any store, we buy it for you and provide it with easy monthly installments!\n\n"
            "💱 <b>Currency & Fixed Rate:</b>\n"
            "• Fixed rate: <b>1 USD = 13,000 UZS</b>\n\n"
            "⏱️ <b>Terms & Percentages:</b>\n"
            "• <b>6 months</b> — 30%\n"
            "• <b>12 months</b> — 45%\n\n"
            "📄 <b>Required Documents:</b> Passport or ID card."
        ),
        'cancelled': "❌ Cancelled.",
        'success_sent': "🎉 <b>Application submitted successfully!</b>\nOur managers will contact you soon."
    },
    'ru': {
        'welcome': "👋 <b>Добро пожаловать!</b>\n\nВыберите нужный раздел для оформления рассрочки 👇",
        'btn_nasiya': "📝 Оформить рассрочку",
        'btn_about': "ℹ️ О боте",
        'btn_lang': "🌐 Изменить язык",
        'select_currency': "💱 <b>Выберите валюту:</b>\n<i>(Фиксированный курс: 1 USD = 13,000 UZS)</i>",
        'enter_price': "💰 Введите стоимость товара в <b>{symbol}</b>:\n<i>(Например: {example})</i>",
        'enter_dp': "💵 Введите сумму первоначального взноса в <b>{symbol}</b>:",
        'dp_choice': "💵 Стоимость товара: <b>{price:,.0f} {symbol}</b>\n\nБудете делать первоначальный взнос?",
        'select_duration': "Выберите срок рассрочки:",
        'passport_req': "📄 <b>Паспорт или ID карта</b>\n\nПожалуйста, отправьте фото или PDF вашего паспорта:",
        'address_req': "📍 <b>Введите ваш адрес проживания:</b>\n<i>Пример: г. Ташкент, ул. Навои 15</i>",
        'phone_req': "📞 <b>Введите ваш номер телефона:</b>\n<i>Пример: +998901234567</i>",
        'back': "⬅️ Назад",
        'cancel': "❌ Отмена",
        'btn_dp_no': "🚫 Без первоначального взноса",
        'btn_dp_yes': "💵 С первоначальным взносом",
        'btn_continue': "✅ Продолжить",
        'btn_submit': "🚀 Отправить заявку",
        'about_text': (
            "✨ <b>ПОЛНАЯ ИНФОРМАЦИЯ О БОТЕ NASIYA BOZOR</b> ✨\n\n"
            "Вы выбираете любой понравившийся товар в любом магазине, мы покупаем его для вас и предоставляем в рассрочку!\n\n"
            "💱 <b>Валюта и Курс:</b>\n"
            "• Фиксированный курс: <b>1 USD = 13,000 UZS</b>\n\n"
            "⏱️ <b>Сроки и наценка:</b>\n"
            "• <b>6 месяцев</b> — 30%\n"
            "• <b>12 месяцев</b> — 45%\n\n"
            "📄 <b>Необходимые документы:</b> Паспорт или ID карта."
        ),
        'cancelled': "❌ Отменено.",
        'success_sent': "🎉 <b>Заявка успешно отправлена!</b>\nСкоро с вами свяжутся администраторы."
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
# 2. CALCULATOR LOGIC
# ----------------------------------------------------
RATES = {6: 0.30, 12: 0.45}

def calculate_nasiya(total_price: float, down_payment: float, months: int, currency_type: str):
    remaining = total_price - down_payment
    margin = RATES[months]
    total_financed = remaining * (1 + margin)
    monthly = total_financed / months

    if currency_type == "usd":
        p_usd, p_uzs = total_price, total_price * USD_RATE
        dp_usd, dp_uzs = down_payment, down_payment * USD_RATE
        rem_usd, rem_uzs = remaining, remaining * USD_RATE
        m_usd, m_uzs = monthly, monthly * USD_RATE
        symbol = "$"
    else:
        p_uzs, p_usd = total_price, total_price / USD_RATE
        dp_uzs, dp_usd = down_payment, down_payment / USD_RATE
        rem_uzs, rem_usd = remaining, remaining / USD_RATE
        m_uzs, m_usd = monthly, monthly / USD_RATE
        symbol = "so'm" if currency_type == "uzs" else "UZS"

    today = datetime.now()
    schedule = []
    for i in range(1, months + 1):
        due_date = today + relativedelta(months=i)
        schedule.append({
            "month": i,
            "date": due_date.strftime("%d.%m.%Y"),
            "amount": round(m_usd if currency_type == "usd" else m_uzs)
        })

    return {
        "original_price": total_price,
        "down_payment": down_payment,
        "months": months,
        "margin_percent": int(margin * 100),
        "monthly_payment": round(monthly),
        "schedule": schedule,
        "currency_type": currency_type,
        "currency_symbol": symbol,
        "price_usd": round(p_usd, 2),
        "price_uzs": round(p_uzs),
        "dp_usd": round(dp_usd, 2),
        "dp_uzs": round(dp_uzs),
        "rem_usd": round(rem_usd, 2),
        "rem_uzs": round(rem_uzs),
        "monthly_usd": round(m_usd, 2),
        "monthly_uzs": round(m_uzs)
    }

# ----------------------------------------------------
# 3. KEYBOARDS
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
            InlineKeyboardButton(text="🇺🇿 So'm (UZS)", callback_data="curr_uzs"),
            InlineKeyboardButton(text="🇺🇸 Dollar ($)", callback_data="curr_usd")
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
            InlineKeyboardButton(text="6 oy (30%)", callback_data="duration_6"),
            InlineKeyboardButton(text="12 oy (45%)", callback_data="duration_12")
        ],
        [
            InlineKeyboardButton(text=t['back'], callback_data="back_to_dp_choice"),
            InlineKeyboardButton(text=t['cancel'], callback_data="confirm_no")
        ]
    ])

def get_confirm_keyboard(lang='uz'):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t['btn_continue'], callback_data="confirm_yes"),
            InlineKeyboardButton(text=t['back'], callback_data="back_to_duration")
        ],
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
            [KeyboardButton(text="📨 Xabarnoma yuborish"), KeyboardButton(text="📈 Foiz va Kurs")],
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

# --- NASIYA RASMIYLASHTIRISH BOSHLANISHI ---
@router.message(F.text.in_({"📝 Nasiya rasmiylashtirish", "📝 New Installment Request", "📝 Оформить рассрочку"}))
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

@router.message(NasiyaOrder.waiting_for_price, F.text.in_({"⬅️ Orqaga", "⬅️ Back", "⬅️ Назад"}))
async def back_from_price(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    await message.answer("Bosh menyu", reply_markup=get_main_menu(lang))

@router.message(NasiyaOrder.waiting_for_price, F.text)
async def process_price(message: Message, state: FSMContext):
    clean_text = message.text.replace(" ", "").replace(",", "")
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
    clean_text = message.text.replace(" ", "").replace(",", "")
    if not clean_text.isdigit():
        await message.answer("❌ Iltimos, faqat raqam kiriting:")
        return

    dp_amount = float(clean_text)
    data = await state.get_data()
    lang = data.get('lang', 'uz')
    price = data.get('price')

    if dp_amount >= price:
        await message.answer("⚠️ Boshlang'ich to'lov narxdan kichik bo'lishi kerak!")
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

    symbol = calc['currency_symbol']
    schedule_text = "\n".join([f"   • {i['month']}-oy ({i['date']}): <b>{i['amount']:,} {symbol}</b>" for i in calc['schedule']])

    summary = (
        f"📋 <b>NASIYA HISOBI ({symbol})</b>\n\n"
        f"🔹 Narx: <b>{calc['original_price']:,} {symbol}</b>\n"
        f"🔹 Boshlang'ich to'lov: <b>{calc['down_payment']:,} {symbol}</b>\n"
        f"🔹 Muddat: <b>{calc['months']} oy</b>\n"
        f"💳 Oylik to'lov: <b>{calc['monthly_payment']:,} {symbol}/oy</b>\n"
        f"💱 <i>(Kurs: 1$ = 13,000 UZS)</i>\n\n"
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
    await state.update_data(user_phone=message.text.strip())

    data = await state.get_data()
    lang = data.get('lang', 'uz')
    calc = data.get('calc_result')
    symbol = calc['currency_symbol']

    final_text = (
        "📑 <b>ARIZA TAYYOR BO'LDI</b>\n\n"
        f"💰 Narxi: <b>{calc['original_price']:,} {symbol}</b>\n"
        f"💵 Boshlang'ich: <b>{calc['down_payment']:,} {symbol}</b>\n"
        f"📅 Muddat: <b>{calc['months']} oy</b>\n"
        f"💳 Oylik: <b>{calc['monthly_payment']:,} {symbol}/oy</b>\n"
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
        f"💰 <b>Narxi:</b> ${calc['price_usd']:,} / {calc['price_uzs']:,} so'm\n"
        f"💵 <b>Boshlang'ich:</b> ${calc['dp_usd']:,} / {calc['dp_uzs']:,} so'm\n"
        f"📅 <b>Muddat:</b> {calc['months']} oy ({calc['margin_percent']}%)\n"
        f"💳 <b>Oylik to'lov:</b> ${calc['monthly_usd']:,} / {calc['monthly_uzs']:,} so'm\n"
        f"💱 <b>Kurs:</b> 1 USD = 13,000 UZS"
    )

    # Ikkala adminga ham bir vaqtda yuborish
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
# 5. ADMIN PANEL HANDLERS
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

@router.message(F.text == "📈 Foiz va Kurs")
async def admin_rates(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(
        "📈 <b>TIZIM SOZLAMALARI:</b>\n\n"
        "• 6 oy: <b>30%</b>\n"
        "• 12 oy: <b>45%</b>\n"
        "• Belgilangan Dollar kursi: <b>1 USD = 13,000 UZS</b>",
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
# 6. RUN
# ----------------------------------------------------
async def main():
    bot = Bot(token="8944862071:AAFcxHz0fIAMO3r6GLSXql7xrn_jzFk_Puc")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())