"""
Вспомогательные утилиты
=======================
Управление состоянием пользователей и вспомогательные функции.
"""

import os
import hashlib
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)


def hash_user_id(user_id: int) -> str:
    """Хеширует user_id для логов (приватность)"""
    return hashlib.sha256(str(user_id).encode()).hexdigest()[:8]


@dataclass
class UserState:
    """Состояние пользователя в боте"""
    user_id: int
    mode: str = "text"
    conversation_history: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str):
        """Добавляет сообщение в историю"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
        
        # Ограничиваем историю
        max_history = config.MAX_HISTORY_LENGTH
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
    
    def get_messages_for_api(self) -> list:
        """Возвращает историю в формате OpenAI API"""
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.conversation_history
        ]
    
    def clear_history(self):
        """Очищает историю диалога"""
        self.conversation_history = []


class UserStateManager:
    """Менеджер состояний пользователей"""
    
    def __init__(self):
        self._states: dict[int, UserState] = {}
    
    def init_user(self, user_id: int) -> UserState:
        """Инициализирует или возвращает состояние пользователя"""
        if user_id not in self._states:
            self._states[user_id] = UserState(user_id=user_id)
            logger.info(f"User state created: {hash_user_id(user_id)}")
        return self._states[user_id]
    
    def get_state(self, user_id: int) -> UserState:
        """Возвращает состояние пользователя"""
        return self.init_user(user_id)
    
    def get_mode(self, user_id: int) -> str:
        """Возвращает текущий режим пользователя"""
        return self.get_state(user_id).mode
    
    def set_mode(self, user_id: int, mode: str):
        """Устанавливает режим работы"""
        state = self.get_state(user_id)
        state.mode = mode
        logger.info(f"User {hash_user_id(user_id)} mode: {mode}")
    
    def add_message(self, user_id: int, role: str, content: str):
        """Добавляет сообщение в историю пользователя"""
        state = self.get_state(user_id)
        state.add_message(role, content)
    
    def get_history(self, user_id: int) -> list:
        """Возвращает историю сообщений для API"""
        return self.get_state(user_id).get_messages_for_api()
    
    def clear_history(self, user_id: int):
        """Очищает историю диалога пользователя"""
        state = self.get_state(user_id)
        state.clear_history()
        logger.info(f"User {hash_user_id(user_id)} history cleared")


def truncate_text(text: str, max_length: int = None) -> str:
    """Обрезает текст до максимальной длины"""
    max_length = max_length or config.MAX_MESSAGE_LENGTH
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_sources(sources: list[dict]) -> str:
    """Форматирует список источников для отображения"""
    if not sources:
        return ""
    
    formatted = "\n\n📚 <b>Источники:</b>\n"
    for i, source in enumerate(sources, 1):
        name = source.get("source", "Неизвестный источник")
        formatted += f"{i}. {name}\n"
    
    return formatted


def split_long_message(text: str, max_length: int = None) -> list[str]:
    """Разбивает длинное сообщение на части"""
    max_length = max_length or config.MAX_MESSAGE_LENGTH
    
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    paragraphs = text.split("\n\n")
    
    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 2 <= max_length:
            if current_part:
                current_part += "\n\n"
            current_part += paragraph
        else:
            if current_part:
                parts.append(current_part)
            
            if len(paragraph) > max_length:
                sentences = paragraph.replace(". ", ".|").split("|")
                current_part = ""
                for sentence in sentences:
                    if len(current_part) + len(sentence) + 1 <= max_length:
                        current_part += sentence
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = sentence
            else:
                current_part = paragraph
    
    if current_part:
        parts.append(current_part)
    
    return parts


def validate_message_length(text: str) -> tuple[bool, str]:
    """
    Проверяет длину входящего сообщения.
    
    Returns:
        (is_valid, error_message)
    """
    if len(text) > config.MAX_INPUT_LENGTH:
        return False, f"Сообщение слишком длинное (максимум {config.MAX_INPUT_LENGTH} символов)"
    return True, ""


def ensure_data_directory():
    """Создаёт директорию data/ если её нет"""
    data_dir = config.DATA_DIR
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"Created directory: {data_dir}")
    return data_dir


def get_file_extension(filename: str) -> str:
    """Возвращает расширение файла"""
    return os.path.splitext(filename)[1].lower()


def is_supported_document(filename: str) -> bool:
    """Проверяет, поддерживается ли формат документа"""
    supported_extensions = {".txt", ".md", ".pdf", ".docx"}
    return get_file_extension(filename) in supported_extensions


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename


def estimate_tokens(text: str) -> int:
    """Примерная оценка количества токенов"""
    return len(text) // 3


def format_timestamp(dt: datetime) -> str:
    """Форматирует дату для отображения"""
    return dt.strftime("%d.%m.%Y %H:%M")
