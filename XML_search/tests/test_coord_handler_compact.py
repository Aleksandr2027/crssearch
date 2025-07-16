"""
Тест для новой функциональности компактного списка координат
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch
from XML_search.bot.handlers.coord_handler import CoordHandler, CoordinateInput
from XML_search.bot.config import BotConfig

class TestCoordHandlerCompact(unittest.TestCase):
    """Тесты для компактного списка координат"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем мок-конфигурацию
        self.config = Mock(spec=BotConfig)
        
        # Создаем мок для db_manager
        self.db_manager = Mock()
        self.db_manager.connection = AsyncMock()
        
        # Создаем обработчик
        self.coord_handler = CoordHandler(
            config=self.config,
            db_manager=self.db_manager,
            metrics=Mock(),
            logger=Mock(),
            cache=Mock()
        )
    
    def test_parse_coordinates_decimal(self):
        """Тест парсинга координат в десятичном формате"""
        # Тест с разделителем $
        coords = self.coord_handler._parse_coordinates("55.7558$37.6173")
        self.assertIsNotNone(coords)
        self.assertEqual(coords.latitude, 55.7558)
        self.assertEqual(coords.longitude, 37.6173)
        
        # Тест с разделителем ;
        coords = self.coord_handler._parse_coordinates("55.7558;37.6173")
        self.assertIsNotNone(coords)
        self.assertEqual(coords.latitude, 55.7558)
        self.assertEqual(coords.longitude, 37.6173)
        
        # Тест с пробелом
        coords = self.coord_handler._parse_coordinates("55.7558 37.6173")
        self.assertIsNotNone(coords)
        self.assertEqual(coords.latitude, 55.7558)
        self.assertEqual(coords.longitude, 37.6173)
    
    def test_parse_coordinates_dms(self):
        """Тест парсинга координат в формате градусы-минуты-секунды"""
        coords = self.coord_handler._parse_coordinates("55 45 20.88;37 37 2.28")
        self.assertIsNotNone(coords)
        
        # Проверяем преобразование в десятичные градусы
        expected_lat = 55 + 45/60 + 20.88/3600
        expected_lon = 37 + 37/60 + 2.28/3600
        
        self.assertAlmostEqual(coords.latitude, expected_lat, places=6)
        self.assertAlmostEqual(coords.longitude, expected_lon, places=6)
    
    def test_parse_coordinates_invalid(self):
        """Тест парсинга некорректных координат"""
        # Пустая строка
        coords = self.coord_handler._parse_coordinates("")
        self.assertIsNone(coords)
        
        # Некорректный формат
        coords = self.coord_handler._parse_coordinates("invalid coordinates")
        self.assertIsNone(coords)
        
        # Только одна координата
        coords = self.coord_handler._parse_coordinates("55.7558")
        self.assertIsNone(coords)
    
    def test_create_compact_list(self):
        """Тест создания компактного списка"""
        coords = CoordinateInput(latitude=55.7558, longitude=37.6173)
        results = [
            (32637, "UTM zone 37N", "37N", "Universal Transverse Mercator zone 37 N", None, 414668.12, 6176909.34),
            (100326, "SK95z7", "7", "СК-95 зона 7", None, 414668.12, 6176909.34),
            (100327, "SK63z7", "7", "СК-63 зона 7", None, 414668.12, 6176909.34)
        ]
        
        text = self.coord_handler._create_compact_list(coords, results)
        
        # Проверяем содержимое
        self.assertIn("Найдено 3 систем координат", text)
        self.assertIn("Lat: 55.7558", text)
        self.assertIn("Lon: 37.6173", text)
        self.assertIn("1. UTM zone 37N", text)
        self.assertIn("2. SK95z7", text)
        self.assertIn("3. SK63z7", text)
    
    def test_create_detailed_view(self):
        """Тест создания развернутого вида"""
        coords = CoordinateInput(latitude=55.7558, longitude=37.6173)
        results = [
            (32637, "UTM zone 37N", "37N", "Universal Transverse Mercator zone 37 N", None, 414668.12, 6176909.34),
            (100326, "SK95z7", "7", "СК-95 зона 7", None, 414668.12, 6176909.34)
        ]
        selected_srid = 32637
        
        text = self.coord_handler._create_detailed_view(coords, results, selected_srid)
        
        # Проверяем, что выбранная система развернута
        self.assertIn("🔷 1. UTM zone 37N", text)
        self.assertIn("SRID: 32637", text)
        self.assertIn("Зона: 37N", text)
        self.assertIn("Координаты: X=414668.12, Y=6176909.34", text)
        
        # Проверяем, что другая система свернута
        self.assertIn("2. SK95z7", text)
        self.assertNotIn("SRID: 100326", text)
    
    def test_get_compact_keyboard(self):
        """Тест создания компактной клавиатуры"""
        results = [
            (32637, "UTM zone 37N", "37N", "Universal Transverse Mercator zone 37 N", None, 414668.12, 6176909.34),
            (100326, "SK95z7", "7", "СК-95 зона 7", None, 414668.12, 6176909.34)
        ]
        
        keyboard = self.coord_handler._get_compact_keyboard(results)
        
        # Проверяем структуру клавиатуры
        self.assertEqual(len(keyboard.inline_keyboard), 3)  # 2 кнопки "Подробнее" + 1 кнопка "Главное меню"
        
        # Проверяем callback_data
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "coord_detail:32637")
        self.assertEqual(keyboard.inline_keyboard[1][0].callback_data, "coord_detail:100326")
        self.assertEqual(keyboard.inline_keyboard[2][0].callback_data, "coord_back_to_menu")
    
    def test_get_detailed_keyboard(self):
        """Тест создания развернутой клавиатуры"""
        results = [
            (32637, "UTM zone 37N", "37N", "Universal Transverse Mercator zone 37 N", None, 414668.12, 6176909.34),
            (100326, "SK95z7", "7", "СК-95 зона 7", None, 414668.12, 6176909.34)
        ]
        selected_srid = 32637
        
        keyboard = self.coord_handler._get_detailed_keyboard(selected_srid, results)
        
        # Проверяем наличие кнопок экспорта
        export_row = keyboard.inline_keyboard[0]
        self.assertEqual(len(export_row), 3)  # Civil3D, GMv20, GMv25
        self.assertEqual(export_row[0].callback_data, "coord_export:civil3d:32637")
        self.assertEqual(export_row[1].callback_data, "coord_export:gmv20:32637")
        self.assertEqual(export_row[2].callback_data, "coord_export:gmv25:32637")
        
        # Проверяем кнопку "Подробнее" для другой системы
        detail_button = keyboard.inline_keyboard[1][0]
        self.assertEqual(detail_button.callback_data, "coord_detail:100326")
        
        # Проверяем кнопки "Свернуть" и "Главное меню"
        bottom_row = keyboard.inline_keyboard[2]
        self.assertEqual(bottom_row[0].callback_data, "coord_collapse")
        self.assertEqual(bottom_row[1].callback_data, "coord_back_to_menu")

if __name__ == '__main__':
    unittest.main() 