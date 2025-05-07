import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, PropertyMock
from telegram import Update, Message, User, Chat
from telegram.ext import CallbackContext
from psycopg2.pool import ThreadedConnectionPool
import psycopg2
from contextlib import contextmanager
import logging

from XML_search.bot.handlers.search_handler import SearchHandler
from XML_search.core.search import SearchEngine, SearchTransliterator, SearchUtils
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.bot.states import States
from XML_search.config import DBConfig
from XML_search.bot.config import BotConfig
from XML_search.enhanced.db_pool import DatabasePool

# Отключаем логирование для тестов
logging.getLogger('db_pool').setLevel(logging.CRITICAL)
logging.getLogger('XML_search.crs_search').setLevel(logging.CRITICAL)

@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Очистка логгеров после каждого теста"""
    yield
    for handler in logging.getLogger().handlers[:]:
        handler.close()
        logging.getLogger().removeHandler(handler)
    
    for name in ['db_pool', 'XML_search.crs_search']:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

class MockConnection:
    """Мок для соединения с базой данных с поддержкой контекстного менеджера"""
    def __init__(self):
        self.closed = False
        self.cursor = Mock(return_value=Mock())
        self.close = Mock()
        self.commit = Mock()
        self.rollback = Mock()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

@pytest.fixture
def mock_psycopg2_connect():
    """Создание мока для psycopg2.connect"""
    mock_conn = MockConnection()
    with patch('psycopg2.connect', return_value=mock_conn) as mock:
        yield mock

@pytest.fixture
def mock_threaded_pool(mock_psycopg2_connect):
    """Создание мока для ThreadedConnectionPool"""
    pool = Mock(spec=ThreadedConnectionPool)
    pool.getconn = Mock(return_value=mock_psycopg2_connect.return_value)
    pool.putconn = Mock()
    pool.closeall = Mock()
    return pool

@pytest.fixture
def mock_db_pool(mock_threaded_pool):
    """Создание мока для DatabasePool"""
    pool = MagicMock(spec=DatabasePool)
    pool._pool = mock_threaded_pool
    pool.get_connection = Mock(return_value=mock_threaded_pool.getconn())
    pool.put_connection = Mock()
    pool.execute_query = Mock(return_value=[
        {
            'srid': 100001,
            'srtext': 'Московская система координат',
            'proj4text': '+proj=tmerc +lat_0=55.6666666667 +lon_0=37.5 +k=1 +x_0=0 +y_0=0 +ellps=krass +units=m +no_defs',
            'relevance': 0.95
        }
    ])
    
    # Добавляем поддержку контекстного менеджера
    @contextmanager
    def connection():
        conn = pool.get_connection()
        try:
            yield conn
        finally:
            pool.put_connection(conn)
    
    pool.connection = connection
    return pool

@pytest.fixture
def mock_db_manager(mock_db_pool):
    """Создание мока для DatabaseManager"""
    db_manager = MagicMock(spec=DatabaseManager)
    db_manager.pool = mock_db_pool
    db_manager.execute_query = Mock(return_value=[
        {
            'srid': 100001,
            'srtext': 'Московская система координат',
            'proj4text': '+proj=tmerc +lat_0=55.6666666667 +lon_0=37.5 +k=1 +x_0=0 +y_0=0 +ellps=krass +units=m +no_defs',
            'relevance': 0.95
        }
    ])
    
    # Добавляем поддержку контекстного менеджера
    @contextmanager
    def get_connection():
        conn = mock_db_pool.get_connection()
        try:
            yield conn
        finally:
            mock_db_pool.put_connection(conn)
    
    db_manager.get_connection = get_connection
    return db_manager

@pytest.fixture
def mock_bot_config():
    """Создание мока для BotConfig"""
    config = Mock(spec=BotConfig)
    db_config = Mock(spec=DBConfig)
    db_config.DB_NAME = "test_db"
    db_config.DB_USER = "test_user"
    db_config.DB_PASSWORD = "test_password"
    db_config.DB_HOST = "localhost"
    db_config.DB_PORT = "5432"
    db_config.min_connections = 5
    db_config.max_connections = 20
    db_config.connection_timeout = 30.0
    db_config.idle_timeout = 600.0
    db_config.health_check_interval = 300
    
    # Создаем property для db_params
    type(db_config).db_params = property(lambda self: {
        "dbname": self.DB_NAME,
        "user": self.DB_USER,
        "password": self.DB_PASSWORD,
        "host": self.DB_HOST,
        "port": self.DB_PORT
    })
    
    config.DB_CONFIG = db_config
    return config

@pytest.fixture
def mock_update():
    """Создание мока для Update"""
    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.text = "мск"
    update.message.chat = Mock(spec=Chat)
    update.message.chat.id = 123
    update.message.from_user = Mock(spec=User)
    update.message.from_user.id = 123
    return update

@pytest.fixture
def mock_context():
    """Создание мока для CallbackContext"""
    context = Mock(spec=CallbackContext)
    context.bot = Mock()
    context.bot.send_message = AsyncMock()
    context.user_data = {}
    return context

@pytest.fixture
def mock_cache_manager():
    """Создание мока для CacheManager"""
    cache_manager = MagicMock(spec=CacheManager)
    cache_manager.get = Mock(return_value=None)
    cache_manager.set = Mock()
    return cache_manager

@pytest.fixture
def mock_metrics():
    """Создание мока для MetricsManager"""
    metrics = MagicMock(spec=MetricsManager)
    metrics.increment = Mock()
    metrics.record_timing = Mock()
    return metrics

@pytest.fixture
def mock_logger():
    """Создание мока для LogManager"""
    logger = MagicMock(spec=LogManager)
    logger.info = Mock()
    logger.error = Mock()
    return logger

@pytest.fixture
def search_engine(mock_db_manager, mock_cache_manager, mock_metrics, mock_logger):
    """Создание экземпляра SearchEngine с моками"""
    engine = SearchEngine(
        db_manager=mock_db_manager,
        cache_manager=mock_cache_manager,
        metrics=mock_metrics,
        logger=mock_logger
    )
    return engine

@pytest.fixture
def mock_formatter():
    """Создание мока для MessageFormatter"""
    formatter = MagicMock()
    formatter.format_search_results = Mock(return_value="Результаты поиска:\n1. МСК")
    return formatter

@pytest.fixture
def mock_keyboard_manager():
    """Создание мока для KeyboardManager"""
    keyboard_manager = MagicMock()
    keyboard_manager.get_pagination_keyboard = Mock(return_value=None)
    keyboard_manager.get_search_keyboard = Mock(return_value=None)
    return keyboard_manager

@pytest.fixture
def search_handler(search_engine, mock_db_manager, mock_metrics, mock_logger, mock_cache_manager, mock_bot_config, mock_formatter, mock_keyboard_manager):
    """Создание экземпляра SearchHandler с моками"""
    with patch('XML_search.bot.handlers.base_handler.BotConfig', return_value=mock_bot_config):
        handler = SearchHandler(
            search_engine=search_engine,
            metrics=mock_metrics,
            logger=mock_logger
        )
        handler.cache = mock_cache_manager
        handler.db_manager = mock_db_manager
        handler.formatter = mock_formatter
        handler.keyboard_manager = mock_keyboard_manager
        return handler

@pytest.mark.asyncio
async def test_full_search_cycle(search_handler, mock_update, mock_context):
    """Тест полного цикла поиска от ввода до вывода"""
    # Настраиваем мок для search
    search_handler.search_engine.search = AsyncMock(return_value=[{
        'srid': 100001,
        'srtext': 'Московская система координат',
        'proj4text': '+proj=tmerc +lat_0=55.6666666667 +lon_0=37.5 +k=1 +x_0=0 +y_0=0 +ellps=krass +units=m +no_defs',
        'relevance': 0.95
    }])
    
    # Настраиваем мок для send_message
    mock_context.bot.send_message = AsyncMock()
    
    # Настраиваем эффективного пользователя
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123
    
    # Настраиваем мок для reply_text
    mock_update.message.reply_text = AsyncMock()
    
    # Вызываем обработчик поиска
    result = await search_handler._handle_update(mock_update, mock_context)
    
    # Проверяем, что состояние обновлено
    assert result == 10  # States.WAITING_SEARCH.value
    
    # Проверяем, что поиск выполнен
    search_handler.search_engine.search.assert_called_once_with("мск", {})
    
    # Проверяем, что результаты отформатированы
    search_handler.formatter.format_search_results.assert_called_once()
    
    # Проверяем, что сообщение отправлено
    mock_update.message.reply_text.assert_called_once()
    
    # Проверяем, что метрики обновлены
    search_handler.metrics.increment.assert_any_call('search_success')
    search_handler.metrics.increment.assert_any_call('search_results_shown')

@pytest.mark.asyncio
async def test_search_with_cache(search_handler, mock_update, mock_context):
    """Тест поиска с использованием кэша"""
    # Настраиваем кэш для возврата данных
    search_handler.search_engine.search = AsyncMock(return_value=[{
        'srid': 100001,
        'srtext': 'Московская система координат',
        'proj4text': '+proj=tmerc +lat_0=55.6666666667 +lon_0=37.5 +k=1 +x_0=0 +y_0=0 +ellps=krass +units=m +no_defs',
        'relevance': 0.95
    }])
    
    # Настраиваем мок для reply_text
    mock_update.message.reply_text = AsyncMock()
    
    # Настраиваем эффективного пользователя
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123
    
    # Вызываем обработчик поиска
    result = await search_handler._handle_update(mock_update, mock_context)
    
    # Проверяем, что поиск выполнен
    search_handler.search_engine.search.assert_called_once_with("мск", {})
    
    # Проверяем, что результаты отформатированы
    search_handler.formatter.format_search_results.assert_called_once()
    
    # Проверяем, что сообщение отправлено
    mock_update.message.reply_text.assert_called_once()
    
    # Проверяем, что метрики обновлены
    search_handler.metrics.increment.assert_any_call('search_success')
    search_handler.metrics.increment.assert_any_call('search_results_shown')

@pytest.mark.asyncio
async def test_search_with_transliteration(search_handler, mock_update, mock_context):
    """Тест поиска с транслитерацией"""
    # Меняем текст сообщения на латиницу
    mock_update.message.text = "msk"
    
    # Настраиваем мок для search
    search_handler.search_engine.search = AsyncMock(return_value=[{
        'srid': 100001,
        'srtext': 'Московская система координат',
        'proj4text': '+proj=tmerc +lat_0=55.6666666667 +lon_0=37.5 +k=1 +x_0=0 +y_0=0 +ellps=krass +units=m +no_defs',
        'relevance': 0.95
    }])
    
    # Настраиваем мок для send_message
    mock_context.bot.send_message = AsyncMock()
    
    # Вызываем обработчик поиска
    result = await search_handler._handle_update(mock_update, mock_context)
    
    # Проверяем, что поиск выполнен
    search_handler.search_engine.search.assert_called_once_with("msk", {})
    
    # Проверяем, что метрики обновлены
    search_handler.metrics.increment.assert_any_call('search_success')

@pytest.mark.asyncio
async def test_search_with_filters(search_handler, mock_update, mock_context):
    """Тест поиска с применением фильтров"""
    # Добавляем фильтры в user_data
    filters = {
        'area': 'Москва',
        'accuracy': 'высокая'
    }
    mock_context.user_data['search_filters'] = filters
    
    # Настраиваем мок для search
    search_handler.search_engine.search = AsyncMock(return_value=[{
        'srid': 100001,
        'srtext': 'Московская система координат',
        'proj4text': '+proj=tmerc +lat_0=55.6666666667 +lon_0=37.5 +k=1 +x_0=0 +y_0=0 +ellps=krass +units=m +no_defs',
        'relevance': 0.95
    }])
    
    # Настраиваем мок для reply_text
    mock_update.message.reply_text = AsyncMock()
    
    # Настраиваем эффективного пользователя
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123
    
    # Настраиваем валидатор
    search_handler.validator.validate_search_params = Mock(return_value=True)
    
    # Вызываем обработчик поиска
    result = await search_handler._handle_update(mock_update, mock_context)
    
    # Проверяем, что поиск выполнен с учетом фильтров
    search_handler.search_engine.search.assert_called_once_with(mock_update.message.text, filters)
    
    # Проверяем, что результаты отформатированы
    search_handler.formatter.format_search_results.assert_called_once()
    
    # Проверяем, что клавиатура создана
    search_handler.keyboard_manager.get_pagination_keyboard.assert_called_once()
    
    # Проверяем, что сообщение отправлено
    mock_update.message.reply_text.assert_called_once()
    
    # Проверяем, что метрики обновлены
    search_handler.metrics.increment.assert_any_call('search_success')
    search_handler.metrics.increment.assert_any_call('search_results_shown')

@pytest.mark.asyncio
async def test_search_error_handling(search_handler, mock_update, mock_context):
    """Тест обработки ошибок при поиске"""
    # Настраиваем ошибку в поиске
    search_handler.search_engine.search = AsyncMock(side_effect=Exception("Database error"))
    
    # Настраиваем мок для reply_text
    mock_update.message.reply_text = AsyncMock()
    
    # Настраиваем эффективного пользователя
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123
    
    # Вызываем обработчик поиска
    result = await search_handler._handle_update(mock_update, mock_context)
    
    # Проверяем, что ошибка обработана
    search_handler.logger.error.assert_called()
    search_handler.metrics.increment.assert_any_call('search_errors')
    
    # Проверяем, что пользователю отправлено сообщение об ошибке
    mock_update.message.reply_text.assert_called()

@pytest.mark.asyncio
async def test_search_pagination(search_handler, mock_update, mock_context):
    """Тест пагинации результатов поиска"""
    # Настраиваем большое количество результатов
    search_handler.search_engine.search = AsyncMock(return_value=[
        {'srid': i, 'srtext': f'System {i}', 'proj4text': '+proj=tmerc', 'relevance': 0.9}
        for i in range(20)
    ])
    
    # Настраиваем мок для reply_text
    mock_update.message.reply_text = AsyncMock()
    
    # Настраиваем эффективного пользователя
    mock_update.effective_user = Mock()
    mock_update.effective_user.id = 123
    
    # Вызываем обработчик поиска
    result = await search_handler._handle_update(mock_update, mock_context)
    
    # Проверяем, что результаты отформатированы
    search_handler.formatter.format_search_results.assert_called_once()
    
    # Проверяем, что клавиатура пагинации создана
    search_handler.keyboard_manager.get_pagination_keyboard.assert_called_once()
    
    # Проверяем, что сообщение отправлено
    mock_update.message.reply_text.assert_called_once()
    
    # Проверяем, что метрики обновлены
    search_handler.metrics.increment.assert_any_call('search_success')
    search_handler.metrics.increment.assert_any_call('search_results_shown') 