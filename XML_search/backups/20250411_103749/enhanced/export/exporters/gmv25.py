from typing import Dict, Any, Optional
import re
from datetime import datetime
from .base import BaseExporter
from XML_search.errors import ValidationError, XMLProcessingError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.cache_manager import CacheManager

class GMv25Exporter(BaseExporter):
    """Экспортер координатных систем в формат PRJ для GlobalMapper v25"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        
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
        Экспорт системы координат в формат PRJ для GlobalMapper v25
        
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
            # Проверяем кэш
            cache_key = f"gmv25_export_{srid}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                self._log_export_attempt(srid, True)
                return cached_result
            
            # Валидация
            self._validate_srid(srid)
            self.validate_params(params)
            
            # Получение данных о системе координат
            crs_data = self._get_crs_data(srid)
            
            # Формирование PRJ
            with self._track_export_timing('gmv25'):
                prj_str = self._generate_prj(crs_data)
                
            # Сохраняем в кэш
            self.cache_manager.set(cache_key, prj_str)
            
            # Логирование успеха
            self._log_export_attempt(srid, True)
            
            return prj_str
            
        except Exception as e:
            # Логирование ошибки
            self._log_export_attempt(srid, False)
            if isinstance(e, (ValidationError, XMLProcessingError)):
                raise
            raise XMLProcessingError(f"Ошибка экспорта в PRJ GMv25: {str(e)}")
            
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
                           c.info, c.p as reliability,
                           c.bbox_min_lat, c.bbox_max_lat,
                           c.bbox_min_lon, c.bbox_max_lon
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
                    'reliability': row[6],
                    'bbox': {
                        'min_lat': row[7],
                        'max_lat': row[8],
                        'min_lon': row[9],
                        'max_lon': row[10]
                    }
                }
                
        except Exception as e:
            raise XMLProcessingError(f"Ошибка получения данных о СК: {str(e)}")
            
    def _generate_prj(self, crs_data: Dict[str, Any]) -> str:
        """
        Генерация PRJ для GlobalMapper v25
        
        В отличие от v20, версия 25 поддерживает:
        - Расширенные метаданные
        - Информацию о границах применимости (bbox)
        - Дополнительные параметры проекции
        """
        try:
            # Получаем и очищаем WKT определение
            wkt = self._clean_wkt(crs_data['srtext'])
            
            # Добавляем метаданные в комментарии
            metadata = [
                f"SRID: {crs_data['srid']}",
                f"Authority: {crs_data['auth_name']}",
                f"Authority SRID: {crs_data['auth_srid']}",
                f"Description: {crs_data['info'] or 'Not provided'}",
                f"Reliability: {crs_data['reliability'] or 'Unknown'}",
                f"Export Date: {datetime.now().isoformat()}",
                f"Format: GlobalMapper v25 PRJ"
            ]
            
            # Добавляем информацию о границах применимости
            if all(v is not None for v in crs_data['bbox'].values()):
                bbox = crs_data['bbox']
                metadata.extend([
                    "Bounds of applicability:",
                    f"  Min Latitude: {bbox['min_lat']}",
                    f"  Max Latitude: {bbox['max_lat']}",
                    f"  Min Longitude: {bbox['min_lon']}",
                    f"  Max Longitude: {bbox['max_lon']}"
                ])
            
            # Формируем PRJ файл
            prj_content = []
            
            # Добавляем метаданные как комментарии
            for meta in metadata:
                prj_content.append(f"# {meta}")
            
            # Добавляем WKT определение
            prj_content.append(wkt)
            
            # Добавляем PROJ4 определение как комментарий
            if crs_data['proj4text']:
                prj_content.extend([
                    "# PROJ4 Definition:",
                    f"# {crs_data['proj4text']}"
                ])
            
            # Объединяем все строки
            return '\n'.join(prj_content)
            
        except Exception as e:
            raise XMLProcessingError(f"Ошибка формирования PRJ: {str(e)}")
            
    def _clean_wkt(self, wkt: str) -> str:
        """
        Очистка WKT определения для формата GMv25
        
        Args:
            wkt: Исходное WKT определение
            
        Returns:
            Очищенное WKT определение
        """
        try:
            # Удаляем лишние пробелы и переносы строк
            wkt = re.sub(r'\s+', ' ', wkt).strip()
            
            # Удаляем лишние пробелы вокруг скобок и запятых
            wkt = re.sub(r'\s*([,\[\]])\s*', r'\1', wkt)
            
            # Добавляем пробелы после запятых для читаемости
            wkt = re.sub(r',', ', ', wkt)
            
            # Форматируем вложенные структуры для лучшей читаемости
            wkt = re.sub(r'\[', '[\n  ', wkt)
            wkt = re.sub(r'\]', '\n]', wkt)
            
            return wkt
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки WKT: {e}")
            return wkt  # Возвращаем исходный WKT в случае ошибки
