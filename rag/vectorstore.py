"""
Vector Store Manager (Simplified)
=================================
Упрощённая версия хранилища на основе текстового поиска.
Работает без ChromaDB — используется простой TF-IDF подход.

Для production рекомендуется использовать ChromaDB с правильно скомпилированным hnswlib.
"""

import os
import logging
import json
import re
from typing import Optional
from collections import Counter
from math import log
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Менеджер хранилища документов (упрощённая in-memory версия)"""
    
    def __init__(self):
        # Настройки из окружения
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "500"))
        self.chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
        
        # In-memory хранилище
        self.documents: list[dict] = []  # {"id": str, "content": str, "source": str}
        self.index_file = os.path.join(self.persist_dir, "index.json")
        
        # Создаём директорию и загружаем существующий индекс
        os.makedirs(self.persist_dir, exist_ok=True)
        self._load_index()
        
        logger.info(f"VectorStore инициализирован (simplified): {self.persist_dir}")
    
    def _load_index(self):
        """Загружает индекс из файла"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                logger.info(f"Загружено {len(self.documents)} чанков из индекса")
            except Exception as e:
                logger.error(f"Ошибка загрузки индекса: {e}")
                self.documents = []
    
    def _save_index(self):
        """Сохраняет индекс в файл"""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения индекса: {e}")
    
    async def index_documents(self, data_dir: str) -> dict:
        """
        Индексирует документы из указанной директории.
        
        Args:
            data_dir: Путь к директории с документами
            
        Returns:
            Статистика индексации
        """
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"Создана директория {data_dir}")
            return {"files": 0, "chunks": 0}
        
        # Поддерживаемые расширения
        supported_extensions = {".txt", ".md"}
        
        files_processed = 0
        chunks_created = 0
        
        # Очищаем старые документы
        self.documents = []
        
        # Перебираем файлы
        for filename in os.listdir(data_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in supported_extensions:
                continue
            
            filepath = os.path.join(data_dir, filename)
            
            try:
                # Читаем файл
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if not content.strip():
                    continue
                
                # Разбиваем на чанки
                chunks = self._split_text(content)
                
                # Добавляем чанки
                for i, chunk in enumerate(chunks):
                    self.documents.append({
                        "id": f"{filename}_{i}",
                        "content": chunk,
                        "source": filename
                    })
                
                files_processed += 1
                chunks_created += len(chunks)
                
                logger.info(f"Проиндексирован файл {filename}: {len(chunks)} чанков")
                
            except Exception as e:
                logger.error(f"Ошибка индексации файла {filename}: {e}")
                continue
        
        # Сохраняем индекс
        self._save_index()
        
        return {
            "files": files_processed,
            "chunks": chunks_created
        }
    
    def _split_text(self, text: str) -> list[str]:
        """
        Разбивает текст на чанки.
        
        Args:
            text: Исходный текст
            
        Returns:
            Список чанков
        """
        chunks = []
        paragraphs = text.split("\n\n")
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(para) > self.chunk_size:
                    sentences = para.replace(". ", ".|").split("|")
                    current_chunk = ""
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                            if current_chunk:
                                current_chunk += " "
                            current_chunk += sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
                else:
                    current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _tokenize(self, text: str) -> list[str]:
        """Простая токенизация текста"""
        # Приводим к нижнему регистру и разбиваем на слова
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        # Фильтруем короткие слова
        return [w for w in words if len(w) > 2]
    
    def _calculate_relevance(self, query_tokens: list[str], doc_content: str) -> float:
        """
        Вычисляет релевантность документа запросу (простой TF-IDF подобный скор).
        
        Args:
            query_tokens: Токены запроса
            doc_content: Содержимое документа
            
        Returns:
            Скор релевантности
        """
        doc_tokens = self._tokenize(doc_content)
        if not doc_tokens:
            return 0.0
        
        doc_counter = Counter(doc_tokens)
        score = 0.0
        
        for token in query_tokens:
            if token in doc_counter:
                # TF компонент
                tf = doc_counter[token] / len(doc_tokens)
                # Упрощённый IDF (бонус за редкие слова)
                idf = 1.0 + log(1.0 + 1.0 / (1.0 + doc_counter[token]))
                score += tf * idf
        
        return score
    
    def search(self, query: str, n_results: int = 3) -> dict:
        """
        Поиск релевантных документов.
        
        Args:
            query: Поисковый запрос
            n_results: Количество результатов
            
        Returns:
            Результаты поиска в формате ChromaDB
        """
        if not self.documents:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        # Вычисляем релевантность для каждого документа
        scored_docs = []
        for doc in self.documents:
            score = self._calculate_relevance(query_tokens, doc["content"])
            if score > 0:
                scored_docs.append((doc, score))
        
        # Сортируем по релевантности
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Берём топ-N
        top_docs = scored_docs[:n_results]
        
        if not top_docs:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        # Формируем результат в формате ChromaDB
        documents = [[doc["content"] for doc, _ in top_docs]]
        metadatas = [[{"source": doc["source"]} for doc, _ in top_docs]]
        distances = [[1.0 - score for _, score in top_docs]]  # Инвертируем скор в "расстояние"
        
        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances
        }
    
    def get_stats(self) -> dict:
        """
        Возвращает статистику базы знаний.
        
        Returns:
            Словарь со статистикой
        """
        sources = set(doc["source"] for doc in self.documents)
        return {
            "total_chunks": len(self.documents),
            "sources": len(sources)
        }
    
    def clear(self) -> bool:
        """
        Очищает хранилище.
        
        Returns:
            True если успешно
        """
        try:
            self.documents = []
            self._save_index()
            logger.info("Хранилище очищено")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки: {e}")
            return False
