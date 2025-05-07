"""
Базовый класс для обработчиков бота
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from telegram import Update
from telegram.ext import ContextTypes
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector
from ..utils.log_utils import bot_logger

class BaseHandler(ABC):
    """Базовый класс для всех обработчиков с поддержкой логирования"""
    
    def __init__(self, name: str = None):
        """
        Инициализация базового обработчика
        
        Args:
            name: Имя обработчика для логирования
        """
        self.name = name or self.__class__.__name__
        self.logger = bot_logger
        self.metrics = MetricsCollector()
        
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Основной метод обработки запроса
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            
        Returns:
            Результат обработки запроса
        """
        pass
        
    async def handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Базовый метод обработки обновлений с логированием
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Результат обработки
        """
        if not update.effective_user:
            return None
            
        user_id = update.effective_user.id
        handler_name = self.__class__.__name__
        
        try:
            # Логируем начало обработки
            self.logger.log_access(
                user_id,
                f"{handler_name}_start",
                {
                    'message': update.message.text if update.message else None,
                    'handler': handler_name
                }
            )
            
            # Засекаем время выполнения
            with self.metrics.timing(f'{handler_name}_execution'):
                result = await self._handle_update(update, context)
            
            # Логируем успешное завершение
            self.logger.log_access(
                user_id,
                f"{handler_name}_success",
                {
                    'result': str(result) if result else None,
                    'handler': handler_name
                }
            )
            
            return result
            
        except Exception as e:
            # Логируем ошибку
            self.logger.log_error(e, {
                'user_id': user_id,
                'handler': handler_name,
                'message': update.message.text if update.message else None
            })
            
            # Отправляем сообщение об ошибке пользователю
            error_message = self._get_user_error_message(e)
            if update.message:
                await update.message.reply_text(error_message)
            
            # Обновляем метрики
            self.metrics.increment(f'{handler_name}_errors')
            
            return None
            
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Метод для переопределения в дочерних классах
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Результат обработки
        """
        raise NotImplementedError
        
    def _get_user_error_message(self, error: Exception) -> str:
        """
        Получение сообщения об ошибке для пользователя
        
        Args:
            error: Исключение
            
        Returns:
            Сообщение для пользователя
        """
        # Можно кастомизировать сообщения для разных типов ошибок
        error_messages = {
            'ValueError': 'Неверный формат данных. Пожалуйста, проверьте ввод.',
            'DatabaseError': 'Произошла ошибка при работе с базой данных. Попробуйте позже.',
            'ConnectionError': 'Проблема с подключением. Попробуйте позже.',
            'TimeoutError': 'Превышено время ожидания. Попробуйте позже.',
        }
        
        error_type = type(error).__name__
        return error_messages.get(
            error_type,
            'Произошла ошибка. Пожалуйста, попробуйте позже.'
        )
        
    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Отладочное логирование
        
        Args:
            message: Сообщение
            data: Дополнительные данные
        """
        self.logger.log_debug(f"[{self.__class__.__name__}] {message}", data)
        
    def log_access(self, user_id: int, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование действий пользователя
        
        Args:
            user_id: ID пользователя
            action: Действие
            details: Детали действия
        """
        details = details or {}
        details['handler'] = self.__class__.__name__
        self.logger.log_access(user_id, action, details)
        
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование ошибки
        
        Args:
            error: Исключение
            context: Контекст ошибки
        """
        context = context or {}
        context['handler'] = self.__class__.__name__
        self.logger.log_error(error, context)
        
    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """
        Обработка ошибок
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            error: Объект ошибки
        """
        self.logger.error(f"Ошибка в обработчике {self.name}: {str(error)}")
        self.metrics.increment(f"handler_errors.{self.name}")
        
        # Отправляем сообщение пользователю об ошибке
        error_message = "Произошла ошибка при обработке запроса. Попробуйте позже."
        if update.effective_message:
            await update.effective_message.reply_text(error_message)
            
    def _log_metrics(self, operation: str, duration: float) -> None:
        """
        Логирование метрик операции
        
        Args:
            operation: Название операции
            duration: Длительность выполнения
        """
        metric_name = f"handler.{self.name}.{operation}"
        self.metrics.record_timing(metric_name, duration)
        self.metrics.increment(f"{metric_name}.count")
        
        if self.metrics.log_metrics:
            self.logger.debug(
                f"Operation {operation} completed in {duration:.2f}s"
            ) 