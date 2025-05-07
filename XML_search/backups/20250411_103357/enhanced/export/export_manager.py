from typing import Dict, List, Any, Optional, Type
import json
import os
from .exporters.base import BaseExporter
from ..log_manager import LogManager
from ..metrics import MetricsCollector
from ..cache_manager import CacheManager
from XML_search.errors import ValidationError, XMLProcessingError

class ExportManager:
    """Менеджер экспорта координатных систем"""
    
    def __init__(self, config_path: str = "config/export_config.json"):
        """
        Инициализация менеджера экспорта
        
        Args:
            config_path: Путь к файлу конфигурации экспортеров
        """
        self.logger = LogManager("export_manager").get_logger()
        self.metrics = MetricsCollector()
        self.cache = CacheManager()
        self.exporters: Dict[str, BaseExporter] = {}
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Загрузка конфигурации экспортеров
        
        Returns:
            Словарь с конфигурацией
            
        Raises:
            FileNotFoundError: Если файл конфигурации не найден
            json.JSONDecodeError: Если файл содержит невалидный JSON
        """
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Файл конфигурации {self.config_path} не найден")
                return {"exporters": {}}
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.info("Конфигурация экспортеров успешно загружена")
                return config
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфигурации: {e}")
            return {"exporters": {}}
            
    def register_exporter(self, name: str, exporter_class: Type[BaseExporter]) -> None:
        """
        Регистрация нового экспортера
        
        Args:
            name: Идентификатор экспортера
            exporter_class: Класс экспортера
            
        Raises:
            ValueError: Если экспортер с таким именем уже зарегистрирован
        """
        if name in self.exporters:
            raise ValueError(f"Экспортер {name} уже зарегистрирован")
            
        config = self.config.get('exporters', {}).get(name, {})
        if not config.get('enabled', True):
            self.logger.info(f"Экспортер {name} отключен в конфигурации")
            return
            
        try:
            exporter = exporter_class(config)
            self.exporters[name] = exporter
            self.logger.info(f"Экспортер {name} успешно зарегистрирован")
            self.metrics.increment('exporters_registered')
        except Exception as e:
            self.logger.error(f"Ошибка при регистрации экспортера {name}: {e}")
            self.metrics.increment('exporter_registration_errors')
            raise
            
    def get_available_formats(self, srid: int) -> List[Dict[str, str]]:
        """
        Получение списка доступных форматов для SRID
        
        Args:
            srid: SRID для проверки
            
        Returns:
            Список словарей с информацией о доступных форматах
        """
        available_formats = []
        for name, exporter in self.exporters.items():
            try:
                if exporter.supports_srid(srid):
                    format_info = exporter.get_format_info()
                    format_info['id'] = name
                    available_formats.append(format_info)
            except Exception as e:
                self.logger.error(f"Ошибка при проверке поддержки формата {name}: {e}")
                continue
                
        return available_formats
        
    def export(self, format_id: str, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Экспорт системы координат в указанный формат
        
        Args:
            format_id: Идентификатор формата
            srid: SRID системы координат
            params: Дополнительные параметры экспорта
            
        Returns:
            Результат экспорта
            
        Raises:
            ValueError: Если формат не найден
            ValidationError: Если параметры невалидны
            XMLProcessingError: При ошибке формирования XML
        """
        # Проверяем наличие экспортера
        if format_id not in self.exporters:
            raise ValueError(f"Формат {format_id} не найден")
            
        exporter = self.exporters[format_id]
        
        # Проверяем кэш
        cache_key = f"export_{format_id}_{srid}_{str(params)}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            self.logger.info(f"Результат экспорта получен из кэша для {format_id}:{srid}")
            self.metrics.increment('export_cache_hits')
            return cached_result
            
        try:
            # Валидируем SRID
            exporter._validate_srid(srid)
            
            # Валидируем параметры
            exporter.validate_params(params)
            
            # Экспортируем с замером времени
            with exporter._track_export_timing(format_id):
                result = exporter.export(srid, params)
                
            # Сохраняем в кэш
            self.cache.set(cache_key, result)
            
            # Логируем успех
            exporter._log_export_attempt(srid, True)
            self.metrics.increment(f'export_{format_id}_success')
            
            return result
            
        except Exception as e:
            # Логируем ошибку
            exporter._log_export_attempt(srid, False)
            self.metrics.increment(f'export_{format_id}_errors')
            self.logger.error(f"Ошибка при экспорте {format_id} для SRID {srid}: {e}")
            raise
            
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик экспорта
        
        Returns:
            Словарь с метриками
        """
        metrics = {
            'exporters_count': len(self.exporters),
            'formats': {}
        }
        
        for name in self.exporters:
            metrics['formats'][name] = {
                'success': self.metrics.get_count_stats(f'export_{name}_success')['value'],
                'errors': self.metrics.get_count_stats(f'export_{name}_errors')['value'],
                'avg_duration': self.metrics.get_timing_stats(f'export_{name}_duration').get('avg', 0)
            }
            
        return metrics
