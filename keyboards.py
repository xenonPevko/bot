from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню (Reply кнопки)
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Забрать бесплатный гайд")],
            [KeyboardButton(text="📚 Мой курс «Маркетолог с нуля до PRO»")],
            [KeyboardButton(text="💬 Задать вопрос Анне")]
        ],
        resize_keyboard=True
    )

# Инлайн-клавиатура после гайда
def after_guide_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Посмотреть содержание курса", callback_data="view_course")],
        [InlineKeyboardButton(text="💬 Задать вопрос Анне", callback_data="ask_support")]
    ])

# Клавиатура для выбора модулей
def course_modules_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Модуль 1", callback_data="module_1"),
         InlineKeyboardButton(text="📖 Модуль 2", callback_data="module_2")],
        [InlineKeyboardButton(text="📖 Модуль 3", callback_data="module_3"),
         InlineKeyboardButton(text="📖 Модуль 4", callback_data="module_4")],
        [InlineKeyboardButton(text="📖 Модуль 5", callback_data="module_5")],
        [InlineKeyboardButton(text="💰 ВЫБРАТЬ ТАРИФ КУРСА", callback_data="select_tariff")]
    ])

# Клавиатура выбора тарифов
def tariffs_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Старт — 3 490 ₽", callback_data="tariff_start")],
        [InlineKeyboardButton(text="🚀 Про — 12 900 ₽", callback_data="tariff_pro")],
        [InlineKeyboardButton(text="👑 VIP — 29 900 ₽", callback_data="tariff_vip")],
        [InlineKeyboardButton(text="🔙 Назад к курсу", callback_data="back_to_course")]
    ])

# Клавиатура для подтверждения оплаты
def payment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ОПЛАТИТЬ (тестовый режим)", callback_data="pay_now")],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="confirm_payment")],
        [InlineKeyboardButton(text="🔙 Назад к тарифам", callback_data="back_to_tariffs")]
    ])

# Клавиатура для возврата в главное меню
def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])