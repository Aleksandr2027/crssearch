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
from dataclasses import dataclass
from XML_search.bot.utils.coord_utils import CoordinateParser, CoordinateConverter
from XML_search.bot.utils.validation_utils import ValidationResult

@dataclass
class CoordinateInput:
    """Класс для хранения введенных координат"""
    latitude: float
    longitude: float

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
        self.menu_handler = None
        
        # Кэш для хранения результатов поиска в рамках сессии
        self._session_results = {}
        
        # Добавляем словарь error_messages
        self.error_messages = {
            'invalid_coord_format': "Неверный формат координат. Пожалуйста, используйте формат: широта;долгота",
            # Можно добавить другие стандартные сообщения об ошибках здесь
        }
        
    def _parse_coordinates(self, text: str) -> Optional[CoordinateInput]:
        """Парсинг координат из текста"""
        text = text.strip().replace(',', '.')
        
        patterns = [
            # DMS с символами: 55°45'20.88";37°37'2.28"
            r'(\d+)°(\d+)\'(\d+\.?\d*)"[;,:]?\s*(\d+)°(\d+)\'(\d+\.?\d*)"',
            # DMS без символов: 55 45 20.88;37 37 2.28
            r'(\d+)\s+(\d+)\s+(\d+\.?\d*)[;$%]\s*(\d+)\s+(\d+)\s+(\d+\.?\d*)',
            # Градусы и десятичные минуты: 55 45.348;37 37.038
            r'(\d+)\s+(\d+\.?\d*)[;$%]\s*(\d+)\s+(\d+\.?\d*)',
            # Простые десятичные: 55.7558;37.6173
            r'([+-]?\d+\.?\d*)[;$%]([+-]?\d+\.?\d*)',
            # Простые с пробелом: 55.7558 37.6173
            r'([+-]?\d+\.?\d*)\s+([+-]?\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    
                    if len(groups) == 6:
                        # DMS формат: градусы минуты секунды
                        lat_d, lat_m, lat_s, lon_d, lon_m, lon_s = groups
                        lat = float(lat_d) + float(lat_m)/60 + float(lat_s)/3600
                        lon = float(lon_d) + float(lon_m)/60 + float(lon_s)/3600
                        return CoordinateInput(lat, lon)
                    elif len(groups) == 4:
                        # Градусы и десятичные минуты
                        lat_d, lat_m, lon_d, lon_m = groups
                        lat = float(lat_d) + float(lat_m)/60
                        lon = float(lon_d) + float(lon_m)/60
                        return CoordinateInput(lat, lon)
                    elif len(groups) == 2:
                        # Простые десятичные координаты
                        lat_str, lon_str = groups
                        return CoordinateInput(float(lat_str), float(lon_str))
                except ValueError:
                    continue
        
        return None

    def _format_single_result(self, result: Tuple) -> str:
        """Форматирует один результат поиска для вывода."""
        srid, name, deg, info, p, x, y = result

        message_parts = []
        message_parts.append(f"🔷 *SRID*: `{srid}`")
        message_parts.append(f"📍 *Название*: {self._escape_markdown_v2_safe(str(name))}")
        
        if info:
            message_parts.append(f"ℹ️ *Описание*: {self._escape_markdown_v2_safe(str(info))}")
        
        if x is not None and y is not None:
            x_str = self._escape_markdown_v2_safe(f"{x:.2f}")
            y_str = self._escape_markdown_v2_safe(f"{y:.2f}")
            message_parts.append(f"📍 *Координаты*: E\\: {x_str}, N\\: {y_str}")
        else:
            message_parts.append(f"📍 *Координаты*: Недоступны")
        
        if p:
            message_parts.append(f"✅ *Достоверность*: {self._escape_markdown_v2_safe(str(p))}")
        else:
            message_parts.append(f"✅ *Достоверность*: unknown")
            
        return "\n".join(message_parts)

    def _escape_markdown_v2_safe(self, text: str) -> str:
        """Безопасное экранирование всех специальных символов для MarkdownV2"""
        if not text:
            return ""
        # Все символы для экранирования согласно документации Telegram Bot API
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        import re
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    def _create_compact_list(self, coords: CoordinateInput, results: List[Tuple]) -> str:
        """Создание компактного заголовка (только кнопки)"""
        lat_escaped = self._escape_markdown_v2_safe(f"{coords.latitude:.4f}")
        lon_escaped = self._escape_markdown_v2_safe(f"{coords.longitude:.4f}")
        
        message_parts = [
            f"📍 Найдено *{len(results)}* систем координат для:",
            f"Lat: `{lat_escaped}` Lon: `{lon_escaped}`",
            "",
            "Выберите систему координат:"
        ]
        
        return "\n".join(message_parts)

    def _create_detailed_view(self, coords: CoordinateInput, results: List[Tuple], selected_srid: int) -> str:
        """Создание развернутого вида для выбранной СК"""
        lat_escaped = self._escape_markdown_v2_safe(f"{coords.latitude:.4f}")
        lon_escaped = self._escape_markdown_v2_safe(f"{coords.longitude:.4f}")
        
        message_parts = [
            f"📍 Найдено *{len(results)}* систем координат для:",
            f"Lat: `{lat_escaped}` Lon: `{lon_escaped}`",
            ""
        ]
        
        # Находим выбранную систему и показываем детали
        selected_index = None
        for i, result in enumerate(results):
            srid = result[0]
            if srid == selected_srid:
                selected_index = i
                # Развернутая информация для выбранной СК
                name, deg, info, p, x, y = result[1:7]
                message_parts.append(f"🔷 *SRID*: `{srid}`")
                message_parts.append(f"📍 *Название*: {self._escape_markdown_v2_safe(str(name))}")
                if info:
                    message_parts.append(f"ℹ️ *Описание*: {self._escape_markdown_v2_safe(str(info))}")
                if x is not None and y is not None:
                    x_str = self._escape_markdown_v2_safe(f"{x:.2f}")
                    y_str = self._escape_markdown_v2_safe(f"{y:.2f}")
                    message_parts.append(f"📍 *Координаты*: E\\: {x_str}, N\\: {y_str}")
                if p:
                    message_parts.append(f"✅ *Достоверность*: {self._escape_markdown_v2_safe(str(p))}")
                else:
                    message_parts.append(f"✅ *Достоверность*: unknown")
                message_parts.append(f"📤 *Экспорт*:")
                break
        
        return "\n".join(message_parts)

    def _get_compact_keyboard(self, results: List[Tuple]) -> InlineKeyboardMarkup:
        """Создание клавиатуры для компактного списка"""
        keyboard = []
        
        # Кнопки для каждой СК
        for i, result in enumerate(results, 1):
            srid = result[0]
            name = result[1]
            name_str = str(name) if name else f"SRID {srid}"
            display_name = name_str if len(name_str) <= 15 else name_str[:12] + "..."
            keyboard.append([
                InlineKeyboardButton(
                    f"📄 {display_name}",
                    callback_data=f"coord_detail:{srid}"
                )
            ])
        
        return InlineKeyboardMarkup(keyboard)

    def _get_detailed_keyboard(self, selected_srid: int, results: List[Tuple]) -> InlineKeyboardMarkup:
        """Создание клавиатуры для развернутого вида"""
        keyboard = []
        
        # Кнопки экспорта для выбранной СК
        export_row = [
            InlineKeyboardButton("📄 Civil3D", callback_data=f"coord_export:civil3d:{selected_srid}"),
            InlineKeyboardButton("📋 GMv20", callback_data=f"coord_export:gmv20:{selected_srid}"),
            InlineKeyboardButton("📋 GMv25", callback_data=f"coord_export:gmv25:{selected_srid}")
        ]
        keyboard.append(export_row)
        
        # Кнопка возврата
        keyboard.append([
            InlineKeyboardButton("🔙 Назад", callback_data="coord_collapse")
        ])
        
        return InlineKeyboardMarkup(keyboard)

    async def handle_coord_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """Обработка callback'ов для координатного интерфейса"""
        query = update.callback_query
        await query.answer()
        
        try:
            user_id = update.effective_user.id
            callback_data = query.data
            
            self._logger.info(f"Получен coord callback: {callback_data} от пользователя {user_id}")
            
            # Получаем результаты из кэша сессии
            session_key = f"coord_results_{user_id}"
            if session_key not in self._session_results:
                await query.edit_message_text(
                    "❌ Данные сессии устарели. Пожалуйста, выполните поиск заново.",
                    reply_markup=None
                )
                return States.COORD_INPUT
            
            coords, results = self._session_results[session_key]
            
            if callback_data.startswith("coord_detail:"):
                # Показать детали конкретной СК
                srid = int(callback_data.split(":")[1])
                detailed_text = self._create_detailed_view(coords, results, srid)
                detailed_keyboard = self._get_detailed_keyboard(srid, results)
                
                await query.edit_message_text(
                    text=detailed_text,
                    reply_markup=detailed_keyboard,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                
            elif callback_data == "coord_collapse":
                # Свернуть к компактному списку
                compact_text = self._create_compact_list(coords, results)
                compact_keyboard = self._get_compact_keyboard(results)
                
                await query.edit_message_text(
                    text=compact_text,
                    reply_markup=compact_keyboard,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                
            elif callback_data.startswith("coord_export:"):
                # Делегируем экспорт в CoordExportHandler
                parts = callback_data.split(":")
                if len(parts) == 3:
                    _, export_format, srid = parts
                    # Преобразуем в формат для CoordExportHandler
                    new_callback_data = f"export_{export_format}_{srid}"
                    
                    # Создаем обработчик экспорта и передаем custom_callback_data
                    coord_export_handler = CoordExportHandler(
                        self.config, self._db_manager, self.menu_handler,
                        self._metrics, self._logger
                    )
                    await coord_export_handler.setup_exporters()
                    await coord_export_handler.handle_export_callback(update, context, custom_callback_data=new_callback_data)
            
            return States.WAITING_EXPORT
            
        except Exception as e:
            self._logger.error(f"Ошибка при обработке coord callback: {e}", exc_info=True)
            await query.edit_message_text(
                "❌ Произошла ошибка при обработке запроса.",
                reply_markup=None
            )
            return States.COORD_INPUT

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
            
            # Парсим координаты
            coords = self._parse_coordinates(update.message.text)
            if not coords:
                await processing_message.edit_text(
                    "❌ Неверный формат координат. Используйте формат: 'широта;долгота' или 'широта$долгота' или 'широта%долгота'"
                )
                return States.COORD_INPUT
            
            # Получаем системы координат для точки
            results = []
            try:
                # Получаем системы координат для точки через асинхронный менеджер
                query = """
                    SELECT cg.srid, cg.name, cg.deg, cg.info, cg.p
                    FROM public.custom_geom cg
                    WHERE ST_Contains(cg.geom, ST_SetSRID(ST_MakePoint($1, $2), 4326))
                    AND cg.srid BETWEEN 100000 AND 101500;
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
                    "❌ Произошла ошибка при поиске систем координат."
                )
                return States.COORD_INPUT

            self._logger.info(f"Найдено {len(results)} СК для координат: {coords.latitude}, {coords.longitude}")

            if results:
                # Сохраняем результаты в кэше сессии
                user_id = update.effective_user.id
                session_key = f"coord_results_{user_id}"
                self._session_results[session_key] = (coords, results)
                
                # Создаем компактный список с кнопками
                compact_text = self._create_compact_list(coords, results)
                compact_keyboard = self._get_compact_keyboard(results)
                
                # Заменяем сообщение "Выполняю поиск..." на компактный список
                await processing_message.edit_text(
                    text=compact_text,
                    reply_markup=compact_keyboard,
                    parse_mode=ParseMode.MARKDOWN_V2
                )

                self._logger.info(f"Состояние FSM изменено на WAITING_EXPORT для user_id={user_id}")
                return States.WAITING_EXPORT
            else:
                await processing_message.edit_text(
                    "❌ Системы координат не найдены для данных широты и долготы."
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
            await update.message.reply_text("Возврат в главное меню...")
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