"""
Image Handler
=============
Обработчик изображений.
Анализирует изображения через Vision API в контексте создания ТЗ.
"""

import logging
from services.openai_client import get_openai_client
from utils.prompts import IMAGE_ANALYSIS_PROMPT, SYSTEM_PROMPT
from utils.helpers import UserStateManager

logger = logging.getLogger(__name__)


class ImageHandler:
    """Обработчик изображений"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
    
    async def handle(
        self,
        user_id: int,
        image_data: bytes,
        caption: str,
        user_state_manager: UserStateManager
    ) -> str:
        """
        Обрабатывает изображение.
        
        Args:
            user_id: ID пользователя
            image_data: Байты изображения
            caption: Подпись к изображению (если есть)
            user_state_manager: Менеджер состояний
            
        Returns:
            Анализ изображения
        """
        try:
            logger.info(f"Анализируем изображение от {user_id}")
            
            # Формируем промпт для анализа
            if caption:
                prompt = f"{IMAGE_ANALYSIS_PROMPT}\n\nКомментарий пользователя: {caption}"
            else:
                prompt = IMAGE_ANALYSIS_PROMPT
            
            # Получаем историю для контекста (только текстовые сообщения)
            history = user_state_manager.get_history(user_id)
            
            # Добавляем системный промпт к истории
            context_messages = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ] + history
            
            # Анализируем изображение
            response = await self.openai_client.analyze_image(
                image_data=image_data,
                prompt=prompt,
                conversation_history=context_messages
            )
            
            # Сохраняем в историю
            user_message = f"[Изображение]{' - ' + caption if caption else ''}"
            user_state_manager.add_message(user_id, "user", user_message)
            user_state_manager.add_message(user_id, "assistant", response)
            
            # Форматируем ответ
            result = f"🖼 <b>Анализ изображения:</b>\n\n{response}"
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа изображения: {e}")
            return (
                "❌ Не удалось проанализировать изображение.\n"
                "Попробуйте отправить другое изображение или опишите его текстом."
            )
    
    async def describe_image(self, image_data: bytes) -> str:
        """
        Простое описание изображения без контекста диалога.
        
        Args:
            image_data: Байты изображения
            
        Returns:
            Описание изображения
        """
        try:
            return await self.openai_client.analyze_image(
                image_data=image_data,
                prompt="Опиши, что изображено на этом изображении."
            )
        except Exception as e:
            logger.error(f"Ошибка описания изображения: {e}")
            raise


