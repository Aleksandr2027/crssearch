"""
Модуль для управления метриками производительности
"""

import time
import asyncio
from typing import Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from .log_manager import LogManager

logger = LogManager().get_logger(__name__)

@dataclass
class OperationMetrics:
    """Метрики для отдельной операции"""
    count: int = 0
    total_time: float = 0.0
    errors: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    min_time: float = float('inf')
    max_time: float = 0.0
    
    def record_operation(self, duration: float) -> None:
        """Запись метрики операции"""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        
    def record_error(self, error: str) -> None:
        """Запись ошибки"""
        self.errors += 1
        self.last_error = error
        self.last_error_time = datetime.now()
        
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        if self.count == 0:
            return {
                'count': 0,
                'errors': self.errors,
                'last_error': self.last_error,
                'last_error_time': self.last_error_time
            }
            
        return {
            'count': self.count,
            'total_time': self.total_time,
            'avg_time': self.total_time / self.count,
            'min_time': self.min_time if self.min_time != float('inf') else 0,
            'max_time': self.max_time,
            'errors': self.errors,
            'last_error': self.last_error,
            'last_error_time': self.last_error_time
        }

class MetricsManager:
    """Менеджер метрик"""
    
    def __init__(self):
        """Инициализация менеджера метрик"""
        self._metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self._start_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        
    def start_operation(self, operation_name: str) -> float:
        """
        Начало отсчета времени операции
        
        Args:
            operation_name: Имя операции
            
        Returns:
            float: Время начала операции
        """
        start_time = time.monotonic()
        self._start_times[operation_name] = start_time
        return start_time
        
    async def record_operation(self, operation_name: str, start_time: float) -> None:
        """
        Запись метрики операции
        
        Args:
            operation_name: Имя операции
            start_time: Время начала операции
        """
        duration = time.monotonic() - start_time
        async with self._lock:
            self._metrics[operation_name].record_operation(duration)
            
    async def record_error(self, operation_name: str, error: str) -> None:
        """
        Запись ошибки операции
        
        Args:
            operation_name: Имя операции
            error: Текст ошибки
        """
        async with self._lock:
            self._metrics[operation_name].record_error(error)
            
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение статистики по всем операциям
        
        Returns:
            Dict[str, Dict[str, Any]]: Статистика операций
        """
        return {
            name: metrics.get_stats()
            for name, metrics in self._metrics.items()
        }
        
    def reset(self) -> None:
        """Сброс всех метрик"""
        self._metrics.clear()
        self._start_times.clear()
        
    async def cleanup_old_metrics(self, max_age: timedelta) -> None:
        """
        Очистка старых метрик
        
        Args:
            max_age: Максимальный возраст метрик
        """
        current_time = datetime.now()
        async with self._lock:
            for metrics in self._metrics.values():
                if (metrics.last_error_time and 
                    current_time - metrics.last_error_time > max_age):
                    metrics.last_error = None
                    metrics.last_error_time = None
                    
    def get_operation_stats(self, operation_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение статистики по конкретной операции
        
        Args:
            operation_name: Имя операции
            
        Returns:
            Optional[Dict[str, Any]]: Статистика операции или None
        """
        if operation_name in self._metrics:
            return self._metrics[operation_name].get_stats()
        return None 