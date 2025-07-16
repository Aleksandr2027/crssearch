"""
Экспортер для формата Civil3D XML
"""

import xml.etree.ElementTree as ET
import xml.dom.minidom
import re
import logging
import pyproj
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import unidecode
import json
import os

from .base_exporter import BaseExporter
from ..exceptions import ExportError
from XML_search.enhanced.log_manager import LogManager

logger = LogManager().get_logger(__name__)

class Civil3DExporter(BaseExporter):
    """Экспортер для формата Civil3D XML"""
    
    def __init__(self, config: Dict[str, Any], db_manager = None, output_dir: str = "output", logger_instance = None):
        """
        Инициализация экспортера Civil3D
        
        Args:
            config: Конфигурация экспортера
            db_manager: Опциональный менеджер базы данных
            output_dir: Директория для сохранения файлов
            logger_instance: Опциональный логгер
        """
        self.logger = logger_instance or LogManager().get_logger(__name__)
        try:
            super().__init__(config, db_manager=db_manager, output_dir=output_dir, logger=self.logger)
            self.format_name = "xml_Civil3D"
            self.logger.info("Инициализирован полнофункциональный экспортер xml_Civil3D")
            self.template_path = self._get_template_path()
            self.encoding = 'utf-8'
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Civil3DExporter: {e}", exc_info=True)
            raise
            
    def _get_template_path(self) -> str:
        """Возвращает путь к шаблону"""
        current_dir = Path(__file__).parent
        template_path = current_dir / "templates" / "civil3d" / "base.xml"
        return str(template_path)

    async def _export_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Полнофункциональная реализация экспорта в формате Civil3D XML
        
        Args:
            data: Данные системы координат
            
        Returns:
            Dict[str, Any]: Информация о созданном файле или заглушке при ошибке
        """
        try:
            srid = int(data['srid'])
            self.logger.info(f"Начинаем экспорт Civil3D для SRID: {srid}")
            
            # Проверяем, является ли SRID EPSG системой северного полушария (32601-32660)
            if 32601 <= srid <= 32660:
                self.logger.info(f"SRID {srid} является EPSG UTM системой северного полушария - возвращаем заглушку")
                return {
                    'file_path': "Функционал в разработке",
                    'format': 'civil3d_xml',
                    'srid': srid,
                    'success': False,
                    'is_development_stub': True
                }
            
            # Получаем дополнительные данные из БД
            extended_data = await self._fetch_extended_data(data['srid'])
            if not extended_data:
                self.logger.warning(f"Не удалось получить расширенные данные для SRID {data['srid']}, используем fallback")
                return self._fallback_response(data['srid'])
            
            # Объединяем данные
            full_data = {**data, **extended_data}
            
            # Парсим proj4text для получения параметров
            proj_params = self._parse_proj4_text(full_data.get('proj4text', ''))
            
            # Создаем XML структуру
            xml_content = await self._create_civil3d_xml(full_data, proj_params)
            
            # Очищаем недопустимые символы
            xml_content = self._clean_xml_content(xml_content)
            
            # Генерируем имя файла на основе поля name из custom_geom
            name = full_data.get('name', f"SRID_{data['srid']}")  # fallback если name отсутствует
            filename = f"{name}_civil3d.xml"
            file_path = self.output_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            self.logger.info(f"Civil3D XML файл успешно создан: {file_path}")
            return {
                'file_path': str(file_path),
                'format': 'civil3d_xml',
                'srid': data['srid'],
                'success': True,
                'size': len(xml_content)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании Civil3D XML для SRID {data['srid']}: {e}", exc_info=True)
            # Возвращаем fallback при любой ошибке
            return self._fallback_response(data['srid'])
    
    def _fallback_response(self, srid: str) -> Dict[str, Any]:
        """Возвращает информацию о заглушке при ошибках"""
        return {
            'message': "Функционал в разработке",
            'format': 'civil3d_xml',
            'srid': srid,
            'success': False,
            'fallback': True
        }
    
    async def _fetch_extended_data(self, srid: str) -> Optional[Dict[str, Any]]:
        """
        Получает расширенные данные из БД
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Dict с расширенными данными или None при ошибке
        """
        try:
            if not self.db_manager:
                self.logger.error("Менеджер БД недоступен")
                return None
                
            async with self.db_manager.connection() as conn:
                # Получаем данные из custom_geom если доступно
                custom_query = "SELECT info, ST_AsText(geom) as geom_text, name FROM custom_geom WHERE srid = $1"
                custom_result = await conn.fetchrow(custom_query, int(srid))
                
                result = {}
                if custom_result:
                    result['info'] = custom_result['info']
                    result['geom_text'] = custom_result['geom_text']
                    result['name'] = custom_result['name']
                    self.logger.debug(f"Получены данные custom_geom для SRID {srid}: name={custom_result['name']}")
                
                return result
                
        except Exception as e:
            self.logger.error(f"Ошибка получения расширенных данных для SRID {srid}: {e}", exc_info=True)
            return None
    
    def _parse_proj4_text(self, proj4text: str) -> Dict[str, str]:
        """
        Парсит proj4text для извлечения параметров
        
        Args:
            proj4text: Строка proj4
            
        Returns:
            Словарь параметров proj4
        """
        params: Dict[str, str] = {}
        if not proj4text:
            return params
            
        try:
            # Разбираем строку proj4 на параметры
            parts = proj4text.split()
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    params[key.lstrip('+')] = value
                else:
                    params[part.lstrip('+')] = "True"  # Сохраняем как строку
                    
            self.logger.debug(f"Извлечены proj4 параметры: {params}")
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга proj4text '{proj4text}': {e}")
            
        return params
    
    async def _create_civil3d_xml(self, data: Dict[str, Any], proj_params: Dict[str, str]) -> str:
        """
        Создает детализированный XML контент для Civil3D в соответствии с форматом custom_acad.py
        
        Args:
            data: Данные системы координат
            proj_params: Параметры proj4
            
        Returns:
            XML контент как строка
        """
        try:
            srid = data['srid']
            auth_name = data.get('auth_name', 'custom')
            srtext = data.get('srtext', '')
            proj4text = data.get('proj4text', '')
            geom_wkt = data.get('geom_text', '')
            
            # Получаем и обрабатываем поле info из custom_geom
            info = data.get('info', '')
            cleaned_description = self._clean_and_convert_info(info) if info else "No Description"
            
            # Извлечение ключевых параметров из proj4
            lat_0 = float(proj_params.get("lat_0", "0"))
            lon_0 = float(proj_params.get("lon_0", "0"))
            k = float(proj_params.get("k", "1.0"))
            x_0 = float(proj_params.get("x_0", "0"))
            y_0 = float(proj_params.get("y_0", "0"))
            ellps = proj_params.get("ellps", "wgs84")
            
            # Обработка towgs84 параметров
            towgs84_raw = proj_params.get("towgs84", "0,0,0,0,0,0,0")
            towgs84_values = [float(x) for x in towgs84_raw.split(',')]
            if len(towgs84_values) < 7:
                towgs84_values.extend([0] * (7 - len(towgs84_values)))
            
            # Конвертация параметров трансформации (как в custom_acad.py)
            towgs84_converted = [
                towgs84_values[0],  # X translation
                towgs84_values[1],  # Y translation  
                towgs84_values[2],  # Z translation
                towgs84_values[3] / 3600 if towgs84_values[3] != 0 else 0,  # X rotation (арксекунды -> градусы)
                towgs84_values[4] / 3600 if towgs84_values[4] != 0 else 0,  # Y rotation
                towgs84_values[5] / 3600 if towgs84_values[5] != 0 else 0,  # Z rotation
                towgs84_values[6] / 1e6  # Scale (ppm -> unity)
            ]
            
            # Получение данных эллипсоида
            ellipsoid_data = await self._fetch_ellipsoid_data(ellps)
            
            # Вычисление границ из геометрии
            bounds = self._parse_bounds_from_geom(geom_wkt)
            
            # Получение правильного DatumId из таблицы datum_all
            towgs84_str = f"+towgs84={towgs84_raw}"
            datum_data = await self._fetch_datum_data(towgs84_str)
            
            if datum_data:
                self.logger.info(f"Найден датум в базе данных для SRID {srid}: {datum_data['name_d']}")
                datum_id = datum_data['name_d']
                transformation_id = datum_data['name_d']
            else:
                self.logger.info(f"Датум не найден в базе данных для SRID {srid}, используем fallback")
                datum_id = f"Transformation-{srid}"
                transformation_id = datum_id
            
            # Формирование имен и идентификаторов
            name = srtext.replace('_', '-') if srtext else f"CRS-{srid}"
            authority = "Not Official" if auth_name == 'custom' else auth_name
            
            # Идентификаторы для различных элементов
            pcs_id = f"{name}-{srid}"
            
            # Создание корневого элемента
            root = ET.Element("Dictionary")
            root.set("xmlns", "http://www.osgeo.org/mapguide/coordinatesystem")
            root.set("version", "1.0")
            
            # ProjectedCoordinateSystem
            pcs = ET.SubElement(root, "ProjectedCoordinateSystem", {"id": pcs_id})
            ET.SubElement(pcs, "Name").text = pcs_id
            ET.SubElement(pcs, "Description").text = cleaned_description  # Используем обработанное поле info
            ET.SubElement(pcs, "Authority").text = authority
            
            # AdditionalInformation
            additional_info = ET.SubElement(pcs, "AdditionalInformation")
            parameter_item = ET.SubElement(additional_info, "ParameterItem", {"type": "CsMap"})
            ET.SubElement(parameter_item, "Key").text = "CSQuadrantSimplified"
            ET.SubElement(parameter_item, "IntegerValue").text = "1"
            
            # DomainOfValidity
            domain_of_validity = ET.SubElement(pcs, "DomainOfValidity")
            extent = ET.SubElement(domain_of_validity, "Extent")
            geographic_element = ET.SubElement(extent, "GeographicElement")
            geographic_bounding_box = ET.SubElement(geographic_element, "GeographicBoundingBox")
            ET.SubElement(geographic_bounding_box, "WestBoundLongitude").text = str(bounds[0])
            ET.SubElement(geographic_bounding_box, "EastBoundLongitude").text = str(bounds[1])
            ET.SubElement(geographic_bounding_box, "SouthBoundLatitude").text = str(bounds[2])
            ET.SubElement(geographic_bounding_box, "NorthBoundLatitude").text = str(bounds[3])
            
            ET.SubElement(pcs, "DatumId").text = datum_id  # Используем правильный DatumId из datum_all
            
            # Axis
            axis = ET.SubElement(pcs, "Axis", {"uom": "Meter"})
            easting_axis = ET.SubElement(axis, "CoordinateSystemAxis")
            ET.SubElement(easting_axis, "AxisOrder").text = "1"
            ET.SubElement(easting_axis, "AxisName").text = "Easting"
            ET.SubElement(easting_axis, "AxisAbbreviation").text = "E"
            ET.SubElement(easting_axis, "AxisDirection").text = "east"
            northing_axis = ET.SubElement(axis, "CoordinateSystemAxis")
            ET.SubElement(northing_axis, "AxisOrder").text = "2"
            ET.SubElement(northing_axis, "AxisName").text = "Northing"
            ET.SubElement(northing_axis, "AxisAbbreviation").text = "N"
            ET.SubElement(northing_axis, "AxisDirection").text = "north"
            
            # Conversion/Projection
            conversion = ET.SubElement(pcs, "Conversion")
            projection = ET.SubElement(conversion, "Projection")
            ET.SubElement(projection, "OperationMethodId").text = "Gauss Kruger"
            
            # Параметры проекции
            projection_params = [
                ("Longitude of natural origin", "degree", lon_0),
                ("Latitude of false origin", "degree", lat_0),
                ("Scaling factor for coord differences", "unity", k),
                ("False easting", "Meter", x_0),
                ("False northing", "Meter", y_0),
            ]
            for param_name, uom, value in projection_params:
                parameter_value = ET.SubElement(projection, "ParameterValue")
                ET.SubElement(parameter_value, "OperationParameterId").text = param_name
                # Форматирование значения
                formatted_value = str(int(value)) if value == int(value) else str(value)
                ET.SubElement(parameter_value, "Value", {"uom": uom}).text = formatted_value
            
            # GeodeticDatum
            datum = ET.SubElement(root, "GeodeticDatum", {"id": datum_id})
            ET.SubElement(datum, "Name").text = datum_id
            ET.SubElement(datum, "Description").text = f"Reference ellipsoid-{datum_id}"
            ET.SubElement(datum, "Authority").text = "Not Official"
            ET.SubElement(datum, "PrimeMeridianId").text = "Greenwich"
            ET.SubElement(datum, "EllipsoidId").text = ellipsoid_data["civil_ellipsoid_id"]
            
            # Ellipsoid
            ellipsoid_elem = ET.SubElement(root, "Ellipsoid", {"id": ellipsoid_data["civil_ellipsoid_id"]})
            ET.SubElement(ellipsoid_elem, "Name").text = ellipsoid_data["civil_name"]
            ET.SubElement(ellipsoid_elem, "Description").text = ellipsoid_data["civil_description"]
            ET.SubElement(ellipsoid_elem, "SemiMajorAxis", {"uom": "meter"}).text = str(ellipsoid_data["semi_major_axis"])
            second_param = ET.SubElement(ellipsoid_elem, "SecondDefiningParameter")
            ET.SubElement(second_param, "SemiMinorAxis", {"uom": "meter"}).text = str(ellipsoid_data["semi_minor_axis"])
            
            # Transformation
            transformation = ET.SubElement(root, "Transformation", {"id": transformation_id})
            ET.SubElement(transformation, "Name").text = f"{transformation_id}_to_WGS84"
            ET.SubElement(transformation, "Description").text = f"{transformation_id} to WGS84"
            
            # DomainOfValidity для трансформации
            transform_domain = ET.SubElement(transformation, "DomainOfValidity")
            transform_extent = ET.SubElement(transform_domain, "Extent")
            transform_geographic_element = ET.SubElement(transform_extent, "GeographicElement")
            transform_geographic_bounding_box = ET.SubElement(transform_geographic_element, "GeographicBoundingBox")
            ET.SubElement(transform_geographic_bounding_box, "WestBoundLongitude").text = "14"
            ET.SubElement(transform_geographic_bounding_box, "EastBoundLongitude").text = "180"
            ET.SubElement(transform_geographic_bounding_box, "SouthBoundLatitude").text = "35"
            ET.SubElement(transform_geographic_bounding_box, "NorthBoundLatitude").text = "89"
            
            accuracy = ET.SubElement(transformation, "CoordinateOperationAccuracy")
            ET.SubElement(accuracy, "Accuracy", {"uom": "meter"}).text = "500"
            ET.SubElement(transformation, "SourceDatumId").text = transformation_id
            ET.SubElement(transformation, "TargetDatumId").text = "WGS84"
            ET.SubElement(transformation, "IsReversible").text = "true"
            
            # OperationMethod для трансформации
            operation_method = ET.SubElement(transformation, "OperationMethod")
            ET.SubElement(operation_method, "OperationMethodId").text = "Seven Parameter Transformation"
            
            # Параметры трансформации
            transformation_params = [
                ("X-axis translation", "meter", towgs84_converted[0]),
                ("Y-axis translation", "meter", towgs84_converted[1]),
                ("Z-axis translation", "meter", towgs84_converted[2]),
                ("X-axis rotation", "degree", -towgs84_converted[3] if towgs84_converted[3] != 0 else 0),
                ("Y-axis rotation", "degree", -towgs84_converted[4] if towgs84_converted[4] != 0 else 0),
                ("Z-axis rotation", "degree", -towgs84_converted[5] if towgs84_converted[5] != 0 else 0),
                ("Scale difference", "unity", towgs84_converted[6]),
            ]
            
            for param_name, uom, value in transformation_params:
                parameter_value = ET.SubElement(operation_method, "ParameterValue")
                ET.SubElement(parameter_value, "OperationParameterId").text = param_name
                ET.SubElement(parameter_value, "Value", {"uom": uom}).text = str(value)
            
            # Форматирование XML
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = xml.dom.minidom.parseString(rough_string)
            formatted_xml = reparsed.toprettyxml(indent="  ", encoding=None)
            
            # Удаление лишней пустой строки после декларации и правильная кодировка
            lines = formatted_xml.split('\n')
            if len(lines) > 1 and lines[1].strip() == '':
                lines.pop(1)
            
            # Замена кодировки в заголовке
            if lines[0].startswith('<?xml'):
                lines[0] = '<?xml version="1.0" encoding="utf-8"?>'
            
            return '\n'.join(lines)
            
        except Exception as e:
            self.logger.error(f"Ошибка создания Civil3D XML: {e}", exc_info=True)
            # Fallback минимальный XML
            return self._create_fallback_xml(data)
    
    async def _fetch_ellipsoid_data(self, ellps_name: str) -> Dict[str, Any]:
        """
        Получение данных об эллипсоиде из таблицы ellps_all (аналогично custom_acad.py)
        
        Args:
            ellps_name: Название эллипсоида (например "bessel", "wgs84")
            
        Returns:
            Dict с данными эллипсоида
        """
        try:
            if not self.db_manager:
                self.logger.debug("Менеджер БД недоступен для поиска эллипсоида, используем fallback")
                return self._get_fallback_ellipsoid_data(ellps_name)
            
            query = """
            SELECT "a", "b", "civil_ellipsoid_id", "civil_name", "civil_description"
            FROM public.ellps_all
            WHERE "name_el" = $1;
            """
            
            async with self.db_manager.connection() as conn:
                result = await conn.fetchrow(query, ellps_name)
                if result:
                    self.logger.debug(f"Найдены данные эллипсоида для '{ellps_name}' в БД")
                    return {
                        "semi_major_axis": result['a'],
                        "semi_minor_axis": result['b'],
                        "civil_ellipsoid_id": result['civil_ellipsoid_id'],
                        "civil_name": result['civil_name'],
                        "civil_description": result['civil_description']
                    }
                else:
                    self.logger.warning(f"Не найдены данные для эллипсоида '{ellps_name}' в ellps_all, используем fallback")
                    return self._get_fallback_ellipsoid_data(ellps_name)
                    
        except Exception as e:
            self.logger.error(f"Ошибка при поиске эллипсоида '{ellps_name}': {e}")
            return self._get_fallback_ellipsoid_data(ellps_name)

    def _get_fallback_ellipsoid_data(self, ellps_name: str) -> Dict[str, Any]:
        """
        Fallback значения для популярных эллипсоидов
        
        Args:
            ellps_name: Название эллипсоида
            
        Returns:
            Dict с fallback данными эллипсоида
        """
        # Fallback значения для популярных эллипсоидов
        ellipsoid_defaults = {
            "bessel": {
                "semi_major_axis": 6377397.155,
                "semi_minor_axis": 6356078.96281819,
                "civil_ellipsoid_id": "BESSEL",
                "civil_name": "BESSEL",
                "civil_description": "Bessel, 1841"
            },
            "wgs84": {
                "semi_major_axis": 6378137.0,
                "semi_minor_axis": 6356752.314245179,
                "civil_ellipsoid_id": "WGS84",
                "civil_name": "WGS84", 
                "civil_description": "World Geodetic System 1984"
            },
            "grs80": {
                "semi_major_axis": 6378137.0,
                "semi_minor_axis": 6356752.314140356,
                "civil_ellipsoid_id": "GRS80",
                "civil_name": "GRS80",
                "civil_description": "Geodetic Reference System 1980"
            }
        }
        
        return ellipsoid_defaults.get(ellps_name.lower(), {
            "semi_major_axis": 6378137.0,
            "semi_minor_axis": 6356752.314245179,
            "civil_ellipsoid_id": "UNKNOWN",
            "civil_name": ellps_name.upper(),
            "civil_description": f"Unknown ellipsoid: {ellps_name}"
        })
    
    def _parse_bounds_from_geom(self, geom_wkt: str) -> Tuple[float, float, float, float]:
        """Извлечение границ из WKT геометрии"""
        try:
            # Простой парсинг координат из POLYGON
            coords_match = re.findall(r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)', geom_wkt)
            if coords_match:
                lons = [float(coord[0]) for coord in coords_match]
                lats = [float(coord[1]) for coord in coords_match]
                return (min(lons), max(lons), min(lats), max(lats))
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга границ из геометрии: {e}")
        
        # Значения по умолчанию для России
        return (14.0, 180.0, 35.0, 89.0)
    
    def _create_fallback_xml(self, data: Dict[str, Any]) -> str:
        """Создание минимального XML при ошибках"""
        srid = data.get('srid', 'unknown')
        return f'''<?xml version="1.0" encoding="utf-8"?>
<Dictionary xmlns="http://www.osgeo.org/mapguide/coordinatesystem" version="1.0">
  <ProjectedCoordinateSystem id="ERROR-{srid}">
    <Name>ERROR-{srid}</Name>
    <Description>Error generating full definition for SRID {srid}</Description>
    <Authority>Error</Authority>
  </ProjectedCoordinateSystem>
</Dictionary>'''
    
    def _clean_text_content(self, text: str) -> str:
        """
        Очищает текстовое содержимое от недопустимых символов XML
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """
        if not text:
            return ""
            
        # Убираем недопустимые XML символы (как в custom_acad.py)
        # XML 1.0 допускает: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        valid_chars = []
        for char in str(text):
            code = ord(char)
            if (code == 0x09 or code == 0x0A or code == 0x0D or 
                (0x20 <= code <= 0xD7FF) or 
                (0xE000 <= code <= 0xFFFD) or 
                (0x10000 <= code <= 0x10FFFF)):
                valid_chars.append(char)
            else:
                valid_chars.append('?')  # Заменяем недопустимые символы
                
        cleaned = ''.join(valid_chars)
        
        # Дополнительная очистка для безопасности
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '?', cleaned)
        
        return cleaned
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """
        Очищает весь XML контент от недопустимых символов
        
        Args:
            xml_content: XML контент
            
        Returns:
            Очищенный XML контент
        """
        return self._clean_text_content(xml_content)
    
    def _validate_data(self, data: Dict[str, Any]) -> None:
        """
        Валидация данных для Civil3D экспорта
        
        Args:
            data: Данные для валидации
        """
        # Вызываем базовую валидацию
        super()._validate_data(data)
        
        # Дополнительные проверки для Civil3D
        if not data.get('srid'):
            raise ExportError("SRID обязателен для Civil3D экспорта")
            
        # Проверяем наличие основных данных
        if not data.get('srtext') and not data.get('proj4text'):
            self.logger.warning(f"Отсутствует WKT или Proj4 определение для SRID {data.get('srid')}")
            # Не прерываем экспорт, но логируем предупреждение

    async def _fetch_datum_data(self, towgs84_params: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные о датуме из таблицы datum_all (аналогично custom_acad.py)
        
        Args:
            towgs84_params: Параметры трансформации (например "+towgs84=...")
            
        Returns:
            Dict с данными датума или None при ошибке
        """
        try:
            if not self.db_manager:
                self.logger.debug("Менеджер БД недоступен для поиска датума")
                return None
            
            # Нормализуем строку параметров трансформации
            towgs84_normalized = towgs84_params.strip().replace(' ', '')
            
            query = """
            SELECT name_d, datum
            FROM public.datum_all
            WHERE replace(replace(datum, ' ', ''), '+towgs84=', '') = replace($1, '+towgs84=', '');
            """
            
            async with self.db_manager.connection() as conn:
                result = await conn.fetchrow(query, towgs84_normalized)
                if result:
                    self.logger.info(f"Найдено соответствие в datum_all: {result}")
                    return {
                        "name_d": result['name_d'],
                        "datum": result['datum']
                    }
                self.logger.debug(f"Не найдено соответствие для параметров трансформации: {towgs84_params}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка при поиске датума: {e}")
            return None

    def _clean_and_convert_info(self, info: str) -> str:
        """
        Функция для очистки и преобразования строки info (аналогично custom_acad.py)
        
        Args:
            info: Исходная строка info
            
        Returns:
            Очищенная строка
        """
        if not info:
            return "No Description"
        
        info_converted = unidecode.unidecode(info)
        info_cleaned = re.sub(r'\s+', ' ', info_converted.strip())
        
        invalid_chars = re.findall(r'[^\w\s\-.,]', info_cleaned)
        if invalid_chars:
            self.logger.warning(f"Недопустимые символы в описании: {invalid_chars}. Описание будет очищено.")
            info_cleaned = re.sub(r'[^\w\s\-.,]', '', info_cleaned)
        
        return self._replace_and_clean_string(info_cleaned)

    def _replace_and_clean_string(self, text: str) -> str:
        """
        Функция для замены символов и удаления сдвоенных тире (аналогично custom_acad.py)
        
        Args:
            text: Исходный текст
            
        Returns:
            Очищенный текст
        """
        if not text:
            return "No Description"
        
        # Замена '_' на '-'
        text = text.replace('_', '-')
        # Удаление сдвоенных тире
        text = re.sub(r'-+', '-', text)
        return text
