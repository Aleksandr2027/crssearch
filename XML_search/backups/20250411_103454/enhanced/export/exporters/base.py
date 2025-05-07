from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.errors import ValidationError, XMLProcessingError

class BaseExporter(ABC):
    """Базовый класс для экспортеров координатных систем"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация экспортера
        
        Args:
            config: Конфигурация экспортера из export_config.json
        """
        self.config = config
        self.logger = LogManager("export").get_logger()
        self.metrics = MetricsCollector()
        
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
    def export(self, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
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
            'description': self.config.get('description', '')
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
            
    def _track_export_timing(self, format_name: str) -> MetricsCollector.TimingContext:
        """
        Контекстный менеджер для отслеживания времени экспорта
        
        Args:
            format_name: Название формата для метрик
            
        Returns:
            Контекстный менеджер для измерения времени
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
