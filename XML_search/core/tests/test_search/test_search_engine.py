"""
Тесты для поискового движка
"""

import pytest
from unittest.mock import patch, call, MagicMock, AsyncMock, ANY
from XML_search.core.search import SearchEngine
from XML_search.errors import DatabaseError
from XML_search.config import DBConfig
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.cache_manager import CacheManager

class TestSearchEngine:
    """Тесты для поискового движка"""
    
    @pytest.fixture
    def mock_search_processor(self):
        """Фикстура для создания мока поискового процессора"""
        processor = MagicMock()
        processor.search_coordinate_systems = AsyncMock()
        return processor
    
    def test_init_with_custom_db_manager(self, mock_db_manager, mock_logger, mock_metrics):
        """Тест инициализации с пользовательским менеджером БД"""
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics):
            
            engine = SearchEngine(db_manager=mock_db_manager)
            
            assert engine.db_manager == mock_db_manager
            mock_logger.get_logger().info.assert_called_with("Использование существующего менеджера БД")
            
    def test_init_without_db_manager(self, mock_logger, mock_metrics, db_config):
        """Тест инициализации без менеджера БД"""
        mock_db = MagicMock(spec=DatabaseManager)
        
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics), \
             patch('XML_search.core.search.search_engine.DBConfig', return_value=db_config), \
             patch('XML_search.core.search.search_engine.DatabaseManager', return_value=mock_db) as mock_db_cls:
            
            engine = SearchEngine()
            
            mock_db_cls.assert_called_once_with(db_config)
            assert engine.db_manager == mock_db
            mock_logger.get_logger().info.assert_called_with("Создание нового менеджера БД")
            
    def test_init_db_manager_error(self, mock_logger, mock_metrics, db_config):
        """Тест обработки ошибок при создании менеджера БД"""
        error_msg = "DB Error"
        
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics), \
             patch('XML_search.core.search.search_engine.DBConfig', return_value=db_config), \
             patch('XML_search.core.search.search_engine.DatabaseManager', side_effect=DatabaseError(error_msg)):
            
            with pytest.raises(DatabaseError) as exc_info:
                SearchEngine()
                
            assert str(exc_info.value) == f"Ошибка при создании менеджера БД: {error_msg}"
            mock_logger.get_logger().error.assert_called_with(f"Ошибка при создании менеджера БД: {error_msg}")
            
    @pytest.mark.asyncio
    async def test_search_with_cache_hit(self, mock_cache, mock_metrics, mock_logger, mock_db_manager):
        """Тест поиска с попаданием в кэш"""
        cached_results = [{"srid": 1}]
        mock_cache.get.return_value = cached_results
        mock_cache.set.return_value = None
        
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics), \
             patch('XML_search.core.search.search_engine.CacheManager', return_value=mock_cache):
            
            engine = SearchEngine(db_manager=mock_db_manager)
            results = await engine.search("test")
            
            assert results == cached_results
            mock_metrics.increment.assert_called_with('search_cache_hits')
            mock_logger.get_logger().info.assert_called_with("Найдены кэшированные результаты для запроса: test")
            
    @pytest.mark.asyncio
    async def test_search_without_cache_hit(
        self, mock_cache, mock_metrics, mock_logger, 
        mock_db_manager, mock_search_processor, sample_search_results
    ):
        """Тест поиска без попадания в кэш"""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_search_processor.search_coordinate_systems.return_value = sample_search_results
        
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics), \
             patch('XML_search.core.search.search_engine.CacheManager', return_value=mock_cache), \
             patch('XML_search.core.search.search_engine.CrsSearchBot', return_value=mock_search_processor):
            
            engine = SearchEngine(db_manager=mock_db_manager)
            results = await engine.search("test")
            
            assert results == sample_search_results
            mock_metrics.increment.assert_called_with('search_success')
            mock_metrics.gauge.assert_called_with('search_results_count', len(sample_search_results))
            mock_cache.set.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, mock_cache, mock_metrics, mock_logger,
        mock_db_manager, mock_search_processor, sample_search_results
    ):
        """Тест поиска с фильтрами"""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_search_processor.search_coordinate_systems.return_value = sample_search_results
        filters = {"region": True}
        
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics), \
             patch('XML_search.core.search.search_engine.CacheManager', return_value=mock_cache), \
             patch('XML_search.core.search.search_engine.CrsSearchBot', return_value=mock_search_processor):
            
            engine = SearchEngine(db_manager=mock_db_manager)
            results = await engine.search("test", filters=filters)
            
            # Должен вернуть только региональные СК
            assert len([r for r in results if r['auth_name'] == 'custom']) == 1
            
            # Проверяем вызовы метрик
            mock_metrics.increment.assert_has_calls([
                call('search_success'),
                call('filter_used_region')
            ], any_order=True)
            
            mock_metrics.gauge.assert_called_with('search_results_count', len(results))
            mock_cache.set.assert_called_once_with(ANY, results)
            
    @pytest.mark.asyncio
    async def test_search_error_handling(
        self, mock_cache, mock_metrics, mock_logger,
        mock_db_manager, mock_search_processor
    ):
        """Тест обработки ошибок при поиске"""
        error_message = "Search Error"
        mock_cache.get.return_value = None
        mock_cache.set.return_value = None
        mock_search_processor.search_coordinate_systems.side_effect = Exception(error_message)
        
        with patch('XML_search.core.search.search_engine.LogManager', return_value=mock_logger), \
             patch('XML_search.core.search.search_engine.MetricsManager', return_value=mock_metrics), \
             patch('XML_search.core.search.search_engine.CacheManager', return_value=mock_cache), \
             patch('XML_search.core.search.search_engine.CrsSearchBot', return_value=mock_search_processor):
            
            engine = SearchEngine(db_manager=mock_db_manager)
            
            with pytest.raises(Exception) as exc_info:
                await engine.search("test")
                
            assert str(exc_info.value) == error_message
            mock_metrics.increment.assert_called_with('search_errors')
            mock_logger.get_logger().error.assert_called_with(f"Ошибка при поиске: {error_message}") 