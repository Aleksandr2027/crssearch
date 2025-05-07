import time
from typing import Dict, Any, Optional
from contextlib import contextmanager
from threading import Lock

class MetricsCollector:
    """Класс для сбора и хранения метрик производительности"""
    
    def __init__(self):
        """Инициализация сборщика метрик"""
        self._metrics: Dict[str, Any] = {
            'counters': {},
            'timers': {},
            'gauges': {}
        }
        self._lock = Lock()
        
    def increment(self, metric_name: str, value: int = 1) -> None:
        """
        Увеличение счетчика метрики
        
        Args:
            metric_name: Имя метрики
            value: Значение для увеличения
        """
        with self._lock:
            self._metrics['counters'][metric_name] = \
                self._metrics['counters'].get(metric_name, 0) + value
                
    def decrement(self, metric_name: str, value: int = 1) -> None:
        """
        Уменьшение счетчика метрики
        
        Args:
            metric_name: Имя метрики
            value: Значение для уменьшения
        """
        with self._lock:
            self._metrics['counters'][metric_name] = \
                self._metrics['counters'].get(metric_name, 0) - value
                
    def set_gauge(self, metric_name: str, value: float) -> None:
        """
        Установка значения метрики-счетчика
        
        Args:
            metric_name: Имя метрики
            value: Значение счетчика
        """
        with self._lock:
            self._metrics['gauges'][metric_name] = value
            
    @contextmanager
    def timing(self, metric_name: str) -> None:
        """
        Контекстный менеджер для измерения времени выполнения
        
        Args:
            metric_name: Имя метрики
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            with self._lock:
                if metric_name not in self._metrics['timers']:
                    self._metrics['timers'][metric_name] = []
                self._metrics['timers'][metric_name].append(duration)
                
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение всех собранных метрик
        
        Returns:
            Словарь с метриками
        """
        with self._lock:
            return {
                'counters': self._metrics['counters'].copy(),
                'timers': {
                    name: {
                        'count': len(values),
                        'avg': sum(values) / len(values) if values else 0,
                        'min': min(values) if values else 0,
                        'max': max(values) if values else 0
                    }
                    for name, values in self._metrics['timers'].items()
                },
                'gauges': self._metrics['gauges'].copy()
            }
            
    def reset(self) -> None:
        """Сброс всех метрик"""
        with self._lock:
            self._metrics = {
                'counters': {},
                'timers': {},
                'gauges': {}
            } 