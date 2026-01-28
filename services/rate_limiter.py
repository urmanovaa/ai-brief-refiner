"""
Rate Limiter Service
====================
Ограничение частоты запросов пользователей.
"""

import time
import logging
from collections import defaultdict
from config import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Простой rate limiter на основе sliding window"""
    
    def __init__(
        self,
        max_requests: int = None,
        window_seconds: int = None
    ):
        self.max_requests = max_requests or config.RATE_LIMIT_MESSAGES
        self.window_seconds = window_seconds or config.RATE_LIMIT_WINDOW
        self._requests: dict[int, list[float]] = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Проверяет, разрешён ли запрос для пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если запрос разрешён
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Очищаем старые запросы
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if t > window_start
        ]
        
        # Проверяем лимит
        if len(self._requests[user_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # Записываем новый запрос
        self._requests[user_id].append(current_time)
        return True
    
    def get_remaining(self, user_id: int) -> int:
        """Возвращает количество оставшихся запросов"""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        recent_requests = [
            t for t in self._requests.get(user_id, [])
            if t > window_start
        ]
        
        return max(0, self.max_requests - len(recent_requests))
    
    def get_reset_time(self, user_id: int) -> int:
        """Возвращает время до сброса лимита в секундах"""
        if user_id not in self._requests or not self._requests[user_id]:
            return 0
        
        oldest_request = min(self._requests[user_id])
        reset_time = oldest_request + self.window_seconds - time.time()
        return max(0, int(reset_time))
    
    def reset(self, user_id: int):
        """Сбрасывает счётчик для пользователя"""
        if user_id in self._requests:
            del self._requests[user_id]


# Глобальный экземпляр
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Возвращает синглтон rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

