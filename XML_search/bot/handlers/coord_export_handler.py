"""
Обработчик экспорта для результатов поиска по координатам
"""

import os
from typing import Dict, Any, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler
from .base_handler import BaseHandler
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exceptions import CustomWktGenerationError
from XML_search.bot.handlers.menu_handler import MenuHandler
from XML_search.bot.keyboards.main_keyboard import MainKeyboard
from XML_search.bot.states import States

class CoordExportHandler(BaseHandler):
    """Обработчик экспорта для результатов поиска по координатам"""
    
    def __init__(self, config, db_manager, menu_handler, metrics=None, logger=None):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
            db_manager: Менеджер базы данных
            menu_handler: Обработчик главного меню
            metrics: Менеджер метрик
            logger: Менеджер логирования
        """
        super().__init__(config)
        self._db_manager = db_manager
        self._metrics = metrics or MetricsManager()
        self._logger = logger or LogManager().get_logger(__name__)
        self.output_dir = getattr(config, 'OUTPUT_DIR', 'output')
        os.makedirs(self.output_dir, exist_ok=True)
        self._exporters: Dict[str, Any] = {}
        self.menu_handler = menu_handler
        self._main_keyboard = MainKeyboard()
        self._logger.debug("CoordExportHandler initialized.")
    
    async def setup_exporters(self):
        """Инициализация экспортеров"""
        self._logger.debug("setup_exporters called.")
        if not hasattr(self, '_exporters') or not self._exporters:
            self._logger.info("Initializing exporters dictionary...")
            # Create instances first to log them individually
            civil_exporter = Civil3DExporter(self.config, self._db_manager, self.output_dir)
            gmv20_exporter = GMv20Exporter(self.config, self._db_manager, self.output_dir)
            gmv25_exporter = GMv25Exporter(self.config, self._db_manager, self.output_dir)

            self._logger.info(f"Civil3DExporter instance: {civil_exporter}, type: {type(civil_exporter)}")
            self._logger.info(f"GMv20Exporter instance: {gmv20_exporter}, type: {type(gmv20_exporter)}")
            self._logger.info(f"GMv25Exporter instance: {gmv25_exporter}, type: {type(gmv25_exporter)}")

            self._exporters = {
                'xml_Civil3D': civil_exporter,
                'prj_GMV20': gmv20_exporter,
                'prj_GMV25': gmv25_exporter
            }
            self._logger.info(f"Exporters dictionary populated. Keys: {list(self._exporters.keys())}")
            for k, v_instance in self._exporters.items():
                self._logger.info(f"In dict: Exporter '{k}' -> Value: {v_instance} (type: {type(v_instance)})")
                if v_instance is None:
                    self._logger.error(f"CRITICAL INITIALIZATION ERROR: Exporter '{k}' is None in the dictionary immediately after creation!")
        else:
            self._logger.info(f"Exporters already initialized. Keys: {list(self._exporters.keys())}")
        
    async def handle_export_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, custom_callback_data: Optional[str] = None) -> Optional[States]:
        """
        Обрабатывает callback-запросы на экспорт.
        Если 'custom_callback_data' предоставлен, использует его. Иначе берет из query.data.
        """
        query = update.callback_query
        
        # Отвечаем на callback только если он не был инициирован из другого обработчика
        if not custom_callback_data and query:
            await query.answer()

        try:
            data_to_process = custom_callback_data or (query.data if query else None)

            if not data_to_process:
                self._logger.warning("handle_export_callback called with no query data.")
                return States.WAITING_EXPORT

            await self.setup_exporters()
            
            parts = data_to_process.split('_')
            if len(parts) < 3:
                self._logger.error(f"Invalid callback data format: {data_to_process}")
                if query and query.message:
                    await query.message.reply_text("Ошибка: Некорректный формат запроса на экспорт.")
                return States.WAITING_EXPORT
                
            export_type = parts[1]
            srid = parts[2]
            
            export_format_map = {
                'civil3d': 'xml_Civil3D',
                'gmv20': 'prj_GMV20',
                'gmv25': 'prj_GMV25'
            }
            export_format_key = export_format_map.get(export_type)

            if not export_format_key:
                self._logger.error(f"Unsupported export type: {export_type}")
                if query and query.message:
                    await query.message.reply_text(f"Ошибка: Неподдерживаемый тип экспорта '{export_type}'.")
                return States.WAITING_EXPORT

            # Убираем специальную обработку Civil3D - он теперь работает как обычный экспортер
            
            self._logger.info(f"Handling {export_format_key.upper()} export for SRID {srid}.")

            exporter = self._exporters.get(export_format_key)
            if not exporter:
                self._logger.error(f"Exporter for key '{export_format_key}' not found.")
                if query and query.message:
                    await query.message.reply_text(f"Ошибка: Не найден обработчик для формата {export_format_key}.")
                return States.WAITING_EXPORT
            
            try:
                export_result = await exporter.export(srid)
                
                file_path = None
                if isinstance(export_result, dict):
                    file_path = export_result.get('file_path')
                elif isinstance(export_result, str):
                    file_path = export_result
                
                # Специальная обработка для Civil3D заглушки
                if export_format_key == 'xml_Civil3D' and file_path == "Функционал в разработке":
                    self._logger.info(f"Civil3D экспорт - показываю сообщение: {file_path}")
                    
                    # Определяем chat_id для отправки сообщения
                    chat_id = None
                    if query and query.message and hasattr(query.message, 'chat') and query.message.chat:
                        chat_id = query.message.chat.id
                    elif update.effective_chat:
                        chat_id = update.effective_chat.id
                    elif query and query.from_user:
                        chat_id = query.from_user.id
                    elif update.effective_user:
                        chat_id = update.effective_user.id
                    
                    if chat_id:
                        try:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"📄 {file_path}"
                            )
                            self._logger.info(f"Civil3D message sent for SRID {srid}.")
                        except Exception as send_error:
                            self._logger.error(f"Failed to send Civil3D message: {send_error}", exc_info=True)
                    
                    return States.WAITING_EXPORT
                
                elif file_path and os.path.exists(file_path):
                    actual_filename = os.path.basename(file_path)
                    self._logger.info(f"Export successful. File: '{actual_filename}' at '{file_path}'. Preparing to send.")
                    
                    # Универсальная отправка файла - работает для обычного и inline экспорта
                    chat_id = None
                    
                    # Диагностика структуры объектов для inline экспорта
                    self._logger.debug(f"ДИАГНОСТИКА: query={query}, update.effective_chat={update.effective_chat}, update.effective_user={update.effective_user}")
                    if query:
                        self._logger.debug(f"ДИАГНОСТИКА: query.message={query.message}, query.from_user={query.from_user}")
                        if query.message:
                            self._logger.debug(f"ДИАГНОСТИКА: query.message.chat={getattr(query.message, 'chat', 'НЕТ АТРИБУТА')}")
                    
                    # Способ 1: Через query.message.chat (обычный экспорт)
                    if query and query.message and hasattr(query.message, 'chat') and query.message.chat:
                        chat_id = query.message.chat.id
                        self._logger.debug(f"Chat ID получен из query.message.chat: {chat_id}")
                    
                    # Способ 2: Через effective_chat (универсальный)
                    elif update.effective_chat:
                        chat_id = update.effective_chat.id
                        self._logger.debug(f"Chat ID получен из update.effective_chat: {chat_id}")
                    
                    # Способ 3: Через from_user для inline (последний шанс)
                    elif query and query.from_user:
                        chat_id = query.from_user.id
                        self._logger.debug(f"Chat ID получен из query.from_user: {chat_id}")
                    
                    # Способ 4: Через effective_user (крайний случай)
                    elif update.effective_user:
                        chat_id = update.effective_user.id
                        self._logger.debug(f"Chat ID получен из update.effective_user: {chat_id}")
                    
                    if chat_id:
                        try:
                            with open(file_path, 'rb') as f:
                                await context.bot.send_document(
                                    chat_id=chat_id,
                                    document=InputFile(f, filename=actual_filename),
                                    caption=f"Экспорт SRID={srid} в формате {export_format_key.upper()}"
                                )
                            self._logger.info(f"Document sent for SRID {srid}, format {export_format_key}.")
                        except Exception as send_error:
                            self._logger.error(f"Failed to send document: {send_error}", exc_info=True)
                            if query and query.message:
                                await query.message.reply_text("❌ Ошибка при отправке файла.")
                    else:
                        self._logger.error("Unable to determine chat_id for sending document.")
                        if query and query.message:
                            await query.message.reply_text("❌ Ошибка: не удалось определить чат для отправки файла.")
                    
                    return States.WAITING_EXPORT
                
                else:
                    self._logger.error(f"File NOT found at the path returned by exporter: {file_path}")
                    if query and query.message:
                        await query.message.reply_text(f"Ошибка: экспортер сообщил о создании файла, но он не найден.")
                    return States.WAITING_EXPORT

            except CustomWktGenerationError as e:
                self._logger.error(f"WKT generation failed for SRID {srid}: {e}")
                if query and query.message:
                    await query.message.reply_text(f"Не удалось сгенерировать WKT для SRID {srid}. Экспорт невозможен.")
                return States.WAITING_EXPORT
            except Exception as e:
                self._logger.error(f"Failed to export SRID {srid} to {export_format_key}: {e}", exc_info=True)
                if query and query.message:
                    await query.message.reply_text("Произошла ошибка при экспорте файла.")
                return States.WAITING_EXPORT
        
        except Exception as e:
            self._logger.error(f"An unexpected error occurred in handle_export_callback: {e}", exc_info=True)
            if query and query.message:
                await query.message.reply_text("Произошла непредвиденная ошибка. Попробуйте снова.")
            return States.WAITING_EXPORT

    def get_handler(self):
        """
        Получение обработчика callback-запросов
        
        Returns:
            Обработчик callback-запросов
        """
        return CallbackQueryHandler(self.handle_export_callback, pattern=r'^export_')
    
    @staticmethod
    def get_export_keyboard(srid: str) -> InlineKeyboardMarkup:
        """
        Получение клавиатуры с кнопками экспорта
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Клавиатура с кнопками экспорта
        """
        keyboard = [
            [
                InlineKeyboardButton("xml_Civil3D", callback_data=f"export_civil3d_{srid}"),
                InlineKeyboardButton("prj_GMv20", callback_data=f"export_gmv20_{srid}"),
                InlineKeyboardButton("prj_GMv25", callback_data=f"export_gmv25_{srid}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard) 

    async def handle_unsupported_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[States]:
        """Обрабатывает нажатие на неподдерживаемый тип экспорта (например, Civil3D)."""
        query = update.callback_query
        await query.answer("Этот тип экспорта пока не поддерживается.")
        # Остаемся в том же состоянии, чтобы пользователь мог выбрать другой экспорт
        return States.WAITING_EXPORT 