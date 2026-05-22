import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, URLInputFile
from aiogram.utils.markdown import hbold

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

# Путь к PDF-файлу (создай пустой файл или добавь реальный)
# Для теста можно создать пустой PDF или скачать любой тестовый
PDF_PATH = "guide.pdf"  # Положи любой PDF файл в папку с ботом

# Приветствие и регистрация
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Проверяем, есть ли пользователь в БД
    user = get_user(user_id)
    
    if user and user[1]:  # Если имя уже есть
        await message.answer(
            AFTER_NAME.format(user[1]),
            reply_markup=main_menu()
        )
        await state.clear()
    else:
        await message.answer(WELCOME_TEXT)
        await state.set_state(UserStates.waiting_for_name)

# Обработка имени
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

# Обработка email
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

# Главное меню - Забрать гайд
@dp.message(F.text == "🎁 Забрать бесплатный гайд")
async def get_guide(message: types.Message):
    user_id = message.from_user.id
    add_tag(user_id, "guide_downloaded")
    
    # Отправляем текст с гайдом
    await message.answer(GUIDE_TEXT, reply_markup=after_guide_keyboard())
    
    # Отправляем PDF файл
    try:
        pdf_file = FSInputFile(PDF_PATH)
        await message.answer_document(pdf_file, caption="📄 Карта старта: от нуля до первого клиента за 14 дней")
    except Exception as e:
        logging.error(f"PDF not found: {e}")
        await message.answer("⚠️ Файл гайда временно недоступен. Мы отправим его тебе на почту!")
        # Можно отправить ссылку на файл или просто текст

# Главное меню - Курс
@dp.message(F.text == "📚 Мой курс «Маркетолог с нуля до PRO»")
async def show_course_intro(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    add_tag(user_id, "course_viewed")
    
    await message.answer(COURSE_HEADER, reply_markup=course_modules_keyboard())
    await state.set_state(UserStates.viewing_course)

# Главное меню - Задать вопрос
@dp.message(F.text == "💬 Задать вопрос Анне")
async def ask_support(message: types.Message, state: FSMContext):
    await message.answer(SUPPORT_MODE_TEXT)
    await state.set_state(UserStates.waiting_for_support_message)

# Обработка сообщений в поддержку
@dp.message(UserStates.waiting_for_support_message)
async def process_support_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = get_user(user_id)
    user_name = user[1] if user else "Неизвестный"
    
    # Сохраняем запрос в БД
    add_support_request(user_id, message.text)
    add_tag(user_id, "support_requested")
    
    # Отправляем уведомление администратору
    try:
        await bot.send_message(
            ADMIN_ID,
            f"📨 НОВЫЙ ЗАПРОС В ПОДДЕРЖКУ\n\n"
            f"👤 Пользователь: @{message.from_user.username or user_name}\n"
            f"🆔 ID: {user_id}\n"
            f"💬 Сообщение: {message.text}"
        )
    except:
        pass
    
    await message.answer(SUPPORT_RECEIVED, reply_markup=main_menu())
    await state.clear()

# Обработка callback'ов - Модули курса
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

# Просмотр курса
@dp.callback_query(F.data == "view_course")
async def view_course(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(COURSE_HEADER, reply_markup=course_modules_keyboard())
    await state.set_state(UserStates.viewing_course)
    await callback.answer()

# Выбор тарифа
@dp.callback_query(F.data == "select_tariff")
async def select_tariff(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("**Выбери подходящий тариф:**", parse_mode="Markdown")
    
    for key, tariff in TARIFFS.items():
        await callback.message.answer(
            f"⭐ *{tariff['name']}* — {tariff['price']:,} ₽\n\n{tariff['description']}",
            parse_mode="Markdown"
        )
    
    await callback.message.answer("👇 Нажми на кнопку с нужным тарифом:", reply_markup=tariffs_keyboard())
    await state.set_state(UserStates.selecting_tariff)
    await callback.answer()

# Обработка выбора тарифа
@dp.callback_query(F.data.startswith("tariff_"))
async def process_tariff_selection(callback: types.CallbackQuery, state: FSMContext):
    tariff_key = callback.data.split("_")[1]  # start, pro, vip
    tariff = TARIFFS.get(tariff_key)
    
    if not tariff:
        await callback.answer("Тариф не найден")
        return
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user[1] if user else "друг"
    
    update_user_tariff(user_id, tariff_key)
    add_tag(user_id, f"tariff_selected_{tariff_key}")
    
    # Сохраняем в состояние
    await state.update_data(selected_tariff=tariff_key, tariff_name=tariff["name"], tariff_price=tariff["price"])
    
    # Показываем подтверждение платежа
    await callback.message.answer(
        PAYMENT_CONFIRMATION.format(name, tariff["name"], tariff["price"]),
        reply_markup=payment_keyboard()
    )
    await state.set_state(UserStates.confirming_payment)
    await callback.answer()

# Эмуляция оплаты
@dp.callback_query(F.data == "pay_now")
async def emulate_payment(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user[1] if user else "друг"
    email = user[2] if user else "твоя почта"
    
    data = await state.get_data()
    tariff_name = data.get("tariff_name", "выбранный тариф")
    
    # Отмечаем оплату в БД
    mark_paid(user_id)
    add_tag(user_id, "payment_success")
    
    # Отправляем сообщение об успешной оплате
    await callback.message.answer(
        PAYMENT_SUCCESS.format(name, email),
        reply_markup=back_to_menu_keyboard()
    )
    
    # Дополнительно отправляем ссылку на курс (эмуляция)
    await callback.message.answer(
        "🔗 **Доступ к курсу:**\nhttps://example.com/course-access\n\n"
        "🔐 **Пароль для доступа:** NAVIGATOR2024",
        parse_mode="Markdown"
    )
    
    await state.clear()
    await callback.answer("✅ Оплата успешно проведена!")

# Подтверждение оплаты (если пользователь нажал "Я оплатил")
@dp.callback_query(F.data == "confirm_payment")
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔄 Мы проверяем статус твоего платежа...\n\n"
        "💰 Если ты уже оплатил(а), доступ придёт в течение 5 минут на почту.\n\n"
        "❓ Если что-то пошло не так, напиши в поддержку."
    )
    await callback.answer()

# Назад к курсу
@dp.callback_query(F.data == "back_to_course")
async def back_to_course(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(COURSE_HEADER, reply_markup=course_modules_keyboard())
    await state.set_state(UserStates.viewing_course)
    await callback.answer()

# Назад к тарифам
@dp.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(callback: types.CallbackQuery, state: FSMContext):
    for key, tariff in TARIFFS.items():
        await callback.message.answer(
            f"⭐ *{tariff['name']}* — {tariff['price']:,} ₽\n\n{tariff['description']}",
            parse_mode="Markdown"
        )
    await callback.message.answer("👇 Нажми на кнопку с нужным тарифом:", reply_markup=tariffs_keyboard())
    await state.set_state(UserStates.selecting_tariff)
    await callback.answer()

# Возврат в главное меню
@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = get_user(user_id)
    name = user[1] if user else "друг"
    
    await callback.message.answer(AFTER_NAME.format(name), reply_markup=main_menu())
    await state.clear()
    await callback.answer()

# Защита от спама - обработка неизвестных сообщений
@dp.message()
async def handle_unknown(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Пожалуйста, используй кнопки меню для навигации 👇",
            reply_markup=main_menu()
        )

# Запуск бота
async def main():
    init_db()
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())