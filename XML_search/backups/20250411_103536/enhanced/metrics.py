from typing import Dict, List, Optional, Any
import time
import threading
from collections import defaultdict
from statistics import mean, median
from .config_enhanced import enhanced_config
from .log_manager import LogManager
import logging

class MetricsCollector:
    """Сборщик метрик производительности"""
    
    def __init__(self):
        self.timing_metrics = defaultdict(list)
        self.count_metrics = defaultdict(int)
        self.last_cleanup = time.time()
        self.logger = logging.getLogger(__name__)
        self.enabled = enhanced_config.metrics.enabled
        self.cache_metrics = enhanced_config.metrics.cache_metrics
        self.log_metrics = enhanced_config.metrics.log_metrics
        self._lock = threading.Lock()
        
        # Запуск фонового потока очистки старых метрик
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """Запуск фонового потока очистки метрик"""
        def cleanup_worker():
            while True:
                time.sleep(enhanced_config.metrics.cleanup_interval)
                self.cleanup_old_metrics()
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
        self.logger.info("Запущен поток очистки метрик")
    
    def record_timing(self, metric_name: str, duration: float) -> None:
        """Записывает время выполнения операции"""
        if not self.enabled:
            return
        with self._lock:
            self.timing_metrics[metric_name].append(duration)
            if self.log_metrics:
                self.logger.debug(f"Recorded timing for {metric_name}: {duration:.2f}s")
    
    def record_count(self, metric_name: str, value: int = 1) -> None:
        """Записывает значение счетчика"""
        if not self.enabled:
            return
        with self._lock:
            self.count_metrics[metric_name] += value
            if self.log_metrics:
                self.logger.debug(f"Recorded count for {metric_name}: {value}")
    
    def increment(self, metric_name: str, value: int = 1) -> None:
        """Увеличивает счетчик метрики"""
        if not self.enabled:
            return
        with self._lock:
            if isinstance(value, dict):
                # Если передан словарь с метаданными, используем только значение 1
                self.count_metrics[metric_name] += 1
            else:
                self.count_metrics[metric_name] += value
            if self.log_metrics:
                self.logger.debug(f"Incremented metric {metric_name} by {value}")
    
    def decrement(self, metric_name: str, value: int = 1) -> None:
        """Уменьшает счетчик метрики"""
        if not self.enabled:
            return
        with self._lock:
            if isinstance(value, dict):
                # Если передан словарь с метаданными, используем только значение 1
                self.count_metrics[metric_name] -= 1
            else:
                self.count_metrics[metric_name] -= value
            if self.log_metrics:
                self.logger.debug(f"Decremented metric {metric_name} by {value}")
    
    def gauge(self, metric: str, value: float) -> None:
        """Установка значения метрики"""
        if not self.enabled:
            return
        with self._lock:
            self.timing_metrics[metric] = [value]
    
    def get_timing_stats(self, metric_name: str) -> Dict[str, float]:
        """Получает статистику по времени выполнения"""
        if not self.enabled:
            return {}
        with self._lock:
            values = self.timing_metrics.get(metric_name, [])
            if not values:
                return {}
            return {
                "min": min(values),
                "max": max(values),
                "avg": mean(values),
                "median": median(values),
                "count": len(values)
            }
    
    def get_count_stats(self, metric_name: str) -> Dict[str, int]:
        """Получает статистику по счетчикам"""
        if not self.enabled:
            return {}
        with self._lock:
            return {
                "value": self.count_metrics.get(metric_name, 0)
            }
    
    def cleanup_old_metrics(self) -> None:
        """Очищает старые метрики"""
        if not self.enabled:
            return
        with self._lock:
            current_time = time.time()
            if current_time - self.last_cleanup >= enhanced_config.metrics.cleanup_interval:
                self.timing_metrics.clear()
                self.count_metrics.clear()
                self.last_cleanup = current_time
                if self.log_metrics:
                    self.logger.debug("Cleaned up old metrics")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Получает все метрики"""
        if not self.enabled:
            return {}
        with self._lock:
            self.cleanup_old_metrics()
            return {
                "timing": {name: self.get_timing_stats(name) for name in self.timing_metrics},
                "count": {name: self.get_count_stats(name) for name in self.count_metrics}
            }
    
    def reset(self) -> None:
        """Сброс всех метрик"""
        with self._lock:
            self.timing_metrics.clear()
            self.count_metrics.clear()
        self.logger.info("Все метрики сброшены")
    
    class TimingContext:
        """Контекстный менеджер для измерения времени выполнения операции"""
        def __init__(self, collector, operation):
            self.collector = collector
            self.operation = operation
            self.start_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.collector.enabled:
                duration = time.time() - self.start_time
                self.collector.record_timing(self.operation, duration)
            
    def timing(self, operation: str):
        """Контекстный менеджер для измерения времени выполнения операции"""
        return self.TimingContext(self, operation)

    def track_search_performance(self, search_type: str, duration: float, results_count: int) -> None:
        """
        Отслеживание производительности поиска
        
        Args:
            search_type: Тип поиска (exact, basic, extended)
            duration: Время выполнения в секундах
            results_count: Количество найденных результатов
        """
        if not self.enabled:
            return
        with self._lock:
            self.record_timing(f'search_{search_type}_duration', duration)
            self.gauge(f'search_{search_type}_results', results_count)
            self.increment(f'search_{search_type}_total')
            
            if self.log_metrics:
                self.logger.debug(
                    f"Search performance: type={search_type}, "
                    f"duration={duration:.2f}s, results={results_count}"
                )

    def track_search_stage(self, stage: str, duration: float) -> None:
        """
        Отслеживание времени выполнения этапа поиска
        
        Args:
            stage: Название этапа поиска
            duration: Время выполнения в секундах
        """
        if not self.enabled:
            return
        with self._lock:
            self.record_timing(f'search_stage_{stage}', duration)
            self.increment(f'search_stage_{stage}_count')
            
            if self.log_metrics:
                self.logger.debug(
                    f"Search stage performance: stage={stage}, duration={duration:.2f}s"
                )

    def track_cache_operation(self, operation: str, success: bool = True) -> None:
        """
        Отслеживание операций с кэшем
        
        Args:
            operation: Тип операции (hit, miss, set, delete)
            success: Успешность операции
        """
        if not self.enabled or not self.cache_metrics:
            return
        with self._lock:
            metric_name = f'cache_{operation}_{"success" if success else "failure"}'
            self.increment(metric_name)
            
            if self.log_metrics:
                self.logger.debug(
                    f"Cache operation: type={operation}, "
                    f"status={'success' if success else 'failure'}"
                )

    def get_search_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение статистики по поиску
        
        Returns:
            Словарь со статистикой поиска
        """
        if not self.enabled:
            return {}
        with self._lock:
            stats = {}
            for search_type in ['exact', 'basic', 'extended']:
                timing_stats = self.get_timing_stats(f'search_{search_type}_duration')
                results_stats = self.get_timing_stats(f'search_{search_type}_results')
                total_searches = self.get_count_stats(f'search_{search_type}_total')['value']
                
                stats[search_type] = {
                    'duration': timing_stats,
                    'total_searches': total_searches,
                    'avg_results': results_stats.get('avg', 0) if results_stats else 0
                }
            return stats

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Получение статистики по кэшу
        
        Returns:
            Словарь со статистикой кэша
        """
        if not self.enabled or not self.cache_metrics:
            return {}
        with self._lock:
            return {
                'hits': self.get_count_stats('cache_hit_success')['value'],
                'misses': self.get_count_stats('cache_miss_success')['value'],
                'sets': self.get_count_stats('cache_set_success')['value'],
                'errors': sum(
                    self.get_count_stats(f'cache_{op}_failure')['value']
                    for op in ['hit', 'miss', 'set', 'delete']
                )
            } 