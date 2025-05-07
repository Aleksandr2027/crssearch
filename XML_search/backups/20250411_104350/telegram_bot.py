import logging
import signal
import asyncio
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, InlineQueryHandler, CallbackQueryHandler
from telegram.request import HTTPXRequest
from XML_search.config import TelegramConfig, LogConfig
import httpx
from transliterate import translit
import re
import psycopg2
import os
from XML_search.search_handler import SearchHandler
import telegram
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.config_enhanced import EnhancedConfig
from XML_search.enhanced.exceptions import DatabaseError, QueryError
from contextlib import contextmanager
import win32api
import win32con
from pathlib import Path
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter
from XML_search.enhanced.export.export_manager import ExportManager

# Инициализация улучшенных компонентов
log_manager = LogManager()
logger = log_manager.get_logger(__name__)
metrics = MetricsCollector()
enhanced_config = EnhancedConfig.load_from_file('config/enhanced_config.json')

# Отключаем логирование HTTP-запросов httpx
logging.getLogger('httpx').setLevel(logging.WARNING)

# Инициализация обработчика поиска
search_processor = SearchHandler()

# Состояния для ConversationHandler
AUTH, MAIN_MENU, WAITING_COORDINATES, WAITING_SEARCH = range(4)

# Словарь для хранения авторизованных пользователей
authorized_users = set()

# Константы для кнопок меню
BUTTON_COORD_SEARCH = 'Поиск СК по Lat/Lon'
BUTTON_DESC_SEARCH = 'Поиск СК по описанию'
BUTTON_MENU = '🔙 Главное меню'

# Глобальные переменные для управления состоянием
is_shutting_down = False
application = None

def transliterate_text(text: str, direction: str = 'ru') -> str:
    """Транслитерация текста между кириллицей и латиницей"""
    try:
        if direction == 'ru':  # кириллица -> латиница
            return translit(text, 'ru', reversed=True)
        else:  # латиница -> кириллица
            return translit(text, 'ru')
    except Exception as e:
        logger.warning(f"Ошибка при транслитерации: {e}")
        return text

async def check_access(update: Update) -> bool:
    """Проверка доступа пользователя"""
    user_id = update.effective_user.id
    if user_id in authorized_users:
        return True
    
    await update.message.reply_text(
        "🔐 Для доступа к боту введите пароль.\n"
        "Используйте команду /auth для авторизации."
    )
    return False

async def auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса авторизации"""
    await update.message.reply_text(
        "🔐 Введите пароль для доступа к боту:"
    )
    return AUTH

async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверка пароля"""
    user_id = update.effective_user.id
    if update.message.text == TelegramConfig.ACCESS_PASSWORD:
        authorized_users.add(user_id)
        metrics.increment('auth_success')
        return await show_main_menu(update, context)
    else:
        metrics.increment('auth_failed')
        await update.message.reply_text(
            "❌ Неверный пароль.\n"
            "Попробуйте еще раз или используйте /cancel для отмены."
        )
        return AUTH

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена процесса авторизации"""
    await update.message.reply_text(
        "❌ Авторизация отменена.\n"
        "Используйте /auth для повторной попытки."
    )
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    metrics.increment('start_command')
    await update.message.reply_text(
        "🔐 Введите пароль для доступа к боту:",
        reply_markup=ReplyKeyboardRemove()
    )
    return AUTH

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать главное меню"""
    metrics.increment('main_menu_show')
    keyboard = [
        [KeyboardButton(BUTTON_COORD_SEARCH)],
        [KeyboardButton(BUTTON_DESC_SEARCH)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Выберите тип поиска:",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора пункта меню"""
    if not update.message or not update.message.text:
        return MAIN_MENU

    choice = update.message.text
    
    if choice == BUTTON_COORD_SEARCH:
        metrics.increment('coord_search_selected')
        keyboard = [[KeyboardButton(BUTTON_MENU)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "📍 Введите координаты в формате 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'\n\n"
            "Поддерживаемые форматы ввода:\n"
            "1. Десятичные градусы: 55.7558;37.6173 или 55.7558$37.6173 или 55.7558%37.6173\n"
            "2. Градусы и минуты: 55 45.348;37 37.038 или 55 45.348$37 37.038 или 55 45.348%37 37.038\n"
            "3. Градусы, минуты и секунды: 55 45 20.88;37 37 2.28 или 55 45 20.88$37 37 2.28 или 55 45 20.88%37 37 2.28\n"
            "4. С обозначениями: 55°45'20.88\";37°37'2.28\" или 55°45'20.88\"$37°37'2.28\" или 55°45'20.88\"%37°37'2.28\"\n\n"
            "Разделитель между широтой и долготой - точка с запятой (;) или знак доллара ($) или знак процента (%)",
            reply_markup=reply_markup
        )
        return WAITING_COORDINATES
    
    elif choice == BUTTON_DESC_SEARCH:
        metrics.increment('desc_search_selected')
        # Создаем клавиатуру с обычными кнопками
        keyboard = [[KeyboardButton(BUTTON_MENU)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Отправляем основное сообщение с инструкциями
        await update.message.reply_text(
            "🔍 Как пользоваться поиском:\n\n"
            "1. Поиск по SRID:\n"
            "   - Отправьте номер системы координат\n"
            "   - Пример: 100000\n\n"
            "2. Поиск по названию:\n"
            "   - Отправьте часть названия\n"
            "   - Пример: MSK01z1\n\n"
            "3. Поиск по описанию:\n"
            "   - Отправьте часть описания\n"
            "   - Пример: Московская, Moskovskaya\n\n"
            "Результаты будут отсортированы по релевантности:\n"
            "- Сначала точные совпадения\n"
            "- Затем частичные совпадения",
            reply_markup=reply_markup
        )
        
        # Создаем inline клавиатуру с кнопкой быстрого поиска
        inline_keyboard = [[
            InlineKeyboardButton(
                "🔍 Быстрый поиск в текущем чате",
                switch_inline_query_current_chat=""
            )
        ]]
        inline_markup = InlineKeyboardMarkup(inline_keyboard)
        
        # Отправляем дополнительное сообщение с inline кнопкой
        await update.message.reply_text(
            "Нажмите кнопку ниже для быстрого поиска:",
            reply_markup=inline_markup
        )
        
        return WAITING_SEARCH
    
    elif choice == BUTTON_MENU:
        return await show_main_menu(update, context)
    
    return MAIN_MENU

async def process_coordinates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенных координат"""
    if update.message.text == BUTTON_MENU:
        return await show_main_menu(update, context)
        
    try:
        # Отправляем сообщение о начале обработки
        processing_message = await update.message.reply_text(
            "🔍 Выполняю поиск систем координат для указанной точки..."
        )

        # Парсим координаты
        latitude, longitude = parse_coordinates(update.message.text)
        
        # Используем search_processor для работы с БД
        results = []
        try:
            # Получаем системы координат для точки в отдельной транзакции
            with search_processor.crs_bot.db_manager.safe_transaction() as conn:
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
                    with search_processor.crs_bot.db_manager.safe_transaction() as trans_conn:
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
                    metrics.increment('coord_transform_errors')
                
            # Добавляем UTM зону для северного полушария в отдельной транзакции
            if latitude >= 0:
                utm_zone = int((longitude + 180) // 6) + 1
                if 1 <= utm_zone <= 60:
                    srid_utm = 32600 + utm_zone
                    try:
                        with search_processor.crs_bot.db_manager.safe_transaction() as utm_conn:
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
                        logger.error(f"Ошибка при получении UTM координат: {e}")
                        metrics.increment('utm_transform_errors')
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
            logger.error(f"Ошибка при получении систем координат: {e}")
            metrics.increment('coord_search_errors')
            await processing_message.edit_text(
                "❌ Произошла ошибка при поиске систем координат."
            )
            return WAITING_COORDINATES

        if not results:
            await processing_message.edit_text(
                "❌ Для указанной точки не найдено подходящих систем координат."
            )
            return WAITING_COORDINATES

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
        keyboard = [[KeyboardButton(BUTTON_MENU)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        # Обновляем метрики
        metrics.increment('coord_search_success')
        metrics.gauge('coord_search_results', len(results))

    except ValueError as e:
        await update.message.reply_text(
            f"❌ Ошибка: {str(e)}\n"
            "Попробуйте еще раз или используйте /cancel для отмены."
        )
        metrics.increment('coord_search_errors')
        return WAITING_COORDINATES
    except Exception as e:
        logger.error(f"Ошибка при обработке координат: {e}")
        metrics.increment('coord_search_errors')
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке координат.\n"
            "Попробуйте еще раз или используйте /cancel для отмены."
        )
        return WAITING_COORDINATES

    return WAITING_COORDINATES

async def search_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик поискового запроса"""
    if update.message.text in [BUTTON_MENU]:
        if update.message.text == BUTTON_MENU:
            return await show_main_menu(update, context)
        return WAITING_SEARCH
        
    if not await check_access(update):
        return ConversationHandler.END

    await process_search(update, context)
    return WAITING_SEARCH

async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик поисковых запросов"""
    if not await check_access(update):
        return

    if update.message.text.startswith('🔹 SRID:'):
        return

    processing_message = await update.message.reply_text(
        "🔍 Выполняю поиск...",
        parse_mode='Markdown'
    )

    try:
        search_term = update.message.text.strip()
        with metrics.timing('search_duration'):
            results = search_processor.search_with_transliteration(search_term)
            formatted_results = search_processor.format_results(results)
            
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
        metrics.increment('search_success')
        metrics.gauge('search_results', len(results))
        
    except Exception as e:
        error_message = f"❌ Произошла ошибка при поиске: {str(e)}"
        logger.error(error_message)
        metrics.increment('search_errors')
        await processing_message.edit_text(error_message)

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик инлайн-запросов"""
    query = update.inline_query.query.strip()
    if not query:
        return

    try:
        with metrics.timing('inline_search_duration'):
            results = search_processor.search_with_transliteration(query)[:20]
            formatted_results = search_processor.format_inline_results(results, limit=20)
        
        inline_results = [
            InlineQueryResultArticle(
                id=result['id'],
                title=result['title'],
                description=result['description'],
                input_message_content=InputTextMessageContent(
                    result['message_text'],
                    parse_mode='Markdown'
                ),
                reply_markup=result['keyboard']
            )
            for result in formatted_results
        ]
        
        await update.inline_query.answer(
            inline_results,
            cache_time=1,
            is_personal=True
        )
        
        # Обновляем метрики
        metrics.increment('inline_search_success')
        metrics.gauge('inline_search_results', len(results))
        
    except telegram.error.BadRequest as e:
        if "Query is too old" in str(e):
            logger.debug("Пропускаю устаревший запрос")
            return
        logger.error(f"Ошибка Bad Request в инлайн-запросе: {e}")
        metrics.increment('inline_search_errors')
    except Exception as e:
        logger.error(f"Ошибка при обработке инлайн-запроса: {e}")
        metrics.increment('inline_search_errors')
        try:
            await update.inline_query.answer(
                [], 
                cache_time=1,
                is_personal=True
            )
        except Exception as inner_e:
            logger.error(f"Ошибка при отправке пустого ответа: {inner_e}")

async def handle_export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-запросов экспорта"""
    query = update.callback_query
    
    try:
        # Проверяем доступ
        if not await check_access(update):
            await query.answer("⛔ Доступ запрещен", show_alert=True)
            return
            
        # Разбираем данные callback
        export_type, srid = query.data.split(':')
        srid = int(srid)
        
        # Инициализируем менеджер экспорта и экспортеры
        export_manager = ExportManager()
        
        # Регистрируем экспортеры
        export_manager.register_exporter('xml_Civil3D', Civil3DExporter({}))
        export_manager.register_exporter('prj_GMv20', GMv20Exporter({}))
        export_manager.register_exporter('prj_GMv25', GMv25Exporter({}))
        
        # Определяем тип экспорта
        export_types = {
            'export_xml': 'xml_Civil3D',
            'export_gmv20': 'prj_GMv20',
            'export_gmv25': 'prj_GMv25'
        }
        
        exporter_id = export_types.get(export_type)
        if not exporter_id:
            await query.answer("❌ Неизвестный формат экспорта", show_alert=True)
            return
            
        # Проверяем доступность формата для SRID
        available_formats = export_manager.get_available_formats(srid)
        if not any(fmt['id'] == exporter_id for fmt in available_formats):
            await query.answer(f"❌ Формат {exporter_id} не поддерживается для SRID {srid}", show_alert=True)
            return
            
        # Выполняем экспорт
        try:
            result = export_manager.export(srid, exporter_id)
            
            # Отправляем результат пользователю
            # Временно показываем сообщение об успехе
            await query.answer(f"✅ Экспорт в формат {exporter_id} успешно выполнен", show_alert=True)
            
            # TODO: Реализовать отправку файла пользователю
            # await context.bot.send_document(
            #     chat_id=update.effective_chat.id,
            #     document=result,
            #     filename=f"export_{srid}_{exporter_id}"
            # )
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте {exporter_id} для SRID {srid}: {e}")
            await query.answer("❌ Произошла ошибка при экспорте. Попробуйте позже.", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке callback экспорта: {e}")
        await query.answer("❌ Произошла ошибка при обработке запроса", show_alert=True)

def dms_to_decimal(coord: str) -> float:
    """Преобразование координат из DMS в десятичные градусы"""
    coord = re.sub(r'\s+', ' ', coord.strip())
    parts = re.split(r'[\s°\'"]+', coord)
    parts = [p for p in parts if p]
    degrees = float(parts[0])
    minutes = float(parts[1]) if len(parts) > 1 else 0
    seconds = float(parts[2]) if len(parts) > 2 else 0
    decimal = degrees + minutes / 60 + seconds / 3600
    return decimal

def parse_coordinates(input_str: str) -> tuple:
    """Разбор строки с координатами"""
    # Заменяем $ и % на ; для унификации разделителя
    input_str = input_str.replace('$', ';').replace('%', ';')
    # Удаляем пробелы вокруг разделителя
    input_str = re.sub(r'\s*;\s*', ';', input_str.strip())
    parts = input_str.split(';')
    if len(parts) != 2:
        raise ValueError("Неверный формат ввода. Ожидается 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'.")
    latitude = dms_to_decimal(parts[0])
    longitude = dms_to_decimal(parts[1])
    return latitude, longitude

async def shutdown() -> None:
    """Корректное завершение работы бота"""
    global application
    if application:
        logger.info("Начало корректного завершения работы...")
        try:
            # Останавливаем только если приложение запущено
            if application.running:
                # Устанавливаем флаг завершения
                application.stop_running()
                
                # Закрываем активные соединения
                search_processor.crs_bot.disconnect()
                
                # Останавливаем приложение
                await application.stop()
                
                # Корректное завершение асинхронных генераторов
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    await loop.shutdown_asyncgens()
                    
                # Завершаем работу приложения
                await application.shutdown()
                
                logger.info("Бот успешно остановлен")
            else:
                logger.info("Бот уже остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")
            # Принудительное завершение при ошибке
            if hasattr(application, 'stop_running'):
                application.stop_running()
                
def win32_handler(sig: int) -> bool:
    """Обработчик сигналов Windows"""
    global is_shutting_down, application
    if sig == win32con.CTRL_C_EVENT or sig == win32con.CTRL_BREAK_EVENT:
        logger.info("Получен сигнал завершения работы")
        is_shutting_down = True
        if application:
            try:
                # Получаем или создаем event loop для текущего потока
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Устанавливаем таймаут для graceful shutdown
                shutdown_task = loop.create_task(shutdown())
                try:
                    loop.run_until_complete(asyncio.wait_for(shutdown_task, timeout=5.0))
                except asyncio.TimeoutError:
                    logger.warning("Превышено время ожидания graceful shutdown, выполняем принудительное завершение")
                finally:
                    if not loop.is_closed():
                        loop.close()
                return True
            except Exception as e:
                logger.error(f"Ошибка при завершении работы: {e}")
                return False
    return False

@contextmanager
def safe_db_operation():
    """Контекстный менеджер для безопасных операций с БД"""
    try:
        yield
    except DatabaseError as e:
        logger.error(f"Ошибка базы данных: {e}")
        metrics.increment('db_errors')
        raise
    except QueryError as e:
        logger.error(f"Ошибка запроса: {e}")
        metrics.increment('query_errors')
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        metrics.increment('unexpected_errors')
        raise

def main() -> None:
    """Основная функция запуска бота"""
    global application
    
    if not TelegramConfig.TOKEN:
        logger.error("TELEGRAM_TOKEN не найден в конфигурации! Проверьте файл .env и его расположение в корне проекта.")
        logger.error(f"Текущая директория: {os.getcwd()}")
        logger.error(f"Ожидаемый путь к .env: {Path(__file__).resolve().parent.parent / '.env'}")
        return

    try:
        # Создаем и устанавливаем основной event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Настройка обработчика сигналов для Windows
        if os.name == 'nt':
            win32api.SetConsoleCtrlHandler(win32_handler, True)
        else:
            loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))

        # Создаем кастомный request объект с увеличенными таймаутами
        request = HTTPXRequest(
            connection_pool_size=100,
            read_timeout=30.0,
            write_timeout=30.0,
            connect_timeout=30.0,
            pool_timeout=30.0
        )

        # Создаем приложение
        application = (
            Application.builder()
            .token(TelegramConfig.TOKEN)
            .request(request)
            .build()
        )

        # Добавляем обработчики
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_check)],
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler)],
                WAITING_COORDINATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_coordinates)],
                WAITING_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_input_handler)]
            },
            fallbacks=[
                CommandHandler("cancel", cancel),
                CommandHandler("start", start)
            ],
        )

        application.add_handler(conv_handler)
        application.add_handler(InlineQueryHandler(inline_query_handler))
        
        # Добавляем обработчик callback-запросов для экспорта
        application.add_handler(
            CallbackQueryHandler(handle_export_callback, pattern=r"^export_")
        )
        
        logger.info("Бот запущен")
        metrics.increment('bot_start')
        
        # Запускаем бот в основном event loop с обработкой завершения
        try:
            loop.run_until_complete(
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
            )
        except KeyboardInterrupt:
            logger.info("Получен сигнал прерывания")
            loop.run_until_complete(shutdown())
        finally:
            # Закрываем все соединения и event loop
            if not loop.is_closed():
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        metrics.increment('bot_errors')
        if application:
            try:
                # Используем текущий event loop для завершения работы
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.run_until_complete(shutdown())
                    loop.close()
            except Exception as shutdown_error:
                logger.error(f"Ошибка при завершении работы: {shutdown_error}")

if __name__ == '__main__':
    main() 