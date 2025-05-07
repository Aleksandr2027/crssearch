"""
Общие фикстуры для тестов обработчиков
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.core.search import SearchEngine
from XML_search.enhanced.export.export_manager import ExportManager

@pytest.fixture
def mock_metrics():
    """Фикстура для создания мока MetricsManager"""
    metrics = MagicMock(spec=MetricsManager)
    metrics.increment = MagicMock()
    metrics.timing = MagicMock()
    metrics.gauge = MagicMock()
    return metrics

@pytest.fixture
def mock_logger():
    """Фикстура для создания мока LogManager"""
    logger = MagicMock(spec=LogManager)
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    logger.get_logger = MagicMock(return_value=logger)
    return logger

@pytest.fixture
def mock_cache():
    """Фикстура для создания мока CacheManager"""
    cache = MagicMock(spec=CacheManager)
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    return cache

@pytest.fixture
def mock_db_manager():
    """Фикстура для создания мока DatabaseManager"""
    db = MagicMock(spec=DatabaseManager)
    db.safe_transaction = AsyncMock()
    db.execute_query = AsyncMock()
    return db

@pytest.fixture
def mock_search_engine(mock_db_manager, mock_cache, mock_metrics, mock_logger):
    """Фикстура для создания мока SearchEngine"""
    engine = MagicMock(spec=SearchEngine)
    engine.search = AsyncMock()
    engine.db_manager = mock_db_manager
    engine.cache = mock_cache
    engine.metrics = mock_metrics
    engine.logger = mock_logger
    return engine

@pytest.fixture
def mock_export_manager(mock_metrics, mock_logger, mock_cache):
    """Фикстура для создания мока ExportManager"""
    manager = MagicMock(spec=ExportManager)
    manager.export = AsyncMock()
    manager.metrics = mock_metrics
    manager.logger = mock_logger
    manager.cache = mock_cache
    return manager

@pytest.fixture
def mock_update():
    """Фикстура для создания мока Update"""
    update = MagicMock(spec=Update)
    user = MagicMock(spec=User)
    user.id = 12345
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    message = MagicMock(spec=Message)
    message.from_user = user
    message.chat = chat
    message.text = "test message"
    message.reply_text = AsyncMock()
    update.effective_user = user
    update.message = message
    update.effective_chat = chat
    update.callback_query = AsyncMock()
    update.callback_query.data = "test_data"
    update.callback_query.answer = AsyncMock()
    update.callback_query.message = message
    return update

@pytest.fixture
def mock_context():
    """Фикстура для создания мока Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.user_data = {}
    return context 