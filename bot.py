import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from config import BOT_TOKEN, ADMIN_ID
from database import init_db, get_user, save_user, update_user_tariff, mark_paid, add_tag, has_tag, add_support_request
from states import UserStates
from keyboards import main_menu, after_guide_keyboard, course_modules_keyboard, tariffs_keyboard, payment_keyboard, back_to_menu_keyboard
from texts import *
from course_content import MODULE_1_DETAIL, MODULE_2_DETAIL, MODULE_3_DETAIL, MODULE_4_DETAIL, MODULE_5_DETAIL

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Путь к PDF-файлу
PDF_PATH = "guide.pdf"


# ==================== КОМАНДА /start ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    user = get_user(user_id)
    
    if user and user[1]:
        await message.answer(
            AFTER_NAME.format(user[1]),
            reply_markup=main_menu()
        )
        await state.clear()
    else:
        await message.answer(WELCOME_TEXT)
        await state.set_state(UserStates.waiting_for_name)


# ==================== РЕГИСТРАЦИЯ ====================
@dp.message(UserStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, напиши своё имя (не менее 2 символов)")
        return
    
    user_id = message.from_user.id
    save_user(user_id, name=name)
    add_tag(user_id, "registered")
    
    await state.update_data(name=name)
    await message.answer(ASK_EMAIL)
    await state.set_state(UserStates.waiting_for_email)


@dp.message(UserStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    if "@" not in email or "." not in email:
        await message.answer("Пожалуйста, введи корректный email (пример: name@domain.com)")
        return
    
    user_id = message.from_user.id
    data = await state.get_data()
    name = data.get("name")
    
    save_user(user_id, email=email)
    add_tag(user_id, "email_provided")
    
    await message.answer(
        AFTER_NAME.format(name),
        reply_markup=main_menu()
    )
    await state.clear()


# ==================== ГЛАВНОЕ МЕНЮ ====================
@dp.message(F.text == "🎁 Забрать бесплатный гайд")
async def get_guide(message: types.Message):
    user_id = message.from_user.id
    
    if has_tag(user_id, "guide_downloaded"):
        await message.answer("📚 Ты уже получал(а) этот гайд! Проверь чат выше 👆")
        return
    
    add_tag(user_id, "guide_downloaded")
    
    await message.answer(GUIDE_TEXT, reply_markup=after_guide_keyboard())
    
    try:
        pdf_file = FSInputFile(PDF_PATH)
        await message.answer_document(pdf_file, caption="📄 Карта старта: от нуля до первого клиента за 14 дней")
    except Exception as e:
        logging.error(f"PDF not found: {e}")
        await message.answer("⚠️ Файл гайда временно недоступен. Мы отправим его тебе на почту!")


@dp.message(F.text == "📚 Мой курс «Маркетолог с нуля до PRO»")
async def show_course_intro(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    add_tag(user_id, "course_viewed")
    
    await message.answer(COURSE_HEADER, reply_markup=course_modules_keyboard())
    await state.set_state(UserStates.viewing_course)


@dp.message(F.text == "💬 Задать вопрос Анне")
async def ask_support(message: types.Message, state: FSMContext):
    await message.answer(SUPPORT_MODE_TEXT)
    await state.set_state(UserStates.waiting_for_support_message)


# ==================== ПОДДЕРЖКА ====================
@dp.message(UserStates.waiting_for_support_message)
async def process_support_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    user_name = user[1] if user else "Неизвестный"
    
    add_support_request(user_id, message.text)
    add_tag(user_id, "support_requested")
    
    try:
        await bot.send_message(
            ADMIN_ID,
            f"📨 **НОВЫЙ ЗАПРОС В ПОДДЕРЖКУ**\n\n"
            f"👤 Пользователь: {user_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💬 Сообщение: {message.text}\n\n"
            f"📝 **Чтобы ответить:**\n"
            f"`/reply {user_id} Твой ответ здесь`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")
    
    await message.answer(SUPPORT_RECEIVED, reply_markup=main_menu())
    await state.clear()


# ==================== КОМАНДЫ АДМИНА ====================
@dp.message(Command("reply"))
async def admin_reply(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для этой команды")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(
                "❌ Неверный формат!\n\n"
                "Используй: `/reply 123456789 Твой текст ответа`\n\n"
                "Где 123456789 — ID пользователя",
                parse_mode="Markdown"
            )
            return
        
        user_id = int(parts[1])
        reply_text = parts[2]
        
        await bot.send_message(
            user_id,
            f"💬 **Ответ от поддержки:**\n\n{reply_text}\n\n"
            "✉️ Если остались вопросы — напиши снова в поддержку.",
            parse_mode="Markdown"
        )
        
        conn = sqlite3.connect("navigator_bot.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE support_requests SET status = 'answered' WHERE user_id = ? AND status = 'pending'",
            (user_id,)
        )
        conn.commit()
        conn.close()
        
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")
        
    except ValueError:
        await message.answer("❌ Неверный ID пользователя (должны быть только цифры)")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке: {e}")


@dp.message(Command("requests"))
async def show_requests(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет прав для этой команды")
        return
    
    conn = sqlite3.connect("navigator_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, message, created_at FROM support_requests WHERE status = 'pending' ORDER BY created_at DESC"
    )
    requests = cursor.fetchall()
    conn.close()
    
    if not requests:
        await message.answer("📭 Нет открытых запросов в поддержку")
        return
    
    text = "📋 **Открытые запросы:**\n\n"
    for req in requests:
        text += f"🆔 {req[1]} | #{req[0]}\n📝 {req[2][:50]}...\n📅 {req[3]}\n`/reply {req[1]} [ответ]`\n\n"
    
    await message.answer(text, parse_mode="Markdown")


# ==================== CALLBACK-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data.startswith("module_"))
async def show_module_detail(callback: types.CallbackQuery):
    module_num = callback.data.split("_")[1]
    
    modules = {
        "1": MODULE_1_DETAIL,
        "2": MODULE_2_DETAIL,
        "3": MODULE_3_DETAIL,
        "4": MODULE_4_DETAIL,
        "5": MODULE_5_DETAIL
    }
    
    text = modules.get(module_num, "Модуль не найден")
    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "view_course")
async def view_course(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(COURSE_HEADER, reply_markup=course_modules_keyboard())
    await state.set_state(UserStates.viewing_course)
    await callback.answer()


@dp.callback_query(F.data == "ask_support")
async def support_from_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(SUPPORT_MODE_TEXT)
    await state.set_state(UserStates.waiting_for_support_message)
    await callback.answer()


@dp.callback_query(F.data == "select_tariff")
async def select_tariff(callback: types.CallbackQuery, state: FSMContext):
    message_text = "**📊 Выбери подходящий тариф:**\n\n"
    
    for key, tariff in TARIFFS.items():
        message_text += f"⭐ *{tariff['name']}* — {tariff['price']:,} ₽\n\n{tariff['description']}\n\n"
    
    message_text += "👇 Нажми на кнопку с нужным тарифом:"
    
    await callback.message.answer(message_text, parse_mode="Markdown", reply_markup=tariffs_keyboard())
    await state.set_state(UserStates.selecting_tariff)
    await callback.answer()


@dp.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: types.CallbackQuery, state: FSMContext):
    tariff_key = callback.data.split("_")[1]
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("Тариф не найден")
        return
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user[1] if user else "друг"
    
    update_user_tariff(user_id, tariff_key)
    add_tag(user_id, f"tariff_selected_{tariff_key}")
    
    await state.update_data(selected_tariff=tariff_key, tariff_name=tariff["name"], tariff_price=tariff["price"])
    
    await callback.message.answer(
        PAYMENT_CONFIRMATION.format(name, tariff["name"], tariff["price"]),
        reply_markup=payment_keyboard()
    )
    await state.set_state(UserStates.confirming_payment)
    await callback.answer()


@dp.callback_query(F.data == "pay_now")
async def emulate_payment(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user[1] if user else "друг"
    email = user[2] if user else "твоя почта"
    
    mark_paid(user_id)
    add_tag(user_id, "payment_success")
    
    success_text = PAYMENT_SUCCESS.format(name, email)
    
    await callback.message.answer(
        success_text,
        reply_markup=back_to_menu_keyboard()
    )
    
    await state.clear()
    await callback.answer("✅ Оплата успешно проведена!")


@dp.callback_query(F.data == "back_to_course")
async def back_to_course(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(COURSE_HEADER, reply_markup=course_modules_keyboard())
    await state.set_state(UserStates.viewing_course)
    await callback.answer()


@dp.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(callback: types.CallbackQuery, state: FSMContext):
    message_text = "**📊 Выбери подходящий тариф:**\n\n"
    
    for key, tariff in TARIFFS.items():
        message_text += f"⭐ *{tariff['name']}* — {tariff['price']:,} ₽\n\n{tariff['description']}\n\n"
    
    message_text += "👇 Нажми на кнопку с нужным тарифом:"
    
    await callback.message.answer(message_text, parse_mode="Markdown", reply_markup=tariffs_keyboard())
    await state.set_state(UserStates.selecting_tariff)
    await callback.answer()


@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user[1] if user else "друг"
    
    await callback.message.answer(AFTER_NAME.format(name), reply_markup=main_menu())
    await state.clear()
    await callback.answer()


# ==================== ОБРАБОТКА НЕИЗВЕСТНЫХ СООБЩЕНИЙ (ДОЛЖНА БЫТЬ ПОСЛЕДНЕЙ) ====================
@dp.message()
async def handle_unknown(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Пожалуйста, используй кнопки меню для навигации 👇",
            reply_markup=main_menu()
        )


# ==================== ЗАПУСК БОТА ====================
async def main():
    init_db()
    logging.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())