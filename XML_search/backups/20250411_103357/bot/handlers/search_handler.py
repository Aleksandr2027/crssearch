"""
Обработчик поисковых запросов
"""

import time
from telegram import Update
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler
from ..keyboards.main_keyboard import MainKeyboard
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.search_handler import SearchHandler as CrsSearchHandler

class SearchHandler(BaseHandler):
    """Обработчик поисковых запросов"""
    
    def __init__(self, db_manager: DatabaseManager, metrics: MetricsCollector):
        """
        Инициализация обработчика поиска
        
        Args:
            db_manager: Менеджер базы данных
            metrics: Сборщик метрик
        """
        super().__init__("search_handler")
        self.db_manager = db_manager
        self.metrics = metrics
        self.main_keyboard = MainKeyboard()
        self.search_processor = CrsSearchHandler()
        
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка поискового запроса
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        start_time = time.time()
        
        try:
            if update.message.text in [self.main_keyboard.BUTTON_MENU]:
                if update.message.text == self.main_keyboard.BUTTON_MENU:
                    keyboard = self.main_keyboard.get_keyboard()
                    await update.message.reply_text(
                        "Выберите тип поиска:",
                        reply_markup=keyboard
                    )
                    return States.MAIN_MENU
                return States.WAITING_SEARCH
                
            if update.message.text.startswith('🔹 SRID:'):
                return States.WAITING_SEARCH
                
            processing_message = await update.message.reply_text(
                "🔍 Выполняю поиск...",
                parse_mode='Markdown'
            )
            
            try:
                search_term = update.message.text.strip()
                with self.metrics.timing('search_duration'):
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
            
        except Exception as e:
            await self._handle_error(update, context, e)
            return States.ERROR
            
        finally:
            self._log_metrics('process', time.time() - start_time) 