"""
Обработчик главного меню бота
"""

from typing import Optional, Any
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.export.export_manager import ExportManager
from ..states import States
from .base_handler import BaseHandler
from .auth_handler import AuthHandler
from XML_search.bot.config import BotConfig
import logging

class MenuHandler(BaseHandler):
    """Обработчик главного меню"""
    
    def __init__(self, 
                 config: BotConfig,
                 db_manager: Optional[DatabaseManager] = None,
                 metrics: Optional[MetricsManager] = None,
                 auth_handler: Optional[AuthHandler] = None,
                 logger: Optional[LogManager] = None,
                 cache: Optional[CacheManager] = None,
                 export_manager: Optional[ExportManager] = None):
        """
        Инициализация обработчика меню
        
        Args:
            config: Конфигурация бота
            db_manager: Менеджер базы данных
            metrics: Сборщик метрик
            auth_handler: Обработчик авторизации
            logger: Менеджер логирования
            cache: Менеджер кэша
            export_manager: Менеджер экспорта
        """
        super().__init__(config)
        self._db_manager = db_manager
        self.metrics = metrics or MetricsManager()
        self.auth_handler = auth_handler
        self.logger = logger or logging.getLogger(self.__class__.__module__)
        self.cache = cache or CacheManager(ttl=config.CACHE_TTL, max_size=config.CACHE_MAX_SIZE)
        self.export_manager = export_manager
        
        # Константы для кнопок меню
        self.BUTTON_COORD_SEARCH = 'Поиск СК по Lat/Lon'
        self.BUTTON_DESC_SEARCH = 'Поиск СК по описанию'
        self.BUTTON_MENU = '🔙 Главное меню'
        
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка команды /start и отображение главного меню
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        try:
            # Проверяем авторизацию
            if not await self.auth_handler.check_auth(update, context):
                return States.AUTH
            
            # Показываем главное меню
            await self.show_main_menu(update, context)
            return States.MAIN_MENU
            
        except Exception as e:
            self.logger.error(f"Ошибка в MenuHandler: {str(e)}")
            await self._handle_error(update, context, e)
            return States.ERROR
        
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Показать главное меню
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
        """
        user_id = update.effective_user.id
        self.logger.info(f"[MenuHandler.show_main_menu] user_id={user_id} — показ главного меню")
        self.log_access(user_id, 'show_main_menu')
        self.metrics.increment('main_menu_show')
        
        # Создаем клавиатуру главного меню
        keyboard = [
            [KeyboardButton(self.BUTTON_COORD_SEARCH)],
            [KeyboardButton(self.BUTTON_DESC_SEARCH)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🔍 Выберите тип поиска:",
            reply_markup=reply_markup
        )
        
    async def handle_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка команды /menu
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        self.logger.info(f"[MenuHandler.handle_menu_command] Вход: user_id={getattr(update.effective_user, 'id', None)}, text={getattr(update.message, 'text', None)}")
        try:
            # Проверяем авторизацию
            is_auth = await self.auth_handler.check_auth(update, context)
            self.logger.info(f"[MenuHandler.handle_menu_command] Авторизация: {is_auth}")
            if not is_auth:
                await update.message.reply_text("⚠️ Необходима авторизация. Пожалуйста, введите пароль:")
                return States.AUTH
            await self.show_main_menu(update, context)
            self.logger.info(f"[MenuHandler.handle_menu_command] Главное меню показано пользователю {getattr(update.effective_user, 'id', None)}")
            return States.MAIN_MENU
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды /menu: {e}")
            self.metrics.increment('menu_command_error')
            await self._handle_error(update, context, e)
            return States.ERROR
            
    async def handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка команды /help
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        try:
            help_text = (
                "📋 Доступные команды:\n\n"
                "/start - Начать работу с ботом\n"
                "/menu - Показать главное меню\n"
                "/help - Показать это сообщение\n"
                "/search - Начать поиск\n"
                "/export - Экспортировать результаты\n"
                "/cancel - Отменить текущую операцию\n"
                "/logout - Выйти из системы"
            )
        
            await update.message.reply_text(help_text)
            return States.MAIN_MENU
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды /help: {e}")
            self.metrics.increment('help_command_error')
            await self._handle_error(update, context, e)
            return States.ERROR
            
    async def handle_cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка команды /cancel
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        try:
            # Очищаем состояние пользователя
            await self.clear_user_state(context)
            
            await update.message.reply_text(
                "🔄 Текущая операция отменена.\n"
                "Используйте /menu для возврата в главное меню."
            )
            return States.MAIN_MENU
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды /cancel: {e}")
            self.metrics.increment('cancel_command_error')
            await self._handle_error(update, context, e)
            return States.ERROR

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Публичный обработчик команды /start для регистрации в BotManager
        """
        self.logger.info(f"[MenuHandler.start] Вход: user_id={getattr(update.effective_user, 'id', None)}, text={getattr(update.message, 'text', None)}")
        result = await self.handle_menu_command(update, context)
        self.logger.info(f"[MenuHandler.start] Результат: {result}")
        return result

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Публичный обработчик команды /help для регистрации в BotManager
        """
        return await self.handle_help_command(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Публичный обработчик команды /cancel для регистрации в BotManager
        """
        return await self.handle_cancel_command(update, context)

    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Публичный обработчик для главного меню в ConversationHandler
        """
        return await self.handle_menu_command(update, context)