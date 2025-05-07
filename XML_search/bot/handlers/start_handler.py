"""
Обработчик команды /start
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

class StartHandler(BaseHandler):
    """Обработчик команды /start"""
    
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
        Обработка команды /start
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        try:
            if not update.effective_user:
                return
            # Логируем начало обработки
            self.log_access(update.effective_user.id, 'start_command')
            # Проверяем авторизацию
            user_data = await self._get_user_data(context)
            if not user_data.get('auth', False):
                await update.effective_message.reply_text(self.messages['start'])
                await self.set_user_state(context, States.AUTH, update)
            else:
                # Показываем главное меню
                await self._show_main_menu(update, context)
        except Exception as e:
            self.logger.error(f"Ошибка в StartHandler.handle: {e}", exc_info=True)
            self.metrics.increment('start_command_error')
            error_message = self.messages.get('error', 'Произошла ошибка. Пожалуйста, попробуйте позже.')
            if update and update.effective_message:
                await update.effective_message.reply_text(error_message)
            
    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Показ главного меню
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        if not update.effective_chat:
            return
            
        # Создаем клавиатуру главного меню
        keyboard = [
            ["🔍 Поиск по координатам"],
            ["📝 Поиск по описанию"],
            ["❓ Помощь"]
        ]
        
        reply_markup = {
            'keyboard': keyboard,
            'resize_keyboard': True
        }
        
        await update.effective_chat.send_message(
            "Выберите действие:",
            reply_markup=reply_markup
        ) 