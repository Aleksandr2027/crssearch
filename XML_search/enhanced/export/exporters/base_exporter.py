"""
Базовый класс для экспортеров систем координат
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ...db_manager_enhanced import EnhancedDatabaseManager
from ...log_manager import LogManager
from ...metrics_manager import MetricsManager
from ..exceptions import ExportError, ValidationError
import json
from pathlib import Path

logger = LogManager().get_logger(__name__)

class BaseExporter(ABC):
    """Базовый класс для экспортеров"""
    
    def __init__(self, config: Dict[str, Any], db_manager: EnhancedDatabaseManager, output_dir: str):
        """
        Инициализация экспортера
        
        Args:
            config: Конфигурация экспортера
            db_manager: Менеджер базы данных
            output_dir: Директория для сохранения файлов
        """
        self.config = config
        self.db_manager = db_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = LogManager().get_logger(__name__)
        self.metrics = MetricsManager()
        self._lock = asyncio.Lock()
        
    async def export(self, srid: str) -> str:
        """
        Экспорт системы координат
        
        Args:
            srid: SRID системы координат
            
        Returns:
            str: Результат экспорта
            
        Raises:
            ExportError: При ошибке экспорта
        """
        try:
            # Получаем данные системы координат
            cs_data = await self._get_coordinate_system(srid)
            
            # Валидируем данные
            self._validate_data(cs_data)
            
            # Выполняем экспорт
            with self.metrics.timing(f'{self.__class__.__name__}_export'):
                result = await self._export_impl(cs_data)
                
            return result
            
        except ValidationError as e:
            self.logger.error(f"Ошибка валидации данных: {e}")
            self.metrics.increment('validation_errors')
            raise ExportError(f"Ошибка валидации данных: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта: {e}")
            self.metrics.increment('export_errors')
            raise ExportError(f"Ошибка экспорта: {str(e)}")
            
    async def _get_coordinate_system(self, srid: str) -> Dict[str, Any]:
        """
        Получение данных системы координат из базы
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Dict[str, Any]: Данные системы координат
            
        Raises:
            ExportError: Если система координат не найдена
        """
        try:
            query = """
                SELECT srid, auth_name, auth_srid, srtext, proj4text
                FROM spatial_ref_sys
                WHERE srid = %s
            """
            
            results = await self.db_manager.execute_query(query, (srid,))
            
            if not results:
                raise ExportError(f"Система координат с SRID {srid} не найдена")
                
            return results[0]
            
        except Exception as e:
            self.logger.error(f"Ошибка получения данных системы координат: {e}")
            self.metrics.increment('db_errors')
            raise
            
    def _validate_data(self, data: Dict[str, Any]) -> None:
        """
        Валидация данных системы координат
        
        Args:
            data: Данные для валидации
            
        Raises:
            ValidationError: При ошибке валидации
        """
        validation_config = self.config.get('validation', {})
        required_fields = validation_config.get('required_fields', [])
        max_text_length = validation_config.get('max_text_length', 4096)
        
        # Проверяем обязательные поля
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValidationError(
                f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
            )
            
        # Проверяем длину текстовых полей
        for field, value in data.items():
            if isinstance(value, str) and len(value) > max_text_length:
                raise ValidationError(
                    f"Превышена максимальная длина поля {field}: "
                    f"{len(value)} > {max_text_length}"
                )
                
    def _load_template(self, template_path: str) -> str:
        """
        Загрузка шаблона
        
        Args:
            template_path: Путь к файлу шаблона
            
        Returns:
            str: Содержимое шаблона
            
        Raises:
            ExportError: При ошибке загрузки шаблона
        """
        try:
            template_file = Path(__file__).parent / template_path
            
            if not template_file.exists():
                raise ExportError(f"Шаблон не найден: {template_path}")
                
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки шаблона {template_path}: {e}")
            raise ExportError(f"Ошибка загрузки шаблона: {str(e)}")
            
    @abstractmethod
    async def _export_impl(self, data: Dict[str, Any]) -> str:
        """
        Реализация экспорта в конкретном формате
        
        Args:
            data: Данные системы координат
            
        Returns:
            str: Результат экспорта
        """
        pass

    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных
        
        Args:
            data: Данные для валидации
            
        Returns:
            bool: True если данные валидны
        """
        start_time = self.metrics.start_operation('validate_data')
        try:
            # Базовая валидация
            if not isinstance(data, dict):
                await self.metrics.record_error('validate_data', 'Data must be a dictionary')
                return False
                
            if not data:
                await self.metrics.record_error('validate_data', 'Data cannot be empty')
                return False
                
            await self.metrics.record_operation('validate_data', start_time)
            return True
            
        except Exception as e:
            await self.metrics.record_error('validate_data', str(e))
            logger.error(f"Ошибка валидации данных: {e}")
            return False
            
    async def prepare_output_dir(self) -> None:
        """Подготовка директории для экспорта"""
        start_time = self.metrics.start_operation('prepare_output_dir')
        try:
            async with self._lock:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                await self.metrics.record_operation('prepare_output_dir', start_time)
                
        except Exception as e:
            await self.metrics.record_error('prepare_output_dir', str(e))
            logger.error(f"Ошибка подготовки директории: {e}")
            raise ExportError(f"Ошибка подготовки директории: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики экспортера"""
        return {
            'output_dir': str(self.output_dir),
            'metrics': self.metrics.get_stats()
        } 