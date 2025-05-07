"""
Обработчик экспорта данных
"""
import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from .exceptions import ExportError, ValidationError
from .export_manager import ExportManager
from .export_config import export_config

logger = logging.getLogger(__name__)

class ExportHandler:
    """Обработчик экспорта данных"""
    
    def __init__(self):
        """Инициализация обработчика экспорта"""
        self.export_manager = ExportManager()
        logger.info("ExportHandler initialized")
    
    async def handle_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды экспорта
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        try:
            # Получаем параметры экспорта
            format_type = context.args[0] if context.args else 'json'
            query = ' '.join(context.args[1:]) if len(context.args) > 1 else None
            
            # Проверяем формат
            if format_type not in export_config.supported_formats:
                await update.message.reply_text(
                    f"Неподдерживаемый формат экспорта. "
                    f"Доступные форматы: {', '.join(export_config.supported_formats)}"
                )
                return
            
            # Экспортируем данные
            result = await self.export_manager.export_data(
                format_type=format_type,
                query=query
            )
            
            # Отправляем результат
            await update.message.reply_document(
                document=result,
                filename=f"export.{format_type}"
            )
            
        except ValidationError as e:
            await update.message.reply_text(f"Ошибка валидации: {str(e)}")
        except ExportError as e:
            await update.message.reply_text(f"Ошибка экспорта: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in export handler: {str(e)}")
            await update.message.reply_text("Произошла непредвиденная ошибка при экспорте")
