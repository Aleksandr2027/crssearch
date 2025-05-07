"""
Обработчик экспорта систем координат
"""

import time
from telegram import Update
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.export.export_manager import ExportManager

class ExportHandler(BaseHandler):
    """Обработчик экспорта систем координат"""
    
    def __init__(self, db_manager: DatabaseManager, metrics: MetricsCollector):
        """
        Инициализация обработчика экспорта
        
        Args:
            db_manager: Менеджер базы данных
            metrics: Сборщик метрик
        """
        super().__init__("export_handler")
        self.db_manager = db_manager
        self.metrics = metrics
        self.export_manager = ExportManager()
        
    async def handle_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка callback-запросов экспорта
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
        """
        start_time = time.time()
        query = update.callback_query
        
        try:
            # Разбираем данные callback
            export_type, srid = query.data.split(':')
            srid = int(srid)
            
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
            available_formats = self.export_manager.get_available_formats(srid)
            if not any(fmt['id'] == exporter_id for fmt in available_formats):
                await query.answer(
                    f"❌ Формат {exporter_id} не поддерживается для SRID {srid}",
                    show_alert=True
                )
                return
                
            # Выполняем экспорт
            try:
                result = self.export_manager.export(srid, exporter_id)
                
                # Отправляем результат пользователю
                # Временно показываем сообщение об успехе
                await query.answer(
                    f"✅ Экспорт в формат {exporter_id} успешно выполнен",
                    show_alert=True
                )
                
                # TODO: Реализовать отправку файла пользователю
                # await context.bot.send_document(
                #     chat_id=update.effective_chat.id,
                #     document=result,
                #     filename=f"export_{srid}_{exporter_id}"
                # )
                
                # Обновляем метрики
                self.metrics.increment('export_success')
                
            except Exception as e:
                self.logger.error(f"Ошибка при экспорте {exporter_id} для SRID {srid}: {e}")
                self.metrics.increment('export_errors')
                await query.answer(
                    "❌ Произошла ошибка при экспорте. Попробуйте позже.",
                    show_alert=True
                )
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback экспорта: {e}")
            self.metrics.increment('export_callback_errors')
            await query.answer(
                "❌ Произошла ошибка при обработке запроса",
                show_alert=True
            )
            
        finally:
            self._log_metrics('handle_export', time.time() - start_time) 