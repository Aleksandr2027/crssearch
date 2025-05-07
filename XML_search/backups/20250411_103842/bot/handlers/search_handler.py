"""
Обработчик поиска
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler
from XML_search.search_handler import SearchHandler as CrsSearchHandler

class SearchHandler(BaseHandler):
    """Обработчик поиска"""
    
    def __init__(self):
        """Инициализация обработчика поиска"""
        super().__init__("search_handler")
        self.search_processor = CrsSearchHandler()
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Основной метод обработки запроса
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        return await self._handle_update(update, context)
        
    async def handle_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик inline-запросов
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
        """
        query = update.inline_query.query.strip()
        if not query:
            return
            
        try:
            # Выполняем поиск
            results = self.search_processor.search_with_transliteration(query)[:20]
            formatted_results = self.search_processor.format_inline_results(results, limit=20)
            
            # Отправляем результаты
            await update.inline_query.answer(
                formatted_results,
                cache_time=1,
                is_personal=True
            )
            
            # Обновляем метрики
            self.metrics.increment('inline_search_success')
            self.metrics.gauge('inline_search_results', len(results))
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке inline-запроса: {e}")
            self.metrics.increment('inline_search_errors')
            
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка поискового запроса
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        if not update.message or not update.message.text:
            return States.WAITING_SEARCH
            
        user_id = update.effective_user.id
        search_term = update.message.text.strip()
        
        # Отправляем сообщение о начале поиска
        processing_message = await update.message.reply_text(
            "🔍 Выполняю поиск...",
            parse_mode='Markdown'
        )
        
        try:
            # Выполняем поиск
            results = self.search_processor.search_with_transliteration(search_term)
            formatted_results = self.search_processor.format_results(results)
            
            if isinstance(formatted_results, str):
                # Если вернулась строка (сообщение об ошибке или слишком много результатов)
                await processing_message.edit_text(
                    formatted_results,
                    parse_mode='Markdown'
                )
            else:
                # Удаляем сообщение о поиске
                await processing_message.delete()
                
                # Отправляем каждый результат отдельным сообщением с кнопками
                for result in formatted_results:
                    await update.message.reply_text(
                        result['text'],
                        parse_mode='Markdown',
                        reply_markup=result['keyboard']
                    )
            
            # Обновляем метрики
            self.metrics.increment('search_success')
            self.metrics.gauge('search_results', len(results))
            
        except Exception as e:
            error_message = f"❌ Произошла ошибка при поиске: {str(e)}"
            self.logger.error(error_message)
            self.metrics.increment('search_errors')
            await processing_message.edit_text(error_message)
            
        return States.WAITING_SEARCH 