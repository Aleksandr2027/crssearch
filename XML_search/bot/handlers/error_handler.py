"""
Обработчик ошибок
"""

from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from XML_search.bot.handlers.base_handler import BaseHandler
from XML_search.bot.config import BotConfig
from XML_search.bot.states import States
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager

class ErrorHandler(BaseHandler):
    """Обработчик ошибок"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
        """
        super().__init__(config)
        self.messages = config.MESSAGES
        
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка ошибок
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        try:
            error = context.error
            self.logger.error(f"Ошибка в обработчике: {error}", exc_info=True)
            self.metrics.increment('error_handled')
            
            # Формируем сообщение об ошибке
            error_message = self.messages.get('error', 'Произошла ошибка. Пожалуйста, попробуйте позже.').format(error=str(error))
            
            # Отправляем сообщение об ошибке
            if update and update.effective_message:
                await update.effective_message.reply_text(error_message)
            elif update and update.effective_chat:
                await update.effective_chat.send_message(error_message)
                
            # Сбрасываем состояние
            if context.user_data:
                await self.clear_user_state(context)
                
        except Exception as e:
            # Используем базовый логгер, если основной недоступен
            print(f"Критическая ошибка в обработчике ошибок: {e}")
            self.metrics.increment('error_handler_failed')
            
            # Пытаемся отправить сообщение об ошибке
            try:
                if update and update.effective_chat:
                    await update.effective_chat.send_message(
                        "Произошла критическая ошибка. Пожалуйста, попробуйте позже."
                    )
            except:
                pass
                
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка обновления
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        await self.handle_error(update, context) 