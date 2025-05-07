"""
Модуль для управления кэшем
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from .exceptions import CacheError
from .log_manager import LogManager
from .metrics_manager import MetricsManager

logger = LogManager().get_logger(__name__)

class CacheManager:
    """Менеджер кэша"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Инициализация менеджера кэша
        
        Args:
            max_size: Максимальный размер кэша
            ttl: Время жизни записей в секундах
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.metrics = MetricsManager()
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша
        
        Args:
            key: Ключ
            
        Returns:
            Optional[Any]: Значение или None
        """
        start_time = self.metrics.start_operation('cache_get')
        try:
            async with self._lock:
                if key not in self.cache:
                    await self.metrics.record_operation('cache_get', start_time)
                    return None
                    
                entry = self.cache[key]
                if datetime.now() > entry['expires_at']:
                    del self.cache[key]
                    await self.metrics.record_operation('cache_get', start_time)
                    return None
                    
                await self.metrics.record_operation('cache_get', start_time)
                return entry['value']
                
        except Exception as e:
            await self.metrics.record_error('cache_get', str(e))
            logger.error(f"Ошибка получения из кэша: {e}")
            raise CacheError(f"Ошибка получения из кэша: {e}")
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Установка значения в кэш
        
        Args:
            key: Ключ
            value: Значение
            ttl: Время жизни в секундах
        """
        start_time = self.metrics.start_operation('cache_set')
        try:
            async with self._lock:
                # Проверяем размер кэша
                if len(self.cache) >= self.max_size:
                    # Удаляем самую старую запись
                    oldest_key = min(
                        self.cache.keys(),
                        key=lambda k: self.cache[k]['expires_at']
                    )
                    del self.cache[oldest_key]
                    
                # Добавляем новую запись
                self.cache[key] = {
                    'value': value,
                    'expires_at': datetime.now() + timedelta(seconds=ttl or self.ttl)
                }
                
                await self.metrics.record_operation('cache_set', start_time)
                
        except Exception as e:
            await self.metrics.record_error('cache_set', str(e))
            logger.error(f"Ошибка установки в кэш: {e}")
            raise CacheError(f"Ошибка установки в кэш: {e}")
            
    async def delete(self, key: str) -> None:
        """
        Удаление значения из кэша
        
        Args:
            key: Ключ
        """
        start_time = self.metrics.start_operation('cache_delete')
        try:
            async with self._lock:
                if key in self.cache:
                    del self.cache[key]
                await self.metrics.record_operation('cache_delete', start_time)
                
        except Exception as e:
            await self.metrics.record_error('cache_delete', str(e))
            logger.error(f"Ошибка удаления из кэша: {e}")
            raise CacheError(f"Ошибка удаления из кэша: {e}")
            
    async def clear(self) -> None:
        """Очистка кэша"""
        start_time = self.metrics.start_operation('cache_clear')
        try:
            async with self._lock:
                self.cache.clear()
                await self.metrics.record_operation('cache_clear', start_time)
                
        except Exception as e:
            await self.metrics.record_error('cache_clear', str(e))
            logger.error(f"Ошибка очистки кэша: {e}")
            raise CacheError(f"Ошибка очистки кэша: {e}")
            
    async def cleanup(self) -> None:
        """Очистка устаревших записей"""
        start_time = self.metrics.start_operation('cache_cleanup')
        try:
            async with self._lock:
                now = datetime.now()
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if now > entry['expires_at']
                ]
                for key in expired_keys:
                    del self.cache[key]
                    
                await self.metrics.record_operation('cache_cleanup', start_time)
                
        except Exception as e:
            await self.metrics.record_error('cache_cleanup', str(e))
            logger.error(f"Ошибка очистки устаревших записей: {e}")
            raise CacheError(f"Ошибка очистки устаревших записей: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'metrics': self.metrics.get_stats()
        } 