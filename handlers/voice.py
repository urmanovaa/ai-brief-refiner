"""
Voice Handler
=============
Обработчик голосовых сообщений.
Транскрибирует аудио через Whisper и передаёт текст в основную логику.
"""

import logging
from services.openai_client import get_openai_client
from utils.prompts import SYSTEM_PROMPT, get_voice_prompt
from utils.helpers import UserStateManager

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Обработчик голосовых сообщений"""
    
    def __init__(self):
        self.openai_client = get_openai_client()
    
    async def handle(
        self,
        user_id: int,
        audio_file_path: str,
        user_state_manager: UserStateManager,
        use_rag: bool = False
    ) -> str:
        """
        Обрабатывает голосовое сообщение.
        
        Args:
            user_id: ID пользователя
            audio_file_path: Путь к аудиофайлу
            user_state_manager: Менеджер состояний
            use_rag: Использовать ли RAG для ответа
            
        Returns:
            Ответ на голосовое сообщение
        """
        try:
            # 1. Транскрибируем аудио
            logger.info(f"Транскрибируем голосовое от {user_id}")
            transcription = await self.openai_client.transcribe_audio(audio_file_path)
            
            if not transcription or not transcription.strip():
                return (
                    "🎤 Не удалось распознать речь.\n"
                    "Попробуйте записать сообщение ещё раз, говоря чётче."
                )
            
            logger.info(f"Транскрипция: {transcription[:100]}...")
            
            # 2. Формируем контекстный промпт
            voice_context = (
                "Пользователь отправил голосовое сообщение. "
                "Учитывай, что речь менее структурирована, чем текст."
            )
            
            # 3. Получаем историю диалога
            history = user_state_manager.get_history(user_id)
            
            # 4. Добавляем информацию о транскрипции
            user_message = f"[Голосовое сообщение]\n{transcription}"
            messages = history + [{"role": "user", "content": user_message}]
            
            # 5. Получаем ответ
            response = await self.openai_client.chat_completion(
                messages=messages,
                system_prompt=SYSTEM_PROMPT
            )
            
            # 6. Сохраняем в историю
            user_state_manager.add_message(user_id, "user", user_message)
            user_state_manager.add_message(user_id, "assistant", response)
            
            # 7. Добавляем префикс с транскрипцией
            result = f"🎤 <b>Распознано:</b>\n<i>{transcription}</i>\n\n{response}"
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обработки голоса: {e}")
            return (
                "❌ Не удалось обработать голосовое сообщение.\n"
                "Попробуйте ещё раз или отправьте текстом."
            )
    
    async def transcribe_only(self, audio_file_path: str) -> str:
        """
        Только транскрибирует аудио без дальнейшей обработки.
        
        Args:
            audio_file_path: Путь к аудиофайлу
            
        Returns:
            Текст транскрипции
        """
        try:
            return await self.openai_client.transcribe_audio(audio_file_path)
        except Exception as e:
            logger.error(f"Ошибка транскрипции: {e}")
            raise


