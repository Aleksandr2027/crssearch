"""
Менеджер бота с интеграцией всех компонентов
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from XML_search.enhanced.config_enhanced import EnhancedConfig
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.bot.states import States
import inspect

from XML_search.bot.handlers.auth_handler import AuthHandler
from XML_search.bot.handlers.export_handler import ExportHandler
from XML_search.bot.handlers.search_handler import SearchHandler
from XML_search.bot.handlers.menu_handler import MenuHandler
from XML_search.bot.handlers.coord_handler import CoordHandler
from XML_search.bot.config import BotConfig


class BotManager:
    """Менеджер бота с интеграцией всех компонентов"""
    
    def __init__(self, token: str, config_path: str):
        """
        Инициализация менеджера
        
        Args:
            token: Токен Telegram бота
            config_path: Путь к конфигурационному файлу
        """
        self.token = token
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsManager()
        
        # Инициализация конфигурации и базовых компонентов
        self.enhanced_config = EnhancedConfig(config_path=config_path)
        self.config = BotConfig(
            BOT_TOKEN=token,
            DB_HOST=self.enhanced_config.database.host,
            DB_PORT=self.enhanced_config.database.port,
            DB_NAME=self.enhanced_config.database.dbname,
            DB_USER=self.enhanced_config.database.user,
            DB_PASSWORD=self.enhanced_config.database.password,
            LOG_LEVEL=self.enhanced_config.logging.level,
            LOG_FORMAT=self.enhanced_config.logging.format,
            LOG_FILE=self.enhanced_config.logging.file,
            CACHE_ENABLED=self.enhanced_config.cache.enabled,
            CACHE_TTL=self.enhanced_config.cache.ttl,
            CACHE_MAX_SIZE=self.enhanced_config.cache.max_size,
            SEARCH_MAX_RESULTS=self.enhanced_config.search.max_results,
            SEARCH_TIMEOUT=self.enhanced_config.search.timeout
        )
        self.db_manager = DatabaseManager(self.enhanced_config)
        self.cache_manager = CacheManager()
        
        # Инициализация обработчиков
        self._init_handlers()
        
        # Настройка приложения
        self.application = self._setup_application()
        
        self.logger.info("BotManager успешно инициализирован")
        self.metrics.start_operation('bot_manager.init')
        
    def _init_handlers(self) -> None:
        """Инициализация всех обработчиков"""
        try:
            # Основные обработчики
            self.auth_handler = AuthHandler(self.config)
            self.menu_handler = MenuHandler(
                config=self.config,
                db_manager=self.db_manager,
                metrics=self.metrics,
                auth_handler=self.auth_handler
            )
            self.coord_handler = CoordHandler(self.config)
            
            # Обработчики с расширенной функциональностью
            self.export_handler = ExportHandler(
                self.config
            )
            
            self.search_handler = SearchHandler(
                self.config
            )
            
            self.metrics.start_operation('handlers.initialized')
            self.logger.info("Все обработчики успешно инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации обработчиков: {e}")
            self.metrics.start_operation('handlers.init_error')
            raise
            
    def _setup_application(self) -> Application:
        """Настройка приложения Telegram-бота"""
        application = Application.builder().token(self.token).build()
        import logging as pylogging
        pylogging.getLogger("telegram.ext").setLevel(pylogging.DEBUG)
        # Глобальный обработчик ошибок
        async def global_error_handler(update, context):
            self.logger.error(f"[GLOBAL ERROR HANDLER] Exception: {context.error}", exc_info=True)
            if update and hasattr(update, 'message') and update.message:
                await update.message.reply_text(f"Произошла непредвиденная ошибка: {context.error}")
        application.add_error_handler(global_error_handler)
        # Глобальный логгер всех апдейтов (переносим в самый высокий group, чтобы не мешал обработчикам)
        async def log_all_updates(update, context):
            self.logger.info(f"[ALL UPDATES] Получен update: {update}")
        application.add_handler(MessageHandler(filters.ALL, log_all_updates), group=99)
        return application
            
    def _register_handlers(self, application: Application) -> None:
        """Регистрация всех обработчиков"""
        try:
            # Сначала ConversationHandler (FSM)
            conv_handler = self._setup_conversation_handler()
            self.logger.info(f"[BotManager] ConversationHandler states: {conv_handler.states}")
            application.add_handler(conv_handler, group=0)
            # Затем отдельные команды (fallback)
            application.add_handler(CommandHandler("start", self.menu_handler.start), group=1)
            application.add_handler(CommandHandler("help", self.menu_handler.help), group=1)
            # Логируем регистрацию
            self.logger.info("ConversationHandler и CommandHandler /start, /help зарегистрированы")
            # Глобальный логирующий обработчик для всех апдейтов
            def global_debug_log_all_messages(update, context):
                import logging
                logger = logging.getLogger("global_debug_all_messages")
                logger.info(f"[GLOBAL DEBUG] Получено сообщение: update={update}, message={getattr(update, 'message', None)}")
                return None
            application.add_handler(MessageHandler(filters.ALL, global_debug_log_all_messages), group=2)
            # Регистрация callback-обработчиков
            self._register_callback_handlers(application)
            self.metrics.start_operation('handlers.registered')
            self.logger.info("Все обработчики успешно зарегистрированы")
        except Exception as e:
            self.logger.error(f"Ошибка при регистрации обработчиков: {e}")
            self.metrics.start_operation('handlers.registration_error')
            raise
            
    def _setup_conversation_handler(self) -> ConversationHandler:
        """Настройка обработчика диалогов"""
        async def debug_log_all_messages(update, context):
            import logging
            logger = logging.getLogger("debug_all_messages")
            logger.info(f"[DEBUG] Получено сообщение: update={update}, message={getattr(update, 'message', None)}")
            return States.AUTH
        # Оборачиваем все handler'ы логирующими функциями
        def log_wrapper(handler, name):
            async def wrapper(update, context):
                self.logger.info(f"[FSM HANDLER] Вход в {name}: user_id={getattr(update.effective_user, 'id', None)}, text={getattr(update.message, 'text', None)}")
                return await handler(update, context)
            return wrapper
        return ConversationHandler(
            entry_points=[
                CommandHandler("start", log_wrapper(self.menu_handler.start, "menu_handler.start")),
                CommandHandler("auth", log_wrapper(self.auth_handler.auth_start, "auth_handler.auth_start"))
            ],
            states={
                States.AUTH: [
                    MessageHandler(
                        filters.TEXT,
                        log_wrapper(self.auth_handler.auth_check, "auth_handler.auth_check")
                    ),
                    MessageHandler(
                        filters.ALL,
                        debug_log_all_messages
                    )
                ],
                States.MAIN_MENU: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        log_wrapper(self.menu_handler.handle_menu, "menu_handler.handle_menu")
                    )
                ],
                States.SEARCH_INPUT: [
                    CallbackQueryHandler(
                        log_wrapper(self.search_handler.handle_filter_callback, "search_handler.handle_filter_callback"),
                        pattern=r"^filter_"
                    ),
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        log_wrapper(self.search_handler.handle_filter_input, "search_handler.handle_filter_input")
                    )
                ],
                States.WAITING_EXPORT: [
                    CallbackQueryHandler(
                        log_wrapper(self.export_handler.handle_export_callback, "export_handler.handle_export_callback"),
                        pattern=r"^export_"
                    ),
                    CallbackQueryHandler(
                        log_wrapper(self.export_handler.handle_format_callback, "export_handler.handle_format_callback"),
                        pattern=r"^format_"
                    )
                ],
                States.COORD_INPUT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        log_wrapper(self.coord_handler.handle_coordinates, "coord_handler.handle_coordinates")
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", log_wrapper(self.menu_handler.cancel, "menu_handler.cancel")),
                CommandHandler("help", log_wrapper(self.menu_handler.help, "menu_handler.help"))
            ],
            name="main_conversation"
        )

    def _register_callback_handlers(self, application: Application) -> None:
        """Регистрация обработчиков callback-запросов"""
        try:
            # Обработчики экспорта
            application.add_handler(
                CallbackQueryHandler(
                    self.export_handler.handle_export_callback,
                    pattern=r"^export_\w+:\d+"
                )
            )
            
            # Обработчики форматов экспорта
            application.add_handler(
                CallbackQueryHandler(
                    self.export_handler.handle_format_callback,
                    pattern=r"^format_\w+:\d+"
                )
            )
            
            # Обработчики поиска
            application.add_handler(
                CallbackQueryHandler(
                    self.search_handler.handle_filter_callback,
                    pattern=r"^filter_\w+:\w+"
                )
            )
            
            # Обработчики пагинации
            application.add_handler(
                CallbackQueryHandler(
                    self.search_handler.handle_pagination_callback,
                    pattern=r"^page:\d+"
                )
            )
            
            # Обработчики отмены
            application.add_handler(
                CallbackQueryHandler(
                    self.menu_handler.cancel,
                    pattern=r"^cancel_"
                )
            )
            
            self.metrics.start_operation('callbacks.registered')
            self.logger.info("Callback-обработчики успешно зарегистрированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка при регистрации callback-обработчиков: {e}")
            self.metrics.start_operation('callbacks.registration_error')
            raise

    async def _handle_callback_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Обработка ошибок в callback-запросах"""
        try:
            if update.callback_query:
                # Получаем данные о callback
                callback_data = update.callback_query.data
                user_id = update.effective_user.id
                
                # Логируем ошибку
                self.logger.error(
                    f"Ошибка в callback: {context.error}",
                    extra={
                        "user_id": user_id,
                        "callback_data": callback_data,
                        "error": str(context.error)
                    }
                )
                
                # Обновляем метрики
                self.metrics.record_operation("callback_errors")
                self.metrics.record_operation(f"callback_errors.{callback_data.split('_')[0]}")
                
                # Уведомляем пользователя
                await update.callback_query.answer(
                    "Произошла ошибка. Попробуйте еще раз.",
                    show_alert=True
                )
                
                # Возвращаемся в предыдущее состояние
                state_data = context.user_data.get("state_data")
                if state_data and state_data.previous_state:
                    state_data.rollback()
                    return state_data.current_state
                    
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ошибки callback: {e}")
            self.metrics.record_operation("callback_error_handler_errors")

    def _setup_metrics(self) -> None:
        """Настройка сбора метрик"""
        # Метрики обработчиков
        self.metrics.gauge("handlers.active", len(self.application.handlers))
        
        # Метрики состояний
        self.metrics.gauge(
            "states.active",
            len(self._conversation_handler.states)
        )
        
        # Метрики callback
        callback_patterns = [
            "export",
            "format",
            "filter",
            "page",
            "confirm",
            "cancel"
        ]
        
        for pattern in callback_patterns:
            self.metrics.gauge(f"callbacks.{pattern}", 0)
            self.metrics.gauge(f"callbacks.{pattern}_errors", 0)
            
    def _save_conversation_state(self) -> None:
        """Сохранение состояния диалогов"""
        if self.config.PERSISTENT_STORAGE_ENABLED:
            try:
                # Сохраняем состояния в базу
                self.db_manager.save_conversation_states(
                    self._conversation_handler.states
                )
                self.logger.info("Состояния диалогов сохранены")
            except Exception as e:
                self.logger.error(f"Ошибка сохранения состояний: {e}")
                self.metrics.record_operation("state_save_errors")

    def run(self) -> None:
        """Запуск бота"""
        try:
            self.logger.info("Запуск бота (polling)...")
            self.application.run_polling()
            self.logger.info("Polling завершён.")
        except Exception as e:
            self.logger.error(f"Ошибка при запуске бота: {e}")
            self.metrics.start_operation('bot.start_error')
            raise
            
    def stop(self) -> None:
        """Остановка бота"""
        try:
            self.logger.info("Остановка бота...")
            self.application.stop()
            self.db_manager.close()
            self.metrics.record_operation('bot.stop')
            
        except Exception as e:
            self.logger.error(f"Ошибка при остановке бота: {e}")
            self.metrics.record_operation('bot.stop_error')
            raise 