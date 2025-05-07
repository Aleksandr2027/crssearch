"""
Экспортер для формата Civil3D
"""

from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET
from datetime import datetime
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.errors import ValidationError, XMLProcessingError
from .base import BaseExporter

class Civil3DExporter(BaseExporter):
    """Экспортер для формата Civil3D"""
    
    def __init__(self, config: Dict[str, Any], db_manager: Optional[DatabaseManager] = None, logger: Optional[Any] = None):
        """
        Инициализация экспортера Civil3D
        
        Args:
            config: Конфигурация экспортера
            db_manager: Опциональный менеджер базы данных
            logger: Опциональный логгер для тестов
        """
        super().__init__(config, db_manager=db_manager, logger=logger)
        self.metrics = MetricsManager()
        
    def supports_srid(self, srid: int) -> bool:
        """
        Проверка поддержки SRID
        
        Args:
            srid: SRID для проверки
            
        Returns:
            True если SRID поддерживается, False в противном случае
        """
        # Поддерживаем UTM зоны
        if 32601 <= srid <= 32660:
            return True
            
        # Проверяем пользовательские СК
        return self._is_custom_crs(srid)
        
    def _is_custom_crs(self, srid: int) -> bool:
        """
        Проверка является ли СК пользовательской
        
        Args:
            srid: SRID для проверки
            
        Returns:
            True если СК пользовательская, False в противном случае
        """
        try:
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM custom_geom WHERE srid = %s",
                    (srid,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            self.logger.error(f"Ошибка проверки SRID {srid}: {e}")
            return False
            
    def _get_crs_data(self, srid: int) -> Dict[str, Any]:
        """
        Получение данных о системе координат
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Словарь с данными о системе координат
        """
        try:
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute("""
                    SELECT s.srid, s.auth_name, s.auth_srid, s.srtext, s.proj4text,
                           c.info, c.p as reliability, c.deg, c.name
                    FROM spatial_ref_sys s
                    LEFT JOIN custom_geom c ON s.srid = c.srid
                    WHERE s.srid = %s
                """, (srid,))
                
                row = cursor.fetchone()
                if not row:
                    raise ValidationError(f"SRID {srid} не найден")
                    
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
            self.logger.error(f"Ошибка получения данных для SRID {srid}: {e}")
            raise
            
    def _generate_xml(self, crs_data: Dict[str, Any]) -> str:
        """
        Генерация XML для системы координат
        
        Args:
            crs_data: Данные о системе координат
            
        Returns:
            XML в виде строки
            
        Raises:
            XMLProcessingError: При ошибке формирования XML
        """
        try:
            # Проверяем обязательные поля
            required_fields = ['srid', 'srtext', 'proj4text']
            for field in required_fields:
                if field not in crs_data:
                    raise XMLProcessingError(f"Отсутствуют обязательные поля: {field}")
                    
            # Создаем корневой элемент
            root = ET.Element('CoordinateSystem')
            root.set('xmlns', 'http://www.osgeo.org/mapguide/coordinatesystem')
            
            # Добавляем метаданные
            metadata = ET.SubElement(root, 'Metadata')
            
            srid = ET.SubElement(metadata, 'SRID')
            srid.text = str(crs_data['srid'])
            
            auth_name = ET.SubElement(metadata, 'AuthorityName')
            auth_name.text = crs_data.get('auth_name', 'CUSTOM')
            
            auth_srid = ET.SubElement(metadata, 'AuthoritySRID')
            auth_srid.text = str(crs_data.get('auth_srid', crs_data['srid']))
            
            # Добавляем определение СК
            definition = ET.SubElement(root, 'Definition')
            definition.text = crs_data['srtext']
            
            # Добавляем proj4
            proj4 = ET.SubElement(root, 'Proj4')
            proj4.text = crs_data['proj4text']
            
            # Добавляем дополнительную информацию
            if crs_data.get('info'):
                info = ET.SubElement(root, 'Info')
                info.text = crs_data['info']
                
            # Добавляем дату генерации
            generation_date = ET.SubElement(root, 'GenerationDate')
            generation_date.text = datetime.now().isoformat()
            
            # Преобразуем в строку
            return ET.tostring(root, encoding='unicode', method='xml')
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации XML: {e}")
            raise XMLProcessingError(f"Ошибка генерации XML: {str(e)}")
            
    async def export(self, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Экспорт системы координат в формат Civil3D
        
        Args:
            srid: SRID системы координат
            params: Дополнительные параметры экспорта
            
        Returns:
            XML в виде строки
            
        Raises:
            ValidationError: Если SRID не поддерживается
            XMLProcessingError: При ошибке формирования XML
        """
        try:
            # Проверяем поддержку SRID
            if not self.supports_srid(srid):
                self.metrics.increment('civil3d_export_validation_errors')
                raise ValidationError(f"SRID {srid} не поддерживается")
                
            # Получаем данные о системе координат
            crs_data = self._get_crs_data(srid)
            
            # Генерируем XML
            xml_str = self._generate_xml(crs_data)
            
            # Обновляем метрики
            self.metrics.increment('civil3d_export_success')
            
            return xml_str
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Ошибка экспорта SRID {srid}: {e}")
            self.metrics.increment('civil3d_export_errors')
            raise XMLProcessingError(f"Ошибка экспорта: {str(e)}")
            
    def export_sync_impl(self, srid: int) -> str:
        """
        Синхронная реализация экспорта системы координат
        
        Args:
            srid: SRID системы координат
            
        Returns:
            XML в виде строки
            
        Raises:
            ValidationError: Если SRID не поддерживается
            XMLProcessingError: При ошибке формирования XML
        """
        try:
            # Проверяем поддержку SRID
            if not self.supports_srid(srid):
                self.metrics.increment('civil3d_export_validation_errors')
                raise ValidationError(f"SRID {srid} не поддерживается")
                
            # Получаем данные о системе координат
            crs_data = self._get_crs_data(srid)
            
            # Генерируем XML
            xml_str = self._generate_xml(crs_data)
            
            # Обновляем метрики
            self.metrics.increment('civil3d_export_success')
            
            return xml_str
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Ошибка экспорта SRID {srid}: {e}")
            self.metrics.increment('civil3d_export_errors')
            raise XMLProcessingError(f"Ошибка экспорта: {str(e)}")
