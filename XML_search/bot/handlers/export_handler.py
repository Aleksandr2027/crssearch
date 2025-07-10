"""
Обработчик экспорта систем координат
"""

from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext, CommandHandler
from XML_search.bot.handlers.base_handler import BaseHandler
from XML_search.bot.config import BotConfig
from XML_search.bot.states import States
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.export.export_manager import ExportManager

class ExportHandler(BaseHandler):
    """Обработчик экспорта систем координат"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
        """
        super().__init__(config)
        self.messages = config.MESSAGES
        self.export_config = config.EXPORT_CONFIG
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка экспорта
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        try:
            if not update.effective_user:
                return
            # Логируем начало обработки
            self.log_access(update.effective_user.id, 'export_command')
            # Проверяем авторизацию
            user_data = await self._get_user_data(context)
            if not user_data.get('authenticated', False):
                await update.effective_message.reply_text(self.messages['auth_request'])
                await self.set_user_state(context, States.AUTH, update)
                return
            # Показываем меню экспорта
            await self._show_export_menu(update, context)
        except Exception as e:
            self.logger.error(f"Ошибка в ExportHandler.handle: {e}", exc_info=True)
            self.metrics.increment('export_command_error')
            error_message = self.messages.get('error', 'Произошла ошибка. Пожалуйста, попробуйте позже.')
            if update and update.effective_message:
                await update.effective_message.reply_text(error_message)
        
    async def handle_callback(self, update: Update, context: CallbackContext) -> None:
        """
        Обработка callback-запросов
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
        """
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "back_to_menu":
                await query.message.edit_reply_markup(reply_markup=None)
                await self.clear_user_state(context)
                return
                
            elif query.data.startswith("export_"):
                format_name = query.data.replace("export_", "")
                
                # Получаем данные пользователя
                user_data = await self._get_user_data(context)
                srid = user_data.get('selected_srid')
                
                if not srid:
                    await query.message.edit_text(
                        "⚠️ Сначала выберите систему координат для экспорта.\n"
                        "Используйте команду /search для поиска."
                    )
                    return
                
                # Выполняем экспорт
                try:
                    async with self.db_operation() as db:
                        export_manager = ExportManager(db)
                        result = await export_manager.export(srid, format_name)
                        
                        # Отправляем результат
                        await query.message.edit_text(
                            f"✅ Результат экспорта в формате {format_name.upper()}:\n\n"
                            f"```\n{result}\n```",
                            parse_mode='Markdown'
                        )
                        
                        # Добавляем кнопку возврата в меню
                        keyboard = [[
                            InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")
                        ]]
                        await query.message.edit_reply_markup(
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        
                except Exception as e:
                    self.logger.error(f"Ошибка при экспорте: {e}")
                    await query.message.edit_text(
                        f"❌ Ошибка при экспорте: {str(e)}\n"
                        "Попробуйте другой формат или обратитесь к администратору."
                    )
                    
        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback: {e}")
            self.metrics.increment('export_callback_errors')
            await self._handle_error(update, context, e)
        
    async def _show_export_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Показ меню экспорта
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        if not update.effective_chat:
            return
            
        keyboard = []
        for format_name, format_config in self.export_config.items():
            keyboard.append([
                InlineKeyboardButton(
                    format_config['display_name'],
                    callback_data=f"export_{format_name}"
                )
            ])
            
            # Добавляем кнопку возврата в меню
            keyboard.append([
                InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")
            ])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_chat.send_message(
            "Выберите формат экспорта:",
            reply_markup=reply_markup
        )
        
        # Устанавливаем состояние
        await self.set_user_state(context, States.EXPORT_MENU, update)
        
    async def handle_export_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Публичный обработчик callback-запросов экспорта для ConversationHandler
        """
        return await self.handle_callback(update, context)

    async def handle_format_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Публичный обработчик callback-запросов формата экспорта для ConversationHandler
        """
        return await self.handle_callback(update, context) 
        
    def get_handler(self):
        """
        Получение обработчика для регистрации в BotManager
        
        Returns:
            Обработчик команды /export
        """
        return CommandHandler("export", self.handle) 