import pytest
from XML_search.bot.utils.coord_utils import (
    parse_coordinates,
    dms_to_decimal,
    validate_coordinates,
    format_coordinates
)

class TestCoordUtils:
    """Тесты для утилит работы с координатами"""
    
    @pytest.mark.parametrize("coord_input,expected", [
        ("55.7558;37.6173", (55.7558, 37.6173)),
        ("55 45.348;37 37.038", (55.7558, 37.6173)),
        ("55 45 20.88;37 37 2.28", (55.7558, 37.6173)),
        ("55°45'20.88\";37°37'2.28\"", (55.7558, 37.6173)),
        ("55.7558$37.6173", (55.7558, 37.6173)),
        ("55.7558%37.6173", (55.7558, 37.6173))
    ])
    def test_parse_coordinates_valid(self, coord_input, expected):
        """Тест парсинга координат в разных форматах"""
        lat, lon = parse_coordinates(coord_input)
        assert pytest.approx(lat, 0.0001) == expected[0]
        assert pytest.approx(lon, 0.0001) == expected[1]
        
    @pytest.mark.parametrize("invalid_input", [
        "invalid",
        "55.7558",
        "55.7558;",
        ";37.6173",
        "55.7558;invalid",
        "invalid;37.6173",
        "90.1;37.6173",  # Широта > 90
        "55.7558;181.0"  # Долгота > 180
    ])
    def test_parse_coordinates_invalid(self, invalid_input):
        """Тест обработки некорректных координат"""
        with pytest.raises(ValueError):
            parse_coordinates(invalid_input)
            
    @pytest.mark.parametrize("dms_input,expected", [
        ("55 45 20.88", 55.7558),
        ("37 37 2.28", 37.6173),
        ("55°45'20.88\"", 55.7558),
        ("37°37'2.28\"", 37.6173),
        ("55 45.348", 55.7558),
        ("37 37.038", 37.6173)
    ])
    def test_dms_to_decimal(self, dms_input, expected):
        """Тест преобразования DMS в десятичные градусы"""
        result = dms_to_decimal(dms_input)
        assert pytest.approx(result, 0.0001) == expected
        
    @pytest.mark.parametrize("lat,lon,expected", [
        (55.7558, 37.6173, True),
        (90.0, 180.0, True),
        (-90.0, -180.0, True),
        (90.1, 37.6173, False),
        (55.7558, 180.1, False),
        (-90.1, 37.6173, False),
        (55.7558, -180.1, False)
    ])
    def test_validate_coordinates(self, lat, lon, expected):
        """Тест валидации координат"""
        assert validate_coordinates(lat, lon) == expected
        
    @pytest.mark.parametrize("lat,lon,expected_format", [
        (55.7558, 37.6173, "55°45'20.88\"N 37°37'2.28\"E"),
        (-55.7558, -37.6173, "55°45'20.88\"S 37°37'2.28\"W"),
        (0.0, 0.0, "0°0'0.00\"N 0°0'0.00\"E"),
        (90.0, 180.0, "90°0'0.00\"N 180°0'0.00\"E")
    ])
    def test_format_coordinates(self, lat, lon, expected_format):
        """Тест форматирования координат"""
        result = format_coordinates(lat, lon)
        assert result == expected_format
        
    def test_dms_to_decimal_invalid(self):
        """Тест обработки некорректного формата DMS"""
        with pytest.raises(ValueError):
            dms_to_decimal("invalid")
            
    def test_format_coordinates_invalid(self):
        """Тест форматирования некорректных координат"""
        with pytest.raises(ValueError):
            format_coordinates(91.0, 37.6173)  # Широта > 90
        with pytest.raises(ValueError):
            format_coordinates(55.7558, 181.0)  # Долгота > 180 