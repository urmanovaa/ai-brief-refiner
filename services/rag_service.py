"""
RAG Service
===========
Сервис для работы с Retrieval-Augmented Generation.
Объединяет поиск по векторной базе и генерацию ответов.
"""

import os
import logging
from typing import Optional

from services.openai_client import get_openai_client
from rag.vectorstore import VectorStoreManager
from utils.prompts import RAG_SYSTEM_PROMPT
from utils.helpers import format_sources

logger = logging.getLogger(__name__)


class RAGService:
    """Сервис для RAG-запросов"""
    
    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store
        self.openai_client = get_openai_client()
        self.top_k = int(os.getenv("RAG_TOP_K", "3"))
    
    async def query(
        self,
        user_query: str,
        conversation_history: list[dict] = None
    ) -> tuple[str, list[dict]]:
        """
        Выполняет RAG-запрос.
        
        Args:
            user_query: Запрос пользователя
            conversation_history: История диалога
            
        Returns:
            Кортеж (ответ, список источников)
        """
        try:
            # 1. Поиск релевантных документов
            search_results = self.vector_store.search(
                query=user_query,
                n_results=self.top_k
            )
            
            if not search_results or not search_results.get("documents"):
                # Если база пуста или нет результатов
                logger.info("RAG: база знаний пуста или нет релевантных документов")
                context = "База знаний пуста или не содержит релевантной информации."
                sources = []
            else:
                # 2. Формируем контекст из найденных документов
                documents = search_results["documents"][0]  # ChromaDB возвращает вложенный список
                metadatas = search_results.get("metadatas", [[]])[0]
                
                context_parts = []
                sources = []
                
                for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                    source_name = meta.get("source", f"Документ {i+1}")
                    context_parts.append(f"[{source_name}]\n{doc}")
                    sources.append({"source": source_name})
                
                context = "\n\n---\n\n".join(context_parts)
            
            # 3. Формируем промпт с контекстом
            system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
            
            # 4. Генерируем ответ
            messages = conversation_history or []
            messages.append({"role": "user", "content": user_query})
            
            response = await self.openai_client.chat_completion(
                messages=messages,
                system_prompt=system_prompt
            )
            
            return response, sources
            
        except Exception as e:
            logger.error(f"Ошибка RAG-запроса: {e}")
            raise
    
    async def query_with_formatted_sources(
        self,
        user_query: str,
        conversation_history: list[dict] = None
    ) -> str:
        """
        Выполняет RAG-запрос и форматирует ответ с источниками.
        
        Args:
            user_query: Запрос пользователя
            conversation_history: История диалога
            
        Returns:
            Отформатированный ответ с источниками
        """
        response, sources = await self.query(user_query, conversation_history)
        
        # Добавляем источники к ответу
        if sources:
            formatted_sources = format_sources(sources)
            return response + formatted_sources
        
        return response
    
    def has_documents(self) -> bool:
        """Проверяет, есть ли документы в базе"""
        stats = self.vector_store.get_stats()
        return stats.get("total_chunks", 0) > 0


