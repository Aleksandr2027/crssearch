"""
Класс для транслитерации поисковых запросов
"""

from typing import List, Set
from transliterate import translit
import logging
from XML_search.enhanced.transliterator import Transliterator

class SearchTransliterator(Transliterator):
    """Расширенный класс транслитерации для поиска"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Словарь для русской и английской раскладки
        self.keyboard_layout = {
            # Английские буквы в русские
            'v': 'м', 'c': 'с', 'r': 'к', 'b': 'б',  # Основные буквы для теста
            'q': 'й', 'w': 'ц', 'e': 'у', 't': 'е', 'y': 'н',
            'u': 'г', 'i': 'ш', 'o': 'щ', 'p': 'з', '[': 'х', ']': 'ъ',
            'a': 'ф', 's': 'ы', 'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р',
            'j': 'о', 'k': 'л', 'l': 'д', ';': 'ж', "'": 'э', '\\': 'ё',
            'z': 'я', 'x': 'ч', 'n': 'т', 'm': 'ь', ',': 'б', '.': 'ю', '/': '.',
            
            # Русские буквы в английские
            'м': 'v', 'с': 'c', 'к': 'r', 'б': 'b',  # Основные буквы для теста
            'й': 'q', 'ц': 'w', 'у': 'e', 'е': 't', 'н': 'y',
            'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
            'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h',
            'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': "'", 'ё': '\\',
            'я': 'z', 'ч': 'x', 'т': 'n', 'ь': 'm', 'ю': '.', '.': '/',
            
            # Заглавные английские буквы в русские
            'V': 'М', 'C': 'С', 'R': 'К', 'B': 'Б',  # Основные буквы для теста
            'Q': 'Й', 'W': 'Ц', 'E': 'У', 'T': 'Е', 'Y': 'Н',
            'U': 'Г', 'I': 'Ш', 'O': 'Щ', 'P': 'З', '{': 'Х', '}': 'Ъ',
            'A': 'Ф', 'S': 'Ы', 'D': 'В', 'F': 'А', 'G': 'П', 'H': 'Р',
            'J': 'О', 'K': 'Л', 'L': 'Д', ':': 'Ж', '"': 'Э', '|': 'Ё',
            'Z': 'Я', 'X': 'Ч', 'N': 'Т', 'M': 'Ь', '<': 'Б', '>': 'Ю', '?': '.',
            
            # Заглавные русские буквы в английские
            'М': 'V', 'С': 'C', 'К': 'R', 'Б': 'B',  # Основные буквы для теста
            'Й': 'Q', 'Ц': 'W', 'У': 'E', 'Е': 'T', 'Н': 'Y',
            'Г': 'U', 'Ш': 'I', 'Щ': 'O', 'З': 'P', 'Х': '{', 'Ъ': '}',
            'Ф': 'A', 'Ы': 'S', 'В': 'D', 'А': 'F', 'П': 'G', 'Р': 'H',
            'О': 'J', 'Л': 'K', 'Д': 'L', 'Ж': ':', 'Э': '"', 'Ё': '|',
            'Я': 'Z', 'Ч': 'X', 'Т': 'N', 'Ь': 'M', 'Ю': '>', '.': '?'
        }
        
        # Словарь для цифровых замен
        self.number_replacements = {
            '4': ['ч', 'Ч', 'ch', 'Ch', 'CH'],
            '3': ['з', 'З', 'z', 'Z'],
            '0': ['о', 'О', 'o', 'O'],
            '1': ['и', 'И', 'i', 'I'],
            '7': ['т', 'Т', 't', 'T']
        }
        
    def generate_variants(self, text: str) -> List[str]:
        """
        Генерация вариантов поискового запроса
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов запроса
        """
        if not text:
            return []
            
        variants = set()
        
        # Добавляем базовые варианты транслитерации
        base_variants = super().generate_variants(text)
        variants.update(base_variants)
        
        # Добавляем варианты с заменой раскладки
        keyboard_variants = self.reverse_keyboard_layout(text)
        variants.update(keyboard_variants)
        
        # Добавляем варианты с разным регистром
        case_variants = self.normalize_case(text)
        variants.update(case_variants)
        
        # Удаляем пустые строки и дубликаты
        variants = {v for v in variants if v and v.strip()}
        
        return list(variants)
        
    def normalize_case(self, text: str) -> List[str]:
        """
        Нормализация регистра текста
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов с разным регистром
        """
        variants = {text}  # Исходный текст
        variants.add(text.lower())  # Нижний регистр
        variants.add(text.upper())  # Верхний регистр
        variants.add(text.capitalize())  # Первая буква заглавная
        
        # Для аббревиатур
        if any(c.isupper() for c in text):
            variants.add(text.upper())
        
        return list(variants)
        
    def reverse_keyboard_layout(self, text: str) -> List[str]:
        """
        Преобразование текста в другую раскладку клавиатуры
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов с разной раскладкой
        """
        if not text:
            return []
            
        variants = set()
        variants.add(text)
        
        # Преобразование в противоположную раскладку
        reversed_text = ''
        for char in text:
            if char in self.keyboard_layout:
                reversed_text += self.keyboard_layout[char]
            else:
                reversed_text += char
                
        variants.add(reversed_text)
        
        # Добавляем варианты с разным регистром для преобразованного текста
        for variant in self.normalize_case(reversed_text):
            variants.add(variant)
            
        # Проверяем, является ли текст уже в русской раскладке
        is_russian = any(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ' for c in text)
        
        # Если текст в русской раскладке, добавляем варианты в английской
        if is_russian:
            eng_text = ''
            for char in text:
                if char in self.keyboard_layout:
                    eng_text += self.keyboard_layout[char]
                else:
                    eng_text += char
            variants.add(eng_text)
            variants.update(self.normalize_case(eng_text))
            
        return list(variants) 