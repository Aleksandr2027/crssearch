"""
Конфигурация для тестов поиска
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.crs_search import CrsSearchBot
from XML_search.config import DBConfig

@pytest.fixture
def db_config():
    """Фикстура для создания конфигурации БД"""
    config = MagicMock()
    config.db_params = {
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_pass",
        "host": "localhost",
        "port": "5432"
    }
    return config

@pytest.fixture
def mock_db_manager(db_config):
    """Фикстура для создания мока DatabaseManager"""
    db_manager = MagicMock()
    return db_manager

@pytest.fixture
def mock_logger():
    """Фикстура для создания мока логгера"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.get_logger = MagicMock(return_value=logger)
    return logger

@pytest.fixture
def mock_metrics():
    """Фикстура для создания мока метрик"""
    metrics = MagicMock()
    metrics.increment = MagicMock()
    metrics.gauge = MagicMock()
    metrics.timing = MagicMock()
    return metrics

@pytest.fixture
def mock_cache():
    """Фикстура для создания мока кэша"""
    cache = MagicMock()
    cache.get = MagicMock()
    cache.set = MagicMock()
    return cache

@pytest.fixture
def mock_search_processor():
    """Фикстура для создания мока CrsSearchBot"""
    processor = AsyncMock(spec=CrsSearchBot)
    return processor

@pytest.fixture
def sample_search_results():
    """Фикстура с примером результатов поиска"""
    return [
        {
            "srid": 1,
            "auth_name": "custom",
            "srtext": "Test CRS 1",
            "proj4text": "+proj=longlat +datum=WGS84",
            "relevance": 1.0
        },
        {
            "srid": 2,
            "auth_name": "EPSG",
            "srtext": "Test CRS 2",
            "proj4text": "+proj=longlat +datum=WGS84",
            "relevance": 0.8
        }
    ] 