"""
Менеджер бота с интеграцией всех компонентов
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    InlineQueryHandler
)
from telegram.request import HTTPXRequest
import re

from XML_search.enhanced.config_enhanced import EnhancedConfig
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.search.search_engine import EnhancedSearchEngine
from XML_search.bot.states import States
import inspect

from XML_search.bot.handlers.auth_handler import AuthHandler
from XML_search.bot.handlers.export_handler import ExportHandler
from XML_search.bot.handlers.search_handler import SearchHandler
from XML_search.bot.handlers.menu_handler import MenuHandler
from XML_search.bot.handlers.coord_handler import CoordHandler
from XML_search.bot.config import BotConfig
from XML_search.bot.handlers.help_handler import HelpHandler
from XML_search.bot.handlers.error_handler import ErrorHandler
from XML_search.bot.handlers.coord_export_handler import CoordExportHandler
from XML_search.bot.keyboards.main_keyboard import MainKeyboard


class BotManager:
    """Менеджер бота с интеграцией всех компонентов"""
    
    def __init__(self, token: str, config_path: str):
        """
        Инициализация менеджера
        
        Args:
            token: Токен Telegram бота
            config_path: Путь к конфигурационному файлу
        """
        self._stop_event = asyncio.Event()
        self.token = token
        self.config_path = config_path
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
        self.db_manager = DatabaseManager(config=self.enhanced_config.database)
        self.cache_manager = CacheManager()
        
        # Инициализация обработчиков
        self._init_handlers()
        
        # Настройка приложения
        self.application = self._setup_application()
        self._register_handlers(self.application)
        
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
            
            # Добавляем ссылку на menu_handler в auth_handler для показа главного меню после авторизации
            self.auth_handler.menu_handler = self.menu_handler
            
            self.coord_handler = CoordHandler(
                self.config,
                db_manager=self.db_manager,
                metrics=self.metrics,
                logger=self.logger,
                cache=self.cache_manager
            )
            self.coord_handler.menu_handler = self.menu_handler
            
            # Создаем экземпляр EnhancedSearchEngine
            enhanced_search_engine_instance = EnhancedSearchEngine(
                db_config=self.enhanced_config.database,
                db_manager=self.db_manager,
                metrics=self.metrics,
                logger=LogManager().get_logger("EnhancedSearchEngine_in_BotManager"),
                cache=self.cache_manager
            )
            
            # Обработчики с расширенной функциональностью
            self.export_handler = ExportHandler(
                self.config
            )
            
            self.search_handler = SearchHandler(
                self.config,
                db_manager=self.db_manager,
                metrics=self.metrics,
                logger=self.logger,
                cache=self.cache_manager,
                menu_handler=self.menu_handler,
                enhanced_search_engine=enhanced_search_engine_instance
            )
            
            self.help_handler = HelpHandler(self.config)
            self.error_handler = ErrorHandler(self.config)
            self.coord_export_handler = CoordExportHandler(self.config, self.db_manager, menu_handler=self.menu_handler)
            
            # Передаем coord_export_handler в search_handler
            self.search_handler.coord_export_handler = self.coord_export_handler

            self.metrics.start_operation('handlers.initialized')
            self.logger.info("Все обработчики успешно инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации обработчиков: {e}")
            self.metrics.start_operation('handlers.init_error')
            raise
            
    async def _initialize_services_after_app(self): # Новый метод для явной инициализации
        """Инициализирует зависимые сервисы, такие как DBManager, после инициализации PTB Application."""
        self.logger.info("[BotManager._initialize_services_after_app] Начало инициализации зависимых сервисов (например, БД)...")
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                self.logger.info("[BotManager._initialize_services_after_app] Вызов db_manager.initialize()...")
                await self.db_manager.initialize()
                self.logger.info("[BotManager._initialize_services_after_app] db_manager.initialize() успешно завершен.")
                # Можно добавить инициализацию других сервисов здесь, если они появятся
            else:
                self.logger.warning("[BotManager._initialize_services_after_app] db_manager не определен, инициализация БД пропущена.")
            self.logger.info("[BotManager._initialize_services_after_app] Инициализация зависимых сервисов успешно завершена.")
        except Exception as e:
            self.logger.error(f"[BotManager._initialize_services_after_app] Ошибка при инициализации зависимых сервисов: {e}", exc_info=True)
            # В зависимости от критичности, можно либо проигнорировать, либо пробросить исключение
            # Для DB это критично, так что лучше пробросить или остановить бота
            raise # Пробрасываем ошибку дальше, чтобы прервать запуск бота

    def _setup_application(self) -> Application:
        """Создает и настраивает экземпляр PTB Application."""
        # === Инициализация PTB Application ===
        self.logger.info("Настройка PTB Application...")

        try:
            http_request_args = {}
            telegram_settings = self.enhanced_config.telegram_bot if hasattr(self.enhanced_config, 'telegram_bot') else None

            if telegram_settings:
                if telegram_settings.connect_timeout is not None:
                    http_request_args['connect_timeout'] = telegram_settings.connect_timeout
                if telegram_settings.read_timeout is not None:
                    http_request_args['read_timeout'] = telegram_settings.read_timeout
                if telegram_settings.write_timeout is not None:
                    http_request_args['write_timeout'] = telegram_settings.write_timeout
                
                if telegram_settings.connection_pool:
                    limits = {}
                    if telegram_settings.connection_pool.max_connections is not None:
                        limits['max_connections'] = telegram_settings.connection_pool.max_connections
                    if telegram_settings.connection_pool.max_keepalive_connections is not None:
                        limits['max_keepalive_connections'] = telegram_settings.connection_pool.max_keepalive_connections
                    if telegram_settings.connection_pool.keepalive_expiry is not None:
                        limits['keepalive_expiry'] = telegram_settings.connection_pool.keepalive_expiry
                    if limits: # Если есть хотя бы один лимит
                        http_request_args['pool_limits'] = limits
            
            http_request = HTTPXRequest(**http_request_args) if http_request_args else None
            self.logger.info(f"HTTPXRequest будет создан с аргументами: {http_request_args if http_request_args else 'по умолчанию'}")

            application_builder = Application.builder().token(self.token)
            
            if http_request:
                application_builder.request(http_request)

            if getattr(self.config, 'PROXY_URL', None):
                proxy_config = {
                    'url': getattr(self.config, 'PROXY_URL'),
                    'username': getattr(self.config, 'PROXY_USERNAME', None),
                    'password': getattr(self.config, 'PROXY_PASSWORD', None)
                }
                # Удаляем None значения, чтобы HTTPXRequest не получил пустые строки или None там, где не ожидает
                proxy_config = {k: v for k, v in proxy_config.items() if v is not None}
                if proxy_config.get('url'): # Убедимся, что URL все еще есть
                    self.logger.info(f"Настройка прокси: {proxy_config['url']}")
                    application_builder.proxy(proxy_config) # Используем обновленный proxy_config
                else:
                    self.logger.info("URL прокси отсутствует после фильтрации, прокси не будет использован.")
            else:
                self.logger.info("Прокси не настроен или URL прокси отсутствует.")

            # Настройки из enhanced_config для ApplicationBuilder
            if telegram_settings:
                if telegram_settings.concurrent_updates is not None:
                    self.logger.info(f"Установка concurrent_updates: {telegram_settings.concurrent_updates}")
                    application_builder.concurrent_updates(telegram_settings.concurrent_updates)
                # if telegram_settings.rate_limiter: # Закомментировано, так как не используется
                #     self.logger.warning("Настройка RateLimiter пока не реализована полностью.")

            self.application = application_builder.build()

            self.logger.info("PTB Application успешно настроен.")
            return self.application
        except Exception as e:
            self.logger.error(f"Ошибка при настройке PTB Application: {e}")
            self.metrics.start_operation('bot.start_error')
            raise
            
    def _register_handlers(self, application: Application) -> None:
        """Регистрация всех обработчиков"""
        try:
            # Сначала ConversationHandler (FSM)
            conv_handler = self._setup_conversation_handler()
            application.add_handler(conv_handler)
            self.logger.info("ConversationHandler зарегистрирован")
            
            # Регистрируем InlineQueryHandler для поиска
            application.add_handler(InlineQueryHandler(self.search_handler.handle_inline))
            self.logger.info("InlineQueryHandler зарегистрирован")
            
            # Регистрируем обработчик для inline экспорта (вне ConversationHandler)
            application.add_handler(CallbackQueryHandler(
                self.search_handler.handle_inline_export_callback, 
                pattern=r'^inline_export_'
            ))
            self.logger.info("Inline Export CallbackQueryHandler зарегистрирован")

        except Exception as e:
            self.logger.error(f"Ошибка при регистрации обработчиков: {e}", exc_info=True)
            raise

    def _setup_conversation_handler(self) -> ConversationHandler:
        """Собирает и возвращает главный ConversationHandler, управляющий всеми состояниями FSM."""
        
        # Добавляем все нужные обработчики в `menu_handler`, чтобы они были доступны
        # Это не самый чистый способ, но он позволяет избежать рефакторинга всех вызовов
        # и сохранить существующую структуру `ConversationHandler`.
        self.menu_handler.auth_handler = self.auth_handler
        self.menu_handler.coord_handler = self.coord_handler
        self.menu_handler.coord_export_handler = self.coord_export_handler
        self.menu_handler.search_handler = self.search_handler
        
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.menu_handler.start),
                CommandHandler("menu", self.menu_handler.handle_menu),
                CallbackQueryHandler(self.menu_handler.handle_menu, pattern='^back_to_main_menu$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.menu_handler.handle_menu)
            ],
            states={
                States.MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.menu_handler.handle_menu_command)],
                States.AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_handler.auth_check)],
                States.COORD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.coord_handler.handle_coord_input)],
                States.WAITING_EXPORT: [
                    CallbackQueryHandler(self.coord_export_handler.handle_export_callback, pattern=r'^export_.*'),
                ],
                States.SEARCH_INPUT: [
                    # Сначала обрабатываем кнопку возврата в меню
                    MessageHandler(filters.Text([MainKeyboard.BUTTON_MENU]), self.menu_handler.show_main_menu_and_return_state),
                    # Затем обрабатываем inline результаты (игнорируем их)
                    MessageHandler(filters.Regex(r'^🔷 SRID:'), self.search_handler.handle_inline_result_message),
                    # Остальные текстовые сообщения обрабатываем как поисковые запросы
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_handler.handle_filter_input),
                ],
            },
            fallbacks=[
                MessageHandler(filters.Regex(f"^{re.escape(MainKeyboard.BUTTON_MENU)}$"), self.menu_handler.show_main_menu_and_return_state),
                CommandHandler("cancel", self.menu_handler.cancel),
                CommandHandler("help", self.menu_handler.help),
                MessageHandler(filters.TEXT, self.menu_handler.handle_unknown_command),
            ],
            map_to_parent={
                States.MAIN_MENU: States.MAIN_MENU,
                ConversationHandler.END: ConversationHandler.END
            }
        )
        return conv_handler

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
                start_time = self.metrics.start_operation("callback_errors")
                start_time = self.metrics.start_operation(f"callback_errors.{callback_data.split('_')[0]}")
                
                # Уведомляем пользователя
                await update.callback_query.answer(
                    "Произошла ошибка. Попробуйте еще раз.",
                    show_alert=True
                )
                    
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ошибки callback: {e}")
            start_time = self.metrics.start_operation("callback_error_handler_errors")

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
            
    async def stop(self) -> None:
        """Инициирует корректную остановку бота, используя более гранулярные методы PTB."""
        self.logger.info("🛑 Инициирую остановку компонентов Telegram-бота...")
        if hasattr(self, '_stop_event'):
            self._stop_event.set() # Сигнализируем основной корутине о завершении

        if hasattr(self, 'application') and self.application:
            try:
                self.logger.info("Вызов application.stop()...")
                await self.application.stop() # Останавливает обработку обновлений
                self.logger.info("application.stop() завершен.")

                if hasattr(self.application, 'updater') and self.application.updater and self.application.updater.running:
                    self.logger.info("Вызов application.updater.stop()...")
                    await self.application.updater.stop() # Останавливает поллинг
                    self.logger.info("application.updater.stop() завершен.")
                else:
                    self.logger.info("Updater не был запущен или уже остановлен.")

                self.logger.info("Вызов application.shutdown()...")
                await self.application.shutdown() # Выполняет задачи очистки
                self.logger.info("application.shutdown() завершен.")
            except Exception as e:
                self.logger.error(f"Ошибка при остановке PTB Application: {e}", exc_info=True)
        else:
            self.logger.warning("Экземпляр приложения Telegram (self.application) не найден для остановки.")

        # Синхронные задачи по очистке
        if hasattr(self, 'metrics') and self.metrics:
            self.logger.info("Сохранение финальных метрик (синхронная часть)...")
            try:
                if hasattr(self.metrics, 'save') or hasattr(self.metrics, 'flush'):
                    save_method = getattr(self.metrics, 'save', None) or getattr(self.metrics, 'flush', None)
                    if save_method and callable(save_method):
                        save_method()
                    self.logger.info("Финальные метрики сохранены (синхронно).")
            except Exception as e:
                self.logger.error(f"Ошибка при синхронном сохранении метрик: {e}", exc_info=True)
        
        self.logger.info("Процесс остановки BotManager.stop() завершен.")

    async def run_bot_async_lifecycle(self):
        """Обрабатывает полный асинхронный жизненный цикл бота, используя гранулярные вызовы PTB."""
        if not self.application:
            self.logger.error("Приложение не инициализировано в BotManager перед вызовом run_bot_async_lifecycle.")
            return
        try:
            self.logger.info("Асинхронный запуск: ПЕРЕД application.initialize()...")
            await self.application.initialize()
            self.logger.info("Асинхронный запуск: ПОСЛЕ application.initialize()...")

            self.logger.info("Асинхронный запуск: ПЕРЕД _initialize_services_after_app()...")
            await self._initialize_services_after_app()
            self.logger.info("Асинхронный запуск: ПОСЛЕ _initialize_services_after_app()...")
            
            # Сброс события остановки перед запуском, если оно было установлено ранее
            if hasattr(self, '_stop_event'):
                 self._stop_event.clear()
            else: # На всякий случай, если _stop_event не было инициализировано (не должно происходить)
                self.logger.warning("ДИАГНОСТИКА: _stop_event не был инициализирован до clear(), создаю новый.")
                self._stop_event = asyncio.Event()

            # --- НАЧАЛО БЛОКА ДИАГНОСТИКИ ---
            if hasattr(self, '_stop_event'):
                self.logger.info(f"ДИАГНОСТИКА: _stop_event существует. Тип: {type(self._stop_event)}, Значение: {self._stop_event}")
                if self._stop_event is None:
                     self.logger.error("ДИАГНОСТИКА: _stop_event существует, НО ЕГО ЗНАЧЕНИЕ None!")
            else:
                self.logger.error("ДИАГНОСТИКА: _stop_event НЕ СУЩЕСТВУЕТ НЕПОСРЕДСТВЕННО ПЕРЕД ПРОВЕРКОЙ is_set()!")
            # --- КОНЕЦ БЛОКА ДИАГНОСТИКИ ---

            if self._stop_event.is_set(): # Проверяем событие остановки
                self.logger.warning("Событие остановки (_stop_event) установлено ПЕРЕД запуском. Бот не будет запущен.")
                return

            if self.application.updater:
                self.logger.info("Асинхронный запуск: Запуск application.updater.start_polling()...")
                await self.application.updater.start_polling(
                    allowed_updates=self.config.ALLOWED_UPDATES,
                    drop_pending_updates=self.config.DROP_PENDING_UPDATES
                )
            else:
                self.logger.error("application.updater не инициализирован! Невозможно запустить поллинг.")
                return # Не можем продолжать без updater

            self.logger.info("Асинхронный запуск: Запуск application.start()...")
            await self.application.start() # Начинает обработку входящих обновлений
            
            self.logger.info(f"Бот запущен и работает. Ожидание события остановки (_stop_event: {self._stop_event})...")
            await self._stop_event.wait() # Держим корутину живой, пока не будет вызван stop()
            self.logger.info("Событие _stop_event получено, run_bot_async_lifecycle готовится к завершению.")

        except asyncio.CancelledError:
            self.logger.info("run_bot_async_lifecycle был отменен (вероятно, из main.py).")
            # Логика остановки будет вызвана из блока finally в main.py, который вызовет self.stop()
            raise 

        except Exception as e:
            self.logger.error(f"Критическая ошибка в run_bot_async_lifecycle: {e}", exc_info=True)
            raise 
        
        finally:
            self.logger.info("run_bot_async_lifecycle завершается (блок finally).")

# Пример использования, если бы мы хотели запускать полностью асинхронно:
# async def run_bot_async():

# if __name__ == '__main__':
#     asyncio.run(run_bot_async()) 