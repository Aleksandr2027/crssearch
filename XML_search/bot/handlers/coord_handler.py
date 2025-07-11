"""
Обработчик координат
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from ..states import States
from .base_handler import BaseHandler
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from ..utils.format_utils import MessageFormatter
from ..utils.validation_utils import ValidationManager
from typing import Optional, List, Dict, Any, Tuple
from .coord_export_handler import CoordExportHandler
from XML_search.bot.keyboards.main_keyboard import MainKeyboard
import re
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

class CoordHandler(BaseHandler):
    """Обработчик координат"""
    
    def __init__(self, config, db_manager=None, metrics=None, logger=None, cache=None):
        """
        Инициализация обработчика координат
        
        Args:
            config: Конфигурация бота
            db_manager: Менеджер базы данных
            metrics: Менеджер метрик
            logger: Менеджер логирования
            cache: Менеджер кэша
        """
        super().__init__(config)
        self._db_manager = db_manager
        self._metrics = metrics or MetricsManager()
        self._logger = logger or LogManager().get_logger(__name__)
        self.cache = cache or CacheManager()
        self.validator = ValidationManager(self._db_manager)
        self.formatter = MessageFormatter()
        self._main_keyboard = MainKeyboard()
        # Добавляем словарь error_messages
        self.error_messages = {
            'invalid_coord_format': "Неверный формат координат. Пожалуйста, используйте формат: широта;долгота",
            # Можно добавить другие стандартные сообщения об ошибках здесь
        }
        
    def _parse_coordinates(self, text: str) -> Optional[Dict[str, float]]:
        # ... (логика остаётся без изменений) ...
        try:
            # ... (остальная логика остаётся без изменений) ...
            return None
        except Exception as e:
            self._logger.error(f"Error parsing coordinates: {e}", exc_info=True)
            return None

    def _format_single_result(self, result: Tuple) -> str:
        """Форматирует один результат поиска для вывода."""
        srid, name, _, info, p, x, y = result

        # Экранирование для MarkdownV2
        name_esc = escape_markdown(name or "Нет данных", version=2)
        info_esc = escape_markdown(info or "Нет данных", version=2)
        p_esc = escape_markdown(p or "unknown", version=2)
        x_esc = escape_markdown(f"{x:.3f}", version=2) if x is not None else "N/A"
        y_esc = escape_markdown(f"{y:.3f}", version=2) if y is not None else "N/A"

        return (
            f"🔹 *SRID:* `{srid}`\n"
            f"📝 *Название:* {name_esc}\n"
            f"ℹ️ *Описание:* {info_esc}\n"
            f"📍 *Координаты:* `E: {x_esc}, N: {y_esc}`\n"
            f"✅ *Достоверность:* `{p_esc}`\n"
            f"🛳️ *Экспорт:*"
        )

    async def handle_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка введенных координат
        
        Args:
            update: Объект обновления
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        try:
            # Явная инициализация пула соединений, если требуется
            if self._db_manager and hasattr(self._db_manager, 'initialize'):
                await self._db_manager.initialize()
            if update.message.text == '🔙 Главное меню':
                await update.message.reply_text("Вы вернулись в главное меню.")
                # Всегда вызываем главное меню через menu_handler
                if hasattr(self, 'menu_handler'):
                    await self.menu_handler.show_main_menu(update, context)
                return States.MAIN_MENU
            # Отправляем сообщение о начале обработки
            processing_message = await update.message.reply_text(
                "🔍 Выполняю поиск систем координат для указанной точки..."
            )
            # Валидируем координаты
            validation_result = self.validator.validate_coordinates(update.message.text)
            if not validation_result.is_valid:
                await processing_message.edit_text(
                    self.formatter.format_error(validation_result.error_message)
                )
                return States.COORD_INPUT
            coords = validation_result.normalized_value
            # Получаем системы координат для точки
            results = []
            try:
                # Получаем системы координат для точки через асинхронный менеджер
                query = """
                    SELECT cg.srid, cg.name, cg.deg, cg.info, cg.p
                    FROM public.custom_geom cg
                    WHERE ST_Contains(cg.geom, ST_SetSRID(ST_MakePoint($1, $2), 4326));
                """
                base_results = await self._db_manager.fetch(query, coords.longitude, coords.latitude)
                transform_query = """
                    SELECT ST_X(transformed) AS x, ST_Y(transformed) AS y
                    FROM (SELECT ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), CAST($3 AS INTEGER)) AS transformed) AS subquery;
                """
                for row in base_results:
                    srid = row['srid']
                    name = row['name']
                    deg = row['deg']
                    info = row['info']
                    p = row['p']
                    try:
                        coords_result = await self._db_manager.fetchrow(transform_query, coords.longitude, coords.latitude, srid)
                        if coords_result and coords_result['x'] is not None and coords_result['y'] is not None:
                            results.append((srid, name, deg, info, p, coords_result['x'], coords_result['y']))
                        else:
                            results.append((srid, name, deg, info, p, None, None))
                    except Exception as e:
                        self._logger.error(f"Ошибка трансформации для SRID {srid}: {e}")
                        await self._metrics.record_error('coord_transform', str(e))
                        results.append((srid, name, deg, info, p, None, None))
                # Добавляем UTM зону для северного полушария
                if coords.latitude >= 0:
                    utm_zone = int((coords.longitude + 180) // 6) + 1
                    if 1 <= utm_zone <= 60:
                        srid_utm = 32600 + utm_zone
                        try:
                            utm_coords = await self._db_manager.fetchrow(transform_query, coords.longitude, coords.latitude, srid_utm)
                            if utm_coords and utm_coords['x'] is not None and utm_coords['y'] is not None:
                                results.append((
                                    srid_utm,
                                    f"UTM zone {utm_zone}N",
                                    6,
                                    "WGS84",
                                    "EPSG",
                                    utm_coords['x'],
                                    utm_coords['y']
                                ))
                            else:
                                results.append((
                                    srid_utm,
                                    f"UTM zone {utm_zone}N",
                                    6,
                                    "WGS84",
                                    "EPSG",
                                    None,
                                    None
                                ))
                        except Exception as e:
                            self._logger.error(f"Ошибка при получении UTM координат: {e}")
                            await self._metrics.record_error('utm_transform', str(e))
                            results.append((
                                srid_utm,
                                f"UTM zone {utm_zone}N",
                                6,
                                "WGS84",
                                "EPSG",
                                None,
                                None
                            ))
            except Exception as e:
                self._logger.error(f"Ошибка при получении систем координат: {e}")
                await self._metrics.record_error('coord_search', str(e))
                await processing_message.edit_text(
                    self.formatter.format_error("Произошла ошибка при поиске систем координат.")
                )
                return States.COORD_INPUT

            # Удаляем старое сообщение "Выполняю поиск..."
            await processing_message.delete()
            
            self._logger.info(f"Найдено {len(results)} СК для координат: {coords.latitude}, {coords.longitude}")

            if results:
                # Отправляем заголовок
                lat_escaped = escape_markdown(f"{coords.latitude:.4f}", version=2)
                lon_escaped = escape_markdown(f"{coords.longitude:.4f}", version=2)
                header_text = f"📍 Найдено *{len(results)}* систем координат для\nLat: `{lat_escaped}`\nLon: `{lon_escaped}`"
                await update.message.reply_text(header_text, parse_mode=ParseMode.MARKDOWN_V2)

                # Отправляем каждую СК в отдельном сообщении
                for result in results:
                    srid = result[0]
                    message_text = self._format_single_result(result)
                    keyboard = CoordExportHandler.get_export_keyboard(str(srid))
                    
            await update.message.reply_text(
                        text=message_text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.MARKDOWN_V2
                    )

                user_id = update.effective_user.id
                self._logger.info(f"Состояние FSM изменено на WAITING_EXPORT для user_id={user_id}")
                return States.WAITING_EXPORT
            else:
                await update.message.reply_text(
                    "Системы координат не найдены для данных широты и долготы.",
                    reply_markup=self._main_keyboard.get_back_keyboard()
                )
            return States.COORD_INPUT

        except ValueError as e:
            self._logger.error(f"Ошибка при обработке координат: {e}", exc_info=True)
            await self._metrics.record_error('coord_handler', str(e))
            error_message = "Произошла ошибка при обработке координат. Пожалуйста, попробуйте позже."
            if update and update.message:
                await update.message.reply_text(error_message)
            return States.COORD_INPUT
        except Exception as e:
            self._logger.error(f"Ошибка при обработке координат: {e}", exc_info=True)
            await self._metrics.record_error('coord_handler', str(e))
            error_message = "Произошла непредвиденная ошибка при обработке координат."
            if update and update.message:
                await update.message.reply_text(error_message)
            return States.COORD_ERROR
    
    def get_handler(self) -> MessageHandler:
        """
        Получение обработчика сообщений
        
        Returns:
            Обработчик сообщений
        """
        return MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_coord_input
        )

    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка обновления от Telegram
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        return await self.handle_coordinates(update, context)

    async def handle_coord_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        user_id = update.effective_user.id
        text = update.message.text

        # Проверка на команду возврата в главное меню
        if text == MainKeyboard.BUTTON_MENU:
            self._logger.info(f"User {user_id} requested main menu from COORD_INPUT state using '{text}'.")
            # Примечание: CoordHandler должен быть зарегистрирован в ConversationHandler,
            # который имеет States.MAIN_MENU в map_to_parent.
            # Или MenuHandler должен быть доступен здесь для прямого вызова.
            # Текущая реализация BaseHandler.menu_handler не инициализируется в CoordHandler.
            # Поэтому мы просто возвращаем состояние, ожидая, что FSM обработает это.
            # Потенциально, нужно будет передать menu_handler в __init__ CoordHandler,
            # если требуется более сложное взаимодействие.
            await update.message.reply_text("Возврат в главное меню...") # Заглушка или вызов menu_handler.show_main_menu
            return States.MAIN_MENU

        # Если пользователь нажал кнопку "Поиск СК по Lat/Lon" уже находясь в COORD_INPUT
        if text == MainKeyboard.BUTTON_SEARCH_COORD:
            self._logger.info(f"User {user_id} sent button text '{text}' in COORD_INPUT state. Re-prompting for coordinates.")
            # Повторно отправляем инструкцию, которую MenuHandler отправлял изначально
            await update.message.reply_text(
                "📍 Введите координаты в формате 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'\n\n"
                "Поддерживаемые форматы ввода:\n"
                "1. Десятичные градусы: 55.7558;37.6173 или 55.7558$37.6173 или 55.7558%37.6173\n"
                "2. Градусы и минуты: 55 45.348;37 37.038 или 55 45.348$37 37.038 или 55 45.348%37 37.038\n"
                "3. Градусы, минуты и секунды: 55 45 20.88;37 37 2.28 или 55 45 20.88$37 37 2.28 или 55 45 20.88%37 37 2.28\n"
                "4. С обозначениями: 55°45\'20.88\";37°37\'2.28\" или 55°45\'20.88\"$37°37\'2.28\" или 55°45\'20.88\"%37°37\'2.28\"\n\n"
                "Разделитель между широтой и долготой - точка с запятой (;) или знак доллара ($) или знак процента (%)"
            )
            return States.COORD_INPUT

        # Если текст не является командой/кнопкой, тогда это, вероятно, ввод координат.
        self._logger.info(f"[CoordHandler.handle_coord_input] User {user_id} entered text, passing to handle_coordinates: {text}")
        return await self.handle_coordinates(update, context) 