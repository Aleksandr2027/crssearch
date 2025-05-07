from typing import List, Set
import re
from unidecode import unidecode
import logging

class Transliterator:
    """Класс для транслитерации текста"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Словарь для транслитерации кириллицы в латиницу
        self.cyrillic_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        
        # Словарь для транслитерации латиницы в кириллицу
        self.latin_to_cyrillic = {
            'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'e': 'е', 'yo': 'ё',
            'zh': 'ж', 'z': 'з', 'i': 'и', 'y': 'й', 'k': 'к', 'l': 'л', 'm': 'м',
            'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
            'f': 'ф', 'h': 'х', 'ts': 'ц', 'ch': 'ч', 'sh': 'ш', 'sch': 'щ',
            'yu': 'ю', 'ya': 'я',
            'A': 'А', 'B': 'Б', 'V': 'В', 'G': 'Г', 'D': 'Д', 'E': 'Е', 'Yo': 'Ё',
            'Zh': 'Ж', 'Z': 'З', 'I': 'И', 'Y': 'Й', 'K': 'К', 'L': 'Л', 'M': 'М',
            'N': 'Н', 'O': 'О', 'P': 'П', 'R': 'Р', 'S': 'С', 'T': 'Т', 'U': 'У',
            'F': 'Ф', 'H': 'Х', 'Ts': 'Ц', 'Ch': 'Ч', 'Sh': 'Ш', 'Sch': 'Щ',
            'Yu': 'Ю', 'Ya': 'Я'
        }
        
        # Словарь для двунаправленной замены цифр на буквы и наоборот
        self.digit_replacements = {
            '4': ['ч', 'ch', 'Ч', 'CH'],  # Цифра -> буквы
            'ч': ['4', 'ch', 'Ч', 'CH'],  # Буква -> цифра и варианты
            'ch': ['4', 'ч', 'Ч', 'CH'],  # Латинский вариант -> цифра и кириллица
            '3': ['з', 'z', 'З', 'Z'],
            'з': ['3', 'z', 'З', 'Z'],
            'z': ['3', 'з', 'З', 'Z'],
            '0': ['о', 'o', 'О', 'O'],
            'о': ['0', 'o', 'О', 'O'],
            'o': ['0', 'о', 'О', 'O'],
            '1': ['и', 'i', 'И', 'I'],
            'и': ['1', 'i', 'И', 'I'],
            'i': ['1', 'и', 'И', 'I'],
            '7': ['т', 't', 'Т', 'T'],
            'т': ['7', 't', 'Т', 'T'],
            't': ['7', 'т', 'Т', 'T']
        }
        
    def transliterate(self, text: str, direction: str = 'ru') -> str:
        """
        Транслитерация текста
        
        Args:
            text: Исходный текст
            direction: Направление транслитерации ('ru' - в латиницу, 'en' - в кириллицу)
            
        Returns:
            Транслитерированный текст
        """
        try:
            if direction == 'ru':
                # Транслитерация из кириллицы в латиницу
                result = ''
                i = 0
                while i < len(text):
                    char = text[i]
                    if char in self.cyrillic_to_latin:
                        result += self.cyrillic_to_latin[char]
                    else:
                        result += char
                    i += 1
                return result
            else:
                # Транслитерация из латиницы в кириллицу
                result = ''
                i = 0
                while i < len(text):
                    # Проверяем двухбуквенные комбинации
                    if i + 1 < len(text):
                        two_chars = text[i:i+2].lower()
                        if two_chars in self.latin_to_cyrillic:
                            result += self.latin_to_cyrillic[two_chars]
                            i += 2
                            continue
                    
                    # Проверяем одиночные символы
                    char = text[i]
                    if char in self.latin_to_cyrillic:
                        result += self.latin_to_cyrillic[char]
                    else:
                        result += char
                    i += 1
                return result
                
        except Exception as e:
            self.logger.error(f"Ошибка при транслитерации: {str(e)}")
            return text
            
    def generate_variants(self, text: str) -> List[str]:
        """
        Генерация вариантов транслитерации
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов транслитерации
        """
        try:
            variants: Set[str] = set()
            
            # Добавляем оригинальный текст
            variants.add(text)
            
            # Добавляем транслитерированные варианты
            variants.add(self.transliterate(text, 'ru'))
            variants.add(self.transliterate(text, 'en'))
            
            # Добавляем варианты с заменой цифр и букв
            for i in range(len(text)):
                char = text[i].lower()
                if char in self.digit_replacements:
                    for replacement in self.digit_replacements[char]:
                        # Создаем новый вариант с заменой символа
                        new_text = text[:i] + replacement + text[i+1:]
                        variants.add(new_text)
                        
                        # Добавляем транслитерированные варианты с заменой
                        variants.add(self.transliterate(new_text, 'ru'))
                        variants.add(self.transliterate(new_text, 'en'))
            
            # Добавляем варианты с использованием unidecode
            variants.add(unidecode(text))
            
            # Удаляем пустые строки и возвращаем список
            return [v for v in variants if v.strip()]
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации вариантов: {str(e)}")
            return [text] 