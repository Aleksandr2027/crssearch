"""
Базовый класс для экспортеров систем координат
"""

import asyncio
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ...db_manager_enhanced import EnhancedDatabaseManager
from ...log_manager import LogManager
from ...metrics_manager import MetricsManager
from ..exceptions import ExportError, ValidationError
import json
from pathlib import Path

logger = LogManager().get_logger(__name__)

class BaseExporter(ABC):
    """Базовый класс для экспортеров"""
    
    def __init__(self, config: Dict[str, Any], db_manager: EnhancedDatabaseManager, output_dir: str, logger: Optional[logging.Logger] = None):
        """
        Инициализация экспортера
        
        Args:
            config: Конфигурация экспортера
            db_manager: Менеджер базы данных
            output_dir: Директория для сохранения файлов
            logger: Экземпляр логгера
        """
        self.config = config
        self.db_manager = db_manager
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or LogManager().get_logger(__name__)
        self._lock = asyncio.Lock()
        
        # Убедимся, что output_dir существует
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir, exist_ok=True)
                self.logger.info(f"Output directory {self.output_dir} created.")
        except Exception as e:
            self.logger.error(f"Error creating output directory {self.output_dir}: {e}", exc_info=True)
            # В зависимости от критичности, можно либо пробросить исключение, либо продолжить работу
        
    async def export(self, srid: str) -> Dict[str, Any]:
        """
        Экспорт системы координат
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Dict[str, Any]: Информация о созданном файле (путь, имя и т.д.)
            
        Raises:
            ExportError: При ошибке экспорта
        """
        try:
            # Получаем данные системы координат
            cs_data = await self._get_coordinate_system(srid)
            
            if cs_data is None:
                self.logger.error(f"Не удалось получить данные для SRID {srid}. Экспорт прерван.")
                raise ExportError(f"Не удалось получить данные для SRID {srid}.")
            
            # Валидируем данные
            self._validate_data(cs_data)
            
            # Выполняем экспорт
            result = await self._export_impl(cs_data)
                
            return result
            
        except ValidationError as e:
            self.logger.error(f"Ошибка валидации данных: {e}")
            raise ExportError(f"Ошибка валидации данных: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта: {e}")
            raise ExportError(f"Ошибка экспорта: {str(e)}")
            
    async def _get_coordinate_system(self, srid: str) -> Optional[Dict[str, Any]]:
        """
        Получение данных о системе координат из базы данных.
        Использует 'custom_geom' для SRID >= 100000 и 'spatial_ref_sys' для остальных.
        """
        if not self.db_manager:
            self.logger.error("Database manager is not initialized.")
            return None

        # Всегда запрашиваем данные из spatial_ref_sys для экспорта PRJ
        query = "SELECT auth_name, srtext, srid, proj4text FROM spatial_ref_sys WHERE srid = $1"
        
        try:
            srid_int = int(srid)
            self.logger.debug(f"Executing query for SRID {srid}: {query}")
            results = await self.db_manager.fetch(query, srid_int)
            
            if results:
                result_data = dict(results[0])
                self.logger.debug(f"Data found for SRID {srid} in spatial_ref_sys: {result_data}")
                # Проверка на наличие srtext, т.к. он критичен для PRJ
                if not result_data.get('srtext'):
                    self.logger.warning(f"No srtext found for SRID {srid} in spatial_ref_sys. PRJ export might fail or be incomplete.")
                # proj4text может отсутствовать, это нормально, но логируем если его нет
                if not result_data.get('proj4text'):
                    self.logger.debug(f"No proj4text found for SRID {srid} in spatial_ref_sys.")
                return result_data
            else:
                self.logger.warning(f"No data found for SRID {srid} in spatial_ref_sys table.")
                # Попытка найти в custom_geom, если это UTM зона, чтобы получить имя (хотя для PRJ это не нужно)
                # Но для консистентности с тем, что видит юзер, можно попробовать достать имя
                # Это не должно влиять на экспорт, так как srtext берется из spatial_ref_sys
                if 32601 <= srid_int <= 32660 or 32701 <= srid_int <= 32760: # Стандартные UTM зоны
                     query_custom_name = "SELECT name FROM custom_geom WHERE srid = $1"
                     custom_results = await self.db_manager.fetch(query_custom_name, srid_int)
                     if custom_results and custom_results[0].get('name'):
                         self.logger.debug(f"Found name '{custom_results[0]['name']}' in custom_geom for UTM SRID {srid_int}")
                         # Возвращаем пустой словарь, чтобы экспортер понял, что srtext нет, но не было ошибки запроса к spatial_ref_sys
                         # Или можно вернуть {'srid': srid_int, 'auth_name': custom_results[0]['name'], 'srtext': None, 'proj4text': None }
                         # Это позволит корректно формировать имя файла для UTM, даже если srtext нет.
                         # Однако, PRJ экспортеры должны будут обработать None srtext
                         return {'srid': srid_int, 'auth_name': custom_results[0]['name'], 'srtext': None, 'proj4text': None}
                return None
        except ValueError:
            self.logger.error(f"Invalid SRID format: {srid}. SRID must be an integer.")
            return None
        except Exception as e:
            self.logger.error(f"Error getting coordinate system data for SRID {srid}: {e}", exc_info=True)
            return None
            
    def _validate_data(self, data: Dict[str, Any]) -> None:
        """
        Валидация данных системы координат
        
        Args:
            data: Данные для валидации
            
        Raises:
            ValidationError: При ошибке валидации
        """
        if data is None:
            raise ValidationError("Данные для валидации не могут быть None.")

        # Убираем валидацию конфигурации - config это BotConfig, а не dict
        required_fields: List[str] = []  # Базовая валидация без конфигурации
        max_text_length: int = 4096  # Стандартное ограничение
        
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
    async def _export_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Реализация экспорта в конкретном формате
        
        Args:
            data: Данные системы координат
            
        Returns:
            Dict[str, Any]: Информация о созданном файле (путь, имя и т.д.)
        """
        start_time = time.monotonic()
        try:
            # Логика экспорта специфичная для формата
            # ...
            # Предположим, что дочерний класс возвращает путь к файлу или сообщение об ошибке
            # Этот метод должен быть реализован в дочерних классах, здесь его вызов некорректен
            # result_message = await self._export_impl(data) # Удаляем рекурсивный вызов
            
            # if self.metrics: # Убираем, т.к. record_operation теперь синхронный
            # await self.metrics.record_operation("export_time", start_time) 
            
            # self.logger.info(f"Export successful for data: {data}. Result: {result_message}") # Логирование должно быть в конкретной реализации
            # return result_message # Возврат результата должен быть в конкретной реализации
            raise NotImplementedError("Метод _export_impl должен быть реализован в дочернем классе")

        except ExportError as e:
            self.logger.error(f"ExportError in export method for data {data}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in export method for data {data}: {e}", exc_info=True)
            raise ExportError(f"Непредвиденная ошибка экспорта: {str(e)}") from e

    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных
        
        Args:
            data: Данные для валидации
            
        Returns:
            bool: True если данные валидны
        """
        # start_time = self.metrics.start_operation('validate_data') # Убираем, т.к. start_operation не существует
        try:
            # Базовая валидация
            if not isinstance(data, dict):
                # await self.metrics.record_error('validate_data', 'Data must be a dictionary') # Убираем
                return False
                
            if not data:
                # await self.metrics.record_error('validate_data', 'Data cannot be empty') # Убираем
                return False
                
            # await self.metrics.record_operation('validate_data', start_time) # Убираем
            return True
            
        except Exception as e:
            # await self.metrics.record_error('validate_data', str(e)) # Убираем
            logger.error(f"Ошибка валидации данных: {e}")
            return False
            
    async def prepare_output_dir(self) -> None:
        """Подготовка директории для экспорта"""
        # start_time = self.metrics.start_operation('prepare_output_dir') # Убираем
        try:
            async with self._lock:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                # await self.metrics.record_operation('prepare_output_dir', start_time) # Убираем
                
        except Exception as e:
            # await self.metrics.record_error('prepare_output_dir', str(e)) # Убираем
            logger.error(f"Ошибка подготовки директории: {e}")
            raise ExportError(f"Ошибка подготовки директории: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики экспортера"""
        return {
            'output_dir': str(self.output_dir),
            # 'metrics': self.metrics.get_stats() # Убираем, т.к. get_stats не существует / некорректно
        } 

    def _get_default_filename(self, srid: str, extension: str, prefix: str = "") -> str:
        """Формирует имя файла по умолчанию."""
        return f"{prefix}{srid}.{extension}" 