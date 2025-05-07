from typing import Dict, Any, Optional
import re
from datetime import datetime
from .base import BaseExporter
from XML_search.errors import ValidationError, XMLProcessingError
from XML_search.enhanced.db_manager import DatabaseManager

class GMv20Exporter(BaseExporter):
    """Экспортер координатных систем в формат PRJ для GlobalMapper v20"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_manager = DatabaseManager()
        
    def supports_srid(self, srid: int) -> bool:
        """
        Проверка поддержки SRID
        
        Args:
            srid: SRID для проверки
            
        Returns:
            True если SRID поддерживается
        """
        # Поддерживаем пользовательские СК и UTM зоны
        return (
            str(srid).startswith('326') or  # UTM зоны
            self._is_custom_crs(srid)       # Пользовательские СК
        )
        
    def export(self, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Экспорт системы координат в формат PRJ для GlobalMapper v20
        
        Args:
            srid: SRID системы координат
            params: Дополнительные параметры экспорта
            
        Returns:
            PRJ строка с описанием системы координат
            
        Raises:
            ValidationError: Если параметры экспорта невалидны
            XMLProcessingError: При ошибке формирования PRJ
        """
        try:
            # Валидация
            self._validate_srid(srid)
            self.validate_params(params)
            
            # Получение данных о системе координат
            crs_data = self._get_crs_data(srid)
            
            # Формирование PRJ
            with self._track_export_timing('gmv20'):
                prj_str = self._generate_prj(crs_data)
                
            # Логирование успеха
            self._log_export_attempt(srid, True)
            
            return prj_str
            
        except Exception as e:
            # Логирование ошибки
            self._log_export_attempt(srid, False)
            if isinstance(e, (ValidationError, XMLProcessingError)):
                raise
            raise XMLProcessingError(f"Ошибка экспорта в PRJ GMv20: {str(e)}")
            
    def _is_custom_crs(self, srid: int) -> bool:
        """Проверка является ли система координат пользовательской"""
        try:
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM spatial_ref_sys 
                    WHERE srid = %s AND auth_name = 'custom'
                """, (srid,))
                return bool(cursor.fetchone())
        except Exception as e:
            self.logger.error(f"Ошибка проверки SRID {srid}: {e}")
            return False
            
    def _get_crs_data(self, srid: int) -> Dict[str, Any]:
        """Получение данных о системе координат из БД"""
        try:
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute("""
                    SELECT s.srid, s.auth_name, s.auth_srid, s.srtext, s.proj4text,
                           c.info, c.p as reliability
                    FROM spatial_ref_sys s
                    LEFT JOIN custom_geom c ON s.srid = c.srid
                    WHERE s.srid = %s
                """, (srid,))
                row = cursor.fetchone()
                
                if not row:
                    raise ValidationError(f"SRID {srid} не найден в базе данных")
                    
                return {
                    'srid': row[0],
                    'auth_name': row[1],
                    'auth_srid': row[2],
                    'srtext': row[3],
                    'proj4text': row[4],
                    'info': row[5],
                    'reliability': row[6]
                }
                
        except Exception as e:
            raise XMLProcessingError(f"Ошибка получения данных о СК: {str(e)}")
            
    def _generate_prj(self, crs_data: Dict[str, Any]) -> str:
        """Генерация PRJ для GlobalMapper v20"""
        try:
            # Очищаем WKT от лишних пробелов и переносов строк
            wkt = self._clean_wkt(crs_data['srtext'])
            
            # Формируем комментарии с метаданными
            metadata = [
                f"# SRID: {crs_data['srid']}",
                f"# Authority: {crs_data['auth_name']}",
                f"# Authority SRID: {crs_data['auth_srid']}",
                f"# Description: {crs_data['info'] or 'Not available'}",
                f"# Reliability: {crs_data['reliability'] or 'Unknown'}",
                f"# Export Date: {datetime.now().isoformat()}",
                f"# Format: GlobalMapper v20 PRJ",
                ""  # Пустая строка для разделения метаданных и WKT
            ]
            
            # Объединяем метаданные и WKT
            return "\n".join(metadata + [wkt])
            
        except Exception as e:
            raise XMLProcessingError(f"Ошибка формирования PRJ: {str(e)}")
            
    def _clean_wkt(self, wkt: str) -> str:
        """Очистка WKT от лишних пробелов и переносов строк"""
        if not wkt:
            return ""
            
        # Удаляем лишние пробелы и переносы строк
        wkt = re.sub(r'\s+', ' ', wkt.strip())
        
        # Добавляем пробелы после запятых для читаемости
        wkt = re.sub(r',(\S)', r', \1', wkt)
        
        return wkt
