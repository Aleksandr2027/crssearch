"""
Утилиты для поиска
"""

from typing import List, Dict, Any
import logging
from XML_search.enhanced.search.search_utils import SearchUtils as EnhancedSearchUtils

class SearchUtils(EnhancedSearchUtils):
    """
    Прокси-класс утилит поиска, использующий улучшенную реализацию
    из enhanced модуля для обратной совместимости
    """
    
    def __init__(self):
        """
        Инициализация утилит поиска
        """
        super().__init__(logger=logging.getLogger(__name__))
    
    def apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, bool]) -> List[Dict[str, Any]]:
        """
        Применение фильтров к результатам поиска
        
        Args:
            results: Список результатов
            filters: Словарь фильтров
            
        Returns:
            Отфильтрованный список результатов
        """
        # Делегируем вызов улучшенной версии
        return super().apply_filters(results, filters)
        
    def fuzzy_search(self, search_term: str, target: str, threshold: float = 0.85) -> bool:
        """
        Нечеткий поиск с использованием расстояния Левенштейна
        
        Args:
            search_term: Поисковый запрос
            target: Целевая строка
            threshold: Порог схожести
            
        Returns:
            True если строки похожи, False в противном случае
        """
        # Делегируем вызов улучшенной версии
        return super().fuzzy_search(search_term, target, threshold) 