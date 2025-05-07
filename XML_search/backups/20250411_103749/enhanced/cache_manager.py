from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
import threading
import time
from .config_enhanced import enhanced_config
from .log_manager import LogManager
import logging
import json
import hashlib

class CacheManager:
    """Класс для управления кэшем"""
    
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        Инициализация менеджера кэша
        
        Args:
            ttl: Время жизни кэша в секундах
            max_size: Максимальный размер кэша
        """
        self.ttl = ttl
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
    def _generate_key(self, data: Any) -> str:
        """
        Генерация ключа кэша
        
        Args:
            data: Данные для генерации ключа
            
        Returns:
            Строка с хешем данных
        """
        if isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True)
        return hashlib.md5(str(data).encode()).hexdigest()
        
    def get(self, key: Any) -> Optional[Any]:
        """
        Получение данных из кэша
        
        Args:
            key: Ключ для поиска
            
        Returns:
            Данные из кэша или None
        """
        cache_key = self._generate_key(key)
        if cache_key not in self.cache:
            return None
            
        item = self.cache[cache_key]
        if datetime.now() > item['expires']:
            del self.cache[cache_key]
            return None
            
        return item['value']
        
    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохранение данных в кэш
        
        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
            ttl: Время жизни в секундах
        """
        if len(self.cache) >= self.max_size:
            self._cleanup()
            
        cache_key = self._generate_key(key)
        expires = datetime.now() + timedelta(seconds=ttl or self.ttl)
        
        self.cache[cache_key] = {
            'value': value,
            'expires': expires
        }
        
    def delete(self, key: Any) -> None:
        """
        Удаление данных из кэша
        
        Args:
            key: Ключ для удаления
        """
        cache_key = self._generate_key(key)
        if cache_key in self.cache:
            del self.cache[cache_key]
            
    def clear(self) -> None:
        """Очистка всего кэша"""
        self.cache.clear()
        
    def _cleanup(self) -> None:
        """Очистка устаревших данных"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now > item['expires']
        ]
        
        for key in expired_keys:
            del self.cache[key]
            
        if len(self.cache) >= self.max_size:
            # Если после очистки кэш все еще полон,
            # удаляем самые старые записи
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1]['expires']
            )
            for key, _ in sorted_items[:len(self.cache) - self.max_size]:
                del self.cache[key]
                
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики по кэшу
        
        Returns:
            Словарь со статистикой
        """
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'expired_items': len([
                key for key, item in self.cache.items()
                if datetime.now() > item['expires']
            ])
        }

    def _start_cleanup_thread(self) -> None:
        """Запуск фонового потока для очистки кэша"""
        def cleanup_worker():
            while True:
                time.sleep(self.config.cleanup_interval)
                self.cleanup()
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
        self.logger.info("Запущен поток очистки кэша")
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """Проверка истечения срока действия записи"""
        return (datetime.now() - timestamp).total_seconds() > self.config.ttl
    
    def cleanup(self, force: bool = False) -> None:
        """
        Очистка устаревших записей
        
        Args:
            force: Принудительная очистка до достижения min_cleanup_size
        """
        with self._lock:
            # Удаляем устаревшие записи
            current_time = datetime.now()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if self._is_expired(timestamp)
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            # Если требуется принудительная очистка
            if force and len(self._cache) > self.config.min_cleanup_size:
                # Сортируем по времени и удаляем старые записи
                sorted_items = sorted(
                    self._cache.items(),
                    key=lambda x: x[1][1]
                )
                
                items_to_remove = len(self._cache) - self.config.min_cleanup_size
                for key, _ in sorted_items[:items_to_remove]:
                    del self._cache[key]
            
            if expired_keys or force:
                self.logger.info(
                    f"Очистка кэша: удалено {len(expired_keys)} устаревших записей, "
                    f"текущий размер: {len(self._cache)}"
                )
    
    def clear(self) -> None:
        """Полная очистка кэша"""
        with self._lock:
            self._cache.clear()
            self.logger.info("Кэш полностью очищен")
    
    def get_stats(self) -> Dict[str, int]:
        """Получение статистики кэша"""
        with self._lock:
            total_items = len(self._cache)
            expired_items = sum(
                1 for _, timestamp in self._cache.values()
                if self._is_expired(timestamp)
            )
            
            return {
                "total_items": total_items,
                "expired_items": expired_items,
                "active_items": total_items - expired_items
            } 