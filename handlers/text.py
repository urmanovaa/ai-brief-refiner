"""
Text Handler
============
Обработчик текстовых сообщений.
Основная логика AI Brief Refiner — превращение запросов в структурированное ТЗ.
"""

import logging
from services.openai_client import get_openai_client
from utils.prompts import SYSTEM_PROMPT
from utils.helpers import UserStateManager

logger = logging.getLogger(__name__)


class TextHandler:
    """Обработчик текстовых сообщений"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
    
    async def handle(
        self,
        user_id: int,
        text: str,
        user_state_manager: UserStateManager
    ) -> str:
        """
        Обрабатывает текстовое сообщение.
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения
            user_state_manager: Менеджер состояний пользователей
            
        Returns:
            Ответ AI Brief Refiner
        """
        try:
            # Получаем историю диалога
            history = user_state_manager.get_history(user_id)
            
            # Добавляем текущее сообщение
            messages = history + [{"role": "user", "content": text}]
            
            # Получаем ответ от OpenAI
            response = await self.openai_client.chat_completion(
                messages=messages,
                system_prompt=SYSTEM_PROMPT
            )
            
            # Сохраняем сообщения в историю
            user_state_manager.add_message(user_id, "user", text)
            user_state_manager.add_message(user_id, "assistant", response)
            
            logger.info(f"Обработано текстовое сообщение от {user_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка обработки текста: {e}")
            return (
                "❌ Произошла ошибка при обработке сообщения.\n"
                "Пожалуйста, попробуйте ещё раз или перефразируйте запрос."
            )
    
    async def handle_with_context(
        self,
        user_id: int,
        text: str,
        additional_context: str,
        user_state_manager: UserStateManager
    ) -> str:
        """
        Обрабатывает текст с дополнительным контекстом.
        Используется для обработки расшифровок голосовых сообщений.
        
        Args:
            user_id: ID пользователя
            text: Текст сообщения
            additional_context: Дополнительный контекст (например, информация о голосовом)
            user_state_manager: Менеджер состояний
            
        Returns:
            Ответ AI Brief Refiner
        """
        # Формируем обогащённый запрос
        enriched_text = f"{additional_context}\n\nТекст пользователя:\n{text}"
        
        return await self.handle(
            user_id=user_id,
            text=enriched_text,
            user_state_manager=user_state_manager
        )


