"""
Базовый обработчик для всех обработчиков бота
"""

from abc import ABC, abstractmethod
import logging
import time
from typing import Any, Optional, Dict, List
from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.bot.config import BotConfig
from XML_search.bot.states import States
from XML_search.bot.utils.format_utils import format_error_message
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class BaseHandler(ABC):
    """Базовый класс для всех обработчиков"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
        """
        self.config = config
        self._db_manager = None
        self._init_lock = asyncio.Lock()
        
        # Инициализация логгера
        self.logger = logging.getLogger(self.__class__.__module__)
        
        # Инициализация метрик
        self.metrics = MetricsManager()
        
        # Инициализация кэша
        self.cache = CacheManager(
            ttl=config.CACHE_TTL,
            max_size=config.CACHE_MAX_SIZE
        )
        
    @property
    async def db_manager(self) -> DatabaseManager:
        """
        Получение менеджера базы данных
        
        Returns:
            DatabaseManager: Менеджер базы данных
        """
        if self._db_manager is None:
            async with self._init_lock:
                if self._db_manager is None:
                    await self._init_db_manager()
        return self._db_manager
        
    async def _init_db_manager(self) -> None:
        """
        Инициализация менеджера базы данных
        """
        try:
            self._db_manager = DatabaseManager(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                database=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD
            )
            await self._db_manager.initialize()
            self.logger.info("Менеджер базы данных успешно инициализирован")
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации менеджера базы данных: {e}")
            raise
            
    async def handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка обновления от Telegram
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        try:
            if not update.effective_user:
                return
                
            # Логируем доступ
            await self.log_access(update.effective_user.id, 'update')
            
            # Обрабатываем обновление
            await self.handle(update, context)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке обновления: {e}", exc_info=True)
            await self.metrics.record_operation('update_error', 'count')
            raise
            
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        raise NotImplementedError("Метод handle должен быть реализован в подклассе")

    async def close(self) -> None:
        """Закрытие обработчика"""
        if self._db_manager:
            await self._db_manager.close()

    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Метод для реализации в дочерних классах
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Результат обработки
        """
        pass
    
    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """
        Обработка ошибки
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            error: Исключение
        """
        error_message = format_error_message(error)
        logger.error(f"Ошибка в обработчике: {str(error)}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(error_message)
    
    async def log_access(self, user_id: int, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование доступа пользователя
        
        Args:
            user_id: ID пользователя
            action: Действие пользователя
            details: Дополнительные детали (опционально)
        """
        log_data = {'user_id': user_id, 'action': action}
        if details:
            log_data.update(details)
        self.logger.info(f"Access log: {log_data}")
    
    async def _ensure_user_data(self, context: CallbackContext) -> None:
        """
        Асинхронная инициализация данных пользователя если они отсутствуют
        
        Args:
            context: Контекст обработчика
        """
        if not context.user_data:
            context.user_data.update({
                'state': None,
                'search_results': [],
                'selected_srid': None,
                'export_format': None,
                'authenticated': False,
                'last_activity': time.time()
            })
    
    async def _get_user_data(self, context: CallbackContext) -> Dict[str, Any]:
        """
        Асинхронное получение данных пользователя из контекста
        
        Args:
            context: Контекст обработчика
            
        Returns:
            Данные пользователя
        """
        await self._ensure_user_data(context)
        return context.user_data
    
    async def _update_user_data(self, context: CallbackContext, data: Dict[str, Any]) -> None:
        """
        Асинхронное обновление данных пользователя в контексте
        
        Args:
            context: Контекст обработчика
            data: Новые данные
        """
        await self._ensure_user_data(context)
        context.user_data.update(data)
        context.user_data['last_activity'] = time.time()

    async def get_user_state(self, context: ContextTypes.DEFAULT_TYPE) -> Optional[States]:
        """
        Асинхронное получение состояния пользователя
        
        Args:
            context: Контекст обработчика
            
        Returns:
            Состояние пользователя или None
        """
        user_data = await self._get_user_data(context)
        return user_data.get('state')
    
    async def set_user_state(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        state: States,
        update: Optional[Update] = None
    ) -> None:
        """
        Асинхронная установка состояния пользователя
        
        Args:
            context: Контекст обработчика
            state: Новое состояние
            update: Объект обновления Telegram (для user_id)
        """
        await self._ensure_user_data(context)
        context.user_data['state'] = state
        context.user_data['last_activity'] = time.time()
        user_id = update.effective_user.id if update and update.effective_user else None
        self.logger.info(f"set_user_state: user_id={user_id}, state={state}, user_data={context.user_data}")
    
    async def clear_user_state(self, context: ContextTypes.DEFAULT_TYPE, update: Optional[Update] = None) -> None:
        """
        Асинхронная очистка состояния пользователя
        
        Args:
            context: Контекст обработчика
            update: Объект обновления Telegram (для user_id)
        """
        if context.user_data:
            context.user_data.pop('state', None)
            context.user_data['last_activity'] = time.time()
            user_id = update.effective_user.id if update and update.effective_user else None
            self.logger.info(f"clear_user_state: user_id={user_id}, user_data={context.user_data}")
    
    @asynccontextmanager
    async def db_operation(self):
        """
        Асинхронный контекстный менеджер для операций с базой данных
        
        Yields:
            DatabaseManager: Инициализированный менеджер базы данных
        """
        db = await self.db_manager
        try:
            yield db
        except Exception as e:
            logger.error(f"Ошибка при работе с базой данных: {e}")
            await self.metrics.record_operation('db_operation_errors', 'count')
            raise 