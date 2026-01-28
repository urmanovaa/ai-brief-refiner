"""
Bot Commands Setup
==================
Регистрация команд бота для показа в меню "/" в Telegram.
"""

import logging
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

logger = logging.getLogger(__name__)


# Команды для всех пользователей
USER_COMMANDS = [
    BotCommand(command="start", description="🚀 Запустить бота"),
    BotCommand(command="new", description="📝 Создать новое ТЗ (бриф)"),
    BotCommand(command="summary", description="📋 Показать черновик ТЗ"),
    BotCommand(command="final", description="📄 Получить ТЗ документом"),
    BotCommand(command="cancel", description="❌ Отменить текущий бриф"),
    BotCommand(command="help", description="❓ Помощь"),
]

# Дополнительные команды для админов
ADMIN_COMMANDS = [
    BotCommand(command="start", description="🚀 Запустить бота"),
    BotCommand(command="new", description="📝 Создать новое ТЗ (бриф)"),
    BotCommand(command="summary", description="📋 Показать черновик ТЗ"),
    BotCommand(command="final", description="📄 Получить ТЗ документом"),
    BotCommand(command="cancel", description="❌ Отменить текущий бриф"),
    BotCommand(command="help", description="❓ Помощь"),
    # Админ-команды
    BotCommand(command="index", description="🔄 Индексация документов RAG"),
    BotCommand(command="stats", description="📊 Статистика базы знаний"),
]


async def setup_bot_commands(bot: Bot, admin_ids: list[int]) -> None:
    """
    Устанавливает команды бота для меню "/" в Telegram.
    
    Args:
        bot: Экземпляр бота
        admin_ids: Список ID администраторов
    """
    try:
        # 1. Устанавливаем команды для всех пользователей (default scope)
        await bot.set_my_commands(
            commands=USER_COMMANDS,
            scope=BotCommandScopeDefault()
        )
        logger.info("✅ Команды бота установлены для всех пользователей")
        
        # 2. Устанавливаем расширенные команды для админов
        for admin_id in admin_ids:
            try:
                await bot.set_my_commands(
                    commands=ADMIN_COMMANDS,
                    scope=BotCommandScopeChat(chat_id=admin_id)
                )
                logger.info(f"✅ Админ-команды установлены для user_id={admin_id}")
            except Exception as e:
                # Админ мог не начать чат с ботом — это нормально
                logger.warning(f"⚠️ Не удалось установить команды для admin_id={admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка установки команд бота: {e}")


async def remove_bot_commands(bot: Bot) -> None:
    """Удаляет все команды бота (для отладки)."""
    try:
        await bot.delete_my_commands(scope=BotCommandScopeDefault())
        logger.info("Команды бота удалены")
    except Exception as e:
        logger.error(f"Ошибка удаления команд: {e}")

