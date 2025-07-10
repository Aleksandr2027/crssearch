"""
Утилиты для работы с координатами
"""

import re
from typing import Tuple, Dict, Any, Optional, List
from dataclasses import dataclass
import math
from .format_utils import MessageFormatter
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
import asyncio

@dataclass
class Coordinates:
    """Класс для хранения координат"""
    latitude: float
    longitude: float
    original_format: str = 'decimal'  # decimal, dms, utm
    
    def __str__(self) -> str:
        return f"{self.latitude};{self.longitude}"

class CoordinateParser:
    """Класс для парсинга и валидации координат"""
    
    # Поддерживаемые разделители координат
    SEPARATORS = [';', '$', '%']
    
    # Поддерживаемые форматы
    FORMATS = ['decimal', 'dms', 'utm']
    
    def __init__(self):
        """Инициализация парсера координат"""
        self.logger = LogManager().get_logger(__name__)
        self.metrics = MetricsManager()
        self.formatter = MessageFormatter()
        
        # Компилируем регулярные выражения для разных форматов
        self.patterns = {
            'decimal': re.compile(r'^-?\d+\.?\d*$'),
            'dms': re.compile(r'^-?\d+°\s*\d+\'\s*\d+(\.\d+)?\"?$'),
            'simple_dms': re.compile(r'^-?\d+\s+\d+\s+\d+(\.\d+)?$'),
            'degrees_minutes': re.compile(r'^-?\d+\s+\d+(\.\d+)?$')  # Градусы и минуты
        }
        
    def parse(self, input_str: str) -> Coordinates:
        """
        Парсинг строки с координатами
        
        Args:
            input_str: Строка с координатами
            
        Returns:
            Объект Coordinates
            
        Raises:
            ValueError: Если формат координат неверный
        """
        try:
            # Унифицируем разделитель
            for sep in self.SEPARATORS[1:]:
                input_str = input_str.replace(sep, self.SEPARATORS[0])
            
            # Очищаем строку и разбиваем на части
            input_str = re.sub(r'\s*;\s*', ';', input_str.strip())
            parts = input_str.split(';')
            
            if len(parts) != 2:
                raise ValueError(
                    "Неверный формат ввода. Ожидается 'широта;долгота' "
                    "или 'широта$долгота' или 'широта%долгота'"
                )
            
            # Определяем формат и парсим каждую координату
            lat = self._parse_coordinate(parts[0], 'latitude')
            lon = self._parse_coordinate(parts[1], 'longitude')
            
            # Валидируем значения
            self._validate_coordinates(lat, lon)
            
            return Coordinates(lat, lon)
            
        except Exception as e:
            self.logger.error(f"Ошибка при парсинге координат: {e}")
            asyncio.create_task(self.metrics.record_error('coordinate_parse', str(e)))
            raise ValueError(str(e))
    
    def _parse_coordinate(self, coord_str: str, coord_type: str) -> float:
        """
        Парсинг одной координаты
        
        Args:
            coord_str: Строка с координатой
            coord_type: Тип координаты ('latitude' или 'longitude')
            
        Returns:
            Значение координаты в десятичных градусах
        """
        coord_str = coord_str.strip()
        
        # Пробуем разные форматы
        if self.patterns['decimal'].match(coord_str):
            return float(coord_str)
        
        if self.patterns['degrees_minutes'].match(coord_str):
            return self._degrees_minutes_to_decimal(coord_str)
        
        if self.patterns['dms'].match(coord_str) or self.patterns['simple_dms'].match(coord_str):
            return self._dms_to_decimal(coord_str)
            
        raise ValueError(f"Неподдерживаемый формат координаты: {coord_str}")
    
    def _dms_to_decimal(self, dms_str: str) -> float:
        """
        Преобразование координат из DMS в десятичные градусы
        
        Args:
            dms_str: Строка в формате DMS
            
        Returns:
            Значение в десятичных градусах
        """
        # Очищаем строку от символов градусов, минут и секунд
        clean_str = re.sub(r'[°\'"]+', ' ', dms_str.strip())
        parts = [p for p in clean_str.split() if p]
        
        if len(parts) < 1:
            raise ValueError("Неверный формат DMS")
            
        degrees = float(parts[0])
        minutes = float(parts[1]) if len(parts) > 1 else 0
        seconds = float(parts[2]) if len(parts) > 2 else 0
        
        return degrees + minutes / 60 + seconds / 3600
    
    def _degrees_minutes_to_decimal(self, dm_str: str) -> float:
        """
        Преобразование координат из формата "градусы минуты" в десятичные градусы
        
        Args:
            dm_str: Строка в формате "градусы минуты" (например, "55 45.348")
            
        Returns:
            Значение в десятичных градусах
        """
        parts = dm_str.strip().split()
        
        if len(parts) != 2:
            raise ValueError("Неверный формат градусы-минуты")
            
        degrees = float(parts[0])
        minutes = float(parts[1])
        
        return degrees + minutes / 60
    
    def _validate_coordinates(self, lat: float, lon: float) -> None:
        """
        Валидация значений координат
        
        Args:
            lat: Широта
            lon: Долгота
            
        Raises:
            ValueError: Если координаты вне допустимого диапазона
        """
        if not -90 <= lat <= 90:
            raise ValueError("Широта должна быть в диапазоне от -90 до 90 градусов")
        if not -180 <= lon <= 180:
            raise ValueError("Долгота должна быть в диапазоне от -180 до 180 градусов")

class CoordinateFormatter:
    """Класс для форматирования координат"""
    
    def __init__(self):
        self.formatter = MessageFormatter()
    
    def format_decimal(self, coords: Coordinates, precision: int = 3) -> str:
        """
        Форматирование в десятичные градусы
        
        Args:
            coords: Объект координат
            precision: Точность округления
            
        Returns:
            Отформатированная строка
        """
        return self.formatter.format_coordinates(
            round(coords.latitude, precision),
            round(coords.longitude, precision)
        )
    
    def format_dms(self, coords: Coordinates) -> str:
        """
        Форматирование в градусы, минуты, секунды
        
        Args:
            coords: Объект координат
            
        Returns:
            Отформатированная строка
        """
        lat_dms = self._decimal_to_dms(coords.latitude)
        lon_dms = self._decimal_to_dms(coords.longitude)
        return (
            f"{self.formatter.EMOJI['coordinates']} *Координаты:*\n"
            f"`N: {lat_dms}`\n"
            f"`E: {lon_dms}`"
        )
    
    def _decimal_to_dms(self, decimal: float) -> str:
        """
        Преобразование десятичных градусов в DMS
        
        Args:
            decimal: Значение в десятичных градусах
            
        Returns:
            Строка в формате DMS
        """
        degrees = int(decimal)
        minutes_float = abs(decimal - degrees) * 60
        minutes = int(minutes_float)
        seconds = round((minutes_float - minutes) * 60, 2)
        
        return f"{abs(degrees)}°{minutes}'{seconds}\""

class CoordinateConverter:
    """Класс для конвертации координат между разными системами"""
    
    @staticmethod
    def get_utm_zone(lon: float) -> int:
        """
        Определение зоны UTM
        
        Args:
            lon: Долгота
            
        Returns:
            Номер зоны UTM
        """
        return int((lon + 180) / 6) + 1
    
    @staticmethod
    def get_hemisphere(lat: float) -> str:
        """
        Определение полушария
        
        Args:
            lat: Широта
            
        Returns:
            'N' для северного полушария, 'S' для южного
        """
        return 'N' if lat >= 0 else 'S'

def parse_coordinates(coord_str: str) -> Tuple[float, float]:
    """
    Парсинг строки с координатами в разных форматах
    
    Args:
        coord_str: Строка с координатами в формате "lat;lon", "lat$lon" или "lat%lon"
        
    Returns:
        Кортеж (широта, долгота) в десятичных градусах
        
    Raises:
        ValueError: Если формат координат неверный
    """
    # Заменяем разделители на стандартный
    coord_str = coord_str.replace('$', ';').replace('%', ';')
    
    # Проверяем наличие разделителя
    if ';' not in coord_str:
        raise ValueError("Неверный формат координат. Используйте разделитель ;, $ или %")
        
    lat_str, lon_str = coord_str.split(';')
    
    try:
        lat = dms_to_decimal(lat_str.strip())
        lon = dms_to_decimal(lon_str.strip())
        
        if not validate_coordinates(lat, lon):
            raise ValueError("Координаты вне допустимого диапазона")
            
        return lat, lon
    except Exception as e:
        raise ValueError(f"Ошибка при парсинге координат: {str(e)}")

def dms_to_decimal(coord: str) -> float:
    """
    Преобразование координат из формата DMS в десятичные градусы
    
    Args:
        coord: Строка с координатой в формате DMS
        
    Returns:
        Координата в десятичных градусах
    """
    # Удаляем градусы, минуты, секунды и кавычки
    coord = re.sub(r'[°\'"]+', ' ', coord.strip())
    # Разбиваем на части
    parts = [p for p in re.split(r'\s+', coord) if p]
    
    if len(parts) == 1:  # Десятичные градусы
        return float(parts[0])
    elif len(parts) == 2:  # Градусы и минуты
        deg, minutes = map(float, parts)
        return deg + minutes / 60
    elif len(parts) == 3:  # Градусы, минуты и секунды
        deg, minutes, seconds = map(float, parts)
        return deg + minutes / 60 + seconds / 3600
    else:
        raise ValueError("Неверный формат DMS координат")

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Проверка координат на допустимые значения
    
    Args:
        lat: Широта
        lon: Долгота
        
    Returns:
        True если координаты валидны, False иначе
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180

def format_coordinates(lat: float, lon: float) -> str:
    """
    Форматирование координат в строку
    
    Args:
        lat: Широта в десятичных градусах
        lon: Долгота в десятичных градусах
        
    Returns:
        Строка с координатами в формате DMS
    """
    if not validate_coordinates(lat, lon):
        raise ValueError("Координаты вне допустимого диапазона")
        
    def decimal_to_dms(decimal: float, is_latitude: bool) -> str:
        """Преобразование десятичных градусов в DMS"""
        direction = 'N' if decimal >= 0 and is_latitude else 'S' if is_latitude else 'E' if decimal >= 0 else 'W'
        decimal = abs(decimal)
        degrees = int(decimal)
        decimal_minutes = (decimal - degrees) * 60
        minutes = int(decimal_minutes)
        seconds = (decimal_minutes - minutes) * 60
        
        return f"{degrees}°{minutes}'{seconds:.2f}\"{direction}"
        
    return f"{decimal_to_dms(lat, True)} {decimal_to_dms(lon, False)}" 