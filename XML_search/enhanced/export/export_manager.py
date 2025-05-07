"""
Менеджер экспорта
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Type, List
from pathlib import Path
from .exporters.base_exporter import BaseExporter
from .exporters.civil3d_exporter import Civil3DExporter
from .exporters.gmv20_exporter import GMv20Exporter
from .exporters.gmv25_exporter import GMv25Exporter
from ..exceptions import ExportError
from ..log_manager import LogManager
from ..metrics_manager import MetricsManager

logger = LogManager().get_logger(__name__)

class ExportManager:
    """Менеджер экспорта"""
    
    def __init__(self, output_dir: str):
        """
        Инициализация менеджера экспорта
        
        Args:
            output_dir: Директория для сохранения файлов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = MetricsManager()
        self._lock = asyncio.Lock()
        self._exporters: Dict[str, Type[BaseExporter]] = {
            'civil3d': Civil3DExporter,
            'gmv20': GMv20Exporter,
            'gmv25': GMv25Exporter
        }
        
    async def export(self, format: str, data: Dict[str, Any], filename: str) -> str:
        """
        Экспорт данных
        
        Args:
            format: Формат экспорта
            data: Данные для экспорта
            filename: Имя файла
            
        Returns:
            str: Путь к экспортированному файлу
        """
        start_time = self.metrics.start_operation('export')
        try:
            if format not in self._exporters:
                await self.metrics.record_error('export', f'Unsupported format: {format}')
                raise ExportError(f'Неподдерживаемый формат: {format}')
                
            exporter_class = self._exporters[format]
            exporter = exporter_class(str(self.output_dir))
            
            if not await exporter.validate_data(data):
                await self.metrics.record_error('export', 'Invalid data')
                raise ExportError('Некорректные данные')
                
            await exporter.prepare_output_dir()
            result = await exporter.export(data, filename)
            
            await self.metrics.record_operation('export', start_time)
            return result
            
        except Exception as e:
            await self.metrics.record_error('export', str(e))
            logger.error(f"Ошибка экспорта: {e}")
            raise ExportError(f"Ошибка экспорта: {e}")
            
    def get_supported_formats(self) -> List[str]:
        """
        Получение списка поддерживаемых форматов
        
        Returns:
            List[str]: Список поддерживаемых форматов экспорта
        """
        return list(self._exporters.keys())
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики менеджера экспорта
        
        Returns:
            Dict[str, Any]: Статистика работы менеджера экспорта
        """
        return {
            'output_dir': str(self.output_dir),
            'supported_formats': self.get_supported_formats(),
            'metrics': self.metrics.get_stats()
        }
