"""
OpenAI Client Service
=====================
Обёртка над OpenAI API с retry, таймаутами и обработкой ошибок.
"""

import os
import asyncio
import logging
import base64
from typing import Optional
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from config import config

logger = logging.getLogger(__name__)


class OpenAIError(Exception):
    """Базовое исключение для ошибок OpenAI"""
    pass


class OpenAIClient:
    """Клиент для работы с OpenAI API с retry и обработкой ошибок"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=config.API_TIMEOUT
        )
        self.model = config.OPENAI_MODEL
        self.vision_model = config.OPENAI_VISION_MODEL
        self.whisper_model = config.WHISPER_MODEL
        self.max_retries = config.API_MAX_RETRIES
        self.retry_delay = config.API_RETRY_DELAY
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Выполняет функцию с exponential backoff"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                last_error = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit, retry {attempt + 1}/{self.max_retries} через {wait_time}s")
                await asyncio.sleep(wait_time)
            except APIConnectionError as e:
                last_error = e
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Connection error, retry {attempt + 1}/{self.max_retries} через {wait_time}s")
                await asyncio.sleep(wait_time)
            except APIError as e:
                # Критичные ошибки API - не ретраим
                logger.error(f"API Error: {e}")
                raise OpenAIError(f"Ошибка API: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise OpenAIError(f"Неожиданная ошибка: {str(e)}")
        
        # Все попытки исчерпаны
        logger.error(f"All retries failed: {last_error}")
        raise OpenAIError("Сервис временно недоступен. Попробуйте позже.")
    
    async def chat_completion(
        self,
        messages: list[dict],
        system_prompt: str,
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Выполняет запрос к Chat Completions API с retry.
        
        Args:
            messages: История сообщений
            system_prompt: Системный промпт
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Ответ модели
        """
        temperature = temperature or config.TEMPERATURE
        max_tokens = max_tokens or config.MAX_TOKENS
        
        full_messages = [
            {"role": "system", "content": system_prompt}
        ] + messages
        
        async def _make_request():
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        
        return await self._retry_with_backoff(_make_request)
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Транскрибирует аудиофайл с помощью Whisper.
        """
        async def _make_request():
            with open(audio_file_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=self.whisper_model,
                    file=audio_file,
                    language="ru"
                )
            return response.text
        
        return await self._retry_with_backoff(_make_request)
    
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        conversation_history: list[dict] = None
    ) -> str:
        """
        Анализирует изображение с помощью Vision API.
        """
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "auto"
                    }
                }
            ]
        })
        
        async def _make_request():
            response = await self.client.chat.completions.create(
                model=self.vision_model,
                messages=messages,
                max_tokens=1500
            )
            return response.choices[0].message.content
        
        return await self._retry_with_backoff(_make_request)
    
    async def chat_with_context(
        self,
        user_message: str,
        system_prompt: str,
        context: str,
        conversation_history: list[dict] = None
    ) -> str:
        """
        Чат с дополнительным контекстом (для RAG).
        """
        messages = conversation_history or []
        messages.append({"role": "user", "content": user_message})
        
        enhanced_prompt = system_prompt.replace("{context}", context)
        
        return await self.chat_completion(
            messages=messages,
            system_prompt=enhanced_prompt
        )


# Синглтон клиента
_client_instance: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """Возвращает синглтон OpenAI клиента"""
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenAIClient()
    return _client_instance
