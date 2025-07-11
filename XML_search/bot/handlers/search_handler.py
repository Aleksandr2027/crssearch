"""
Обработчик поиска систем координат
"""

import os
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackContext, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.transliterator import Transliterator
from XML_search.bot.states import States
from XML_search.bot.handlers.base_handler import BaseHandler
from XML_search.bot.config import BotConfig
from XML_search.enhanced.search.search_engine import EnhancedSearchEngine
from XML_search.bot.keyboards.inline_keyboard import get_export_keyboard_for_srid
from XML_search.bot.keyboards.main_keyboard import MainKeyboard
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from telegram import InputFile
import re # Импортируем re для функции экранирования
import uuid
import logging
from XML_search.bot.handlers.coord_export_handler import CoordExportHandler

# Вспомогательная функция для экранирования специальных символов MarkdownV2
def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2."""
    if not text:
        return ""
    # Список символов для экранирования согласно документации Telegram Bot API
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

class SearchHandler(BaseHandler):
    """Обработчик поиска систем координат"""
    
    # ОПРЕДЕЛЯЕМ _log_wrapper КАК МЕТОД КЛАССА
    def _log_wrapper(self, handler_func, name):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = getattr(update.effective_user, 'id', None) if update.effective_user else None
            self._logger.info(f"[SearchFSM] {name}: user_id={user_id}, state={context.user_data.get('state') if context.user_data else 'N/A'}")
            try:
                result = await handler_func(update, context)
                if isinstance(result, States):
                    self._logger.info(f"[SearchFSM] {name}: new_state={result}, user_id={user_id}")
                return result
            except Exception as e:
                self._logger.error(f"[SearchFSM] {name}: ОШИБКА={e}, user_id={user_id}", exc_info=True)
                if update.callback_query:
                    try:
                        await update.callback_query.answer("Произошла ошибка при обработке вашего запроса.", show_alert=True)
                    except Exception: pass
                elif update.message:
                    try:
                        await update.message.reply_text("Произошла ошибка. Попробуйте позже или обратитесь к администратору.")
                    except Exception: pass
                return States.MAIN_MENU
        return wrapper

    def __init__(self, config: BotConfig, db_manager=None, metrics=None, logger=None, cache=None, menu_handler=None, enhanced_search_engine: Optional[EnhancedSearchEngine] = None):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
            db_manager: Менеджер базы данных
            metrics: Менеджер метрик
            logger: Менеджер логирования
            cache: Менеджер кэша
            menu_handler: Обработчик меню
            enhanced_search_engine: Улучшенный поисковый движок
        """
        super().__init__(config)
        self.messages = config.MESSAGES
        self.items_per_page = 5  # Количество результатов на странице
        self._db_manager = db_manager
        self._metrics = metrics or MetricsManager()
        self._logger = logger or LogManager().get_logger(__name__)
        self.cache = cache or CacheManager()
        self.menu_handler = menu_handler
        self.transliterator = Transliterator()  # Добавляем транслитератор
        self.enhanced_search_engine = enhanced_search_engine
        self.output_dir = getattr(config, 'OUTPUT_DIR', 'output')
        os.makedirs(self.output_dir, exist_ok=True)
        self.coord_export_handler: Optional[CoordExportHandler] = None # Добавляем атрибут
        
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
        await self.log_access(update.effective_user.id, 'search_command')
        
        # Проверяем авторизацию
        user_data = await self._get_user_data(context)
        if not user_data.get('authenticated', False):
            await update.effective_message.reply_text(self.messages['auth_request'])
            await self.set_user_state(context, States.AUTH, update)
            return
            
        # Показываем меню поиска
        await self._show_search_menu(update, context)
        
        # Убедимся, что обработчик экспорта готов
        if self.coord_export_handler and not self.coord_export_handler._exporters:
            await self.coord_export_handler.setup_exporters()
        
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
        await self.set_user_state(context, States.SEARCH_INPUT, update)
        
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка поискового запроса
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        if update.message and update.message.text and update.message.text.strip().startswith("🔷 SRID:"):
            self._logger.info(f"[_handle_update] Игнорирование 'эха' от выбора инлайн-результата: {update.message.text[:100]}...")
            current_fsm_state = await self.get_user_state(context)
            # Если состояние не найдено или некорректно, можно вернуть состояние по умолчанию для поиска.
            return current_fsm_state if current_fsm_state in [States.SEARCH_INPUT, States.SEARCH_RESULTS] else States.SEARCH_INPUT

        query_type = context.user_data.get("query_type", "description")
        current_filters = context.user_data.get("search_filters", {})
        
        try:
            if not update.message or not update.message.text:
                await update.message.reply_text(
                    "⚠️ Пожалуйста, введите текст для поиска."
                )
                return States.SEARCH_INPUT
                
            query = update.message.text.strip()
            
            # Проверяем минимальную длину запроса
            if len(query) < 3:
                await update.message.reply_text(
                    "⚠️ Запрос слишком короткий. Минимум 3 символа."
                )
                return States.SEARCH_INPUT
                
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
            await self.log_access(
                update.effective_user.id,
                'search_completed',
                {'results_count': len(results)}
            )
            if self._metrics:
                start_time = self._metrics.start_operation('search_success')
                await self._metrics.record_operation('search_success', start_time)
            
            return States.SEARCH_RESULTS
            
        except Exception as e:
            self._logger.error(f"Ошибка при обработке поиска: {e}")
            if hasattr(self, '_metrics') and self._metrics:
                await self._metrics.record_error('search_error', str(e))
            await update.message.reply_text(
                f"❌ Произошла ошибка при поиске систем координат: {e}\nПожалуйста, обратитесь к администратору."
            )
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
            if not self._db_manager:
                self._logger.error("Менеджер базы данных не инициализирован в SearchHandler!")
                raise RuntimeError("Менеджер базы данных не инициализирован. Обратитесь к администратору.")
            
            # Поиск в custom_geom (основные системы координат)
            search_query_custom = """
                SELECT cg.srid, cg.name, cg.deg, cg.info, cg.p
                FROM public.custom_geom cg
                WHERE (
                    cg.name ILIKE $1
                    OR cg.info ILIKE $2
                    OR CAST(cg.srid AS TEXT) = $3
                    OR cg.p ILIKE $4
                )
                ORDER BY 
                    CASE 
                        WHEN CAST(cg.srid AS TEXT) = $5 THEN 1
                        WHEN cg.name ILIKE $6 THEN 2
                        WHEN cg.info ILIKE $7 THEN 3
                        ELSE 4
                    END,
                    cg.srid
                LIMIT 50
            """
            params = (
                f"%{query}%", f"%{query}%", query, f"%{query}%",  # Основные поиски
                query, f"%{query}%", f"%{query}%"  # Для сортировки
            )
            
            results_custom = await self._db_manager.fetch(search_query_custom, *params)
            
            # Поиск UTM систем в spatial_ref_sys (только зоны северного полушария 32601-32660)
            search_query_utm = """
                SELECT srs.srid, srs.auth_name, srs.auth_srid, srs.srtext, srs.proj4text
                FROM public.spatial_ref_sys srs
                WHERE srs.srid BETWEEN 32601 AND 32660
                AND (
                    CAST(srs.srid AS TEXT) = $1
                    OR srs.srtext ILIKE $2
                    OR srs.proj4text ILIKE $3
                )
                ORDER BY srs.srid
                LIMIT 10
            """
            utm_params = (query, f"%{query}%", f"%{query}%")
            
            results_utm = await self._db_manager.fetch(search_query_utm, *utm_params)
            
            # Объединяем результаты
            formatted_results = []
            
            # Обрабатываем результаты из custom_geom
            for row in results_custom:
                # Определяем значение достоверности как в координатном поиске
                if str(row['srid']).startswith('326'):
                    p_value = "EPSG"
                else:
                    p_value = row['p'] if row['p'] is not None else "unknown"
                
                # Отладочная информация
                self._logger.debug(f"Custom result: srid={row['srid']}, name='{row['name']}', info='{row['info']}', p='{row['p']}'")
                
                formatted_results.append({
                    'srid': row['srid'],
                    'name': row['name'],  # Используем name из custom_geom
                    'info': row['info'],  # Используем info как описание
                    'p': p_value,  # Достоверность
                    'deg': row['deg'],  # Степень точности
                    # Для обратной совместимости с остальным кодом
                    'auth_name': p_value,
                    'auth_srid': row['srid'],
                    'srtext': row['info'],
                    'proj4text': row['info'],
                    'description': row['info']
                })
            
            # Обрабатываем UTM результаты из spatial_ref_sys
            for row in results_utm:
                srid = row['srid']
                # Вычисляем номер UTM зоны из SRID
                utm_zone = srid - 32600
                name = f"UTM zone {utm_zone}N"
                description = "WGS84"
                
                formatted_results.append({
                    'srid': srid,
                    'name': name,
                    'info': description,
                    'p': "EPSG",  # UTM системы всегда EPSG
                    'deg': 6,  # Стандартная степень для UTM
                    # Для обратной совместимости с остальным кодом
                    'auth_name': "EPSG",
                    'auth_srid': srid,
                    'srtext': description,
                    'proj4text': description,
                    'description': description
                })
            
            return formatted_results
            
        except Exception as e:
            self._logger.error(f"Ошибка при выполнении поиска: {e}")
            if hasattr(self, '_metrics') and self._metrics:
                await self._metrics.record_error('search_query', str(e))
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
            self._logger.error(f"Ошибка при обработке callback: {e}")
            if self._metrics:
                await self._metrics.record_error('callback_errors', str(e))
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

    def _get_export_keyboard_for_srid(self, srid: str) -> InlineKeyboardMarkup:
        """
        Создание клавиатуры с кнопками экспорта для конкретного SRID (inline режим)
        
        Args:
            srid: SRID системы координат
            
        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопками экспорта
        """
        keyboard = [
            [
                InlineKeyboardButton("📄 Civil3D", callback_data=f"inline_export_xml_Civil3D_{srid}"),
                InlineKeyboardButton("📋 GMv20", callback_data=f"inline_export_prj_GMV20_{srid}"),
                InlineKeyboardButton("📋 GMv25", callback_data=f"inline_export_prj_GMV25_{srid}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def handle_inline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка инлайн-запросов для поиска систем координат"""
        query = update.inline_query.query
        if not query or len(query) < 3:
            if self._logger:
                self._logger.debug(f"Инлайн-запрос слишком короткий или пустой: '{query}'")
            await update.inline_query.answer([], cache_time=10)
            return

        if self._logger:
            self._logger.info(f"Получен инлайн-запрос: '{query}' от пользователя {update.inline_query.from_user.id}")

        try:
            if self.enhanced_search_engine:
                results = await self.enhanced_search_engine.search(query, limit=10)
            else:
                if self._logger:
                    self._logger.error("EnhancedSearchEngine не инициализирован в SearchHandler для инлайн-поиска.")
                await update.inline_query.answer([], cache_time=10)
                return
                
            if self._logger:
                 self._logger.info(f"EnhancedSearchEngine вернул {len(results)} результатов для инлайн-запроса: '{query}'")

            articles = []
            for res in results:
                srid = res.get('srid')
                # Используем новые поля name и description
                name_val = str(res.get('name', f'SRID: {srid}'))
                description_val = str(res.get('description', 'Описание отсутствует'))
                # auth_name_val = str(res.get('auth_name', 'unknown')) # Больше не используем для достоверности

                # Получаем и форматируем значение 'p'
                p_value = res.get('p')
                p_value_str = "unknown" # Значение по умолчанию
                if isinstance(p_value, bool):
                    p_value_str = str(p_value).lower()
                elif p_value is not None: # Если не bool, но не None, берем как строку
                    p_value_str = str(p_value)

                # Экранирование для MarkdownV2
                escaped_srid = escape_markdown_v2(str(srid))
                escaped_name_val = escape_markdown_v2(name_val)
                escaped_description_val = escape_markdown_v2(description_val)
                escaped_p_val = escape_markdown_v2(p_value_str) # Экранируем отформатированное значение p

                input_text_content = (
                    f"🔷 *SRID:* `{escaped_srid}`\n"
                    f"📝 *Название:* {escaped_name_val}\n"
                    f"ℹ️ *Описание:* {escaped_description_val}\n"
                    f"✅ *Достоверность:* {escaped_p_val}" # Используем экранированное значение p
                )
                
                # Для отображения в списке инлайн-результатов:
                # title - краткое название
                # description - SRID и часть полного описания
                # Ограничиваем длину description для инлайн отображения
                inline_description_preview = f"SRID: {srid} ({description_val[:50]}{'...' if len(description_val) > 50 else ''})"

                articles.append(
                    InlineQueryResultArticle(
                        id=str(srid),
                        title=name_val, # Краткое имя для заголовка
                        description=inline_description_preview, # SRID и часть полного описания для подписи
                        input_message_content=InputTextMessageContent(
                            input_text_content,
                            parse_mode=ParseMode.MARKDOWN_V2
                        ),
                        reply_markup=self._get_export_keyboard_for_srid(str(srid)) # Добавляем кнопки экспорта
                    )
                )
            await update.inline_query.answer(articles, cache_time=300)
        except Exception as e:
            if self._logger:
                self._logger.exception(f"Ошибка при обработке инлайн-запроса '{query}': {e}")
            try:
                await update.inline_query.answer([], cache_time=5)
            except Exception as ex_answer: 
                 if self._logger:
                    self._logger.exception(f"Критическая ошибка при отправке ответа на инлайн-запрос: {ex_answer}")

    def _filter_problematic_variants(self, original_query: str, variants: List[str]) -> List[str]:
        """
        Фильтрует проблемные варианты, которые могут давать слишком широкие результаты
        
        Args:
            original_query: Исходный запрос пользователя
            variants: Список всех вариантов от транслитератора
            
        Returns:
            Отфильтрованный список вариантов
        """
        filtered_variants = []
        
        # Определяем, является ли исходный запрос полным (содержит номер зоны)
        original_lower = original_query.lower()
        has_zone_number = any(char.isdigit() and original_lower[i-1:i+1] in ['z1', 'з1', 'z2', 'з2', 'z3', 'з3', 'z4', 'з4', 'z5', 'з5', 'z6', 'з6', 'z7', 'з7', 'z8', 'з8', 'z9', 'з9'] or
                             (char.isdigit() and i > 0 and original_lower[i-1] in ['z', 'з']) 
                             for i, char in enumerate(original_lower))
        
        for variant in variants:
            variant_lower = variant.lower()
            
            # Пропускаем базовые варианты GSK/MSK без номера зоны если исходный запрос содержал номер
            if has_zone_number:
                # Список проблемных базовых вариантов
                problematic_bases = ['gsk11', 'гск11', 'msk', 'мск', 'sk42', 'ск42', 'sk95', 'ск95', 'sk63', 'ск63']
                
                # Проверяем, является ли вариант проблемным базовым
                is_problematic = False
                for base in problematic_bases:
                    if variant_lower == base or variant.upper() == base.upper():
                        is_problematic = True
                        self._logger.debug(f"Отфильтрован проблемный базовый вариант: '{variant}'")
                        break
                
                if is_problematic:
                    continue
            
            # Добавляем остальные варианты
            filtered_variants.append(variant)
        
        # Если после фильтрации осталось мало вариантов, оставляем самые релевантные
        if len(filtered_variants) < 5:
            # Добавляем обратно несколько самых близких к оригинальному запросу
            remaining_variants = [v for v in variants if v not in filtered_variants]
            for variant in remaining_variants[:3]:  # Добавляем максимум 3 дополнительных варианта
                filtered_variants.append(variant)
        
        return filtered_variants 

    async def start_search_by_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        self._logger.info(f"[SearchHandler.start_search_by_description] user_id={update.effective_user.id}")
        await update.message.reply_text("Введите описание для поиска СК:")
        return States.SEARCH_INPUT

    async def handle_filter_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        query = update.callback_query
        await query.answer()
        self._logger.info(f"[SearchHandler.handle_filter_callback] data={query.data}, user_id={update.effective_user.id}")
        # Здесь должна быть логика обработки фильтров
        await query.edit_message_text(text=f"Выбран фильтр: {query.data}. Логика не реализована.")
        return States.SEARCH_INPUT

    async def handle_filter_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Обработка ввода текста для поиска по описанию"""
        if update.message and update.message.text:
            txt = update.message.text.strip()
            
            self._logger.info(f"[SearchHandler.handle_filter_input] text='{txt}', user_id={update.effective_user.id}")
            
            # Выполняем поиск
            try:
                await self._handle_update(update, context)
                # После показа результатов остаемся в состоянии поиска
                return States.SEARCH_INPUT
            except Exception as e:
                self._logger.error(f"Ошибка при обработке поискового запроса: {e}", exc_info=True)
                await update.message.reply_text("Произошла ошибка при поиске. Попробуйте еще раз.")
                return States.SEARCH_INPUT
        
        return States.SEARCH_INPUT
        
    async def handle_pagination_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        query = update.callback_query
        await query.answer()
        self._logger.info(f"[SearchHandler.handle_pagination_callback] data={query.data}, user_id={update.effective_user.id}")
        # Здесь должна быть логика пагинации
        await query.edit_message_text(text=f"Выбрана пагинация: {query.data}. Логика не реализована.")
        return States.SEARCH_RESULTS

    async def handle_inline_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает 'эхо' от выбора инлайн-результата.
        """
        user_id = update.effective_user.id
        self._logger.info(f"[SearchHandler.handle_inline_result] Проигнорировано 'эхо' инлайн-результата для user_id={user_id}.")
        # Ничего не возвращаем, просто поглощаем обновление

    async def handle_inline_result_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обрабатывает сообщения с inline результатами (начинающиеся с "🔷 SRID:").
        Возвращает текущее состояние поиска без изменений.
        """
        if update.message and update.message.text:
            user_id = update.effective_user.id
            text_preview = update.message.text[:50] + "..." if len(update.message.text) > 50 else update.message.text
            self._logger.info(f"[SearchHandler.handle_inline_result_message] Игнорирую inline результат для user_id={user_id}: {text_preview}")
        
        # Возвращаем текущее состояние без изменений - остаемся в режиме поиска
        return States.SEARCH_INPUT

    async def handle_inline_export_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает callback'и от кнопок экспорта, прикрепленных к inline-сообщениям.
        Делегирует фактический экспорт в `CoordExportHandler`.
        """
        query = update.callback_query
        
        if query:
            await query.answer()

        try:
            if not query or not query.data:
                self._logger.warning("handle_inline_export_callback получен без данных.")
                return

            parts = query.data.split('_')
            if len(parts) < 5:
                self._logger.warning(f"Некорректный callback_data в inline экспорте: {query.data}")
                return

            _, _, export_type, format_name, srid = parts
            
            self._logger.info(f"[SearchHandler.handle_inline_export_callback] user_id={query.from_user.id}, type={export_type}, format={format_name}, srid={srid}")
            
            # Преобразуем callback_data в формат, понятный CoordExportHandler.
            # Например, из 'inline_export_prj_GMV25_100619' в 'export_gmv25_100619'.
            # Ожидаемый формат: export_{format}_{srid}
            new_callback_data = f"export_{format_name.lower()}_{srid}"
            
            self._logger.info(f"Делегирую экспорт в CoordExportHandler с новой callback_data: {new_callback_data}")

            if self.coord_export_handler:
                await self.coord_export_handler.handle_export_callback(update, context, custom_callback_data=new_callback_data)
            else:
                self._logger.error("coord_export_handler не инициализирован в SearchHandler.")
                if query.message:
                    await query.message.reply_text("❌ Ошибка конфигурации: сервис экспорта не доступен.")

        except Exception as e:
            self._logger.error(f"Критическая ошибка в handle_inline_export_callback: {e}", exc_info=True)
            if query and query.message:
                try:
                    await query.edit_message_text("❌ Произошла ошибка при обработке экспорта.")
                except Exception as edit_e:
                    self._logger.error(f"Не удалось отредактировать сообщение об ошибке: {edit_e}")

    async def cancel_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Отменяет операцию поиска и возвращает в главное меню."""
        self._logger.info(f"Пользователь {update.effective_user.id} отменил поиск.")
        user_id = update.effective_user.id
        self._logger.info(f"[SearchHandler.cancel_search] user_id={user_id}")

        if self.menu_handler:
            await self.menu_handler.show_main_menu(update, context)
        
        return ConversationHandler.END

    def get_handler(self) -> ConversationHandler:
        """Возвращает настроенный ConversationHandler для всего диалога поиска."""
        
        back_button_text = MainKeyboard.BUTTON_MENU

        # Создаем фильтр для inline результатов (сообщения, начинающиеся с "🔷 SRID:")
        inline_result_filter = filters.Regex(r'^🔷 SRID:')
        
        handler = ConversationHandler(
            entry_points=[
                 CallbackQueryHandler(self.start_search_by_description, pattern='^search_desc$')
            ],
            states={
                States.SEARCH_INPUT: [
                    # Сначала обрабатываем кнопку возврата в меню
                    MessageHandler(filters.Text([back_button_text]), self.cancel_search),
                    # Затем обрабатываем inline результаты (игнорируем их)
                    MessageHandler(inline_result_filter, self.handle_inline_result_message),
                    # Остальные текстовые сообщения обрабатываем как поисковые запросы
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_filter_input),
                ],
                States.SEARCH_RESULTS: [
                    CallbackQueryHandler(self.handle_pagination_callback, pattern=r"^page_"),
                    CallbackQueryHandler(self.handle_filter_callback, pattern=r"^filter_"),
                    MessageHandler(filters.Text([back_button_text]), self.cancel_search)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_search),
                MessageHandler(filters.Text([back_button_text]), self.cancel_search)
            ],
            map_to_parent={ 
                ConversationHandler.END: States.MAIN_MENU,
            },
            per_user=True,
            per_chat=True,
        )
        return handler 