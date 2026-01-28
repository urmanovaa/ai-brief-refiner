"""
RAG Handler
===========
Обработчик запросов с использованием базы знаний (Retrieval-Augmented Generation).
"""

import logging
from rag.vectorstore import VectorStoreManager
from services.openai_client import get_openai_client
from utils.prompts import RAG_SYSTEM_PROMPT
from utils.helpers import UserStateManager, format_sources

logger = logging.getLogger(__name__)


class RAGHandler:
    """Обработчик RAG-запросов"""
    
    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store
        self.openai_client = get_openai_client()
        self.top_k = 3  # Количество релевантных чанков
    
    async def handle(
        self,
        user_id: int,
        text: str,
        user_state_manager: UserStateManager
    ) -> str:
        """
        Обрабатывает запрос с использованием RAG.
        
        Args:
            user_id: ID пользователя
            text: Текст запроса
            user_state_manager: Менеджер состояний
            
        Returns:
            Ответ с учётом базы знаний
        """
        try:
            # 1. Проверяем наличие документов в базе
            stats = self.vector_store.get_stats()
            if stats.get("total_chunks", 0) == 0:
                return (
                    "📚 База знаний пуста.\n\n"
                    "Чтобы использовать режим RAG:\n"
                    "1. Добавьте документы в папку <code>data/</code>\n"
                    "2. Выполните команду /index\n\n"
                    "Поддерживаемые форматы: .txt, .md"
                )
            
            # 2. Ищем релевантные документы
            logger.info(f"RAG-поиск для пользователя {user_id}: {text[:50]}...")
            
            search_results = self.vector_store.search(
                query=text,
                n_results=self.top_k
            )
            
            # 3. Формируем контекст
            context, sources = self._format_context(search_results)
            
            # 4. Получаем историю диалога
            history = user_state_manager.get_history(user_id)
            messages = history + [{"role": "user", "content": text}]
            
            # 5. Формируем промпт с контекстом
            system_prompt = RAG_SYSTEM_PROMPT.format(context=context)
            
            # 6. Получаем ответ
            response = await self.openai_client.chat_completion(
                messages=messages,
                system_prompt=system_prompt
            )
            
            # 7. Сохраняем в историю
            user_state_manager.add_message(user_id, "user", text)
            user_state_manager.add_message(user_id, "assistant", response)
            
            # 8. Добавляем источники если они есть
            if sources:
                formatted_sources = format_sources(sources)
                response = response + formatted_sources
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка RAG-запроса: {e}")
            return (
                "❌ Произошла ошибка при поиске по базе знаний.\n"
                "Попробуйте ещё раз или переключитесь в режим /mode text"
            )
    
    def _format_context(self, search_results: dict) -> tuple[str, list[dict]]:
        """
        Форматирует результаты поиска в контекст.
        
        Args:
            search_results: Результаты поиска из ChromaDB
            
        Returns:
            Кортеж (контекст, список источников)
        """
        if not search_results or not search_results.get("documents"):
            return "Релевантные документы не найдены.", []
        
        documents = search_results["documents"][0]
        metadatas = search_results.get("metadatas", [[]])[0]
        distances = search_results.get("distances", [[]])[0]
        
        context_parts = []
        sources = []
        seen_sources = set()
        
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            source_name = meta.get("source", f"Документ {i+1}")
            
            # Добавляем в контекст
            context_parts.append(f"[Источник: {source_name}]\n{doc}")
            
            # Собираем уникальные источники
            if source_name not in seen_sources:
                sources.append({"source": source_name})
                seen_sources.add(source_name)
        
        context = "\n\n---\n\n".join(context_parts)
        
        return context, sources
    
    async def search_only(self, query: str, n_results: int = 3) -> list[dict]:
        """
        Только поиск по базе без генерации ответа.
        
        Args:
            query: Поисковый запрос
            n_results: Количество результатов
            
        Returns:
            Список найденных документов
        """
        results = self.vector_store.search(query=query, n_results=n_results)
        
        if not results or not results.get("documents"):
            return []
        
        documents = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        
        return [
            {
                "content": doc,
                "source": meta.get("source", "Unknown")
            }
            for doc, meta in zip(documents, metadatas)
        ]


