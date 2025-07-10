"""
Поисковый движок
"""

from typing import List, Dict, Any, Optional
from XML_search.enhanced.search.search_engine import EnhancedSearchEngine
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from .transliterator import SearchTransliterator

class SearchEngine(EnhancedSearchEngine):
    """
    Прокси-класс поискового движка, использующий улучшенную реализацию
    из enhanced модуля для обратной совместимости
    """
    
    def __init__(self, db_manager: DatabaseManager, metrics: Optional[MetricsManager] = None, logger: Optional[LogManager] = None):
        """
        Инициализация поискового движка
        
        Args:
            db_manager: Менеджер базы данных
            metrics: Коллектор метрик
            logger: Логгер
        """
        super().__init__(db_manager=db_manager, metrics=metrics, logger=logger)
        
        # Используем SearchTransliterator вместо базового Transliterator для обратной совместимости
        self.transliterator = SearchTransliterator()
        
    async def search(self, query: str, filters: Optional[Dict[str, bool]] = None, use_cache: bool = True, cache_ttl: int = 3600, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Выполнение поиска
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска
            use_cache: Использовать ли кэширование
            cache_ttl: Время жизни кэша в секундах
            limit: Максимальное количество результатов (параметр для EnhancedSearchEngine)
            
        Returns:
            Список результатов поиска
        """
        # Делегируем вызов улучшенной версии, передавая все параметры
        return await super().search(query=query, filters=filters, use_cache=use_cache, cache_ttl=cache_ttl, limit=limit) 