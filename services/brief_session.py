"""
Brief Session Manager
=====================
Управление сессией сбора брифа пользователя.
Расширенная модель данных с валидацией.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class BriefStatus(Enum):
    """Статус сессии брифа"""
    IDLE = "idle"              # Нет активной сессии
    COLLECTING = "collecting"  # Сбор информации
    READY = "ready"            # Достаточно данных для генерации


@dataclass
class BriefData:
    """
    Единая структура данных брифа.
    Все поля, которые собираются и попадают в документ.
    """
    # === ОСНОВНАЯ ИНФОРМАЦИЯ ===
    project_name: str = ""          # Название проекта (опционально)
    project_goal: str = ""          # Цель проекта (ОБЯЗАТЕЛЬНО)
    target_audience: str = ""       # Целевая аудитория
    project_type: str = ""          # Тип проекта (ОБЯЗАТЕЛЬНО)
    platform: str = ""              # Платформа (ОБЯЗАТЕЛЬНО)
    
    # === ФУНКЦИОНАЛЬНОСТЬ ===
    must_have_features: list[str] = field(default_factory=list)   # Обязательные функции
    nice_to_have_features: list[str] = field(default_factory=list) # Желательные функции
    integrations: list[str] = field(default_factory=list)         # Интеграции
    references: list[str] = field(default_factory=list)           # Референсы/примеры
    
    # === КОНТЕНТ ===
    content_ready: str = ""         # Готовность контента (тексты, фото)
    
    # === ОГРАНИЧЕНИЯ ===
    deadline: str = ""              # Сроки (ОБЯЗАТЕЛЬНО)
    budget_range: str = ""          # Бюджет (ОБЯЗАТЕЛЬНО)
    constraints: list[str] = field(default_factory=list)  # Другие ограничения
    
    # === РЕЗУЛЬТАТЫ ===
    deliverables: list[str] = field(default_factory=list)         # Что должно быть на выходе
    acceptance_criteria: list[str] = field(default_factory=list)  # Критерии приёмки
    
    # === КОММУНИКАЦИЯ ===
    stakeholders: str = ""          # Кто принимает решения
    communication_format: str = ""   # Предпочтительный формат связи
    
    # === АВТОГЕНЕРАЦИЯ (заполняется LLM) ===
    risks: list[str] = field(default_factory=list)          # Выявленные риски
    open_questions: list[str] = field(default_factory=list) # Открытые вопросы
    
    # === СЛУЖЕБНЫЕ ===
    raw_messages: list[str] = field(default_factory=list)   # Все сообщения пользователя
    llm_analysis: str = ""          # Анализ от LLM (для дополнительного контекста)
    
    # === ОБЯЗАТЕЛЬНЫЕ ПОЛЯ ===
    REQUIRED_FIELDS = [
        ("project_goal", "цель проекта"),
        ("project_type", "тип проекта"),
        ("platform", "платформа"),
    ]
    
    RECOMMENDED_FIELDS = [
        ("deadline", "сроки"),
        ("budget_range", "бюджет"),
        ("deliverables", "ожидаемые результаты"),
        ("must_have_features", "основной функционал"),
    ]
    
    def get_missing_required(self) -> list[tuple[str, str]]:
        """Возвращает список недостающих обязательных полей"""
        missing = []
        for field_name, display_name in self.REQUIRED_FIELDS:
            value = getattr(self, field_name, None)
            if not value or (isinstance(value, list) and len(value) == 0):
                missing.append((field_name, display_name))
        return missing
    
    def get_missing_recommended(self) -> list[tuple[str, str]]:
        """Возвращает список недостающих рекомендуемых полей"""
        missing = []
        for field_name, display_name in self.RECOMMENDED_FIELDS:
            value = getattr(self, field_name, None)
            if not value or (isinstance(value, list) and len(value) == 0):
                missing.append((field_name, display_name))
        return missing
    
    def is_valid_for_generation(self) -> bool:
        """Проверяет, достаточно ли данных для генерации ТЗ"""
        return len(self.get_missing_required()) == 0
    
    def get_completion_percent(self) -> int:
        """Возвращает процент заполненности брифа"""
        all_fields = self.REQUIRED_FIELDS + self.RECOMMENDED_FIELDS
        filled = 0
        for field_name, _ in all_fields:
            value = getattr(self, field_name, None)
            if value and (not isinstance(value, list) or len(value) > 0):
                filled += 1
        return int((filled / len(all_fields)) * 100)
    
    def to_summary(self) -> str:
        """Форматирует собранные данные для показа пользователю"""
        lines = ["📋 <b>Собранная информация:</b>\n"]
        
        # Основная информация
        if self.project_name:
            lines.append(f"📌 <b>Название:</b> {self.project_name}")
        if self.project_goal:
            lines.append(f"🎯 <b>Цель:</b> {self.project_goal[:200]}{'...' if len(self.project_goal) > 200 else ''}")
        if self.project_type:
            lines.append(f"📁 <b>Тип проекта:</b> {self.project_type}")
        if self.platform:
            lines.append(f"💻 <b>Платформа:</b> {self.platform}")
        if self.target_audience:
            lines.append(f"👥 <b>Аудитория:</b> {self.target_audience}")
        
        # Функционал
        if self.must_have_features:
            lines.append(f"\n✅ <b>Обязательные функции:</b>")
            for f in self.must_have_features[:5]:
                lines.append(f"  • {f}")
            if len(self.must_have_features) > 5:
                lines.append(f"  <i>...и ещё {len(self.must_have_features) - 5}</i>")
        
        if self.nice_to_have_features:
            lines.append(f"\n💡 <b>Желательные функции:</b>")
            for f in self.nice_to_have_features[:3]:
                lines.append(f"  • {f}")
        
        if self.integrations:
            lines.append(f"\n🔗 <b>Интеграции:</b> {', '.join(self.integrations)}")
        
        if self.references:
            lines.append(f"\n🔍 <b>Референсы:</b> {', '.join(self.references)}")
        
        # Ограничения
        if self.deadline:
            lines.append(f"\n⏰ <b>Сроки:</b> {self.deadline}")
        if self.budget_range:
            lines.append(f"💰 <b>Бюджет:</b> {self.budget_range}")
        
        # Результаты
        if self.deliverables:
            lines.append(f"\n📦 <b>Результаты:</b>")
            for d in self.deliverables:
                lines.append(f"  • {d}")
        
        # Статус
        completion = self.get_completion_percent()
        missing_required = self.get_missing_required()
        
        lines.append(f"\n━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 <b>Заполнено:</b> {completion}%")
        
        if missing_required:
            lines.append(f"\n⚠️ <b>Не хватает для генерации:</b>")
            for _, name in missing_required:
                lines.append(f"  • {name}")
        else:
            lines.append(f"\n✅ <b>Можно генерировать ТЗ!</b>")
        
        if len(lines) <= 3:
            return "📋 Пока нет собранной информации.\n\nНачни с /new"
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict[str, Any]:
        """Конвертирует в словарь для передачи в генератор"""
        return {
            "project_name": self.project_name,
            "project_goal": self.project_goal,
            "target_audience": self.target_audience,
            "project_type": self.project_type,
            "platform": self.platform,
            "must_have_features": self.must_have_features,
            "nice_to_have_features": self.nice_to_have_features,
            "integrations": self.integrations,
            "references": self.references,
            "content_ready": self.content_ready,
            "deadline": self.deadline,
            "budget_range": self.budget_range,
            "constraints": self.constraints,
            "deliverables": self.deliverables,
            "acceptance_criteria": self.acceptance_criteria,
            "stakeholders": self.stakeholders,
            "communication_format": self.communication_format,
            "risks": self.risks,
            "open_questions": self.open_questions,
            "raw_messages": self.raw_messages,
            "llm_analysis": self.llm_analysis,
        }


@dataclass
class BriefSession:
    """Сессия брифа пользователя"""
    user_id: int
    status: BriefStatus = BriefStatus.IDLE
    data: BriefData = field(default_factory=BriefData)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    current_step: str = "start"  # Текущий шаг сбора
    
    def start(self):
        """Начинает новую сессию"""
        self.status = BriefStatus.COLLECTING
        self.data = BriefData()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.current_step = "project_type"
        logger.info(f"Начата сессия брифа для пользователя {self.user_id}")
    
    def cancel(self):
        """Отменяет сессию"""
        self.status = BriefStatus.IDLE
        self.data = BriefData()
        self.current_step = "start"
        logger.info(f"Отменена сессия брифа для пользователя {self.user_id}")
    
    def add_message(self, text: str):
        """Добавляет сообщение пользователя"""
        self.data.raw_messages.append(text)
        self.updated_at = datetime.now()
    
    def is_active(self) -> bool:
        """Проверяет, активна ли сессия"""
        return self.status == BriefStatus.COLLECTING
    
    def mark_ready(self):
        """Отмечает сессию как готовую к генерации"""
        if self.data.is_valid_for_generation():
            self.status = BriefStatus.READY


class BriefSessionManager:
    """Менеджер сессий брифов"""
    
    def __init__(self):
        self._sessions: dict[int, BriefSession] = {}
    
    def get_session(self, user_id: int) -> BriefSession:
        """Получает или создаёт сессию пользователя"""
        if user_id not in self._sessions:
            self._sessions[user_id] = BriefSession(user_id=user_id)
        return self._sessions[user_id]
    
    def start_session(self, user_id: int) -> BriefSession:
        """Начинает новую сессию"""
        session = self.get_session(user_id)
        session.start()
        return session
    
    def cancel_session(self, user_id: int) -> bool:
        """Отменяет сессию"""
        if user_id in self._sessions:
            self._sessions[user_id].cancel()
            return True
        return False
    
    def is_session_active(self, user_id: int) -> bool:
        """Проверяет, есть ли активная сессия"""
        session = self._sessions.get(user_id)
        return session is not None and session.is_active()
    
    def get_brief_data(self, user_id: int) -> Optional[BriefData]:
        """Возвращает данные брифа"""
        session = self._sessions.get(user_id)
        if session:
            return session.data
        return None
    
    def update_brief_data(self, user_id: int, **kwargs):
        """Обновляет данные брифа"""
        session = self.get_session(user_id)
        for key, value in kwargs.items():
            if hasattr(session.data, key):
                current = getattr(session.data, key)
                # Для списков — добавляем, а не заменяем
                if isinstance(current, list) and isinstance(value, str):
                    current.append(value)
                elif isinstance(current, list) and isinstance(value, list):
                    current.extend(value)
                else:
                    setattr(session.data, key, value)
        session.updated_at = datetime.now()
        logger.debug(f"Updated brief data for user {user_id}: {kwargs}")
    
    def set_brief_field(self, user_id: int, field_name: str, value: Any):
        """Устанавливает конкретное поле (заменяет значение)"""
        session = self.get_session(user_id)
        if hasattr(session.data, field_name):
            setattr(session.data, field_name, value)
            session.updated_at = datetime.now()
    
    def add_to_list_field(self, user_id: int, field_name: str, value: str):
        """Добавляет значение в список"""
        session = self.get_session(user_id)
        if hasattr(session.data, field_name):
            current = getattr(session.data, field_name)
            if isinstance(current, list):
                current.append(value)
                session.updated_at = datetime.now()
