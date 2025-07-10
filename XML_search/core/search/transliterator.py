"""
Класс для транслитерации поисковых запросов
"""

from typing import List, Set
import logging
from XML_search.enhanced.transliterator import Transliterator

class SearchTransliterator(Transliterator):
    """Прокси-класс транслитерации для поиска, использующий улучшенную реализацию"""
    
    def __init__(self):
        """
        Инициализация транслитератора
        
        Использует расширенную версию транслитератора из enhanced
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    def generate_variants(self, text: str) -> List[str]:
        """
        Генерация вариантов поискового запроса.
        Для сохранения обратной совместимости возвращает List[str].
        Внутри вызывает generate_prioritized_variants и извлекает строки.
        """
        # Используем новую реализацию из базового класса (enhanced.Transliterator)
        prioritized_variants_tuples = super().generate_prioritized_variants(text)
        # Извлекаем только строки вариантов, отбрасывая приоритеты
        variants_list = [variant_tuple[0] for variant_tuple in prioritized_variants_tuples]
        # Возвращаем уникальные варианты, сохраняя порядок (примерно)
        # Для более строгого сохранения порядка, если generate_prioritized_variants его гарантирует для одинаковых приоритетов,
        # можно использовать dict.fromkeys() для уникальности и затем list()
        return list(dict.fromkeys(variants_list)) 