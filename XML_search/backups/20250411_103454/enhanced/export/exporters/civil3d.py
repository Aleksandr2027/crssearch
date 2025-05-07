from typing import Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
from .base import BaseExporter
from XML_search.errors import ValidationError, XMLProcessingError
from XML_search.enhanced.db_manager import DatabaseManager

class Civil3DExporter(BaseExporter):
    """Экспортер координатных систем в формат XML для Civil3D"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_manager = DatabaseManager()
        self.xml_namespace = "http://www.osgeo.org/mapguide/coordinatesystem"
        
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
        Экспорт системы координат в формат XML для Civil3D
        
        Args:
            srid: SRID системы координат
            params: Дополнительные параметры экспорта
            
        Returns:
            XML строка с описанием системы координат
            
        Raises:
            ValidationError: Если параметры экспорта невалидны
            XMLProcessingError: При ошибке формирования XML
        """
        try:
            # Валидация
            self._validate_srid(srid)
            self.validate_params(params)
            
            # Получение данных о системе координат
            crs_data = self._get_crs_data(srid)
            
            # Формирование XML
            with self._track_export_timing('civil3d'):
                xml_str = self._generate_xml(crs_data)
                
            # Логирование успеха
            self._log_export_attempt(srid, True)
            
            return xml_str
            
        except Exception as e:
            # Логирование ошибки
            self._log_export_attempt(srid, False)
            if isinstance(e, (ValidationError, XMLProcessingError)):
                raise
            raise XMLProcessingError(f"Ошибка экспорта в XML Civil3D: {str(e)}")
            
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
                           c.deg, c.name
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
                    'deg': row[7],
                    'name': row[8]
                }
                
        except Exception as e:
            raise XMLProcessingError(f"Ошибка получения данных о СК: {str(e)}")
            
    def _generate_xml(self, crs_data: Dict[str, Any]) -> str:
        """Генерация XML для Civil3D"""
        try:
            # Создаем корневой элемент
            root = ET.Element("CoordinateSystem", xmlns=self.xml_namespace)
            
            # Добавляем метаданные
            metadata = ET.SubElement(root, "Metadata")
            ET.SubElement(metadata, "SRID").text = str(crs_data['srid'])
            ET.SubElement(metadata, "Authority").text = crs_data['auth_name']
            ET.SubElement(metadata, "AuthoritySRID").text = str(crs_data['auth_srid'])
            ET.SubElement(metadata, "Description").text = crs_data['info'] or "Not available"
            ET.SubElement(metadata, "Reliability").text = str(crs_data['reliability'] or "Unknown")
            ET.SubElement(metadata, "ExportDate").text = datetime.now().isoformat()
            ET.SubElement(metadata, "Format").text = "Civil3D XML"
            
            # Добавляем определение системы координат
            definition = ET.SubElement(root, "Definition")
            ET.SubElement(definition, "WKT").text = crs_data['srtext']
            ET.SubElement(definition, "PROJ4").text = crs_data['proj4text']
            
            if crs_data['deg'] is not None:
                ET.SubElement(definition, "Precision").text = str(crs_data['deg'])
            
            if crs_data['name']:
                ET.SubElement(definition, "Name").text = crs_data['name']
            
            # Преобразуем в строку с отступами
            return ET.tostring(root, encoding='unicode', method='xml')
            
        except Exception as e:
            raise XMLProcessingError(f"Ошибка формирования XML: {str(e)}")
