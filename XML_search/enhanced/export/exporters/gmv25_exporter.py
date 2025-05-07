"""
Экспортер в формат GMv25 (демонстрационная версия)
"""

from typing import Dict, Any
from .base_exporter import BaseExporter
from ..exceptions import ExportError
import json
from datetime import datetime

class GMv25Exporter(BaseExporter):
    """Демонстрационный экспортер в формат GMv25"""
    
    async def _export_impl(self, data: Dict[str, Any]) -> str:
        """
        Упрощенная реализация экспорта в формат GMv25
        
        Args:
            data: Данные системы координат
            
        Returns:
            str: Демонстрационное представление экспорта
        """
        try:
            # Загружаем тестовый шаблон
            template = json.loads(self._load_template("test_export.json"))
            
            # Заполняем метаданные
            template['metadata']['timestamp'] = datetime.now().isoformat()
            template['metadata']['format'] = 'GMv25'
            
            # Заполняем данные
            template['data']['srid'] = data['srid']
            template['data']['description'] = f"GMv25 coordinate system export for SRID: {data['srid']}"
            template['data']['parameters'] = {
                'auth_name': data.get('auth_name', ''),
                'auth_srid': data.get('auth_srid', ''),
                'wkt': data.get('srtext', '')[:100] + '...' if data.get('srtext') else '',  # Сокращаем для демонстрации
                'proj4': data.get('proj4text', '')[:100] + '...' if data.get('proj4text') else ''  # Сокращаем для демонстрации
            }
            
            # Возвращаем результат
            return json.dumps(template, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"Ошибка демонстрационного экспорта GMv25: {e}")
            self.metrics.increment('gmv25_export_errors')
            raise ExportError(f"Ошибка демонстрационного экспорта GMv25: {str(e)}")
            
    def _validate_data(self, data: Dict[str, Any]) -> None:
        """
        Упрощенная валидация для демонстрации
        
        Args:
            data: Данные для валидации
        """
        # Вызываем базовую валидацию
        super()._validate_data(data)
        
        # Минимальная проверка для демонстрации
        if not data.get('srtext') or not data.get('proj4text'):
            raise ValidationError("Отсутствует WKT или Proj4 определение") 