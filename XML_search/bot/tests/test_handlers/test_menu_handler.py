"""
Тесты для обработчика главного меню
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from telegram import Update, User, Message, Chat, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from XML_search.bot.handlers.menu_handler import MenuHandler
from XML_search.bot.states import States
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager

class TestMenuHandlerImpl(MenuHandler):
    """Тестовая реализация MenuHandler"""
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Тестовая реализация абстрактного метода"""
        return await super()._handle_update(update, context)

@pytest.fixture
def mock_db_manager():
    """Фикстура для создания мока DatabaseManager"""
    db_manager = MagicMock(spec=DatabaseManager)
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
def menu_handler(mock_db_manager, mock_metrics, mock_logger, mock_cache):
    """Фикстура для создания обработчика меню"""
    return MenuHandler(
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

class TestMenuHandler:
    """Тесты обработчика меню"""
    
    @pytest.mark.asyncio
    async def test_show_main_menu(self, menu_handler, mock_update, mock_context):
        """Тест отображения главного меню"""
        mock_update.message.reply_text = AsyncMock()
        
        result = await menu_handler.show_main_menu(mock_update, mock_context)
        
        assert result == States.MAIN_MENU
        mock_update.message.reply_text.assert_called_once_with(
            "Выберите тип поиска:",
            reply_markup=pytest.approx(ReplyKeyboardMarkup([
                [menu_handler.BUTTON_COORD_SEARCH],
                [menu_handler.BUTTON_DESC_SEARCH]
            ], resize_keyboard=True))
        )
        menu_handler.metrics.increment.assert_called_with('main_menu_show')
        menu_handler.logger.info.assert_called()
        
    @pytest.mark.asyncio
    async def test_handle_coord_search(self, menu_handler, mock_update, mock_context):
        """Тест обработки выбора поиска по координатам"""
        mock_update.message.text = menu_handler.BUTTON_COORD_SEARCH
        mock_update.message.reply_text = AsyncMock()
        
        result = await menu_handler._handle_update(mock_update, mock_context)
        
        assert result == States.WAITING_COORDINATES
        mock_update.message.reply_text.assert_called_once_with(
            "📍 Введите координаты в формате 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'\n\n"
            "Поддерживаемые форматы ввода:\n"
            "1. Десятичные градусы: 55.7558;37.6173 или 55.7558$37.6173 или 55.7558%37.6173\n"
            "2. Градусы и минуты: 55 45.348;37 37.038 или 55 45.348$37 37.038 или 55 45.348%37 37.038\n"
            "3. Градусы, минуты и секунды: 55 45 20.88;37 37 2.28 или 55 45 20.88$37 37 2.28 или 55 45 20.88%37 37 2.28\n"
            "4. С обозначениями: 55°45'20.88\";37°37'2.28\" или 55°45'20.88\"$37°37'2.28\" или 55°45'20.88\"%37°37'2.28\"\n\n"
            "Разделитель между широтой и долготой - точка с запятой (;) или знак доллара ($) или знак процента (%)",
            reply_markup=pytest.approx(ReplyKeyboardMarkup([[menu_handler.BUTTON_MENU]], resize_keyboard=True))
        )
        menu_handler.metrics.increment.assert_called_with('coord_search_selected')
        menu_handler.logger.info.assert_called()
        
    @pytest.mark.asyncio
    async def test_handle_desc_search(self, menu_handler, mock_update, mock_context):
        """Тест обработки выбора поиска по описанию"""
        mock_update.message.text = menu_handler.BUTTON_DESC_SEARCH
        mock_update.message.reply_text = AsyncMock()
        
        result = await menu_handler._handle_update(mock_update, mock_context)
        
        assert result == States.WAITING_SEARCH
        
        # Проверяем первый вызов reply_text с основными инструкциями
        assert mock_update.message.reply_text.call_args_list[0] == call(
            "🔍 Как пользоваться поиском:\n\n"
            "1. Поиск по SRID:\n"
            "   - Отправьте номер системы координат\n"
            "   - Пример: 100000\n\n"
            "2. Поиск по названию:\n"
            "   - Отправьте часть названия\n"
            "   - Пример: MSK01z1\n\n"
            "3. Поиск по описанию:\n"
            "   - Отправьте часть описания\n"
            "   - Пример: Московская, Moskovskaya\n\n"
            "Результаты будут отсортированы по релевантности:\n"
            "- Сначала точные совпадения\n"
            "- Затем частичные совпадения",
            reply_markup=pytest.approx(ReplyKeyboardMarkup([[menu_handler.BUTTON_MENU]], resize_keyboard=True))
        )
        
        # Проверяем второй вызов reply_text с inline кнопкой
        inline_button = InlineKeyboardButton(
            text="🔍 Быстрый поиск в текущем чате",
            switch_inline_query_current_chat=""
        )
        expected_markup = InlineKeyboardMarkup([[inline_button]])
        
        assert mock_update.message.reply_text.call_args_list[1] == call(
            "Нажмите кнопку ниже для быстрого поиска:",
            reply_markup=pytest.approx(expected_markup)
        )
        
        menu_handler.metrics.increment.assert_called_with('desc_search_selected')
        menu_handler.logger.info.assert_called()
        
    @pytest.mark.asyncio
    async def test_handle_menu_return(self, menu_handler, mock_update, mock_context):
        """Тест обработки возврата в главное меню"""
        mock_update.message.text = menu_handler.BUTTON_MENU
        mock_update.message.reply_text = AsyncMock()
        
        result = await menu_handler._handle_update(mock_update, mock_context)
        
        assert result == States.MAIN_MENU
        mock_update.message.reply_text.assert_called_once_with(
            "Выберите тип поиска:",
            reply_markup=pytest.approx(ReplyKeyboardMarkup([
                [menu_handler.BUTTON_COORD_SEARCH],
                [menu_handler.BUTTON_DESC_SEARCH]
            ], resize_keyboard=True))
        )
        menu_handler.metrics.increment.assert_called_with('menu_return')
        menu_handler.logger.info.assert_called()
        
    @pytest.mark.asyncio
    async def test_handle_invalid_message(self, menu_handler, mock_update, mock_context):
        """Тест обработки некорректного сообщения"""
        mock_update.message = None
        
        result = await menu_handler._handle_update(mock_update, mock_context)
        
        assert result == States.MAIN_MENU
        menu_handler.metrics.increment.assert_called_with('invalid_message')
        
    @pytest.mark.asyncio
    async def test_handle_invalid_text(self, menu_handler, mock_update, mock_context):
        """Тест обработки некорректного текста"""
        mock_update.message.text = "invalid_command"
        
        result = await menu_handler._handle_update(mock_update, mock_context)
        
        assert result == States.MAIN_MENU
        menu_handler.metrics.increment.assert_called_with('invalid_command') 