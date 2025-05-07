"""
Тесты для транслитератора поисковых запросов
"""

import pytest
from XML_search.core.search import SearchTransliterator

class TestSearchTransliterator:
    """Тесты для транслитератора"""
    
    @pytest.fixture
    def transliterator(self):
        """Фикстура для создания транслитератора"""
        return SearchTransliterator()
    
    def test_generate_variants_basic(self, transliterator):
        """Тест генерации базовых вариантов"""
        text = "мск"
        variants = transliterator.generate_variants(text)
        
        # Проверяем наличие базовых вариантов
        assert "мск" in variants
        assert "МСК" in variants
        assert "Мск" in variants
        assert "msk" in variants
        
    def test_generate_variants_with_numbers(self, transliterator):
        """Тест генерации вариантов с цифрами"""
        text = "мск4"
        variants = transliterator.generate_variants(text)
        
        # Проверяем наличие базовых вариантов
        assert "мск4" in variants
        assert "МСК4" in variants
        assert "Мск4" in variants
        assert "msk4" in variants
        
        # Проверяем варианты с заменой цифры
        assert any("мскч" in v.lower() for v in variants)
        
    def test_generate_variants_with_layout(self, transliterator):
        """Тест генерации вариантов с разной раскладкой"""
        text = "vcrb"  # 'мскб' в английской раскладке
        variants = transliterator.generate_variants(text)
        
        # Проверяем наличие базовых вариантов
        assert "vcrb" in variants  # Исходный текст
        assert "мскб" in variants  # Текст в русской раскладке
        assert "МСКБ" in variants  # Верхний регистр
        assert "Мскб" in variants  # Первая заглавная
        
    def test_normalize_case(self, transliterator):
        """Тест нормализации регистра"""
        text = "мск"
        variants = set(transliterator.normalize_case(text))
        
        expected = {"мск", "МСК", "Мск"}
        assert variants == expected
        
    def test_normalize_case_with_abbreviation(self, transliterator):
        """Тест нормализации регистра для аббревиатур"""
        text = "МСК"
        variants = set(transliterator.normalize_case(text))
        
        expected = {"МСК", "мск", "Мск"}
        assert variants == expected
        
    def test_reverse_keyboard_layout(self, transliterator):
        """Тест преобразования раскладки клавиатуры"""
        text = "vcrb"  # 'мскб' в английской раскладке
        variants = transliterator.reverse_keyboard_layout(text)
        
        # Проверяем наличие базовых вариантов
        assert "vcrb" in variants  # Исходный текст
        assert "мскб" in variants  # Текст в русской раскладке
        assert "МСКБ" in variants  # Верхний регистр
        assert "Мскб" in variants  # Первая заглавная
        
    def test_empty_input(self, transliterator):
        """Тест обработки пустого ввода"""
        variants = transliterator.generate_variants("")
        assert variants == []
        
    def test_special_characters(self, transliterator):
        """Тест обработки специальных символов"""
        text = "мск-01"
        variants = transliterator.generate_variants(text)
        
        # Проверяем наличие базовых вариантов
        assert "мск-01" in variants
        assert "МСК-01" in variants
        assert "Мск-01" in variants
        assert "msk-01" in variants
        
        # Проверяем варианты с заменой цифр
        assert any("-o" in v.lower() for v in variants)
        assert any("-0" in v for v in variants) 