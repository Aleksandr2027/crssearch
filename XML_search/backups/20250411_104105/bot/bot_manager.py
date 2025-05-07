"""
Менеджер бота
"""

import logging
import signal
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, InlineQueryHandler, CallbackQueryHandler
from telegram.request import HTTPXRequest
from XML_search.config import TelegramConfig, LogConfig
from .handlers.auth_handler import AuthHandler
from .handlers.menu_handler import MenuHandler
from .handlers.search_handler import SearchHandler
from .handlers.coord_handler import CoordHandler
from .handlers.export_handler import ExportHandler
from .states.conversation_states import States
from .utils.log_utils import bot_logger
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.config_enhanced import EnhancedConfig

class BotManager:
    """Класс для управления ботом"""
    
    def __init__(self):
        """Инициализация менеджера бота"""
        self.logger = bot_logger
        self.metrics = MetricsCollector()
        self.config = EnhancedConfig.load_from_file('config/enhanced_config.json')
        
        # Отключаем логирование HTTP-запросов
        logging.getLogger('httpx').setLevel(logging.WARNING)
        
        # Инициализация обработчиков
        self.auth_handler = AuthHandler()
        self.menu_handler = MenuHandler()
        self.coord_handler = CoordHandler()
        self.search_handler = SearchHandler()
        self.export_handler = ExportHandler()
        
        # Флаг завершения работы
        self.is_shutting_down = False
        
    async def initialize(self) -> bool:
        """
        Инициализация бота
        
        Returns:
            True если инициализация успешна
        """
        try:
            # Создаем кастомный request объект с увеличенными таймаутами
            request = HTTPXRequest(
                connection_pool_size=100,
                read_timeout=30.0,
                write_timeout=30.0,
                connect_timeout=30.0,
                pool_timeout=30.0
            )
            
            # Создаем приложение
            self.application = (
                Application.builder()
                .token(TelegramConfig.TOKEN)
                .request(request)
                .build()
            )
            
            # Добавляем обработчики
            self._add_handlers()
            
            self.logger.info("Бот успешно инициализирован")
            self.metrics.increment('bot_initialized')
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации бота: {e}")
            self.metrics.increment('bot_init_errors')
            return False
            
    def _add_handlers(self) -> None:
        """Добавление обработчиков команд"""
        # Создаем обработчик диалога
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.auth_handler.start)],
            states={
                States.AUTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handler.auth_check)
                ],
                States.MAIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.menu_handler.handle_menu)
                ],
                States.WAITING_COORDINATES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.coord_handler.handle)
                ],
                States.WAITING_SEARCH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_handler.handle)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.auth_handler.cancel),
                CommandHandler("start", self.auth_handler.start)
            ],
        )
        
        # Добавляем обработчики
        self.application.add_handler(conv_handler)
        self.application.add_handler(InlineQueryHandler(self.search_handler.handle_inline))
        self.application.add_handler(
            CallbackQueryHandler(self.export_handler.handle_callback, pattern=r"^export_")
        )
        
    async def run(self) -> None:
        """Запуск бота"""
        try:
            self.logger.info("Запуск бота...")
            self.metrics.increment('bot_start')
            
            # Запускаем бота
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске бота: {e}")
            self.metrics.increment('bot_run_errors')
            
    async def shutdown(self) -> None:
        """Корректное завершение работы бота"""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            self.logger.info("Начало корректного завершения работы...")
            
            try:
                # Останавливаем только если приложение запущено
                if hasattr(self, 'application') and self.application.running:
                    # Останавливаем приложение
                    await self.application.stop()
                    
                    # Корректное завершение асинхронных генераторов
                    loop = asyncio.get_event_loop()
                    if not loop.is_closed():
                        await loop.shutdown_asyncgens()
                        
                    # Завершаем работу приложения
                    await self.application.shutdown()
                    
                    self.logger.info("Бот успешно остановлен")
                    self.metrics.increment('bot_shutdown_success')
                else:
                    self.logger.info("Бот уже остановлен")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при остановке бота: {e}")
                self.metrics.increment('bot_shutdown_errors')
                
    def __del__(self):
        """Деструктор класса"""
        if not self.is_shutting_down:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.shutdown())
            loop.close() 