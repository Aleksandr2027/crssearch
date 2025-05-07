"""
Тесты для обработчика авторизации
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, User, Message, Chat, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from XML_search.bot.handlers.auth_handler import AuthHandler
from XML_search.bot.states import States
from XML_search.config import TelegramConfig
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.bot.keyboards.main_keyboard import MainKeyboard

class TestAuthHandlerImpl(AuthHandler):
    """Тестовая реализация AuthHandler для тестов"""
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Тестовая реализация абстрактного метода"""
        return States.AUTH

@pytest.fixture
def mock_keyboard():
    """Фикстура для создания мока клавиатуры"""
    keyboard = MagicMock(spec=MainKeyboard)
    keyboard.get_keyboard.return_value = ReplyKeyboardMarkup([[]], resize_keyboard=True)
    return keyboard

@pytest.fixture
def auth_handler(mock_db_manager, mock_metrics, mock_logger, mock_cache):
    """Фикстура для создания обработчика авторизации"""
    handler = AuthHandler(
        db_manager=mock_db_manager,
        metrics=mock_metrics,
        logger=mock_logger,
        cache=mock_cache
    )
    handler.authorized_users = set()
    return handler

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

class TestAuthHandler:
    """Тесты обработчика авторизации"""
    
    @pytest.mark.asyncio
    async def test_auth_start(self, auth_handler, mock_update, mock_context):
        """Тест начала процесса авторизации"""
        mock_update.message.reply_text = AsyncMock()
        
        result = await auth_handler.auth_start(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "пароль" in mock_update.message.reply_text.call_args[0][0].lower()
        assert result == States.AUTH
        
    @pytest.mark.asyncio
    async def test_auth_check_valid_password(self, auth_handler, mock_update, mock_context):
        """Тест проверки правильного пароля"""
        mock_update.message.text = "123"  # Правильный пароль
        
        result = await auth_handler.auth_check(mock_update, mock_context)
        
        assert result == States.MAIN_MENU
        assert mock_update.effective_user.id in auth_handler.authorized_users
        auth_handler.metrics.increment.assert_called_with('auth_success')
        
    @pytest.mark.asyncio
    async def test_auth_check_invalid_password(self, auth_handler, mock_update, mock_context):
        """Тест проверки неправильного пароля"""
        mock_update.message.text = "wrong_password"
        
        result = await auth_handler.auth_check(mock_update, mock_context)
        
        assert result == States.AUTH
        assert mock_update.effective_user.id not in auth_handler.authorized_users
        auth_handler.metrics.increment.assert_called_with('auth_failed')
        
    @pytest.mark.asyncio
    async def test_cancel(self, auth_handler, mock_update, mock_context):
        """Тест отмены авторизации"""
        result = await auth_handler.cancel(mock_update, mock_context)
        assert result == ConversationHandler.END
        
    @pytest.mark.asyncio
    async def test_check_access_authorized(self, auth_handler, mock_update):
        """Тест проверки доступа авторизованного пользователя"""
        auth_handler.authorized_users.add(mock_update.effective_user.id)
        result = await auth_handler.check_access(mock_update)
        assert result is True
        
    @pytest.mark.asyncio
    async def test_check_access_unauthorized(self, auth_handler, mock_update):
        """Тест проверки доступа неавторизованного пользователя"""
        result = await auth_handler.check_access(mock_update)
        assert result is False
        
    def test_is_authorized(self, auth_handler, mock_update):
        """Тест проверки статуса авторизации"""
        assert not auth_handler.is_authorized(mock_update.effective_user.id)
        
        auth_handler.authorized_users.add(mock_update.effective_user.id)
        assert auth_handler.is_authorized(mock_update.effective_user.id)
        
    def test_add_authorized_user(self, auth_handler, mock_update):
        """Тест добавления пользователя в список авторизованных"""
        user_id = mock_update.effective_user.id
        
        auth_handler.add_authorized_user(user_id)
        assert user_id in auth_handler.authorized_users
        
    def test_remove_authorized_user(self, auth_handler, mock_update):
        """Тест удаления пользователя из списка авторизованных"""
        user_id = mock_update.effective_user.id
        auth_handler.authorized_users.add(user_id)
        
        auth_handler.remove_authorized_user(user_id)
        assert user_id not in auth_handler.authorized_users 