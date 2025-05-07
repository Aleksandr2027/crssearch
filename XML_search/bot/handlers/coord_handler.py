"""
Обработчик координат
"""

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from ..states import States
from .base_handler import BaseHandler
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from ..utils.format_utils import MessageFormatter
from ..utils.validation_utils import ValidationManager
from typing import Optional

class CoordHandler(BaseHandler):
    """Обработчик координат"""
    
    def __init__(self, config):
        """
        Инициализация обработчика координат
        
        Args:
            config: Конфигурация бота
        """
        super().__init__(config)
        self.validator = ValidationManager(self._db_manager)
        self.formatter = MessageFormatter()
        
    async def handle_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка введенных координат
        
        Args:
            update: Объект обновления
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        try:
            if update.message.text == '🔙 Главное меню':
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
                return States.WAITING_COORDINATES
            coords = validation_result.normalized_value
            # Получаем системы координат для точки
            results = []
            try:
                # Получаем системы координат для точки в отдельной транзакции
                with self._db_manager.safe_transaction() as conn:
                    with conn.cursor() as cursor:
                        # Получаем системы координат для точки
                        query = """
                            SELECT cg.srid, cg.name, cg.deg, cg.info, cg.p
                            FROM public.custom_geom cg
                            WHERE ST_Contains(cg.geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
                        """
                        cursor.execute(query, (coords.longitude, coords.latitude))
                        base_results = cursor.fetchall()
                # Обрабатываем каждую систему координат в отдельной транзакции
                transform_query = """
                    SELECT ST_X(transformed), ST_Y(transformed)
                    FROM (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s) AS transformed) AS subquery;
                """
                for row in base_results:
                    srid = row[0]
                    name = row[1]
                    deg = row[2]
                    info = row[3]
                    p = row[4]
                    try:
                        # Используем отдельную транзакцию для каждой трансформации
                        with self._db_manager.safe_transaction() as trans_conn:
                            with trans_conn.cursor() as trans_cursor:
                                trans_cursor.execute(transform_query, (coords.longitude, coords.latitude, srid))
                                coords_result = trans_cursor.fetchone()
                            if coords_result and None not in coords_result:
                                results.append((srid, name, deg, info, p, coords_result[0], coords_result[1]))
                            else:
                                results.append((srid, name, deg, info, p, None, None))
                    except Exception as e:
                        self._logger.error(f"Ошибка трансформации для SRID {srid}: {e}")
                        self._metrics.increment('coord_transform_errors')
                        results.append((srid, name, deg, info, p, None, None))
                # Добавляем UTM зону для северного полушария
                if coords.latitude >= 0:
                    utm_zone = int((coords.longitude + 180) // 6) + 1
                    if 1 <= utm_zone <= 60:
                        srid_utm = 32600 + utm_zone
                        try:
                            with self._db_manager.safe_transaction() as utm_conn:
                                with utm_conn.cursor() as utm_cursor:
                                    utm_cursor.execute(transform_query, (coords.longitude, coords.latitude, srid_utm))
                                    utm_coords = utm_cursor.fetchone()
                                    if utm_coords and None not in utm_coords:
                                        results.append((
                                            srid_utm,
                                            f"UTM zone {utm_zone}N",
                                            6,
                                            "WGS84",
                                            "EPSG",
                                            utm_coords[0],
                                            utm_coords[1]
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
                            self._metrics.increment('utm_transform_errors')
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
                self._metrics.increment('coord_search_errors')
                await processing_message.edit_text(
                    self.formatter.format_error("Произошла ошибка при поиске систем координат.")
                )
                return States.WAITING_COORDINATES
            if not results:
                await processing_message.edit_text(
                    self.formatter.format_error("Для указанной точки не найдено подходящих систем координат.")
                )
                return States.WAITING_COORDINATES
            # Удаляем сообщение о поиске
            await processing_message.delete()
            # Отправляем исходные координаты в разных форматах
            await update.message.reply_text(
                f"{self.formatter.format_coordinates(coords.latitude, coords.longitude)}",
                parse_mode='Markdown'
            )
            # Отправляем результаты поиска
            for result in results:
                srid, name, deg, info, p, x, y = result
                # Определяем значение достоверности
                if str(srid).startswith('326'):
                    p_value = "EPSG"
                else:
                    p_value = p if p is not None else "Уточнить у Администратора"
                # Форматируем сообщение
                message_text = (
                    f"🔹 *SRID:* `{srid}`\n"
                    f"📝 *Название:* `{name}`"
                )
                if info:
                    message_text += f"\nℹ️ *Описание:* `{info}`"
                if x is not None and y is not None:
                    message_text += f"\n📍 *Координаты:* `E: {round(x, 3)}, N: {round(y, 3)}`"
                else:
                    message_text += f"\n📍 *Координаты:* `E: -, N: -`"
                message_text += (
                    f"\n✅ *Достоверность:* `{p_value}`\n"
                    f"📤 *Экспорт:* `xml_Civil3D, prj_GMv20, prj_GMv25`"
                )
                await update.message.reply_text(
                    message_text,
                    parse_mode='Markdown'
                )
            return States.WAITING_COORDINATES
        except Exception as e:
            self._logger.error(f"Ошибка в CoordHandler.handle_coordinates: {e}", exc_info=True)
            self._metrics.increment('coord_handler_error')
            error_message = "Произошла ошибка при обработке координат. Пожалуйста, попробуйте позже."
            if update and update.message:
                await update.message.reply_text(error_message)
            return States.WAITING_COORDINATES
    
    def get_handler(self) -> MessageHandler:
        """
        Получение обработчика сообщений
        
        Returns:
            Обработчик сообщений
        """
        return MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_coordinates
        )

    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка обновления от Telegram
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        return await self.handle_coordinates(update, context) 