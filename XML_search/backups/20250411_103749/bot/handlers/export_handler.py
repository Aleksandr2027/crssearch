"""
Обработчик экспорта
"""

from telegram import Update
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler
from XML_search.enhanced.export.export_manager import ExportManager
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter

class ExportHandler(BaseHandler):
    """Обработчик экспорта"""
    
    def __init__(self):
        """Инициализация обработчика экспорта"""
        super().__init__("export_handler")
        
        # Инициализируем менеджер экспорта и экспортеры
        self.export_manager = ExportManager()
        
        # Регистрируем экспортеры
        self.export_manager.register_exporter('xml_Civil3D', Civil3DExporter({}))
        self.export_manager.register_exporter('prj_GMv20', GMv20Exporter({}))
        self.export_manager.register_exporter('prj_GMv25', GMv25Exporter({}))
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Основной метод обработки запроса
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        return await self._handle_update(update, context)
        
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка callback-запросов экспорта
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
        """
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
                
            except Exception as e:
                self.logger.error(f"Ошибка при экспорте {exporter_id} для SRID {srid}: {e}")
                await query.answer(
                    "❌ Произошла ошибка при экспорте. Попробуйте позже.",
                    show_alert=True
                )
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback экспорта: {e}")
            await query.answer(
                "❌ Произошла ошибка при обработке запроса",
                show_alert=True
            )
            
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка запроса на экспорт
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        if not update.message or not update.message.text:
            return States.EXPORT_SELECTION
            
        user_id = update.effective_user.id
        text = update.message.text
        
        # TODO: Реализовать обработку прямых команд экспорта
        await update.message.reply_text(
            "Для экспорта используйте кнопки под сообщением с результатами поиска."
        )
        
        return States.EXPORT_SELECTION 