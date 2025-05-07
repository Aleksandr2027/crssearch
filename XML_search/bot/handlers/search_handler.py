"""
Обработчик поиска систем координат
"""

from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.bot.states import States
from XML_search.bot.handlers.base_handler import BaseHandler
from XML_search.bot.config import BotConfig

class SearchHandler(BaseHandler):
    """Обработчик поиска систем координат"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
        """
        super().__init__(config)
        self.messages = config.MESSAGES
        self.items_per_page = 5  # Количество результатов на странице
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка поиска
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        if not update.effective_user:
            return
            
        # Логируем начало обработки
        self.log_access(update.effective_user.id, 'search_command')
        
        # Проверяем авторизацию
        user_data = await self._get_user_data(context)
        if not user_data.get('auth', False):
            await update.effective_message.reply_text(self.messages['auth_request'])
            await self.set_user_state(context, States.AUTH, update)
            return
            
        # Показываем меню поиска
        await self._show_search_menu(update, context)
        
    async def _show_search_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Показ меню поиска
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        if not update.effective_chat:
            return
            
        keyboard = [
            [
                InlineKeyboardButton("🔍 Поиск по координатам", callback_data="search_coords"),
                InlineKeyboardButton("📝 Поиск по описанию", callback_data="search_desc")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_chat.send_message(
            "Выберите тип поиска:",
            reply_markup=reply_markup
        )
        
        # Устанавливаем состояние
        await self.set_user_state(context, States.SEARCH_MENU, update)
        
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка поискового запроса
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        try:
            if not update.message or not update.message.text:
                await update.message.reply_text(
                    "⚠️ Пожалуйста, введите текст для поиска."
                )
                return States.SEARCH_WAITING
                
            query = update.message.text.strip()
            
            # Проверяем минимальную длину запроса
            if len(query) < 3:
                await update.message.reply_text(
                    "⚠️ Запрос слишком короткий. Минимум 3 символа."
                )
                return States.SEARCH_WAITING
                
            # Выполняем поиск
            results = await self._perform_search(query, {})
            
            # Сохраняем результаты в контексте
            await self._update_user_data(
                context,
                {
                    'search_results': results,
                    'current_page': 0,
                    'query': query
                }
            )
            
            # Отображаем результаты
            await self._show_search_results(update, context, results)
            
            # Логируем успешный поиск
            self.log_access(
                update.effective_user.id,
                'search_completed',
                {'results_count': len(results)}
            )
            self.metrics.increment('search_success')
            
            return States.SEARCH_RESULTS
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке поиска: {e}")
            self.metrics.increment('search_errors')
            await self._handle_error(update, context, e)
            return States.SEARCH_ERROR
            
    async def _perform_search(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Выполнение поиска в базе данных
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска
            
        Returns:
            List[Dict[str, Any]]: Результаты поиска
        """
        try:
            # Временное решение: базовый поиск по LIKE
            async with self.db_operation() as db:
                search_query = """
                    SELECT srid, auth_name, auth_srid, srtext, proj4text
                    FROM spatial_ref_sys
                    WHERE srtext ILIKE %s
                    OR auth_name ILIKE %s
                    OR CAST(srid AS TEXT) = %s
                    ORDER BY srid
                    LIMIT 50
                """
                params = (f"%{query}%", f"%{query}%", query)
                results = await db.execute_query(search_query, params)
                
                # Форматируем результаты
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'srid': row['srid'],
                        'name': row['auth_name'],
                        'description': row['srtext'],
                        'proj4': row['proj4text']
                    })
                
                return formatted_results
            
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении поиска: {e}")
            self.metrics.increment('search_query_errors')
            raise
            
    async def _show_search_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, results: List[Dict[str, Any]]) -> None:
        """
        Отображение результатов поиска
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            results: Результаты поиска
        """
        if not results:
            await update.message.reply_text(
                "🔍 По вашему запросу ничего не найдено.\n"
                "Попробуйте изменить параметры поиска или ввести другой запрос."
            )
            return
            
        # Получаем текущую страницу
        user_data = await self._get_user_data(context)
        current_page = user_data.get('current_page', 0)
        
        # Пагинация результатов
        start_idx = current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_results = results[start_idx:end_idx]
        
        # Формируем сообщение с результатами
        message_text = "🔍 Результаты поиска:\n\n"
        for idx, result in enumerate(page_results, start=1):
            message_text += (
                f"{idx}. SRID: {result['srid']}\n"
                f"Название: {result['name']}\n"
                f"Описание: {result['description'][:100]}...\n\n"
            )
            
        # Создаем клавиатуру для навигации
        keyboard = []
        
        # Кнопки для выбора результата
        for idx, result in enumerate(page_results, start=1):
            keyboard.append([
                InlineKeyboardButton(
                    f"Выбрать {idx}",
                    callback_data=f"select_srid_{result['srid']}"
                )
            ])
            
        # Кнопки пагинации
        navigation = []
        if current_page > 0:
            navigation.append(
                InlineKeyboardButton("⬅️ Назад", callback_data="prev_page")
            )
        if end_idx < len(results):
            navigation.append(
                InlineKeyboardButton("Вперед ➡️", callback_data="next_page")
            )
        if navigation:
            keyboard.append(navigation)
            
        # Добавляем кнопку возврата в меню
        keyboard.append([
            InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup
        )

    async def handle_callback(self, update: Update, context: CallbackContext) -> States:
        """
        Обработка callback-запросов
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == "back_to_menu":
                await query.message.edit_reply_markup(reply_markup=None)
                return States.MAIN_MENU
                
            elif query.data == "prev_page":
                user_data = await self._get_user_data(context)
                current_page = user_data.get('current_page', 0)
                if current_page > 0:
                    await self._update_user_data(context, {'current_page': current_page - 1})
                    results = user_data.get('search_results', [])
                    await self._show_search_results(update, context, results)
                    
            elif query.data == "next_page":
                user_data = await self._get_user_data(context)
                current_page = user_data.get('current_page', 0)
                results = user_data.get('search_results', [])
                if (current_page + 1) * self.items_per_page < len(results):
                    await self._update_user_data(context, {'current_page': current_page + 1})
                    await self._show_search_results(update, context, results)
                    
            elif query.data.startswith("select_srid_"):
                srid = query.data.split("_")[-1]
                await self._update_user_data(context, {'selected_srid': srid})
                await query.message.edit_text(
                    f"✅ Выбрана система координат с SRID: {srid}\n"
                    "Выберите формат экспорта или вернитесь в меню.",
                    reply_markup=self._get_export_keyboard()
                )
                return States.EXPORT_FORMAT
                
            return States.SEARCH_RESULTS
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback: {e}")
            self.metrics.increment('callback_errors')
            await self._handle_error(update, context, e)
            return States.SEARCH_ERROR
            
    def _get_export_keyboard(self) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры для выбора формата экспорта
        
        Returns:
            InlineKeyboardMarkup: Клавиатура с форматами экспорта
        """
        keyboard = [
            [
                InlineKeyboardButton("Civil 3D", callback_data="export_civil3d"),
                InlineKeyboardButton("GMv20", callback_data="export_gmv20")
            ],
            [
                InlineKeyboardButton("GMv25", callback_data="export_gmv25")
            ],
            [
                InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Публичный обработчик поиска для ConversationHandler
        """
        return await self._handle_update(update, context)

    async def handle_filter_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Публичный обработчик callback-запросов для ConversationHandler
        """
        return await self.handle_callback(update, context)

    async def handle_pagination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Публичный обработчик callback-запросов для пагинации в ConversationHandler
        """
        return await self.handle_callback(update, context)

    async def handle_filter_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """
        Публичный обработчик текстового ввода фильтра для ConversationHandler
        """
        return await self.handle_search(update, context) 