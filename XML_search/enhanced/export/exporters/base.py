"""
Базовый класс для экспортеров
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.db_context import get_db_manager
from XML_search.errors import ValidationError, XMLProcessingError, ExportError
import logging

class BaseExporter(ABC):
    """Базовый класс для всех экспортеров"""
    
    def __init__(self, config: Dict[str, Any], db_manager: Optional[DatabaseManager] = None, logger: Optional[Any] = None):
        """
        Инициализация базового экспортера
        
        Args:
            config: Конфигурация экспортера
            db_manager: Опциональный менеджер базы данных
            logger: Опциональный логгер для тестов
            
        Raises:
            RuntimeError: Если глобальный менеджер БД не инициализирован
        """
        self.config = config
        self.format_name = config.get('format_name', 'base')
        
        # Инициализируем логгер
        if logger:
            self.logger = logger
        else:
            log_manager = LogManager()
            self.logger = log_manager.get_logger(__name__)
        
        # Инициализируем метрики
        self.metrics = MetricsManager()
        
        # Используем переданный менеджер БД или глобальный
        if db_manager:
            self.db_manager = db_manager
            self.logger.info("Использован переданный DatabaseManager")
        else:
            self.db_manager = get_db_manager()
            if self.db_manager:
                self.logger.info("Использован глобальный DatabaseManager")
            else:
                self.logger.error("Глобальный менеджер БД не найден")
                raise RuntimeError("Глобальный менеджер БД не инициализирован")
            
        # Логируем успешную инициализацию
        self.logger.info(f"Инициализирован экспортер {self.format_name}")
            
    def __del__(self):
        """Деструктор класса"""
        try:
            if hasattr(self, 'logger'):
                self.logger.info("Соединение с базой данных закрыто")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Ошибка при закрытии соединения: {e}")
        
    @abstractmethod
    def supports_srid(self, srid: int) -> bool:
        """
        Проверка поддержки SRID экспортером
        
        Args:
            srid: SRID для проверки
            
        Returns:
            True если SRID поддерживается, False в противном случае
        """
        pass
        
    @abstractmethod
    async def export(self, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Экспорт системы координат в нужный формат
        
        Args:
            srid: SRID системы координат для экспорта
            params: Дополнительные параметры экспорта
            
        Returns:
            Результат экспорта в виде строки
            
        Raises:
            ValidationError: Если параметры экспорта невалидны
            XMLProcessingError: При ошибке формирования XML
        """
        pass
        
    def validate_params(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Валидация параметров экспорта
        
        Args:
            params: Параметры для валидации
            
        Returns:
            True если параметры валидны
            
        Raises:
            ValidationError: Если параметры невалидны
        """
        if not params:
            return True
            
        required_params = self.config.get('required_params', [])
        for param in required_params:
            if param not in params:
                raise ValidationError(f"Отсутствует обязательный параметр: {param}")
                
        return True
        
    def get_format_info(self) -> Dict[str, str]:
        """
        Получение информации о формате экспорта
        
        Returns:
            Словарь с информацией о формате
        """
        return {
            'display_name': self.config.get('display_name', ''),
            'description': self.config.get('description', ''),
            'extension': self.config.get('extension', '')
        }
        
    def _log_export_attempt(self, srid: int, success: bool) -> None:
        """
        Логирование попытки экспорта
        
        Args:
            srid: SRID системы координат
            success: Успешность экспорта
        """
        format_name = self.config.get('display_name', 'Unknown')
        if success:
            self.logger.info(f"Успешный экспорт {format_name} для SRID {srid}")
            self.metrics.increment(f"export_{format_name}_success")
        else:
            self.logger.error(f"Ошибка экспорта {format_name} для SRID {srid}")
            self.metrics.increment(f"export_{format_name}_errors")
            
    def _track_export_timing(self, format_name: str) -> None:
        """
        Контекстный менеджер для отслеживания времени экспорта
        
        Args:
            format_name: Название формата для метрик
        """
        return self.metrics.timing(f"export_{format_name}_duration")
        
    def _validate_srid(self, srid: int) -> None:
        """
        Валидация SRID
        
        Args:
            srid: SRID для валидации
            
        Raises:
            ValidationError: Если SRID невалиден
        """
        if not isinstance(srid, int) or srid <= 0:
            raise ValidationError(f"Невалидный SRID: {srid}")
            
        if not self.supports_srid(srid):
            raise ValidationError(f"SRID {srid} не поддерживается экспортером {self.config.get('display_name')}")

    def export_sync(self, srid: int) -> str:
        """
        Синхронный экспорт системы координат
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Результат экспорта
            
        Raises:
            ExportError: При ошибке экспорта
        """
        try:
            self._validate_srid(srid)
            with self._track_export_timing(self.format_name):
                result = self.export_sync_impl(srid)
                self._log_export_attempt(srid, True)
                return result
        except Exception as e:
            self._log_export_attempt(srid, False)
            raise ExportError(f"Ошибка экспорта: {str(e)}")
            
    @abstractmethod
    def export_sync_impl(self, srid: int) -> str:
        """
        Реализация синхронного экспорта
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Результат экспорта
        """
        pass
