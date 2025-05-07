"""
Тесты для обработчика координат
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes, MessageHandler
from XML_search.bot.handlers.coord_handler import CoordHandler
from XML_search.bot.states import States
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.bot.utils.validation_utils import ValidationResult, Coordinates

class TestCoordHandlerImpl(CoordHandler):
    """Тестовая реализация CoordHandler"""
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Тестовая реализация абстрактного метода"""
        return await self.handle_coordinates(update, context)

@pytest.fixture
def mock_db_manager():
    """Фикстура для создания мока DatabaseManager"""
    db_manager = MagicMock(spec=DatabaseManager)
    db_manager.safe_transaction = MagicMock()
    return db_manager

@pytest.fixture
def mock_metrics():
    """Фикстура для создания мока MetricsManager"""
    metrics = MagicMock(spec=MetricsManager)
    return metrics

@pytest.fixture
def mock_logger():
    """Фикстура для создания мока Logger"""
    logger = MagicMock()
    return logger

@pytest.fixture
def mock_cache():
    """Фикстура для создания мока Cache"""
    cache = MagicMock()
    return cache

@pytest.fixture
def coord_handler(mock_db_manager, mock_metrics, mock_logger, mock_cache):
    """Фикстура для создания обработчика координат"""
    return CoordHandler(
        db_manager=mock_db_manager,
        metrics=mock_metrics,
        logger=mock_logger,
        cache=mock_cache
    )

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
    update.effective_user = user
    update.message = message
    update.effective_chat = chat
    return update

@pytest.fixture
def mock_context():
    """Фикстура для создания мока Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    return context

class TestCoordHandler:
    """Тесты обработчика координат"""
    
    @pytest.mark.asyncio
    async def test_return_to_menu(self, coord_handler, mock_update, mock_context):
        """Тест возврата в главное меню"""
        mock_update.message.text = '🔙 Главное меню'
        
        result = await coord_handler.handle_coordinates(mock_update, mock_context)
        
        assert result == States.MAIN_MENU
        
    @pytest.mark.asyncio
    async def test_invalid_coordinates(self, coord_handler, mock_update, mock_context):
        """Тест обработки некорректных координат"""
        mock_update.message.text = "invalid coords"
        
        result = await coord_handler.handle_coordinates(mock_update, mock_context)
        
        assert result == States.WAITING_COORDINATES
        coord_handler.metrics.increment.assert_called_with('coord_validation_errors')
        coord_handler.logger.error.assert_called()
        
    @pytest.mark.asyncio
    async def test_valid_coordinates_no_results(self, coord_handler, mock_update, mock_context):
        """Тест обработки корректных координат без результатов"""
        mock_update.message.text = "55.7558, 37.6173"
        coord_handler.db_manager.safe_transaction.return_value.__aenter__.return_value = []
        
        result = await coord_handler.handle_coordinates(mock_update, mock_context)
        
        assert result == States.WAITING_COORDINATES
        coord_handler.metrics.increment.assert_called_with('coord_search_empty')
        
    @pytest.mark.asyncio
    async def test_valid_coordinates_with_results(self, coord_handler, mock_update, mock_context):
        """Тест обработки корректных координат с результатами"""
        mock_update.message.text = "55.7558, 37.6173"
        test_results = [{"srid": 1, "name": "Test CRS"}]
        coord_handler.db_manager.safe_transaction.return_value.__aenter__.return_value = test_results
        
        result = await coord_handler.handle_coordinates(mock_update, mock_context)
        
        assert result == States.WAITING_COORDINATES
        coord_handler.metrics.increment.assert_called_with('coord_search_success')
        
    @pytest.mark.asyncio
    async def test_database_error(self, coord_handler, mock_update, mock_context):
        """Тест обработки ошибки базы данных"""
        mock_update.message.text = "55.7558, 37.6173"
        coord_handler.db_manager.safe_transaction.side_effect = Exception("Database error")
        
        result = await coord_handler.handle_coordinates(mock_update, mock_context)
        
        assert result == States.WAITING_COORDINATES
        coord_handler.metrics.increment.assert_called_with('coord_handler_errors')
        coord_handler.logger.error.assert_called()
        
    def test_get_handler(self, coord_handler):
        """Тест получения обработчика сообщений"""
        handler = coord_handler.get_handler()
        
        assert isinstance(handler, MessageHandler)
        assert handler.callback == coord_handler.handle_coordinates 