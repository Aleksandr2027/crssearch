"""
Утилиты для обработки координат
"""

import re
from typing import Tuple

class CoordUtils:
    """Утилиты для работы с координатами"""
    
    @staticmethod
    def dms_to_decimal(coord: str) -> float:
        """
        Преобразование координат из DMS в десятичные градусы
        
        Args:
            coord: Строка с координатами в формате DMS
            
        Returns:
            Координата в десятичных градусах
            
        Raises:
            ValueError: Если формат координат неверный
        """
        coord = re.sub(r'\s+', ' ', coord.strip())
        parts = re.split(r'[\s°\'"]+', coord)
        parts = [p for p in parts if p]
        
        if not parts:
            raise ValueError("Пустая строка координат")
            
        try:
            degrees = float(parts[0])
            minutes = float(parts[1]) if len(parts) > 1 else 0
            seconds = float(parts[2]) if len(parts) > 2 else 0
            
            decimal = degrees + minutes / 60 + seconds / 3600
            return decimal
            
        except (ValueError, IndexError) as e:
            raise ValueError(f"Неверный формат координат: {str(e)}")
            
    @staticmethod
    def parse_coordinates(input_str: str) -> Tuple[float, float]:
        """
        Разбор строки с координатами
        
        Args:
            input_str: Строка с координатами в формате "latitude;longitude"
            
        Returns:
            Кортеж (широта, долгота) в десятичных градусах
            
        Raises:
            ValueError: Если формат координат неверный
        """
        # Заменяем $ и % на ; для унификации разделителя
        input_str = input_str.replace('$', ';').replace('%', ';')
        
        # Удаляем пробелы вокруг разделителя
        input_str = re.sub(r'\s*;\s*', ';', input_str.strip())
        
        # Разбиваем на части
        parts = input_str.split(';')
        if len(parts) != 2:
            raise ValueError(
                "Неверный формат ввода. Ожидается 'latitude;longitude' "
                "или 'latitude$longitude' или 'latitude%longitude'."
            )
            
        try:
            latitude = CoordUtils.dms_to_decimal(parts[0])
            longitude = CoordUtils.dms_to_decimal(parts[1])
            
            # Проверяем диапазоны
            if not (-90 <= latitude <= 90):
                raise ValueError("Широта должна быть в диапазоне [-90, 90]")
            if not (-180 <= longitude <= 180):
                raise ValueError("Долгота должна быть в диапазоне [-180, 180]")
                
            return latitude, longitude
            
        except ValueError as e:
            raise ValueError(f"Ошибка при разборе координат: {str(e)}")
            
    @staticmethod
    def format_coordinates(latitude: float, longitude: float) -> str:
        """
        Форматирование координат для вывода
        
        Args:
            latitude: Широта в десятичных градусах
            longitude: Долгота в десятичных градусах
            
        Returns:
            Отформатированная строка с координатами
        """
        return f"N: {latitude:.6f}, E: {longitude:.6f}" 