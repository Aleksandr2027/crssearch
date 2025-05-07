import pytest
from XML_search.bot.utils.format_utils import (
    format_coordinate_result,
    format_search_result,
    format_inline_result,
    format_error_message
)

class TestFormatUtils:
    """Тесты для функций форматирования"""
    
    def test_format_coordinate_result(self):
        """Тест форматирования результата поиска по координатам"""
        test_result = {
            'srid': 100000,
            'name': 'Test CRS',
            'info': 'Test Info',
            'reliability': 'EPSG',
            'coordinates': {'x': 123.456, 'y': 789.012}
        }
        formatted = format_coordinate_result(test_result)
        assert '100000' in formatted
        assert 'Test CRS' in formatted
        assert 'Test Info' in formatted
        assert 'EPSG' in formatted
        assert '123.456' in formatted
        assert '789.012' in formatted
        
    def test_format_search_result(self):
        """Тест форматирования результата текстового поиска"""
        test_result = {
            'srid': 100000,
            'name': 'Test CRS',
            'info': 'Test Info',
            'reliability': 'EPSG'
        }
        formatted = format_search_result(test_result)
        assert '100000' in formatted
        assert 'Test CRS' in formatted
        assert 'Test Info' in formatted
        assert 'EPSG' in formatted
        
    def test_format_inline_result(self):
        """Тест форматирования результата для inline-режима"""
        test_result = {
            'srid': 100000,
            'name': 'Test CRS',
            'info': 'Test Info',
            'reliability': 'EPSG'
        }
        formatted = format_inline_result(test_result)
        assert formatted['id'] == '100000'
        assert 'Test CRS' in formatted['title']
        assert 'Test Info' in formatted['description']
        assert 'EPSG' in formatted['message_text']
        
    def test_format_error_message(self):
        """Тест форматирования сообщения об ошибке"""
        test_error = "Test Error"
        formatted = format_error_message(test_error)
        assert '❌' in formatted
        assert 'Test Error' in formatted
        
    def test_format_coordinate_result_no_info(self):
        """Тест форматирования результата без дополнительной информации"""
        test_result = {
            'srid': 100000,
            'name': 'Test CRS',
            'reliability': 'EPSG',
            'coordinates': {'x': 123.456, 'y': 789.012}
        }
        formatted = format_coordinate_result(test_result)
        assert '100000' in formatted
        assert 'Test CRS' in formatted
        assert 'EPSG' in formatted
        
    def test_format_search_result_no_reliability(self):
        """Тест форматирования результата без значения reliability"""
        test_result = {
            'srid': 100000,
            'name': 'Test CRS',
            'info': 'Test Info'
        }
        formatted = format_search_result(test_result)
        assert 'Уточнить у Администратора' in formatted
        
    def test_format_inline_result_long_text(self):
        """Тест форматирования длинного текста для inline-режима"""
        test_result = {
            'srid': 100000,
            'name': 'Test CRS' * 20,  # Длинное название
            'info': 'Test Info' * 20,  # Длинное описание
            'reliability': 'EPSG'
        }
        formatted = format_inline_result(test_result)
        assert len(formatted['title']) <= 50
        assert len(formatted['description']) <= 100 