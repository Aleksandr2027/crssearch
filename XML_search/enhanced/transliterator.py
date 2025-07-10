from typing import List, Set, Dict, Tuple
import re
from unidecode import unidecode
import logging
from functools import lru_cache

class Transliterator:
    """Модернизированный класс для транслитерации текста с улучшенной производительностью"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Предкомпилированные регулярные выражения для UTM паттернов (для производительности)
        self.utm_pattern1 = re.compile(r'(utm|гем|геь|UTM|ГЕМ|ГЕЬ)\s*(zone|зона|ящту|ZONE|ЗОНА|ЯЩТУ)?\s*(\d+)([NS]?)', re.IGNORECASE)
        self.utm_pattern2 = re.compile(r'(utm|гем|геь|UTM|ГЕМ|ГЕЬ)(\d+)([NS]?)', re.IGNORECASE)
        
        # Паттерны для быстрого определения типа системы координат
        self.system_patterns = {
            'MSK': re.compile(r'^(msk|мск|ьыл)', re.IGNORECASE),
            'GSK': re.compile(r'^(gsk|гск|гыл)', re.IGNORECASE),
            'SK': re.compile(r'^(sk\d+|ск\d+|ыл\d+)', re.IGNORECASE),
            'USK': re.compile(r'^(usk|уск)', re.IGNORECASE),
            'USL': re.compile(r'^(usl|усл)', re.IGNORECASE),
            'UTM': re.compile(r'^(utm|утм|гем|геь)', re.IGNORECASE)
        }
        
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
            't': ['7', 'т', 'Т', 'T'],
            # Дополнительные варианты для обозначения зон
            'p': ['з', 'р', 'З', 'Р'],  # p может быть з или р
            'P': ['з', 'р', 'З', 'Р'],  # P может быть з или р
            'р': ['p', 'з', 'Р', 'З'],  # р может быть p или з
            'Р': ['p', 'з', 'р', 'З'],   # Р может быть p или з
            # НОВОЕ: Добавляем букву "я" как индикатор зоны (проблема из скриншота 5)
            'я': ['z', 'з', 'Z', 'З'],   # "я" может использоваться вместо z/з
            'Я': ['Z', 'З', 'z', 'з']    # "Я" может использоваться вместо Z/З
        }
        
        # МОДЕРНИЗИРОВАННЫЕ сокращения для систем координат
        self.coordinate_abbreviations = {
            # === ОСНОВНЫЕ СИСТЕМЫ КООРДИНАТ ===
            # MSK системы
            'msk': ['мск', 'МСК'],
            'vcr': ['мск', 'МСК'],  # Популярная ошибка ввода
            'мск': ['msk', 'MSK'],
            
            # GSK системы  
            'gsk': ['гск', 'ГСК'],
            'gsk11': ['гск11', 'ГСК11'],
            'gsk2011': ['гск2011', 'ГСК2011'],
            'гск': ['gsk', 'GSK'],
            'гск11': ['gsk11', 'GSK11'],
            'гск2011': ['gsk2011', 'GSK2011'],
            
            # SK системы
            'sk': ['ск', 'СК'],
            'sk42': ['ск42', 'СК42'],
            'sk95': ['ск95', 'СК95'],
            'sk63': ['ск63', 'СК63'],
            'ск': ['sk', 'SK'],
            'ск42': ['sk42', 'SK42'],
            'ск95': ['sk95', 'SK95'],
            'ск63': ['sk63', 'SK63'],
            
            # === НОВЫЕ USK/USL СИСТЕМЫ ===
            'usk': ['уск', 'УСК'],
            'usl': ['усл', 'УСЛ'],
            'уск': ['usk', 'USK'],
            'усл': ['usl', 'USL'],
            
            # UTM системы
            'utm': ['утм', 'УТМ'],
            'утм': ['utm', 'UTM'],
            
            # Зонные обозначения
            'zone': ['зона', 'ЗОНА', 'з'],
            'зона': ['zone', 'ZONE', 'z'],
            'з': ['z', 'zone'],
            
            # === ГЕОГРАФИЧЕСКИЕ СОКРАЩЕНИЯ ===
            'g_': ['г_', 'город_', 'г.', 'city_'],
            'г_': ['g_', 'город_', 'city_'],
            'p_': ['п_', 'поселок_', 'п.', 'town_'],
            'п_': ['p_', 'поселок_', 'town_'],
            's_': ['с_', 'село_', 'с.', 'village_'],
            'с_': ['s_', 'село_', 'village_'],
            'd_': ['д_', 'деревня_', 'д.', 'hamlet_'],
            'д_': ['d_', 'деревня_', 'hamlet_'],
            'r-n': ['р-н', 'район', 'region'],
            'р-н': ['r-n', 'район', 'region'],
            'oblast': ['область', 'обл', 'region'],
            'область': ['oblast', 'region'],
            'krai': ['край', 'territory'],
            'край': ['krai', 'territory'],
            
            # === НЕПРАВИЛЬНАЯ РАСКЛАДКА КЛАВИАТУРЫ ===
            # MSK варианты
            'ьыл': ['мск', 'МСК', 'msk', 'MSK'],  # ЬЫЛ при попытке набрать MSK на русской раскладке
            'ЬЫЛ': ['мск', 'МСК', 'msk', 'MSK'],
            'мыл': ['vcr', 'VCR', 'мск', 'МСК'],  # МЫЛ при попытке набрать VCR на русской раскладке
            'МЫЛ': ['vcr', 'VCR', 'мск', 'МСК'],
            
            # GSK варианты
            'гыл': ['gsk', 'GSK', 'гск', 'ГСК'],  # ГЫЛ при попытке набрать GSK на русской раскладке
            'ГЫЛ': ['gsk', 'GSK', 'гск', 'ГСК'],
            'гыл11': ['gsk11', 'GSK11', 'гск11', 'ГСК11'],
            'ГЫЛ11': ['gsk11', 'GSK11', 'гск11', 'ГСК11'],
            'гыл2011': ['gsk2011', 'GSK2011', 'гск2011', 'ГСК2011'],
            'ГЫЛ2011': ['gsk2011', 'GSK2011', 'гск2011', 'ГСК2011'],
            
            # SK варианты
            'ыл': ['sk', 'SK', 'ск', 'СК'],  # ЫЛ при попытке набрать SK на русской раскладке
            'ЫЛ': ['sk', 'SK', 'ск', 'СК'],
            'ыл42': ['sk42', 'SK42', 'ск42', 'СК42'],
            'ЫЛ42': ['sk42', 'SK42', 'ск42', 'СК42'],
            'ыл95': ['sk95', 'SK95', 'ск95', 'СК95'],
            'ЫЛ95': ['sk95', 'SK95', 'ск95', 'СК95'],
            'ыл63': ['sk63', 'SK63', 'ск63', 'СК63'],
            'ЫЛ63': ['sk63', 'SK63', 'ск63', 'СК63'],
            
            # UTM варианты
            'гем': ['utm', 'UTM', 'утм', 'УТМ'],  # ГЕМ при попытке набрать UTM на русской раскладке
            'ГЕМ': ['utm', 'UTM', 'утм', 'УТМ'],
            'геь': ['utm', 'UTM', 'утм', 'УТМ'],  # ГЕЬ при попытке набрать UTM на русской раскладке
            'ГЕЬ': ['utm', 'UTM', 'утм', 'УТМ'],
            
            # Zone варианты
            'ящту': ['zone', 'ZONE', 'зона', 'ЗОНА'],  # ЯЩТУ при попытке набрать ZONE на русской раскладке
            'ЯЩТУ': ['zone', 'ZONE', 'зона', 'ЗОНА'],
            'ящт': ['zon', 'ZON', 'зон', 'ЗОН'],      # ЯЩТ при попытке набрать ZON на русской раскладке
            'ЯЩТ': ['zon', 'ZON', 'зон', 'ЗОН'],
            'ящ': ['zo', 'ZO', 'зо', 'ЗО'],           # ЯЩ при попытке набрать ZO на русской раскладке
            'ЯЩ': ['zo', 'ZO', 'зо', 'ЗО'],
            
            # НОВОЕ: Улучшенная обработка "яшту" (проблема из скриншота 2)
            'яшту': ['zone', 'ZONE', 'зона', 'ЗОНА'],   # ЯШТУ - опечатка в ЯЩТУ при попытке набрать ZONE 
            'ЯШТУ': ['zone', 'ZONE', 'зона', 'ЗОНА'],
            
            # Прочие системы
            'pz': ['пз', 'ПЗ'],
            'пз': ['pz', 'PZ'],
            'mggt': ['мггт', 'МГГТ'],
            'мггт': ['mggt', 'MGGT']
        }
        
        # Зонные паттерны для улучшенной обработки
        self.zone_patterns = {
            'z': ['з', 'zone', 'зона', 'я'],       # НОВОЕ: добавлен вариант "я"
            'з': ['z', 'zone', 'зона', 'я'],       # НОВОЕ: добавлен вариант "я"
            'zone': ['з', 'z', 'зона', 'я'],       # НОВОЕ: добавлен вариант "я"
            'зона': ['з', 'z', 'zone', 'я'],       # НОВОЕ: добавлен вариант "я"
            'я': ['з', 'z', 'zone', 'зона']        # НОВОЕ: добавлен зонный паттерн для "я"
        }
        
        # Кэш для часто используемых вариантов
        self._cache = {}
        self._cache_size_limit = 1000
    
    @lru_cache(maxsize=500)
    def detect_system_type(self, text: str) -> str:
        """
        Быстрое определение типа системы координат
        
        Args:
            text: Исходный текст
            
        Returns:
            Тип системы координат
        """
        text_lower = text.lower()
        
        for system_type, pattern in self.system_patterns.items():
            if pattern.match(text_lower):
                return system_type
                
        return 'UNKNOWN'
        
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
            
    def process_separators(self, text: str) -> List[str]:
        """
        Обработка разделителей (подчеркивания, дефисы, точки)
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов с разными разделителями
        """
        variants = {text}
        
        # Замена подчеркиваний
        if '_' in text:
            variants.add(text.replace('_', ' '))
            variants.add(text.replace('_', '-'))
            variants.add(text.replace('_', ''))
        
        # Замена дефисов
        if '-' in text:
            variants.add(text.replace('-', '_'))
            variants.add(text.replace('-', ' '))
            variants.add(text.replace('-', ''))
        
        # Замена пробелов
        if ' ' in text:
            variants.add(text.replace(' ', '_'))
            variants.add(text.replace(' ', '-'))
            variants.add(text.replace(' ', ''))
        
        return list(variants)
    
    def process_zone_patterns(self, text: str) -> List[str]:
        """
        Обработка зонных паттернов (z1, з2, zone3, etc.)
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов с разными зонными обозначениями
        """
        variants = set()
        
        # Паттерны для зон с цифрами
        zone_pattern = re.compile(r'(z|з|zone|зона|я|яшту|ящту|ящт)(\d+(?:\.\d+)?)', re.IGNORECASE)  # НОВОЕ: добавлены "я", "яшту", "ящт"
        
        for match in zone_pattern.finditer(text):
            zone_prefix, zone_number = match.groups()
            start, end = match.span()
            
            # Генерируем варианты замены зонного префикса
            for original_prefix, replacements in self.zone_patterns.items():
                if zone_prefix.lower() == original_prefix:
                    for replacement in replacements:
                        new_text = text[:start] + replacement + zone_number + text[end:]
                        variants.add(new_text)
                        # Также добавляем варианты с разным регистром
                        variants.add(new_text.upper())
                        variants.add(new_text.lower())
        
        # УЛУЧШЕНО: Обработка случаев, когда "я" идет сразу после числового индекса системы координат (42я)
        # Изменяем регулярное выражение для обработки случаев с цифрами после "я"
        number_ya_pattern = re.compile(r'(\d+)(я)(\d*)', re.IGNORECASE)
        
        for match in number_ya_pattern.finditer(text):
            number, ya_marker, zone_suffix = match.groups()
            start_of_match, end_of_match = match.span()

            original_prefix = text[:start_of_match]
            original_suffix = text[end_of_match:]

            # Базовые префиксы для генерации (с учетом возможной замены 'ьыл')
            candidate_prefixes = []
            if original_prefix.lower() == 'ьыл':
                candidate_prefixes.extend(['мск', 'МСК', 'msk', 'MSK'])
            else:
                candidate_prefixes.append(original_prefix) # Используем оригинальный префикс, если это не 'ьыл'
            
            if not candidate_prefixes and not original_prefix : # Случай когда нет префикса вообще (например, просто "22я1")
                 candidate_prefixes.extend(['мск', 'МСК', 'msk', 'MSK']) # По умолчанию предполагаем МСК/MSK


            for prefix_val in candidate_prefixes:
                # Определяем маркеры зон в зависимости от регистра префикса
                zone_markers_latin = ['z', 'Z']
                zone_markers_cyrillic = ['з', 'З']
                
                if prefix_val.islower():
                    chosen_latin_marker = zone_markers_latin[0]
                    chosen_cyrillic_marker = zone_markers_cyrillic[0]
                else:
                    chosen_latin_marker = zone_markers_latin[1]
                    chosen_cyrillic_marker = zone_markers_cyrillic[1]

                # Латинские варианты
                variants.add(prefix_val + number + chosen_latin_marker + zone_suffix + original_suffix)
                variants.add((prefix_val + number + chosen_latin_marker + zone_suffix + original_suffix).lower())
                variants.add((prefix_val + number + chosen_latin_marker + zone_suffix + original_suffix).upper())

                # Кириллические варианты (если префикс кириллический или стал кириллическим после замены)
                if any(c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ' for c in prefix_val):
                    variants.add(prefix_val + number + chosen_cyrillic_marker + zone_suffix + original_suffix)
                    variants.add((prefix_val + number + chosen_cyrillic_marker + zone_suffix + original_suffix).lower())
                    variants.add((prefix_val + number + chosen_cyrillic_marker + zone_suffix + original_suffix).upper())
        
        return list(variants)
    
    def process_msk_variants(self, text: str) -> List[str]:
        """
        Специализированная обработка MSK систем
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов для MSK систем
        """
        variants = set()
        variants.add(text)
        
        # Базовые транслитерации
        variants.add(self.transliterate(text, 'ru'))
        variants.add(self.transliterate(text, 'en'))
        
        # Обработка зонных паттернов
        variants.update(self.process_zone_patterns(text))
        
        # НОВОЕ: Специальная обработка для "ьыл" + цифры (без буквы "я")
        text_lower = text.lower()
        if text_lower.startswith('ьыл'):
            # Получаем суффикс после "ьыл"
            suffix = text[3:]
            
            # Если суффикс состоит только из цифр (без буквы "я"), добавляем варианты с зонными маркерами
            if suffix.isdigit():
                for prefix in ['мск', 'МСК', 'msk', 'MSK']:
                    # Добавляем просто с префиксом (базовый вариант)
                    variants.add(prefix + suffix)
                    
                    # Добавляем с зонными маркерами между префиксом и числом
                    for marker in ['з', 'З', 'z', 'Z']:
                        variants.add(prefix + marker + suffix)
        
        # Замены цифр на буквы для MSK
        variants.update(self._apply_digit_replacements(text, max_replacements=2))
        
        return list(variants)
    
    def process_gsk_variants(self, text: str) -> List[str]:
        """
        Специализированная обработка GSK систем
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов для GSK систем
        """
        variants = set()
        variants.add(text)
        
        # Базовые транслитерации
        latin_variant = self.transliterate(text, 'ru')
        cyrillic_variant = self.transliterate(text, 'en')
        variants.add(latin_variant)
        variants.add(cyrillic_variant)
        
        # ИСПРАВЛЕНИЕ: Добавляем ключевые варианты с правильным регистром
        if latin_variant != text:  # Если была транслитерация
            # Добавляем варианты с разным регистром для латинского варианта
            variants.add(latin_variant.upper())
            variants.add(latin_variant.lower())
            variants.add(latin_variant.capitalize())
            variants.add(latin_variant.title())
            
            # Специальная обработка для GSK11: GSK11z15 формат
            if 'gsk11' in latin_variant.lower():
                # Создаем правильный GSK11z## формат
                import re
                pattern = re.compile(r'(gsk11)(.+)', re.IGNORECASE)
                match = pattern.match(latin_variant)
                if match:
                    gsk_part, rest_part = match.groups()
                    # Генерируем варианты GSK11 + rest
                    variants.add(f"GSK11{rest_part}")
                    variants.add(f"GSK11{rest_part.lower()}")
                    variants.add(f"GSK11{rest_part.upper()}")
                    variants.add(f"gsk11{rest_part}")
                    variants.add(f"gsk11{rest_part.lower()}")
        
        # Обработка зонных паттернов
        variants.update(self.process_zone_patterns(text))
        
        # Специальные варианты для GSK11
        if 'gsk11' in text.lower() or 'гск11' in text.lower():
            variants.update(['GSK11', 'gsk11', 'ГСК11', 'гск11'])
        
        # Замены цифр на буквы (ограниченно для GSK)
        variants.update(self._apply_digit_replacements(text, max_replacements=1))
        
        return list(variants)
    
    def process_sk_variants(self, text: str) -> List[str]:
        """
        Специализированная обработка SK систем (SK42, SK95, SK63)
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов для SK систем
        """
        variants = set()
        variants.add(text)
        
        # Базовые транслитерации
        variants.add(self.transliterate(text, 'ru'))
        variants.add(self.transliterate(text, 'en'))
        
        # Обработка зонных паттернов
        variants.update(self.process_zone_patterns(text))
        
        # Специальные варианты для SK42, SK95, SK63
        text_lower = text.lower()
        if any(sk_type in text_lower for sk_type in ['sk42', 'sk95', 'sk63']):
            # Добавляем варианты с точками (SK42z1.3)
            if 'z' in text_lower:
                dot_variant = re.sub(r'z(\d+)', r'z\1.3', text, flags=re.IGNORECASE)
                variants.add(dot_variant)
        
        # Замены цифр на буквы
        variants.update(self._apply_digit_replacements(text, max_replacements=2))
        
        return list(variants)
    
    def process_usk_usl_variants(self, text: str) -> List[str]:
        """
        Специализированная обработка USK/USL систем
        
        Args:
            text: Исходный текст
            
        Returns:
            Список вариантов для USK/USL систем
        """
        variants = set()
        variants.add(text)
        
        # Базовые транслитерации
        variants.add(self.transliterate(text, 'ru'))
        variants.add(self.transliterate(text, 'en'))
        
        # Обработка разделителей (очень важно для USK/USL)
        variants.update(self.process_separators(text))
        
        # Обработка географических сокращений
        for separator_variant in self.process_separators(text):
            variants.update(self._apply_geographic_abbreviations(separator_variant))
        
        # Замены цифр на буквы (ограниченно)
        variants.update(self._apply_digit_replacements(text, max_replacements=1))
        
        return list(variants)
    
    def _apply_digit_replacements(self, text: str, max_replacements: int = 2) -> Set[str]:
        """
        Применение замен цифр на буквы с ограничением количества замен
        
        Args:
            text: Исходный текст
            max_replacements: Максимальное количество одновременных замен
            
        Returns:
            Множество вариантов с заменами
        """
        variants = set()
        
        def apply_replacements(current_text: str, position: int = 0, replacements_made: int = 0) -> None:
            if position >= len(current_text) or replacements_made >= max_replacements:
                variants.add(current_text)
                return
            
            char = current_text[position].lower()
            
            if char in self.digit_replacements and replacements_made < max_replacements:
                # Применяем замену
                for replacement in self.digit_replacements[char][:2]:  # Ограничиваем количество вариантов
                    # Сохраняем регистр
                    if current_text[position].isupper():
                        replacement = replacement.upper()
                    elif current_text[position].islower():
                        replacement = replacement.lower()
                    
                    new_text = current_text[:position] + replacement + current_text[position+1:]
                    apply_replacements(new_text, position + len(replacement), replacements_made + 1)
            
            # Продолжаем без замены
            apply_replacements(current_text, position + 1, replacements_made)
        
        apply_replacements(text)
        return variants
    
    def _apply_geographic_abbreviations(self, text: str) -> Set[str]:
        """
        Применение географических сокращений
        
        Args:
            text: Исходный текст
            
        Returns:
            Множество вариантов с географическими сокращениями
        """
        variants = {text}
        text_lower = text.lower()
        
        # Ищем географические сокращения
        for abbrev, replacements in self.coordinate_abbreviations.items():
            if abbrev in text_lower and any(geo in abbrev for geo in ['g_', 'p_', 's_', 'd_', 'r-n', 'oblast', 'krai']):
                for replacement in replacements:
                    new_text = text_lower.replace(abbrev, replacement.lower())
                    variants.add(new_text)
                    variants.add(new_text.upper())
                    variants.add(new_text.capitalize())
        
        return variants
    
    @lru_cache(maxsize=1000)
    def generate_prioritized_variants(self, query: str) -> List[Tuple[str, int]]:
        """
        Генерирует варианты с уровнями приоритета:
        0: Оригинал и его регистровые вариации.
        1: Ошибки раскладки клавиатуры для вариантов приоритета 0.
        2: Прямая транслитерация (Латиница <-> Кириллица) для вариантов приоритета 0 и 1.
           Также включает специализированные варианты для MSK, GSK, SK и т.д.
        3: Ошибки раскладки для вариантов приоритета 2.
        4: Более широкая/общая транслитерация (unidecode) и обработка разделителей.
        """
        if not query or not query.strip():
            return []

        all_variants_map: Dict[str, int] = {} # variant_str -> min_priority_level

        def add_variant(variant_str: str, priority_level: int):
            if not variant_str or not variant_str.strip(): return
            # Добавляем или обновляем, если новый приоритет выше (меньше число)
            if variant_str not in all_variants_map or priority_level < all_variants_map[variant_str]:
                all_variants_map[variant_str] = priority_level

        # Уровень 0: Оригинал и регистровые вариации
        base_p0_variants = self._get_case_variations(query)
        for v in base_p0_variants:
            add_variant(v, 0)
        
        # Варианты, для которых будем генерить следующие уровни
        variants_for_level_1 = list(all_variants_map.keys()) # Все с приоритетом 0

        # Уровень 1: Ошибки раскладки для вариантов приоритета 0
        for p0_var in variants_for_level_1:
            kb_vars = self._apply_keyboard_layout_swap(p0_var)
            for v_kb in kb_vars:
                for vc in self._get_case_variations(v_kb): # Также учитываем регистр для ошибок раскладки
                    add_variant(vc, 1)
        
        variants_for_level_2 = list(all_variants_map.keys()) # Все с приоритетами 0, 1

        # Уровень 2: Прямая транслитерация и специализированные обработчики
        system_type = self.detect_system_type(query) # Определяем тип по оригинальному запросу
        
        for p_prev_var in variants_for_level_2: # Для всех вариантов с приоритетом 0 и 1
            translit_vars = self._apply_direct_transliteration(p_prev_var)
            for v_translit in translit_vars:
                for vc in self._get_case_variations(v_translit):
                    add_variant(vc, 2)

            # Специализированная обработка по типу системы (применяем к вариантам с предыдущих уровней)
            # Это позволит, например, для "ьыл95z" (ошибка раскладки от msk95z) применить MSK-специфичные правила
            current_system_type = self.detect_system_type(p_prev_var) # Переопределяем тип для текущего варианта
            
            special_handler_results = set()
            if current_system_type == 'MSK':
                special_handler_results.update(self.process_msk_variants(p_prev_var))
            elif current_system_type == 'GSK':
                special_handler_results.update(self.process_gsk_variants(p_prev_var))
            elif current_system_type == 'SK':
                special_handler_results.update(self.process_sk_variants(p_prev_var))
            elif current_system_type == 'USK' or current_system_type == 'USL':
                special_handler_results.update(self.process_usk_usl_variants(p_prev_var))
            elif current_system_type == 'UTM':
                special_handler_results.update(self.process_utm_patterns(p_prev_var))
            
            for v_special in special_handler_results:
                 for vc_special in self._get_case_variations(v_special): # И для них тоже регистр
                    add_variant(vc_special, 2) # Специализированные варианты тоже на уровне 2

        variants_for_level_3 = list(all_variants_map.keys()) # Все с приоритетами 0, 1, 2

        # Уровень 3: Ошибки раскладки для транслитерированных/специализированных вариантов (с уровня 2)
        variants_from_p2 = [v for v, p in all_variants_map.items() if p == 2]
        for p2_var in variants_from_p2:
            kb_vars_on_translit = self._apply_keyboard_layout_swap(p2_var)
            for v_kb_translit in kb_vars_on_translit:
                for vc in self._get_case_variations(v_kb_translit):
                    add_variant(vc, 3)
        
        # Изменяем выборку вариантов для уровня 4
        variants_for_level_4_processing = [v for v, p in all_variants_map.items() if p <= 1] # Только с приоритетами 0, 1

        # Уровень 4: Более общая транслитерация (unidecode), обработка разделителей, аббревиатур
        # Используем variants_for_level_4_processing вместо полного списка all_variants_map.keys()
        for p_prev_var in variants_for_level_4_processing:
            # Unidecode (для более грубой транслитерации)
            # unidecode(text) всегда возвращает латиницу.
            # Если p_prev_var содержит кириллицу, unidecode его транслитерирует в латиницу.
            # Если p_prev_var уже латиница, unidecode может его немного изменить (убрать диакритические знаки).
            ud_variant = unidecode(p_prev_var)
            if ud_variant != p_prev_var:
                 for vc_ud in self._get_case_variations(ud_variant):
                    add_variant(vc_ud, 4)
            
            # Обработка разделителей
            sep_variants = self.process_separators(p_prev_var)
            for v_sep in sep_variants:
                if v_sep != p_prev_var: # Добавляем только если есть изменения
                    for vc_sep in self._get_case_variations(v_sep):
                        add_variant(vc_sep, 4)
            
            # Применение координатных аббревиатур (может быть избыточным, если уже применялось)
            # Но здесь может поймать комбинации, которые не были обработаны ранее.
            abbr_variants = self._apply_coordinate_abbreviations(p_prev_var)
            for v_abbr in abbr_variants:
                if v_abbr != p_prev_var:
                     for vc_abbr in self._get_case_variations(v_abbr):
                        add_variant(vc_abbr, 4)


        # Собираем отсортированный по приоритету, затем по строке (для стабильности)
        # Преобразуем карту обратно в список кортежей
        final_prioritized_list = sorted(all_variants_map.items(), key=lambda item: (item[1], item[0]))
        
        self.logger.debug(f"Сгенерированные варианты для '{query}': {final_prioritized_list[:20]}... (всего {len(final_prioritized_list)})") # Логируем только часть
        
        # Ограничиваем количество возвращаемых вариантов, если нужно
        return final_prioritized_list[:15] # УМЕНЬШЕН ЛИМИТ до 15
    
    def _get_case_variations(self, text: str) -> List[str]:
        variations = {text, text.lower(), text.upper()}
        if len(text) > 1: # Для title() и capitalize()
            variations.add(text.title()) 
            variations.add(text.capitalize())
        return list(variations)

    def _apply_keyboard_layout_swap(self, text: str) -> List[str]:
        # Заглушка - должна быть реальная реализация на основе словарей раскладок
        # Пример: ru_to_en_layout = {'й': 'q', ...}; en_to_ru_layout = {'q': 'й', ...}
        # self.ru_to_en_layout = {...} ; self.en_to_ru_layout = {...}
        # Пока просто возвращаем пустой список, чтобы не генерировать неверные данные
        swapped_variants = [] # ВРЕМЕННО ВОЗВРАЩАЕМ ПУСТОЙ СПИСОК
        # Здесь должна быть логика, использующая self.ru_to_en_layout и self.en_to_ru_layout
        # Например:
        # if all(c.lower() in self.en_to_ru_layout or not c.isalpha() for c in text):
        #     swapped_variants.append("".join(self.en_to_ru_layout.get(c.lower(), c.lower()).upper() if c.isupper() else self.en_to_ru_layout.get(c.lower(), c.lower()) for c in text))
        # if all(c.lower() in self.ru_to_en_layout or not c.isalpha() for c in text):
        #    swapped_variants.append("".join(self.ru_to_en_layout.get(c.lower(), c.lower()).upper() if c.isupper() else self.ru_to_en_layout.get(c.lower(), c.lower()) for c in text))
        
        # Эта заглушка НЕ БУДЕТ работать корректно без реальных словарей раскладок.
        # Для демонстрации оставим её такой.
        # В реальном проекте здесь должна быть полная карта символов.
        # Пример очень упрощенной замены для демонстрации структуры (неполный и некорректный для реального использования):
        if 'ыл' in text.lower(): # Очень грубый пример
            swapped_variants.append(text.lower().replace('ыл', 'sk'))
        if 'мск' in text.lower():
            swapped_variants.append(text.lower().replace('мск', 'vcr')) # просто для примера обратной логики

        return list(set(swapped_variants) - {text})


    def _apply_direct_transliteration(self, text: str) -> List[str]:
        translit_variants = set()
        # Кириллица -> Латиница
        if re.search(r'[а-яА-Я]', text):
            res_ru_en = "".join(self.cyrillic_to_latin.get(char, char) for char in text)
            if res_ru_en != text: translit_variants.add(res_ru_en)
        
        # Латиница -> Кириллица
        if re.search(r'[a-zA-Z]', text):
            # Сначала пытаемся обработать сложные замены типа 'sch', 'zh' и т.д.
            # Это упрощенный подход, для более точной транслитерации может потребоваться более сложный алгоритм
            # или использование готовой библиотеки транслитерации, если unidecode не подходит.
            # Текущий self.transliterate уже пытается это делать.
            res_en_ru = self.transliterate(text, direction='en')
            if res_en_ru != text: translit_variants.add(res_en_ru)
            
            # Дополнительно, более простой вариант с unidecode для латиницы в кириллицу (может быть неточным)
            # decoded_to_cyrillic = unidecode(text) # unidecode(text) обычно дает латиницу.
            # Здесь нужна логика преобразования латиницы в кириллицу, если self.transliterate недостаточно.
            # Пока оставим как есть.

        return list(translit_variants)

    @lru_cache(maxsize=500)
    def _generate_legacy_variants(self, text: str) -> List[str]: # Переименованный старый generate_variants
        """
        ОПТИМИЗИРОВАННАЯ генерация вариантов транслитерации (старая версия)
        ... (остальной код старого метода generate_variants без изменений) ...
        """
        if not text or not text.strip():
            return []
        
        # Проверяем кэш
        cache_key = text.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            variants = set()
            
            # НОВОЕ: Предварительная обработка составных запросов с пробелами (типа "геь яшту")
            # Если в запросе есть пробел, обрабатываем каждую часть отдельно и затем комбинируем
            if ' ' in text:
                # Разбиваем на части по пробелам
                parts = text.split()
                if len(parts) == 2:  # Обрабатываем двухчастные запросы отдельно (например "геь яшту")
                    # Получаем варианты для первой и второй части
                    first_part_variants = self._generate_variants_for_part(parts[0])
                    second_part_variants = self._generate_variants_for_part(parts[1])
                    
                    # Создаем комбинации вариантов
                    for first in first_part_variants:
                        for second in second_part_variants:
                            # Соединяем варианты с пробелом и без
                            variants.add(f"{first} {second}")
                            variants.add(f"{first}{second}")
            
            # 1. Добавляем оригинальный текст и простые варианты регистра
            priority_variants = [
                text,                    # Оригинальный текст
                text.upper(),           # Верхний регистр
                text.lower(),           # Нижний регистр
                text.capitalize(),      # Первая буква заглавная
                text.title()            # Каждое слово с заглавной
            ]
            
            # Убираем дубликаты из приоритетных вариантов
            priority_variants = list(dict.fromkeys(priority_variants))
            variants.update(priority_variants)
            
            # 2. Быстрое определение типа системы
            system_type = self.detect_system_type(text)
            
            # ИСПРАВЛЕНИЕ: Сохраняем специализированные варианты отдельно для приоритета
            specialized_variants = set()
            
            # 3. Специализированная обработка по типу системы
            if system_type == 'MSK':
                specialized_variants.update(self.process_msk_variants(text))
            elif system_type == 'GSK':
                specialized_variants.update(self.process_gsk_variants(text))
            elif system_type == 'SK':
                specialized_variants.update(self.process_sk_variants(text))
            elif system_type == 'USK' or system_type == 'USL':
                specialized_variants.update(self.process_usk_usl_variants(text))
            elif system_type == 'UTM':
                # UTM обрабатывается отдельным методом
                specialized_variants.update(self.process_utm_patterns(text))
            else:
                # Общая обработка для неопознанных систем
                specialized_variants.update(self._process_generic_variants(text))
            
            # Добавляем специализированные варианты к общему набору
            variants.update(specialized_variants)
            
            # 4. Применяем специальные сокращения для всех вариантов
            all_variants = set(variants)
            for variant in list(all_variants):
                variants.update(self._apply_coordinate_abbreviations(variant))
            
            # 5. Добавляем варианты с unidecode
            for variant in list(variants):
                variants.add(unidecode(variant))
            
            # 6. Очистка и финализация с УЛУЧШЕННЫМ приоритетом
            all_variants_list = [v for v in variants if v and v.strip()]
            
            # ИСПРАВЛЕНИЕ: Создаем улучшенную систему приоритетов
            result = []
            
            # Шаг 1: Добавляем приоритетные варианты (оригинальные)
            for variant in priority_variants:
                if variant and variant.strip() and variant not in result:
                    result.append(variant)
            
            # Шаг 2: Добавляем специализированные варианты с высоким приоритетом
            # Это гарантирует, что важные GSK/MSK/SK варианты попадут в результат
            specialized_clean = [v for v in specialized_variants if v and v.strip()]
            for variant in specialized_clean:
                if variant not in result:
                    result.append(variant)
                    # Ограничиваем специализированные варианты, чтобы не забить весь результат
                    if len(result) >= 30:  # Оставляем место для других вариантов
                        break
            
            # Шаг 3: Добавляем остальные варианты
            for variant in all_variants_list:
                if variant not in result:
                    result.append(variant)
                    # Ограничиваем общее количество результатов
                    if len(result) >= 50:
                        break
            
            # Кэшируем результат
            if len(self._cache) < self._cache_size_limit:
                self._cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации вариантов: {str(e)}")
            return [text]

    # НОВЫЙ МЕТОД: Обработка отдельных частей составных запросов
    def _generate_variants_for_part(self, part: str) -> Set[str]:
        """
        Генерация вариантов транслитерации для отдельной части составного запроса
        
        Args:
            part: Часть составного запроса
            
        Returns:
            Множество вариантов транслитерации
        """
        variants = set([part])
        
        # Добавляем базовые варианты из словаря сокращений
        part_lower = part.lower()
        if part_lower in self.coordinate_abbreviations:
            variants.update(self.coordinate_abbreviations[part_lower])
        
        # Транслитерация части
        variants.add(self.transliterate(part, 'ru'))
        variants.add(self.transliterate(part, 'en'))
        
        # Обработка неправильной раскладки клавиатуры
        if part_lower == 'яшту' or part_lower == 'ящту':
            variants.update(['zone', 'ZONE', 'зона', 'ЗОНА'])
        elif part_lower == 'ящт':
            variants.update(['zon', 'ZON', 'зон', 'ЗОН'])
        elif part_lower == 'ящ':
            variants.update(['zo', 'ZO', 'зо', 'ЗО'])
        elif part_lower == 'геь' or part_lower == 'гем':
            variants.update(['utm', 'UTM', 'утм', 'УТМ'])
        elif part_lower == 'я':
            variants.update(['z', 'Z', 'з', 'З'])
        
        return variants
    
    def _process_generic_variants(self, text: str) -> Set[str]:
        """
        Общая обработка для неопознанных систем координат
        
        Args:
            text: Исходный текст
            
        Returns:
            Множество базовых вариантов
        """
        variants = set()
        
        # Базовые транслитерации
        variants.add(self.transliterate(text, 'ru'))
        variants.add(self.transliterate(text, 'en'))
        
        # Обработка разделителей
        variants.update(self.process_separators(text))
        
        # Ограниченные замены цифр
        variants.update(self._apply_digit_replacements(text, max_replacements=1))
        
        return variants
    
    def _apply_coordinate_abbreviations(self, text: str) -> Set[str]:
        """
        Применение сокращений систем координат
        
        Args:
            text: Исходный текст
            
        Returns:
            Множество вариантов с сокращениями
        """
        variants = {text}
        text_lower = text.lower()
        text_upper = text.upper()
        
        for abbrev, replacements in self.coordinate_abbreviations.items():
            abbrev_lower = abbrev.lower()
            abbrev_upper = abbrev.upper()
            abbrev_cap = abbrev.capitalize()
            
            # Проверяем все возможные варианты входного текста
            for source_text, source_abbrev in [
                (text_lower, abbrev_lower),
                (text_upper, abbrev_upper), 
                (text, abbrev),
                (text, abbrev_cap)
            ]:
                if source_abbrev in source_text:
                    for replacement in replacements:
                        # Генерируем варианты с разными регистрами
                        new_text = source_text.replace(source_abbrev, replacement.lower())
                        variants.add(new_text)
                        variants.add(new_text.upper())
                        variants.add(new_text.capitalize())
                        
                        # Также добавляем вариант с сохранением регистра замены
                        if replacement.isupper():
                            variants.add(source_text.replace(source_abbrev, replacement.upper()))
                        elif replacement.islower():
                            variants.add(source_text.replace(source_abbrev, replacement.lower()))
                        else:
                            variants.add(source_text.replace(source_abbrev, replacement))
        
        return variants
            
    def process_utm_patterns(self, text: str) -> Set[str]:
        """
        Обработка UTM паттернов для преобразования пользовательского ввода в формат базы данных
        
        Args:
            text: Исходный текст
            
        Returns:
            Множество вариантов UTM форматов
        """
        utm_variants = set()
        
        try:
            # Паттерн 1: UTM zone 20, utm зона 20, гем ящту 20, UTM zone 20N
            for match in self.utm_pattern1.finditer(text):
                utm_part, zone_part, number, hemisphere = match.groups()
                hemisphere = hemisphere or ''
                
                # Нормализуем UTM часть
                utm_normalized = 'UTM'
                
                # Генерируем различные форматы
                formats = [
                    f'UTM +zone={number}{hemisphere}',
                    f'UTM zone {number}{hemisphere}',
                    f'UTM +zone={number}',
                    f'UTM zone {number}',
                    f'utm +zone={number}{hemisphere}',
                    f'utm zone {number}{hemisphere}',
                    f'utm +zone={number}',
                    f'utm zone {number}'
                ]
                
                # Если есть полушарие, добавляем варианты с противоположным полушарием
                if hemisphere:
                    opposite = 'S' if hemisphere.upper() == 'N' else 'N'
                    formats.extend([
                        f'UTM +zone={number}{opposite}',
                        f'UTM zone {number}{opposite}',
                        f'utm +zone={number}{opposite}',
                        f'utm zone {number}{opposite}'
                    ])
                else:
                    # Если полушарие не указано, добавляем варианты с N и S
                    for hem in ['N', 'S']:
                        formats.extend([
                            f'UTM +zone={number}{hem}',
                            f'UTM zone {number}{hem}',
                            f'utm +zone={number}{hem}',
                            f'utm zone {number}{hem}'
                        ])
                
                utm_variants.update(formats)
                
                # Заменяем найденный паттерн в оригинальном тексте
                for fmt in formats:
                    new_text = text[:match.start()] + fmt + text[match.end():]
                    utm_variants.add(new_text)
            
            # Паттерн 2: UTM20, UTM20N, гем20
            for match in self.utm_pattern2.finditer(text):
                utm_part, number, hemisphere = match.groups()
                hemisphere = hemisphere or ''
                
                # Генерируем форматы
                formats = [
                    f'UTM +zone={number}{hemisphere}',
                    f'UTM zone {number}{hemisphere}',
                    f'UTM +zone={number}',
                    f'UTM zone {number}',
                    f'UTM{number}{hemisphere}',
                    f'UTM{number}',
                    f'utm +zone={number}{hemisphere}',
                    f'utm zone {number}{hemisphere}',
                    f'utm +zone={number}',
                    f'utm zone {number}',
                    f'utm{number}{hemisphere}',
                    f'utm{number}'
                ]
                
                # Если есть полушарие, добавляем варианты с противоположным полушарием
                if hemisphere:
                    opposite = 'S' if hemisphere.upper() == 'N' else 'N'
                    formats.extend([
                        f'UTM +zone={number}{opposite}',
                        f'UTM zone {number}{opposite}',
                        f'UTM{number}{opposite}',
                        f'utm +zone={number}{opposite}',
                        f'utm zone {number}{opposite}',
                        f'utm{number}{opposite}'
                    ])
                else:
                    # Если полушарие не указано, добавляем варианты с N и S
                    for hem in ['N', 'S']:
                        formats.extend([
                            f'UTM +zone={number}{hem}',
                            f'UTM zone {number}{hem}',
                            f'UTM{number}{hem}',
                            f'utm +zone={number}{hem}',
                            f'utm zone {number}{hem}',
                            f'utm{number}{hem}'
                        ])
                
                utm_variants.update(formats)
                
                # Заменяем найденный паттерн в оригинальном тексте
                for fmt in formats:
                    new_text = text[:match.start()] + fmt + text[match.end():]
                    utm_variants.add(new_text)
                    
        except Exception as e:
            self.logger.error(f"Ошибка при обработке UTM паттернов: {str(e)}")
        
        return utm_variants