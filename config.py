"""
Централизованная конфигурация приложения
=========================================
Все настройки в одном месте для удобного управления.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""
    
    # === Telegram ===
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # === Admin ===
    # Список admin user_id через запятую: "123456,789012"
    ADMIN_IDS: set[int] = set()
    _admin_ids_raw = os.getenv("ADMIN_IDS", "")
    if _admin_ids_raw:
        ADMIN_IDS = {int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()}
    
    # === OpenAI ===
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_VISION_MODEL: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")
    
    # === OpenAI Limits ===
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    
    # === Retry settings ===
    API_MAX_RETRIES: int = int(os.getenv("API_MAX_RETRIES", "3"))
    API_RETRY_DELAY: float = float(os.getenv("API_RETRY_DELAY", "1.0"))
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "60"))
    
    # === Rate Limiting ===
    RATE_LIMIT_MESSAGES: int = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # секунд
    
    # === RAG / ChromaDB ===
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "brief_refiner_docs")
    RAG_CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "500"))
    RAG_CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))
    
    # === Paths ===
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "./temp")
    
    # === Limits ===
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "4000"))
    MAX_HISTORY_LENGTH: int = int(os.getenv("MAX_HISTORY_LENGTH", "20"))
    MAX_INPUT_LENGTH: int = int(os.getenv("MAX_INPUT_LENGTH", "10000"))
    
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Проверяет, является ли пользователь админом"""
        return user_id in cls.ADMIN_IDS
    
    @classmethod
    def validate(cls) -> list[str]:
        """Проверяет обязательные настройки, возвращает список ошибок"""
        errors = []
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY не установлен")
        return errors


# Синглтон для удобного импорта
config = Config()

