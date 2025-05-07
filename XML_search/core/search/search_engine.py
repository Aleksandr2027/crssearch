"""
Поисковый движок
"""

from typing import List, Dict, Any, Optional
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.db_context import get_db_manager
from XML_search.crs_search import CrsSearchBot
from XML_search.config import DBConfig
from XML_search.errors import DatabaseError
from .transliterator import SearchTransliterator
from .utils import SearchUtils

class SearchEngine:
    """Класс поискового движка"""
    
    def __init__(self, db_manager: DatabaseManager, metrics: Optional[MetricsManager] = None, logger: Optional[LogManager] = None):
        """
        Инициализация поискового движка
        
        Args:
            db_manager: Менеджер базы данных
            metrics: Коллектор метрик
            logger: Логгер
        """
        self.metrics = metrics or MetricsManager()
        self.logger = logger or LogManager().get_logger(__name__)
        self.db_manager = db_manager
        self.cache = CacheManager()
        self.transliterator = SearchTransliterator()
        self.utils = SearchUtils()
        self.search_processor = CrsSearchBot(db_manager=self.db_manager)
        
    async def search(self, query: str, filters: Optional[Dict[str, bool]] = None) -> List[Dict[str, Any]]:
        """
        Выполнение поиска
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска
            
        Returns:
            Список результатов поиска
        """
        try:
            # Проверяем кэш
            cache_key = f"search_{query}_{hash(str(filters))}"
            cached_results = self.cache.get(cache_key)
            if cached_results:
                self.metrics.increment('search_cache_hits')
                self.logger.info(f"Найдены кэшированные результаты для запроса: {query}")
                return cached_results

            # Генерируем варианты поискового запроса
            search_variants = self.transliterator.generate_variants(query)
            
            # Выполняем поиск
            with self.metrics.timing('search_execution_time'):
                results = await self.search_processor.search_coordinate_systems(search_variants)

            # Применяем фильтры
            if filters:
                results = self.utils.apply_filters(results, filters)
                for filter_name, is_active in filters.items():
                    if is_active:
                        self.metrics.increment(f'filter_used_{filter_name}')

            # Кэшируем результаты
            self.cache.set(cache_key, results)
            
            # Обновляем метрики
            self.metrics.increment('search_success')
            self.metrics.gauge('search_results_count', len(results))

            return results

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Ошибка при поиске: {error_msg}")
            self.metrics.increment('search_errors')
            raise Exception(error_msg) 