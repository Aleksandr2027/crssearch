"""
Обработчик главного меню бота
"""

from typing import Optional, Any
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
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
        await self.log_access(user_id, 'show_main_menu')
        
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
        
        # Приветственное сообщение
        await update.message.reply_text(
            "Добро пожаловать! Я бот для поиска и экспорта систем координат."
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
                # Сообщение об авторизации отправляет только auth_handler, здесь не дублируем
                return States.AUTH
            context.user_data['auth_prompted'] = False
            # Обработка выбора пункта меню
            if update.message and update.message.text:
                choice = update.message.text
                if choice == self.BUTTON_COORD_SEARCH:
                    # Подробная инструкция по форматам координат
                    keyboard = [[KeyboardButton(self.BUTTON_MENU)]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        "📍 Введите координаты в формате 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'\n\n"
                        "Поддерживаемые форматы ввода:\n"
                        "1. Десятичные градусы: 55.7558;37.6173 или 55.7558$37.6173 или 55.7558%37.6173\n"
                        "2. Градусы и минуты: 55 45.348;37 37.038 или 55 45.348$37 37.038 или 55 45.348%37 37.038\n"
                        "3. Градусы, минуты и секунды: 55 45 20.88;37 37 2.28 или 55 45 20.88$37 37 2.28 или 55 45 20.88%37 37 2.28\n"
                        "4. С обозначениями: 55°45'20.88\";37°37'2.28\" или 55°45'20.88\"$37°37'2.28\" или 55°45'20.88\"%37°37'2.28\"\n\n"
                        "Разделитель между широтой и долготой - точка с запятой (;) или знак доллара ($) или знак процента (%)",
                        reply_markup=reply_markup
                    )
                    return States.COORD_INPUT
                elif choice == self.BUTTON_DESC_SEARCH:
                    keyboard = [[KeyboardButton(self.BUTTON_MENU)]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
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
                        reply_markup=reply_markup
                    )
                    # Inline-кнопка быстрого поиска
                    inline_keyboard = [[
                        InlineKeyboardButton(
                            "🔍 Быстрый поиск в текущем чате",
                            switch_inline_query_current_chat=""
                        )
                    ]]
                    inline_markup = InlineKeyboardMarkup(inline_keyboard)
                    await update.message.reply_text(
                        "Нажмите кнопку ниже для быстрого поиска:",
                        reply_markup=inline_markup
                    )
                    return States.SEARCH_INPUT
                elif choice == self.BUTTON_MENU:
                    await self.show_main_menu(update, context)
                    return States.MAIN_MENU
            # Если не выбрано ничего — показать главное меню
            await self.show_main_menu(update, context)
            return States.MAIN_MENU
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды /menu: {e}")
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
            await self._handle_error(update, context, e)
            return States.ERROR

    async def handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка неизвестной команды.
        """
        user_id = update.effective_user.id if update.effective_user else "unknown"
        self.logger.info(f"[MenuHandler.handle_unknown_command] user_id={user_id}, text={update.message.text}")
        await update.message.reply_text(
            "🤷‍♂️ Неизвестная команда. Пожалуйста, используйте кнопки меню или доступные команды."
        )
        # Вместо того чтобы просто показывать меню, мы возвращаем состояние,
        # чтобы ConversationHandler мог правильно на него среагировать.
        # Если это вызывается из fallback другого ConversationHandler, то тот должен
        # иметь MAIN_MENU в map_to_parent или обработать его.
        await self.show_main_menu(update, context) # Сначала покажем меню
        return States.MAIN_MENU # Затем вернем состояние

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Публичный обработчик команды /start для регистрации в BotManager
        """
        self.logger.info(f"[MenuHandler.start] Вход: user_id={getattr(update.effective_user, 'id', None)}, text={getattr(update.message, 'text', None)}")
        try:
            # Этот вызов является основной операцией в блоке try
            return await self.handle_menu_command(update, context)
        except Exception as e:
            self.logger.error(f"Ошибка при обработке команды /menu: {str(e)} ({type(e).__name__})", exc_info=True)
            error_message_text = "Произошла ошибка при отображении меню. Попробуйте /start."
            try:
                # Предпочитаем ответить на сообщение из callback_query, если оно есть
                if update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_text(error_message_text)
                # Иначе, если есть прямое сообщение (хотя в данном потоке его, скорее всего, нет)
                elif update.message:
                    await update.message.reply_text(error_message_text)
                # Как крайний случай, отправляем новое сообщение в чат
                elif update.effective_chat:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message_text)
                else:
                    # Если некуда отправить, просто логируем
                    self.logger.error("Не удалось отправить сообщение об ошибке пользователю в MenuHandler.start: нет контекста для ответа.")
            except Exception as send_e:
                self.logger.error(f"Также не удалось отправить уведомление об ошибке в MenuHandler.start: {send_e}", exc_info=True)
            return States.ERROR

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

    async def show_main_menu_and_return_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Показывает главное меню и возвращает состояние MAIN_MENU. Используется в fallbacks."""
        await self.show_main_menu(update, context)
        return States.MAIN_MENU