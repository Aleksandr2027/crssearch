import pytest
from XML_search.bot.utils.validation_utils import (
    validate_srid,
    validate_search_query,
    validate_export_format,
    validate_user_access
)

class TestValidationUtils:
    """Тесты для утилит валидации"""
    
    @pytest.mark.parametrize("srid,expected", [
        (100000, True),
        (32601, True),
        (32660, True),
        (99999, False),
        (32661, False),
        (32600, False),
        ("invalid", False),
        (None, False)
    ])
    def test_validate_srid(self, srid, expected):
        """Тест валидации SRID"""
        assert validate_srid(srid) == expected
        
    @pytest.mark.parametrize("query,expected", [
        ("MSK", True),
        ("мск", True),
        ("100000", True),
        ("", False),
        (" ", False),
        ("a" * 101, False),  # Слишком длинный запрос
        (None, False)
    ])
    def test_validate_search_query(self, query, expected):
        """Тест валидации поискового запроса"""
        assert validate_search_query(query) == expected
        
    @pytest.mark.parametrize("format,expected", [
        ("xml_Civil3D", True),
        ("prj_GMv20", True),
        ("prj_GMv25", True),
        ("invalid_format", False),
        ("", False),
        (None, False)
    ])
    def test_validate_export_format(self, format, expected):
        """Тест валидации формата экспорта"""
        assert validate_export_format(format) == expected
        
    @pytest.mark.parametrize("user_id,authorized_users,expected", [
        (12345, {12345}, True),
        (12345, set(), False),
        (12345, {54321}, False),
        (None, {12345}, False)
    ])
    def test_validate_user_access(self, user_id, authorized_users, expected):
        """Тест валидации доступа пользователя"""
        assert validate_user_access(user_id, authorized_users) == expected
        
    def test_validate_srid_range(self):
        """Тест валидации диапазона SRID"""
        # Проверка граничных значений для UTM зон
        assert validate_srid(32601)  # Первая зона
        assert validate_srid(32660)  # Последняя зона
        assert not validate_srid(32600)  # До первой зоны
        assert not validate_srid(32661)  # После последней зоны
        
    def test_validate_search_query_special_chars(self):
        """Тест валидации запроса со специальными символами"""
        # Проверка допустимых специальных символов
        assert validate_search_query("MSK-01")
        assert validate_search_query("MSK_01")
        assert validate_search_query("MSK.01")
        # Проверка недопустимых специальных символов
        assert not validate_search_query("MSK@01")
        assert not validate_search_query("MSK#01")
        
    def test_validate_export_format_case_sensitive(self):
        """Тест валидации формата экспорта с учетом регистра"""
        assert validate_export_format("xml_Civil3D")
        assert not validate_export_format("XML_CIVIL3D")
        assert not validate_export_format("xml_civil3d") 