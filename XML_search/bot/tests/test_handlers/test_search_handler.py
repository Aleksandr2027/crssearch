"""
Тесты для обработчика поиска
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from telegram import Update, User, Message, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from XML_search.bot.handlers.search_handler import SearchHandler
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.core.search import SearchEngine
from XML_search.bot.utils.validation_utils import ValidationManager
from XML_search.bot.states import States

# Определяем состояния здесь, так как они используются в тестах
class ConversationStates:
    WAITING_SEARCH = 'WAITING_SEARCH'
    SEARCHING = 'SEARCHING'
    SHOWING_RESULTS = 'SHOWING_RESULTS'

@pytest.fixture
def mock_db_manager():
    """Фикстура для создания мока DatabaseManager"""
    return AsyncMock(spec=DatabaseManager)

@pytest.fixture
def mock_metrics():
    """Фикстура для создания мока MetricsCollector"""
    metrics = MagicMock(spec=MetricsCollector)
    metrics.increment = MagicMock()
    return metrics

@pytest.fixture
def mock_cache():
    """Фикстура для создания мока CacheManager"""
    return MagicMock(spec=CacheManager)

@pytest.fixture
def mock_search_processor():
    """Фикстура для создания мока SearchEngine"""
    processor = AsyncMock(spec=SearchEngine)
    processor.search = AsyncMock(return_value=[{"id": 1, "name": "Test"}])
    return processor

@pytest.fixture
def mock_validator():
    """Фикстура для создания мока ValidationManager"""
    validator = MagicMock(spec=ValidationManager)
    validator.validate_search_params.return_value = True
    return validator

@pytest.fixture
def mock_update():
    """Фикстура для создания мока Update"""
    update = MagicMock(spec=Update)
    update.message = MagicMock(spec=Message)
    update.message.text = "test query"
    update.message.reply_text = AsyncMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123
    return update

@pytest.fixture
def mock_context():
    """Фикстура для создания мока Context"""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context

@pytest.fixture
def mock_logger():
    return MagicMock(spec=LogManager)

@pytest.fixture
def mock_keyboard_manager():
    """Фикстура для создания мока KeyboardManager"""
    keyboard_manager = MagicMock()
    keyboard_manager.get_main_keyboard.return_value = InlineKeyboardMarkup([[]])
    keyboard_manager.get_pagination_keyboard.return_value = InlineKeyboardMarkup([[]])
    return keyboard_manager

@pytest.fixture
def mock_formatter():
    """Фикстура для создания мока MessageFormatter"""
    formatter = MagicMock()
    formatter.format_search_results.return_value = "Formatted results"
    return formatter

@pytest.fixture
def search_handler(mock_db_manager, mock_search_processor, mock_metrics, mock_logger, mock_cache, mock_keyboard_manager, mock_formatter):
    """Фикстура для создания обработчика поиска"""
    handler = SearchHandler(
        db_manager=mock_db_manager,
        search_engine=mock_search_processor,
        metrics=mock_metrics,
        logger=mock_logger,
        cache=mock_cache
    )
    handler.search_engine = mock_search_processor
    handler.keyboard_manager = mock_keyboard_manager
    handler.formatter = mock_formatter
    return handler

class TestSearchHandler:
    """Тесты обработчика поиска"""

    @pytest.mark.asyncio
    async def test_show_search_filters(self, search_handler, mock_update, mock_context):
        """Тест отображения фильтров поиска"""
        mock_update.message.reply_text = AsyncMock()
        mock_context.user_data['search_filters'] = {'filter1': True, 'filter2': False}

        await search_handler.show_search_filters(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Настройте параметры поиска:",
            reply_markup=pytest.approx(search_handler.keyboard_manager.get_search_keyboard(
                mock_context.user_data['search_filters']
            ))
        )
        search_handler.metrics.increment.assert_called_once_with('search_filters_shown')

    @pytest.mark.asyncio
    async def test_handle_filter_callback_reset(self, search_handler, mock_update, mock_context):
        """Тест сброса фильтров поиска"""
        mock_query = MagicMock()
        mock_query.data = 'reset_filters'
        mock_query.answer = AsyncMock()
        mock_query.message = MagicMock()
        mock_query.message.edit_reply_markup = AsyncMock()
        mock_update.callback_query = mock_query
        mock_context.user_data['search_filters'] = {'filter1': True}

        await search_handler.handle_filter_callback(mock_update, mock_context)

        mock_query.answer.assert_called_once_with("✅ Фильтры сброшены")
        assert mock_context.user_data['search_filters'] == {}
        search_handler.metrics.increment.assert_called_once_with('filters_reset')

    @pytest.mark.asyncio
    async def test_handle_filter_callback_toggle(self, search_handler, mock_update, mock_context):
        """Тест переключения фильтра"""
        mock_query = MagicMock()
        mock_query.data = 'filter_test'
        mock_query.answer = AsyncMock()
        mock_query.message = MagicMock()
        mock_query.message.edit_reply_markup = AsyncMock()
        mock_update.callback_query = mock_query
        mock_context.user_data['search_filters'] = {}

        await search_handler.handle_filter_callback(mock_update, mock_context)

        mock_query.answer.assert_called_once_with("✅ Фильтр test")
        assert mock_context.user_data['search_filters'] == {'test': True}
        search_handler.metrics.increment.assert_called_once_with('filter_toggled')

    @pytest.mark.asyncio
    async def test_show_search_results_empty(self, search_handler, mock_update, mock_context):
        """Тест отображения пустых результатов поиска"""
        await search_handler.show_search_results(mock_update, mock_context, [])
        
        mock_update.message.reply_text.assert_called_once()
        search_handler.metrics.increment.assert_called_with('search_empty')

    @pytest.mark.asyncio
    async def test_show_search_results_with_data(self, search_handler, mock_update, mock_context):
        """Тест отображения результатов поиска с данными"""
        results = [{"id": 1, "name": "Test Result", "info": "Test Info"}]
        mock_context.user_data['current_page'] = 1
        
        await search_handler.show_search_results(mock_update, mock_context, results)
        
        mock_update.message.reply_text.assert_called_once_with(
            "Formatted results",
            reply_markup=search_handler.keyboard_manager.get_pagination_keyboard.return_value,
            parse_mode='Markdown'
        )
        search_handler.metrics.increment.assert_called_with('search_results_shown')

    @pytest.mark.asyncio
    async def test_handle_pagination_callback(self, search_handler, mock_update, mock_context):
        """Тест обработки пагинации"""
        mock_query = AsyncMock()
        mock_query.data = 'page_next'
        mock_query.answer = AsyncMock()
        mock_update.callback_query = mock_query
        mock_context.user_data = {
            'current_page': 1,
            'search_results': [{'srid': i} for i in range(20)]
        }

        await search_handler.handle_pagination_callback(mock_update, mock_context)

        assert mock_context.user_data['current_page'] == 2
        mock_query.answer.assert_called_once()
        assert call('pagination_used') in search_handler.metrics.increment.call_args_list

    @pytest.mark.asyncio
    async def test_show_error(self, search_handler, mock_update, mock_context):
        """Тест отображения ошибки"""
        error_message = "Test error"
        mock_update.message = MagicMock(spec=Message)
        mock_update.message.reply_text = AsyncMock()
        
        await search_handler.show_error(mock_update, mock_context, error_message)
        
        mock_update.message.reply_text.assert_called_once_with(
            f"❌ {error_message}",
            reply_markup=search_handler.keyboard_manager.get_main_keyboard.return_value
        )
        search_handler.metrics.increment.assert_called_with('search_errors_shown')

    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_handler, mock_update, mock_context):
        """Тест поиска с фильтрами"""
        query = "test"
        filters = {'filter1': True}
        results = [{'srid': 1, 'name': 'Test1'}]
        search_handler.search_engine.search.return_value = results

        result = await search_handler.search_with_filters(query, filters, mock_context)

        assert result == results
        search_handler.search_engine.search.assert_called_once_with(query, filters)
        assert mock_context.user_data['search_results'] == results
        assert mock_context.user_data['current_page'] == 1
        assert mock_context.user_data['search_filters'] == filters

    @pytest.mark.asyncio
    async def test_handle_update_success(self, search_handler, mock_update, mock_context):
        """Тест успешной обработки поискового запроса"""
        mock_context.user_data['search_filters'] = {}
        search_handler.search_engine.search.return_value = [{"id": 1, "name": "Test"}]
        
        result = await search_handler._handle_update(mock_update, mock_context)
        
        assert result == 10  # States.WAITING_SEARCH
        search_handler.metrics.increment.assert_any_call('search_success')
        assert mock_update.message.reply_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_update_empty_message(self, search_handler, mock_update, mock_context):
        """Тест обработки пустого сообщения"""
        mock_update.message = None
        
        result = await search_handler._handle_update(mock_update, mock_context)
        
        assert result == 10  # States.WAITING_SEARCH
        search_handler.metrics.increment.assert_called_once_with('invalid_message')

    @pytest.mark.asyncio
    async def test_show_search_results_success(self, search_handler, mock_update, mock_context):
        """Тест успешного отображения результатов"""
        results = [{"id": 1, "name": "Test", "info": "Test Info"}]
        mock_context.user_data['current_page'] = 1
        
        await search_handler.show_search_results(mock_update, mock_context, results)
        
        mock_update.message.reply_text.assert_called_once_with(
            "Formatted results",
            reply_markup=search_handler.keyboard_manager.get_pagination_keyboard.return_value,
            parse_mode='Markdown'
        )
        search_handler.metrics.increment.assert_called_with('search_results_shown')

    @pytest.mark.asyncio
    async def test_handle_pagination(self, search_handler, mock_update, mock_context):
        """Тест обработки пагинации"""
        mock_update.callback_query = AsyncMock()
        mock_update.callback_query.data = "page_next"
        mock_context.user_data = {
            'current_page': 1,
            'search_results': [{"id": 1}, {"id": 2}]
        }
        
        await search_handler.handle_pagination_callback(mock_update, mock_context)
        
        search_handler.metrics.increment.assert_called_with('pagination_used')
        assert mock_context.user_data['current_page'] == 2 