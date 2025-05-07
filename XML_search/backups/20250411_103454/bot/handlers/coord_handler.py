"""
Обработчик поиска по координатам
"""

import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler
from ..keyboards.main_keyboard import MainKeyboard
from ..utils.coord_utils import CoordUtils
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.search_handler import SearchHandler as CrsSearchHandler

class CoordHandler(BaseHandler):
    """Обработчик поиска по координатам"""
    
    def __init__(self, db_manager: DatabaseManager, metrics: MetricsCollector):
        """
        Инициализация обработчика координат
        
        Args:
            db_manager: Менеджер базы данных
            metrics: Сборщик метрик
        """
        super().__init__("coord_handler")
        self.db_manager = db_manager
        self.metrics = metrics
        self.main_keyboard = MainKeyboard()
        self.search_processor = CrsSearchHandler()
        self.coord_utils = CoordUtils()
        
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка введенных координат
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        start_time = time.time()
        
        try:
            if update.message.text == self.main_keyboard.BUTTON_MENU:
                keyboard = self.main_keyboard.get_keyboard()
                await update.message.reply_text(
                    "Выберите тип поиска:",
                    reply_markup=keyboard
                )
                return States.MAIN_MENU
                
            # Отправляем сообщение о начале обработки
            processing_message = await update.message.reply_text(
                "🔍 Выполняю поиск систем координат для указанной точки..."
            )
            
            try:
                # Парсим координаты
                latitude, longitude = self.coord_utils.parse_coordinates(update.message.text)
                
                # Используем search_processor для работы с БД
                results = []
                try:
                    # Получаем системы координат для точки в отдельной транзакции
                    with self.db_manager.safe_transaction() as conn:
                        with conn.cursor() as cursor:
                            # Получаем системы координат для точки
                            query = """
                                SELECT cg.srid, cg.name, cg.deg, cg.info, cg.p
                                FROM public.custom_geom cg
                                WHERE ST_Contains(cg.geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
                            """
                            cursor.execute(query, (longitude, latitude))
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
                            with self.db_manager.safe_transaction() as trans_conn:
                                with trans_conn.cursor() as trans_cursor:
                                    trans_cursor.execute(transform_query, (longitude, latitude, srid))
                                    coords = trans_cursor.fetchone()
                                if coords and None not in coords:
                                    results.append((srid, name, deg, info, p, coords[0], coords[1]))
                                else:
                                    results.append((srid, name, deg, info, p, None, None))
                        except Exception as e:
                            # Не логируем ошибки трансформации, так как это ожидаемое поведение
                            # для систем с некорректными параметрами проекции
                            results.append((srid, name, deg, info, p, None, None))
                            self.metrics.increment('coord_transform_errors')
                        
                    # Добавляем UTM зону для северного полушария в отдельной транзакции
                    if latitude >= 0:
                        utm_zone = int((longitude + 180) // 6) + 1
                        if 1 <= utm_zone <= 60:
                            srid_utm = 32600 + utm_zone
                            try:
                                with self.db_manager.safe_transaction() as utm_conn:
                                    with utm_conn.cursor() as utm_cursor:
                                        utm_cursor.execute(transform_query, (longitude, latitude, srid_utm))
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
                                self.logger.error(f"Ошибка при получении UTM координат: {e}")
                                self.metrics.increment('utm_transform_errors')
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
                    self.logger.error(f"Ошибка при получении систем координат: {e}")
                    self.metrics.increment('coord_search_errors')
                    await processing_message.edit_text(
                        "❌ Произошла ошибка при поиске систем координат."
                    )
                    return States.WAITING_COORDINATES
                    
                if not results:
                    await processing_message.edit_text(
                        "❌ Для указанной точки не найдено подходящих систем координат."
                    )
                    return States.WAITING_COORDINATES
                    
                # Группируем результаты по SRID
                srid_groups = {}
                for result in results:
                    srid = result[0]
                    if srid not in srid_groups:
                        srid_groups[srid] = []
                    srid_groups[srid].append(result)
                    
                # Форматируем результаты
                formatted_results = []
                for srid, group in srid_groups.items():
                    result = group[0]
                    
                    if str(srid).startswith('326'):
                        p_value = "EPSG"
                    else:
                        p_values = set(r[4] for r in group if r[4] is not None)
                        if len(p_values) == 1:
                            p_value = next(iter(p_values))
                        else:
                            p_value = "Уточнить у Администратора"
                            
                    result_text = (
                        f"🔹 *SRID:* `{result[0]}`\n"
                        f"📝 *Название:* `{result[1]}`"
                    )
                    if result[3]:
                        result_text += f"\nℹ️ *Описание:* `{result[3]}`"
                    
                    if result[5] is not None and result[6] is not None:
                        result_text += f"\n📍 *Координаты:* `E: {round(result[5], 3)}, N: {round(result[6], 3)}`"
                    else:
                        result_text += f"\n📍 *Координаты:* `E: -, N: -`"
                        
                    result_text += (
                        f"\n✅ *Достоверность:* `{p_value}`\n"
                        f"📤 *Экспорт:* `xml_Civil3D, prj_GMv20, prj_GMv25`"
                    )
                    
                    # Создаем кнопки экспорта
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "xml_Civil3D",
                                callback_data=f"export_xml:{result[0]}"
                            ),
                            InlineKeyboardButton(
                                "prj_GMv20",
                                callback_data=f"export_gmv20:{result[0]}"
                            ),
                            InlineKeyboardButton(
                                "prj_GMv25",
                                callback_data=f"export_gmv25:{result[0]}"
                            )
                        ]
                    ]
                    
                    formatted_results.append({
                        'text': result_text,
                        'keyboard': InlineKeyboardMarkup(keyboard)
                    })
                    
                # Удаляем сообщение о поиске
                await processing_message.delete()
                
                # Отправляем каждый результат отдельным сообщением с кнопками
                for result in formatted_results:
                    await update.message.reply_text(
                        result['text'],
                        parse_mode='Markdown',
                        reply_markup=result['keyboard']
                    )
                    
                # Отправляем сообщение с кнопкой меню
                keyboard = self.main_keyboard.get_menu_keyboard()
                await update.message.reply_text(
                    "Выберите действие:",
                    reply_markup=keyboard
                )
                
                # Обновляем метрики
                self.metrics.increment('coord_search_success')
                self.metrics.gauge('coord_search_results', len(results))
                
            except ValueError as e:
                await update.message.reply_text(
                    f"❌ Ошибка: {str(e)}\n"
                    "Попробуйте еще раз или используйте /cancel для отмены."
                )
                self.metrics.increment('coord_search_errors')
                return States.WAITING_COORDINATES
                
            except Exception as e:
                self.logger.error(f"Ошибка при обработке координат: {e}")
                self.metrics.increment('coord_search_errors')
                await update.message.reply_text(
                    "❌ Произошла ошибка при обработке координат.\n"
                    "Попробуйте еще раз или используйте /cancel для отмены."
                )
                return States.WAITING_COORDINATES
                
            return States.WAITING_COORDINATES
            
        except Exception as e:
            await self._handle_error(update, context, e)
            return States.ERROR
            
        finally:
            self._log_metrics('process', time.time() - start_time) 