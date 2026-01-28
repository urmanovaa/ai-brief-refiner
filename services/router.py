"""
Message Router
==============
Роутер сообщений — определяет тип входящего сообщения и текущий режим пользователя,
направляет запрос в соответствующий handler.
"""

import os
import logging
import tempfile
from aiogram import types, Bot

from handlers.text import TextHandler
from handlers.voice import VoiceHandler
from handlers.image import ImageHandler
from handlers.rag import RAGHandler
from utils.helpers import UserStateManager, split_long_message

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Роутер сообщений.
    Определяет тип сообщения и режим пользователя, направляет в нужный handler.
    """
    
    def __init__(
        self,
        text_handler: TextHandler,
        voice_handler: VoiceHandler,
        image_handler: ImageHandler,
        rag_handler: RAGHandler,
        user_state_manager: UserStateManager
    ):
        self.text_handler = text_handler
        self.voice_handler = voice_handler
        self.image_handler = image_handler
        self.rag_handler = rag_handler
        self.user_state_manager = user_state_manager
    
    async def route_text(self, message: types.Message) -> None:
        """
        Роутинг текстовых сообщений.
        
        Args:
            message: Telegram сообщение
        """
        user_id = message.from_user.id
        text = message.text
        
        # Игнорируем команды (они обрабатываются отдельно)
        if text.startswith("/"):
            return
        
        # Получаем текущий режим пользователя
        mode = self.user_state_manager.get_mode(user_id)
        logger.info(f"Текстовое сообщение от {user_id}, режим: {mode}")
        
        # Показываем индикатор "печатает"
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        try:
            # Роутинг по режиму
            if mode == "rag":
                response = await self.rag_handler.handle(
                    user_id=user_id,
                    text=text,
                    user_state_manager=self.user_state_manager
                )
            else:
                # В режимах text, voice, image — обрабатываем как обычный текст
                response = await self.text_handler.handle(
                    user_id=user_id,
                    text=text,
                    user_state_manager=self.user_state_manager
                )
            
            # Отправляем ответ (разбиваем если длинный)
            await self._send_response(message, response)
            
        except Exception as e:
            logger.error(f"Ошибка обработки текста: {e}")
            await message.answer(
                "❌ Произошла ошибка при обработке сообщения. Попробуйте ещё раз."
            )
    
    async def route_voice(self, message: types.Message, bot: Bot) -> None:
        """
        Роутинг голосовых сообщений.
        
        Args:
            message: Telegram сообщение с голосом
            bot: Экземпляр бота
        """
        user_id = message.from_user.id
        mode = self.user_state_manager.get_mode(user_id)
        
        logger.info(f"Голосовое сообщение от {user_id}, режим: {mode}")
        
        # Показываем индикатор
        await bot.send_chat_action(message.chat.id, "typing")
        
        try:
            # Скачиваем голосовое сообщение
            voice = message.voice
            file = await bot.get_file(voice.file_id)
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = tmp.name
            
            # Скачиваем файл
            await bot.download_file(file.file_path, tmp_path)
            
            # Обрабатываем голосовое сообщение
            response = await self.voice_handler.handle(
                user_id=user_id,
                audio_file_path=tmp_path,
                user_state_manager=self.user_state_manager,
                use_rag=(mode == "rag")
            )
            
            # Удаляем временный файл
            os.unlink(tmp_path)
            
            # Отправляем ответ
            await self._send_response(message, response)
            
        except Exception as e:
            logger.error(f"Ошибка обработки голоса: {e}")
            await message.answer(
                "❌ Не удалось обработать голосовое сообщение. Попробуйте ещё раз."
            )
    
    async def route_image(self, message: types.Message, bot: Bot) -> None:
        """
        Роутинг изображений.
        
        Args:
            message: Telegram сообщение с фото
            bot: Экземпляр бота
        """
        user_id = message.from_user.id
        mode = self.user_state_manager.get_mode(user_id)
        
        logger.info(f"Изображение от {user_id}, режим: {mode}")
        
        # Показываем индикатор
        await bot.send_chat_action(message.chat.id, "typing")
        
        try:
            # Получаем фото максимального размера
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)
            
            # Скачиваем файл в память
            from io import BytesIO
            file_data = BytesIO()
            await bot.download_file(file.file_path, file_data)
            image_bytes = file_data.getvalue()
            
            # Получаем подпись к фото (если есть)
            caption = message.caption or ""
            
            # Обрабатываем изображение
            response = await self.image_handler.handle(
                user_id=user_id,
                image_data=image_bytes,
                caption=caption,
                user_state_manager=self.user_state_manager
            )
            
            # Отправляем ответ
            await self._send_response(message, response)
            
        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}")
            await message.answer(
                "❌ Не удалось обработать изображение. Попробуйте ещё раз."
            )
    
    async def _send_response(self, message: types.Message, response: str) -> None:
        """
        Отправляет ответ пользователю, разбивая длинные сообщения.
        
        Args:
            message: Исходное сообщение для ответа
            response: Текст ответа
        """
        # Разбиваем длинные сообщения
        parts = split_long_message(response)
        
        for part in parts:
            await message.answer(part, parse_mode="HTML")


