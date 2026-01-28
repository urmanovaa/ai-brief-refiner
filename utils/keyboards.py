"""
Inline Keyboards
================
Все клавиатуры бота в одном месте.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ==================== START / MAIN MENU ====================

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Главное меню после /start"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Создать ТЗ", callback_data="new_brief"),
        ],
        [
            InlineKeyboardButton(text="📄 Как пользоваться", callback_data="help"),
        ],
    ])


def get_after_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после показа справки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Начать бриф", callback_data="new_brief"),
        ],
    ])


# ==================== PROJECT TYPE ====================

def get_project_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа проекта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Лендинг", callback_data="project_type:landing"),
            InlineKeyboardButton(text="🏢 Корп. сайт", callback_data="project_type:website"),
        ],
        [
            InlineKeyboardButton(text="🛒 Интернет-магазин", callback_data="project_type:ecommerce"),
            InlineKeyboardButton(text="📱 Приложение", callback_data="project_type:app"),
        ],
        [
            InlineKeyboardButton(text="🤖 Telegram-бот", callback_data="project_type:bot"),
            InlineKeyboardButton(text="🔧 Другое", callback_data="project_type:other"),
        ],
    ])


# ==================== PLATFORM ====================

def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Выбор платформы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Web", callback_data="platform:web"),
            InlineKeyboardButton(text="📱 iOS", callback_data="platform:ios"),
        ],
        [
            InlineKeyboardButton(text="🤖 Android", callback_data="platform:android"),
            InlineKeyboardButton(text="📲 Web + Mobile", callback_data="platform:cross"),
        ],
        [
            InlineKeyboardButton(text="💬 Telegram", callback_data="platform:telegram"),
        ],
    ])


# ==================== DEADLINE ====================

def get_deadline_keyboard() -> InlineKeyboardMarkup:
    """Выбор сроков"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ До 1 недели", callback_data="deadline:1w"),
            InlineKeyboardButton(text="📅 2-4 недели", callback_data="deadline:1m"),
        ],
        [
            InlineKeyboardButton(text="📆 1-3 месяца", callback_data="deadline:3m"),
            InlineKeyboardButton(text="🗓 3+ месяца", callback_data="deadline:3m+"),
        ],
        [
            InlineKeyboardButton(text="❓ Пока не знаю", callback_data="deadline:unknown"),
        ],
    ])


# ==================== BUDGET ====================

def get_budget_keyboard() -> InlineKeyboardMarkup:
    """Выбор бюджета"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Минимальный", callback_data="budget:low"),
            InlineKeyboardButton(text="💰 Средний", callback_data="budget:mid"),
        ],
        [
            InlineKeyboardButton(text="💎 Большой", callback_data="budget:high"),
            InlineKeyboardButton(text="🤷 Гибкий / не знаю", callback_data="budget:flex"),
        ],
    ])


# ==================== BRIEF ACTIONS ====================

def get_brief_actions_keyboard() -> InlineKeyboardMarkup:
    """Действия с брифом"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Что собрано", callback_data="summary"),
            InlineKeyboardButton(text="📄 Сгенерировать ТЗ", callback_data="final"),
        ],
        [
            InlineKeyboardButton(text="❌ Отменить бриф", callback_data="cancel"),
        ],
    ])


def get_continue_keyboard() -> InlineKeyboardMarkup:
    """Продолжить или завершить"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Готово, сгенерировать ТЗ", callback_data="final"),
        ],
        [
            InlineKeyboardButton(text="📝 Добавить детали", callback_data="continue"),
        ],
    ])


# ==================== CONFIRMATION ====================

def get_confirm_cancel_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, отменить", callback_data="confirm_cancel"),
            InlineKeyboardButton(text="❌ Нет, продолжить", callback_data="continue"),
        ],
    ])


# ==================== MISSING FIELDS ====================

def get_missing_fields_keyboard(missing_fields: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """
    Клавиатура для заполнения недостающих полей.
    missing_fields: список кортежей (field_name, display_name)
    """
    buttons = []
    
    field_to_callback = {
        "project_goal": "fill:goal",
        "project_type": "fill:project_type",
        "platform": "fill:platform",
        "deadline": "fill:deadline",
        "budget_range": "fill:budget",
        "deliverables": "fill:deliverables",
        "must_have_features": "fill:features",
        "target_audience": "fill:audience",
    }
    
    field_icons = {
        "project_goal": "🎯",
        "project_type": "📁",
        "platform": "💻",
        "deadline": "⏰",
        "budget_range": "💰",
        "deliverables": "📦",
        "must_have_features": "✅",
        "target_audience": "👥",
    }
    
    for field_name, display_name in missing_fields[:4]:  # Максимум 4 кнопки
        callback = field_to_callback.get(field_name)
        icon = field_icons.get(field_name, "📝")
        if callback:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{icon} Указать {display_name}",
                    callback_data=callback
                )
            ])
    
    # Кнопка "Заполнить всё текстом"
    buttons.append([
        InlineKeyboardButton(text="📝 Описать текстом", callback_data="fill:text")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_fill_goal_keyboard() -> InlineKeyboardMarkup:
    """Подсказка для заполнения цели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="summary"),
        ]
    ])


def get_summary_actions_keyboard(is_ready: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура после summary"""
    if is_ready:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Сгенерировать ТЗ", callback_data="final"),
            ],
            [
                InlineKeyboardButton(text="📝 Добавить детали", callback_data="continue"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"),
            ],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Продолжить заполнение", callback_data="continue"),
            ],
            [
                InlineKeyboardButton(text="❌ Отменить бриф", callback_data="cancel"),
            ],
        ])


# ==================== МАППИНГИ ЗНАЧЕНИЙ ====================

PROJECT_TYPE_MAP = {
    "landing": "Лендинг",
    "website": "Корпоративный сайт",
    "ecommerce": "Интернет-магазин",
    "app": "Мобильное приложение",
    "bot": "Telegram-бот",
    "other": "Другое",
}

PLATFORM_MAP = {
    "web": "Web",
    "ios": "iOS",
    "android": "Android",
    "cross": "Web + Mobile",
    "telegram": "Telegram",
}

DEADLINE_MAP = {
    "1w": "До 1 недели",
    "1m": "2-4 недели",
    "3m": "1-3 месяца",
    "3m+": "3+ месяца",
    "unknown": "Не определены (требуется уточнение)",
}

BUDGET_MAP = {
    "low": "Минимальный (до 50K ₽)",
    "mid": "Средний (50-200K ₽)",
    "high": "Большой (200K+ ₽)",
    "flex": "Гибкий / обсуждается",
}

