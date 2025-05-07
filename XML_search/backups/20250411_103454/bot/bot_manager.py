"""
Основной класс управления Telegram ботом
"""

import logging
import signal
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from telegram.request import HTTPXRequest
import win32api
import win32con
from pathlib import Path

from .config import BotConfig
from .handlers.auth_handler import AuthHandler
from .handlers.menu_handler import MenuHandler
from .handlers.search_handler import SearchHandler
from .handlers.coord_handler import CoordHandler
from .handlers.export_handler import ExportHandler
from .states.conversation_states import States

from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.config import TelegramConfig
from XML_search.enhanced.config_enhanced import EnhancedConfig
from .utils.log_utils import bot_logger

class BotManager:
    """Менеджер Telegram бота"""
    
    def __init__(self):
        """Инициализация менеджера бота"""
        # Заменяем старое логирование на новое
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
        
        # Приложение бота
        self.application = None
        
    async def initialize(self):
        """Инициализация бота"""
        if not TelegramConfig.TOKEN:
            self.logger.log_error(
                ValueError("TELEGRAM_TOKEN не найден в конфигурации!"),
                {'config_file': '.env'}
            )
            return False
            
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
            self._setup_handlers()
            
            self.logger.log_debug("Бот успешно инициализирован")
            self.metrics.increment('bot_initialized')
            return True
            
        except Exception as e:
            self.logger.log_error(e, {
                'stage': 'initialization',
                'config': self.config.__dict__
            })
            self.metrics.increment('bot_init_errors')
            return False
            
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        try:
            # Основной обработчик диалога
            conv_handler = ConversationHandler(
                entry_points=[
                    CommandHandler("start", self.auth_handler.start),
                    CommandHandler("auth", self.auth_handler.auth_start)
                ],
                states={
                    States.AUTH: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self.auth_handler.auth_check
                        )
                    ],
                    States.MAIN_MENU: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self.menu_handler.handle_menu
                        )
                    ],
                    States.WAITING_COORDINATES: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self.coord_handler.process_coordinates
                        )
                    ],
                    States.WAITING_SEARCH: [
                        MessageHandler(
                            filters.TEXT & ~filters.COMMAND,
                            self.search_handler.handle_search
                        )
                    ]
                },
                fallbacks=[
                    CommandHandler("cancel", self.auth_handler.cancel),
                    CommandHandler("start", self.auth_handler.start)
                ],
            )
            
            # Добавляем обработчики
            self.application.add_handler(conv_handler)
            self.application.add_handler(self.search_handler.get_inline_handler())
            self.application.add_handler(self.export_handler.get_callback_handler())
            
            self.logger.log_debug("Обработчики успешно настроены")
            
        except Exception as e:
            self.logger.log_error(e, {
                'stage': 'handler_setup',
                'handlers': [
                    'conv_handler',
                    'inline_handler',
                    'callback_handler'
                ]
            })
            raise
        
    async def shutdown(self):
        """Корректное завершение работы бота"""
        if self.is_shutting_down:
            return
            
        self.logger.log_debug("Начало корректного завершения работы...")
        self.is_shutting_down = True
        
        try:
            if self.application and self.application.running:
                # Останавливаем приложение
                self.application.stop_running()
                await self.application.stop()
                await self.application.shutdown()
                
                # Закрываем соединения
                self.search_handler.close_connections()
                
                # Завершаем асинхронные генераторы
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    await loop.shutdown_asyncgens()
                    
                self.logger.log_debug("Бот успешно остановлен")
                self.metrics.increment('bot_shutdown_success')
            else:
                self.logger.log_debug("Бот уже остановлен")
                
        except Exception as e:
            self.logger.log_error(e, {
                'stage': 'shutdown',
                'is_running': self.application.running if self.application else False
            })
            self.metrics.increment('bot_shutdown_errors')
            
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        def win32_handler(sig):
            if sig in [win32con.CTRL_C_EVENT, win32con.CTRL_BREAK_EVENT]:
                self.logger.log_debug("Получен сигнал завершения работы")
                asyncio.create_task(self.shutdown())
                return True
            return False
            
        # Устанавливаем обработчик для Windows
        if hasattr(win32api, 'SetConsoleCtrlHandler'):
            win32api.SetConsoleCtrlHandler(win32_handler, True)
            
    async def run(self):
        """Запуск бота"""
        if not await self.initialize():
            return
            
        self.setup_signal_handlers()
        self.logger.log_debug("Бот запущен")
        self.metrics.increment('bot_start')
        
        try:
            await self.application.run_polling(
                allowed_updates=Application.ALL_TYPES,
                drop_pending_updates=True
            )
        except KeyboardInterrupt:
            self.logger.log_debug("Получен сигнал прерывания")
            await self.shutdown()
        except Exception as e:
            self.logger.log_error(e, {
                'stage': 'runtime',
                'uptime': self.metrics.get_gauge('bot_uptime')
            })
            self.metrics.increment('bot_runtime_errors')
            await self.shutdown() 