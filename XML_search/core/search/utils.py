"""
Утилиты для поиска
"""

from typing import List, Dict, Any
from Levenshtein import ratio

class SearchUtils:
    """Утилиты для поиска"""
    
    def apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, bool]) -> List[Dict[str, Any]]:
        """
        Применение фильтров к результатам поиска
        
        Args:
            results: Список результатов
            filters: Словарь фильтров
            
        Returns:
            Отфильтрованный список результатов
        """
        filtered_results = results.copy()
        
        if filters.get('region'):
            filtered_results = [r for r in filtered_results if self._is_region(r)]
            
        if filters.get('custom'):
            filtered_results = [r for r in filtered_results if self._is_custom(r)]
            
        if filters.get('active'):
            filtered_results = [r for r in filtered_results if not r.get('deprecated')]
            
        return filtered_results
        
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
        similarity = ratio(search_term.lower(), target.lower())
        return similarity >= threshold
        
    def _is_region(self, result: Dict[str, Any]) -> bool:
        """Проверка принадлежности к региональным СК"""
        return result.get('auth_name') == 'custom'
        
    def _is_custom(self, result: Dict[str, Any]) -> bool:
        """Проверка принадлежности к пользовательским СК"""
        return result.get('auth_name') == 'custom' and result.get('auth_srid', 0) >= 100000 