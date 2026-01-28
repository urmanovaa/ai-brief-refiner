"""
Document Generator Service
==========================
Генерация финального ТЗ в виде файла.
"""

import os
import logging
from datetime import datetime
from typing import Optional
from config import config

logger = logging.getLogger(__name__)


class DocumentGenerator:
    """Генератор документов ТЗ"""
    
    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def generate_brief_txt(
        self,
        goal: str = "",
        audience: str = "",
        project_type: str = "",
        platform: str = "",
        budget: str = "",
        deadline: str = "",
        scope_in: list[str] = None,
        scope_out: list[str] = None,
        deliverables: list[str] = None,
        success_criteria: str = "",
        constraints: str = "",
        red_flags: list[str] = None,
        open_questions: list[str] = None,
        raw_text: str = "",
        user_id: int = 0
    ) -> str:
        """
        Генерирует ТЗ в формате .txt
        
        Returns:
            Путь к сгенерированному файлу
        """
        scope_in = scope_in or []
        scope_out = scope_out or []
        deliverables = deliverables or []
        red_flags = red_flags or []
        open_questions = open_questions or []
        
        # Формируем документ
        lines = [
            "=" * 60,
            "ТЕХНИЧЕСКОЕ ЗАДАНИЕ",
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            "=" * 60,
            "",
        ]
        
        # 1. Цель проекта
        lines.extend([
            "1. ЦЕЛЬ ПРОЕКТА",
            "-" * 40,
            goal or "Не указана",
            "",
        ])
        
        # 2. Целевая аудитория
        lines.extend([
            "2. ЦЕЛЕВАЯ АУДИТОРИЯ",
            "-" * 40,
            audience or "Не указана",
            "",
        ])
        
        # 3. Тип проекта и платформа
        lines.extend([
            "3. ТИП ПРОЕКТА",
            "-" * 40,
            f"Тип: {project_type or 'Не указан'}",
            f"Платформа: {platform or 'Не указана'}",
            "",
        ])
        
        # 4. Объём работ
        lines.extend([
            "4. ОБЪЁМ РАБОТ (SCOPE OF WORK)",
            "-" * 40,
            "",
            "Входит в проект:",
        ])
        if scope_in:
            for item in scope_in:
                lines.append(f"  ✓ {item}")
        else:
            lines.append("  • Не определено")
        
        lines.extend(["", "НЕ входит в проект:"])
        if scope_out:
            for item in scope_out:
                lines.append(f"  ✗ {item}")
        else:
            lines.append("  • Не определено")
        lines.append("")
        
        # 5. Ограничения
        lines.extend([
            "5. ОГРАНИЧЕНИЯ И УСЛОВИЯ",
            "-" * 40,
            f"Бюджет: {budget or 'Не указан'}",
            f"Сроки: {deadline or 'Не указаны'}",
        ])
        if constraints:
            lines.append(f"Дополнительно: {constraints}")
        lines.append("")
        
        # 6. Результаты
        lines.extend([
            "6. ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ",
            "-" * 40,
        ])
        if deliverables:
            for item in deliverables:
                lines.append(f"  • {item}")
        else:
            lines.append("  • Не определены")
        lines.append("")
        
        # 7. Критерии успеха
        lines.extend([
            "7. КРИТЕРИИ УСПЕШНОСТИ",
            "-" * 40,
            success_criteria or "Не определены",
            "",
        ])
        
        # 8. Риски
        if red_flags:
            lines.extend([
                "⚠️ ВОЗМОЖНЫЕ РИСКИ И НЕТОЧНОСТИ",
                "-" * 40,
            ])
            for flag in red_flags:
                lines.append(f"  ! {flag}")
            lines.append("")
        
        # 9. Открытые вопросы
        if open_questions:
            lines.extend([
                "❓ ОТКРЫТЫЕ ВОПРОСЫ",
                "-" * 40,
            ])
            for q in open_questions:
                lines.append(f"  ? {q}")
            lines.append("")
        
        # Подвал
        lines.extend([
            "",
            "=" * 60,
            "Документ сгенерирован AI Brief Refiner",
            "=" * 60,
        ])
        
        # Сохраняем файл
        filename = f"tz_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Сгенерирован документ: {filepath}")
        return filepath
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Удаляет старые временные файлы"""
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(self.temp_dir):
            filepath = os.path.join(self.temp_dir, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    logger.debug(f"Удалён старый файл: {filename}")

