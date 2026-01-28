"""
Auto-RAG Service
================
Автоматическое определение необходимости использования RAG.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ключевые слова и паттерны для определения RAG-запросов
RAG_KEYWORDS = {
    # Best practices и правила
    "best practice", "лучшие практики", "как правильно", "правило", "правила",
    "рекомендации", "советы", "совет",
    
    # Справочные запросы
    "что такое", "как составить", "как написать", "шаблон", "пример",
    "структура", "формат", "чек-лист", "чеклист", "checklist",
    
    # Ошибки и риски
    "ошибка", "ошибки", "типичные ошибки", "частые ошибки",
    "риск", "риски", "red flag", "проблема", "проблемы",
    
    # ТЗ специфика
    "техническое задание", "тз", "бриф", "требования",
    "scope", "скоуп", "deliverable"
}

# Паттерны вопросов, требующих справочной информации
RAG_PATTERNS = [
    r"как\s+(правильно|лучше|нужно)",
    r"что\s+(должно|нужно|следует)",
    r"какие\s+(бывают|есть|существуют)",
    r"почему\s+(важно|нужно|стоит)",
    r"в\s+чём\s+(разница|отличие)",
    r"что\s+такое",
    r"зачем\s+нужн",
]


class AutoRAGService:
    """Сервис автоматического определения необходимости RAG"""
    
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in RAG_PATTERNS]
    
    def should_use_rag(self, message: str) -> bool:
        """
        Определяет, нужно ли использовать RAG для данного сообщения.
        
        Args:
            message: Текст сообщения пользователя
            
        Returns:
            True если нужен RAG, False иначе
        """
        message_lower = message.lower()
        
        # 1. Проверяем ключевые слова
        for keyword in RAG_KEYWORDS:
            if keyword in message_lower:
                logger.debug(f"RAG triggered by keyword: {keyword}")
                return True
        
        # 2. Проверяем паттерны
        for pattern in self._compiled_patterns:
            if pattern.search(message_lower):
                logger.debug(f"RAG triggered by pattern: {pattern.pattern}")
                return True
        
        # 3. Проверяем, есть ли вопросительный характер + справочные слова
        is_question = "?" in message or message_lower.startswith(("как", "что", "какие", "почему", "зачем"))
        has_reference_context = any(word in message_lower for word in ["тз", "бриф", "проект", "задание"])
        
        if is_question and has_reference_context:
            logger.debug("RAG triggered by question + reference context")
            return True
        
        return False
    
    def get_rag_context(self, query: str, top_k: int = 3) -> Optional[str]:
        """
        Получает релевантный контекст из базы знаний.
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            
        Returns:
            Контекст для LLM или None
        """
        if not self.vector_store:
            return None
        
        try:
            results = self.vector_store.search(query=query, n_results=top_k)
            
            if not results or not results.get("documents") or not results["documents"][0]:
                return None
            
            documents = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0]
            
            # Форматируем контекст
            context_parts = []
            for doc, meta in zip(documents, metadatas):
                source = meta.get("source", "unknown")
                context_parts.append(f"[{source}]\n{doc}")
            
            return "\n\n---\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Ошибка получения RAG-контекста: {e}")
            return None
    
    def has_knowledge_base(self) -> bool:
        """Проверяет, есть ли документы в базе знаний"""
        if not self.vector_store:
            return False
        try:
            stats = self.vector_store.get_stats()
            return stats.get("total_chunks", 0) > 0
        except:
            return False

