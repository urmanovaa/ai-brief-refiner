"""
AI Brief Refiner - Telegram Bot
================================
Production-ready версия бота для превращения запросов в структурированное ТЗ.
"""

import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile

from config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    
    # Проверяем конфигурацию
    errors = config.validate()
    if errors:
        for err in errors:
            logger.error(f"Config error: {err}")
        return
    
    # Импорты внутри async функции
    from services.router import MessageRouter
    from services.brief_session import BriefSessionManager
    from services.auto_rag import AutoRAGService
    from services.document_generator import DocumentGenerator
    from services.rate_limiter import get_rate_limiter
    from services.openai_client import get_openai_client, OpenAIError
    from handlers.text import TextHandler
    from handlers.voice import VoiceHandler
    from handlers.image import ImageHandler
    from handlers.rag import RAGHandler
    from rag.vectorstore import VectorStoreManager
    from utils.helpers import (
        UserStateManager, split_long_message, 
        validate_message_length, hash_user_id
    )
    from utils.prompts import SYSTEM_PROMPT
    from utils.keyboards import (
        get_start_keyboard,
        get_after_help_keyboard,
        get_project_type_keyboard,
        get_platform_keyboard,
        get_deadline_keyboard,
        get_budget_keyboard,
        get_brief_actions_keyboard,
        get_continue_keyboard,
        get_missing_fields_keyboard,
        get_summary_actions_keyboard,
        PROJECT_TYPE_MAP,
        PLATFORM_MAP,
        DEADLINE_MAP,
        BUDGET_MAP,
    )
    from services.tz_document import get_tz_generator
    from services.bot_commands import setup_bot_commands
    
    # Инициализация
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Компоненты
    user_state_manager = UserStateManager()
    brief_session_manager = BriefSessionManager()
    vector_store = VectorStoreManager()
    auto_rag = AutoRAGService(vector_store)
    doc_generator = DocumentGenerator()  # Для совместимости
    tz_generator = get_tz_generator()    # Новый генератор .docx
    rate_limiter = get_rate_limiter()
    openai_client = get_openai_client()
    
    text_handler = TextHandler()
    voice_handler = VoiceHandler()
    image_handler = ImageHandler()
    rag_handler = RAGHandler(vector_store)
    
    message_router = MessageRouter(
        text_handler=text_handler,
        voice_handler=voice_handler,
        image_handler=image_handler,
        rag_handler=rag_handler,
        user_state_manager=user_state_manager
    )

    # ==================== КОМАНДЫ ====================

    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        """Обработчик команды /start"""
        welcome_text = """
🎯 <b>AI Brief Refiner</b>

Привет! Я помогу превратить твою идею в чёткое техническое задание.

<b>Что я умею:</b>
• Задавать правильные вопросы
• Выявлять недостающую информацию  
• Предупреждать о рисках
• Формировать готовое ТЗ

Выбери действие 👇
"""
        user_state_manager.init_user(message.from_user.id)
        await message.answer(
            welcome_text, 
            parse_mode="HTML",
            reply_markup=get_start_keyboard()
        )

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        """Обработчик команды /help"""
        help_text = """
📖 <b>Как пользоваться ботом</b>

<b>1. Создай бриф</b>
Нажми «Создать ТЗ» и ответь на вопросы.
Можно использовать кнопки или писать текстом.

<b>2. Добавь детали</b>
Опиши цель проекта, что должно получиться.
Чем подробнее — тем лучше результат.

<b>3. Получи ТЗ</b>
Когда готово — нажми «Сгенерировать ТЗ».
Получишь документ в формате .txt

<b>Команды:</b>
/new — начать бриф
/summary — посмотреть собранное
/final — сгенерировать ТЗ
/cancel — отменить бриф

💡 <i>Совет: отвечай на вопросы максимально конкретно!</i>
"""
        await message.answer(
            help_text, 
            parse_mode="HTML",
            reply_markup=get_after_help_keyboard()
        )

    @dp.message(Command("new"))
    async def cmd_new(message: types.Message):
        """Начать новый бриф"""
        await start_new_brief(message.from_user.id, message)

    async def start_new_brief(user_id: int, message_or_callback):
        """Общая логика начала брифа"""
        brief_session_manager.start_session(user_id)
        user_state_manager.clear_history(user_id)
        
        text = """
📋 <b>Новый бриф</b>

Давай соберём информацию о твоём проекте.
Выбери тип проекта 👇
"""
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_project_type_keyboard()
            )
        else:
            await message_or_callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_project_type_keyboard()
            )

    @dp.message(Command("summary"))
    async def cmd_summary(message: types.Message):
        """Показать собранную информацию"""
        await show_summary(message.from_user.id, message)

    async def show_summary(user_id: int, message_or_callback):
        """Общая логика показа summary — источник истины для документа"""
        brief_data = brief_session_manager.get_brief_data(user_id)
        
        if not brief_data:
            text = "📋 Нет активного брифа.\n\nНажми кнопку, чтобы начать 👇"
            keyboard = get_start_keyboard()
        else:
            text = brief_data.to_summary()
            is_ready = brief_data.is_valid_for_generation()
            keyboard = get_summary_actions_keyboard(is_ready=is_ready)
        
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

    @dp.message(Command("final"))
    async def cmd_final(message: types.Message):
        """Сгенерировать финальное ТЗ"""
        await generate_final_tz(message.from_user.id, message, bot)

    async def generate_final_tz(user_id: int, message_or_callback, bot_instance):
        """
        Генерация финального ТЗ с валидацией.
        Если не хватает обязательных полей — показывает что нужно заполнить.
        """
        session = brief_session_manager.get_session(user_id)
        
        if not session.is_active():
            text = "📋 Нет активного брифа.\n\nНажми кнопку, чтобы начать 👇"
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer(text, reply_markup=get_start_keyboard())
            else:
                await message_or_callback.message.edit_text(text, reply_markup=get_start_keyboard())
            return
        
        brief_data = session.data
        
        # === ВАЛИДАЦИЯ: проверяем обязательные поля ===
        missing_required = brief_data.get_missing_required()
        
        if missing_required:
            # НЕ генерируем документ — просим уточнить
            text = "⚠️ <b>Не хватает информации для генерации ТЗ:</b>\n\n"
            for _, display_name in missing_required:
                text += f"• {display_name}\n"
            text += "\nВыбери что заполнить или опиши текстом 👇"
            
            keyboard = get_missing_fields_keyboard(missing_required)
            
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            return
        
        # === ГЕНЕРАЦИЯ ===
        
        # Отправляем сообщение о генерации
        if isinstance(message_or_callback, types.Message):
            status_msg = await message_or_callback.answer("⏳ Генерирую техническое задание...")
            chat_id = message_or_callback.chat.id
        else:
            await message_or_callback.message.edit_text("⏳ Генерирую техническое задание...")
            status_msg = message_or_callback.message
            chat_id = message_or_callback.message.chat.id
        
        try:
            # Используем LLM только для генерации рисков и уточняющих вопросов
            history = user_state_manager.get_history(user_id)
            raw_text = "\n".join(brief_data.raw_messages)
            
            analysis_prompt = f"""Проанализируй собранную информацию о проекте и сформируй:
1. Список возможных рисков (red flags) — что может пойти не так
2. Список открытых вопросов — что нужно уточнить перед началом работ

Информация о проекте:
- Цель: {brief_data.project_goal}
- Тип: {brief_data.project_type}
- Платформа: {brief_data.platform}
- Аудитория: {brief_data.target_audience or 'не указана'}
- Бюджет: {brief_data.budget_range or 'не указан'}
- Сроки: {brief_data.deadline or 'не указаны'}
- Функции: {', '.join(brief_data.must_have_features) if brief_data.must_have_features else 'не указаны'}

Дополнительный контекст из диалога:
{raw_text[:2000] if raw_text else 'нет'}

Ответь в формате:
РИСКИ:
- риск 1
- риск 2

ВОПРОСЫ:
- вопрос 1
- вопрос 2

Если рисков/вопросов нет — напиши "нет"."""

            messages = [{"role": "user", "content": analysis_prompt}]
            
            analysis = await openai_client.chat_completion(
                messages=messages,
                system_prompt="Ты — эксперт по анализу проектов. Выявляй риски и открытые вопросы.",
                max_tokens=1000
            )
            
            # Парсим риски и вопросы из ответа LLM
            risks = []
            questions = []
            
            if "РИСКИ:" in analysis:
                risks_section = analysis.split("РИСКИ:")[1]
                if "ВОПРОСЫ:" in risks_section:
                    risks_section = risks_section.split("ВОПРОСЫ:")[0]
                for line in risks_section.strip().split("\n"):
                    line = line.strip().lstrip("- •").strip()
                    if line and line.lower() != "нет" and len(line) > 3:
                        risks.append(line)
            
            if "ВОПРОСЫ:" in analysis:
                questions_section = analysis.split("ВОПРОСЫ:")[1]
                for line in questions_section.strip().split("\n"):
                    line = line.strip().lstrip("- •").strip()
                    if line and line.lower() != "нет" and len(line) > 3:
                        questions.append(line)
            
            # Обновляем brief_data
            brief_data.risks = risks[:5]  # Максимум 5 рисков
            brief_data.open_questions = questions[:5]  # Максимум 5 вопросов
            
            # Генерируем .docx документ
            filepath = tz_generator.generate_tz_docx(
                brief_data=brief_data.to_dict(),
                user_id=user_id
            )
            
            # Удаляем сообщение о генерации
            try:
                await status_msg.delete()
            except:
                pass
            
            # Формируем краткое превью для чата
            preview_text = f"""✅ <b>Техническое задание готово!</b>

📋 <b>Проект:</b> {brief_data.project_name or brief_data.project_type}
🎯 <b>Цель:</b> {brief_data.project_goal[:100]}{'...' if len(brief_data.project_goal) > 100 else ''}
💻 <b>Платформа:</b> {brief_data.platform}
"""
            if brief_data.deadline:
                preview_text += f"⏰ <b>Сроки:</b> {brief_data.deadline}\n"
            if brief_data.budget_range:
                preview_text += f"💰 <b>Бюджет:</b> {brief_data.budget_range}\n"
            
            if risks:
                preview_text += f"\n⚠️ <b>Выявлено рисков:</b> {len(risks)}"
            if questions:
                preview_text += f"\n❓ <b>Открытых вопросов:</b> {len(questions)}"
            
            await bot_instance.send_message(chat_id, preview_text, parse_mode="HTML")
            
            # Отправляем файл
            document = FSInputFile(filepath)
            await bot_instance.send_document(
                chat_id,
                document,
                caption="📄 Скачай документ — в нём полная версия ТЗ.\n\nХочешь создать ещё один бриф?",
                reply_markup=get_start_keyboard()
            )
            
            # Завершаем сессию
            brief_session_manager.cancel_session(user_id)
            
        except OpenAIError as e:
            logger.error(f"OpenAI error generating TZ: {e}")
            await bot_instance.send_message(chat_id, f"❌ Ошибка генерации: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating TZ: {e}", exc_info=True)
            await bot_instance.send_message(chat_id, "❌ Произошла ошибка. Попробуй ещё раз.")

    @dp.message(Command("cancel"))
    async def cmd_cancel(message: types.Message):
        """Отменить текущую сессию"""
        user_id = message.from_user.id
        
        if brief_session_manager.cancel_session(user_id):
            await message.answer(
                "🗑 Бриф отменён.\n\nНачать заново?",
                reply_markup=get_start_keyboard()
            )
        else:
            await message.answer(
                "📋 Нет активного брифа.",
                reply_markup=get_start_keyboard()
            )

    @dp.message(Command("clear"))
    async def cmd_clear(message: types.Message):
        """Очистка истории диалога"""
        user_id = message.from_user.id
        user_state_manager.clear_history(user_id)
        await message.answer("🗑 История очищена.")

    # ==================== ADMIN КОМАНДЫ ====================

    @dp.message(Command("index"))
    async def cmd_index(message: types.Message):
        """Индексация документов (только для админов)"""
        if not config.is_admin(message.from_user.id):
            await message.answer("⛔ Команда недоступна.")
            return
        
        await message.answer("📥 Начинаю индексацию...")
        
        try:
            stats = await vector_store.index_documents(config.DATA_DIR)
            await message.answer(
                f"✅ <b>Индексация завершена!</b>\n\n"
                f"📄 Файлов: {stats['files']}\n"
                f"📦 Чанков: {stats['chunks']}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Index error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")

    @dp.message(Command("stats"))
    async def cmd_stats(message: types.Message):
        """Статистика (только для админов)"""
        if not config.is_admin(message.from_user.id):
            await message.answer("⛔ Команда недоступна.")
            return
        
        try:
            stats = vector_store.get_stats()
            await message.answer(
                f"📊 <b>Статистика</b>\n\n"
                f"📦 Чанков: {stats['total_chunks']}\n"
                f"📄 Источников: {stats['sources']}\n"
                f"👥 Админов: {len(config.ADMIN_IDS)}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Stats error: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")

    # ==================== CALLBACK HANDLERS ====================

    @dp.callback_query(F.data == "new_brief")
    async def cb_new_brief(callback: types.CallbackQuery):
        """Начать новый бриф через кнопку"""
        await callback.answer()
        await start_new_brief(callback.from_user.id, callback)

    @dp.callback_query(F.data == "help")
    async def cb_help(callback: types.CallbackQuery):
        """Показать справку через кнопку"""
        await callback.answer()
        help_text = """
📖 <b>Как пользоваться ботом</b>

<b>1. Создай бриф</b>
Нажми «Создать ТЗ» и ответь на вопросы.

<b>2. Добавь детали</b>
Опиши цель проекта, что должно получиться.

<b>3. Получи ТЗ</b>
Нажми «Сгенерировать ТЗ» и получи документ.

💡 <i>Отвечай максимально конкретно!</i>
"""
        await callback.message.edit_text(
            help_text,
            parse_mode="HTML",
            reply_markup=get_after_help_keyboard()
        )

    @dp.callback_query(F.data == "summary")
    async def cb_summary(callback: types.CallbackQuery):
        """Показать summary через кнопку"""
        await callback.answer()
        await show_summary(callback.from_user.id, callback)

    @dp.callback_query(F.data == "final")
    async def cb_final(callback: types.CallbackQuery):
        """Сгенерировать ТЗ через кнопку"""
        await callback.answer("Генерирую ТЗ...")
        await generate_final_tz(callback.from_user.id, callback, bot)

    @dp.callback_query(F.data == "cancel")
    async def cb_cancel(callback: types.CallbackQuery):
        """Отменить бриф через кнопку"""
        await callback.answer()
        user_id = callback.from_user.id
        brief_session_manager.cancel_session(user_id)
        await callback.message.edit_text(
            "🗑 Бриф отменён.\n\nНачать заново?",
            reply_markup=get_start_keyboard()
        )

    @dp.callback_query(F.data == "continue")
    async def cb_continue(callback: types.CallbackQuery):
        """Продолжить добавлять детали"""
        await callback.answer()
        await callback.message.edit_text(
            "📝 Отлично! Опиши подробнее свой проект.\n\n"
            "Что должно получиться в итоге? Какие функции нужны?",
            parse_mode="HTML"
        )

    # === PROJECT TYPE ===
    @dp.callback_query(F.data.startswith("project_type:"))
    async def cb_project_type(callback: types.CallbackQuery):
        """Обработка выбора типа проекта"""
        await callback.answer()
        user_id = callback.from_user.id
        
        type_key = callback.data.split(":")[1]
        type_value = PROJECT_TYPE_MAP.get(type_key, "Другое")
        
        brief_session_manager.update_brief_data(user_id, project_type=type_value)
        
        await callback.message.edit_text(
            f"✅ Тип проекта: <b>{type_value}</b>\n\n"
            "На какой платформе? 👇",
            parse_mode="HTML",
            reply_markup=get_platform_keyboard()
        )

    # === PLATFORM ===
    @dp.callback_query(F.data.startswith("platform:"))
    async def cb_platform(callback: types.CallbackQuery):
        """Обработка выбора платформы"""
        await callback.answer()
        user_id = callback.from_user.id
        
        platform_key = callback.data.split(":")[1]
        platform_value = PLATFORM_MAP.get(platform_key, "Web")
        
        brief_session_manager.update_brief_data(user_id, platform=platform_value)
        
        await callback.message.edit_text(
            f"✅ Платформа: <b>{platform_value}</b>\n\n"
            "Какие сроки? 👇",
            parse_mode="HTML",
            reply_markup=get_deadline_keyboard()
        )

    # === DEADLINE ===
    @dp.callback_query(F.data.startswith("deadline:"))
    async def cb_deadline(callback: types.CallbackQuery):
        """Обработка выбора сроков"""
        await callback.answer()
        user_id = callback.from_user.id
        
        deadline_key = callback.data.split(":")[1]
        deadline_value = DEADLINE_MAP.get(deadline_key, "Не определены")
        
        brief_session_manager.update_brief_data(user_id, deadline=deadline_value)
        
        await callback.message.edit_text(
            f"✅ Сроки: <b>{deadline_value}</b>\n\n"
            "Какой бюджет? 👇",
            parse_mode="HTML",
            reply_markup=get_budget_keyboard()
        )

    # === BUDGET ===
    @dp.callback_query(F.data.startswith("budget:"))
    async def cb_budget(callback: types.CallbackQuery):
        """Обработка выбора бюджета"""
        await callback.answer()
        user_id = callback.from_user.id
        
        budget_key = callback.data.split(":")[1]
        budget_value = BUDGET_MAP.get(budget_key, "Не определён")
        
        brief_session_manager.update_brief_data(user_id, budget_range=budget_value)
        
        # Показываем собранное и просим описать цель
        brief_data = brief_session_manager.get_brief_data(user_id)
        
        await callback.message.edit_text(
            f"✅ Бюджет: <b>{budget_value}</b>\n\n"
            f"📋 <b>Базовая информация собрана:</b>\n"
            f"• Тип: {brief_data.project_type}\n"
            f"• Платформа: {brief_data.platform}\n"
            f"• Сроки: {brief_data.deadline}\n"
            f"• Бюджет: {brief_data.budget_range}\n\n"
            f"Теперь <b>опиши цель проекта</b>:\n"
            f"Что должно получиться? Какую задачу решает?",
            parse_mode="HTML"
        )
    
    # === FILL MISSING FIELDS ===
    @dp.callback_query(F.data.startswith("fill:"))
    async def cb_fill_field(callback: types.CallbackQuery):
        """Обработка запроса на заполнение поля"""
        await callback.answer()
        user_id = callback.from_user.id
        field = callback.data.split(":")[1]
        
        prompts = {
            "goal": (
                "🎯 <b>Опиши цель проекта:</b>\n\n"
                "Что должно получиться в результате?\n"
                "Какую задачу/проблему решает проект?"
            ),
            "project_type": (
                "📁 <b>Выбери тип проекта:</b>"
            ),
            "platform": (
                "💻 <b>Выбери платформу:</b>"
            ),
            "deadline": (
                "⏰ <b>Укажи сроки:</b>"
            ),
            "budget": (
                "💰 <b>Укажи бюджет:</b>"
            ),
            "features": (
                "✅ <b>Опиши основной функционал:</b>\n\n"
                "Что обязательно должно быть в проекте?\n"
                "Перечисли основные функции."
            ),
            "deliverables": (
                "📦 <b>Что должно быть на выходе:</b>\n\n"
                "Какие материалы/результаты ты ожидаешь?\n"
                "(код, дизайн, документация, ...)"
            ),
            "audience": (
                "👥 <b>Опиши целевую аудиторию:</b>\n\n"
                "Кто будет пользоваться проектом?\n"
                "Какие у них потребности?"
            ),
            "text": (
                "📝 <b>Опиши проект своими словами:</b>\n\n"
                "Расскажи всё что знаешь о проекте.\n"
                "Я извлеку нужную информацию."
            ),
        }
        
        keyboards = {
            "project_type": get_project_type_keyboard(),
            "platform": get_platform_keyboard(),
            "deadline": get_deadline_keyboard(),
            "budget": get_budget_keyboard(),
        }
        
        text = prompts.get(field, "📝 Опиши информацию:")
        keyboard = keyboards.get(field)
        
        # Сохраняем текущий шаг для обработки текстового ответа
        session = brief_session_manager.get_session(user_id)
        session.current_step = field
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    # ==================== ОБРАБОТКА СООБЩЕНИЙ ====================

    @dp.message(F.voice)
    async def handle_voice(message: types.Message):
        """Обработка голосовых"""
        if not rate_limiter.is_allowed(message.from_user.id):
            reset_time = rate_limiter.get_reset_time(message.from_user.id)
            await message.answer(f"⏳ Подожди {reset_time} сек.")
            return
        await message_router.route_voice(message, bot)

    @dp.message(F.photo)
    async def handle_photo(message: types.Message):
        """Обработка изображений"""
        if not rate_limiter.is_allowed(message.from_user.id):
            reset_time = rate_limiter.get_reset_time(message.from_user.id)
            await message.answer(f"⏳ Подожди {reset_time} сек.")
            return
        await message_router.route_image(message, bot)

    @dp.message(F.text)
    async def handle_text(message: types.Message):
        """Обработка текстовых сообщений с сохранением в BriefData"""
        user_id = message.from_user.id
        text = message.text
        
        # Пропускаем команды
        if text.startswith("/"):
            return
        
        # Rate limiting
        if not rate_limiter.is_allowed(user_id):
            reset_time = rate_limiter.get_reset_time(user_id)
            await message.answer(f"⏳ Подожди {reset_time} сек.")
            return
        
        # Проверка длины
        is_valid, error = validate_message_length(text)
        if not is_valid:
            await message.answer(f"⚠️ {error}")
            return
        
        # Показываем индикатор
        await bot.send_chat_action(message.chat.id, "typing")
        
        try:
            user_state_manager.init_user(user_id)
            session = brief_session_manager.get_session(user_id)
            
            # Добавляем в сессию если активна
            if session.is_active():
                session.add_message(text)
                
                # Сохраняем в соответствующее поле в зависимости от текущего шага
                current_step = session.current_step
                
                if current_step == "goal" or (not session.data.project_goal and current_step not in ["features", "deliverables", "audience"]):
                    # Сохраняем как цель проекта
                    session.data.project_goal = text[:1000]
                    session.current_step = "details"
                elif current_step == "features":
                    # Парсим функции (каждая строка — отдельная функция)
                    features = [f.strip() for f in text.split("\n") if f.strip()]
                    if len(features) == 1 and "," in features[0]:
                        features = [f.strip() for f in features[0].split(",") if f.strip()]
                    session.data.must_have_features.extend(features[:10])
                    session.current_step = "details"
                elif current_step == "deliverables":
                    deliverables = [d.strip() for d in text.split("\n") if d.strip()]
                    if len(deliverables) == 1 and "," in deliverables[0]:
                        deliverables = [d.strip() for d in deliverables[0].split(",") if d.strip()]
                    session.data.deliverables.extend(deliverables[:10])
                    session.current_step = "details"
                elif current_step == "audience":
                    session.data.target_audience = text[:500]
                    session.current_step = "details"
                elif current_step == "text":
                    # Свободный текст — сохраняем в цель если пустая, иначе в raw
                    if not session.data.project_goal:
                        session.data.project_goal = text[:1000]
                    session.current_step = "details"
            
            # Авто-RAG
            rag_context = None
            if auto_rag.should_use_rag(text) and auto_rag.has_knowledge_base():
                rag_context = auto_rag.get_rag_context(text)
            
            # Получаем историю
            history = user_state_manager.get_history(user_id)
            messages = history + [{"role": "user", "content": text}]
            
            # Формируем промпт для извлечения информации
            extraction_context = ""
            if session.is_active():
                extraction_context = f"""
Текущие данные брифа:
- Цель: {session.data.project_goal or 'не указана'}
- Тип: {session.data.project_type or 'не указан'}
- Платформа: {session.data.platform or 'не указана'}
- Функции: {', '.join(session.data.must_have_features) if session.data.must_have_features else 'не указаны'}

Если пользователь предоставляет новую информацию — помоги её структурировать.
Если чего-то не хватает — задай 1-2 уточняющих вопроса.
"""
            
            # Формируем промпт
            if rag_context:
                system_prompt = SYSTEM_PROMPT + f"\n\nКОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:\n{rag_context}"
            else:
                system_prompt = SYSTEM_PROMPT
            
            if extraction_context:
                system_prompt += extraction_context
            
            # Генерируем ответ
            response = await openai_client.chat_completion(
                messages=messages,
                system_prompt=system_prompt
            )
            
            # Сохраняем в историю
            user_state_manager.add_message(user_id, "user", text)
            user_state_manager.add_message(user_id, "assistant", response)
            
            # Отправляем ответ
            for part in split_long_message(response):
                await message.answer(part, parse_mode="HTML")
            
            # Если сессия активна, показываем кнопки действий
            if session.is_active() and session.data.project_goal:
                is_ready = session.data.is_valid_for_generation()
                await message.answer(
                    "👆 Продолжай описывать или выбери действие:",
                    reply_markup=get_summary_actions_keyboard(is_ready=is_ready)
                )
                
        except OpenAIError as e:
            logger.error(f"OpenAI error for user {hash_user_id(user_id)}: {e}")
            await message.answer(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error for user {hash_user_id(user_id)}: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка. Попробуй ещё раз.")

    # ==================== ЗАПУСК ====================
    
    logger.info("🚀 Starting AI Brief Refiner Bot...")
    
    # Полная очистка перед запуском
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook удалён, pending updates очищены")
    except Exception as e:
        logger.warning(f"Не удалось очистить webhook: {e}")
    
    # Устанавливаем команды бота (меню "/" в Telegram)
    await setup_bot_commands(bot, list(config.ADMIN_IDS))
    
    # Запускаем polling с обработкой конфликтов
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=True
        )
    except Exception as e:
        logger.error(f"Ошибка polling: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
