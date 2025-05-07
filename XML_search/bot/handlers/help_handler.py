"""
Обработчик команды /help
"""

from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from XML_search.bot.handlers.base_handler import BaseHandler
from XML_search.bot.config import BotConfig
from XML_search.bot.states import States
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager

class HelpHandler(BaseHandler):
    """Обработчик команды /help"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
        """
        super().__init__(config)
        self.messages = config.MESSAGES
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды /help
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        try:
            if not update.effective_user:
                return
            # Логируем начало обработки
            self.log_access(update.effective_user.id, 'help_command')
            # Отправляем сообщение с помощью
            await update.effective_message.reply_text(
                self.messages['help'],
                parse_mode='Markdown'
            )
            # Сбрасываем состояние
            await self.clear_user_state(context)
        except Exception as e:
            self.logger.error(f"Ошибка в HelpHandler.handle: {e}", exc_info=True)
            self.metrics.increment('help_command_error')
            error_message = self.messages.get('error', 'Произошла ошибка. Пожалуйста, попробуйте позже.')
            if update and update.effective_message:
                await update.effective_message.reply_text(error_message) 