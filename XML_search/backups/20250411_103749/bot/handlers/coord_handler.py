"""
Обработчик координат
"""

from telegram import Update
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler
import re

class CoordHandler(BaseHandler):
    """Обработчик координат"""
    
    def __init__(self):
        """Инициализация обработчика координат"""
        super().__init__("coord_handler")
        
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
        
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка координат
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        if not update.message or not update.message.text:
            return States.WAITING_COORDINATES
            
        user_id = update.effective_user.id
        text = update.message.text
        
        try:
            # Парсим координаты
            latitude, longitude = self.parse_coordinates(text)
            
            # Логируем успешный парсинг
            self.log_access(user_id, 'coordinates_parsed', {
                'latitude': latitude,
                'longitude': longitude
            })
            
            # Отправляем координаты в обработчик поиска
            # TODO: Реализовать поиск систем координат по точке
            await update.message.reply_text(
                f"Координаты успешно распознаны:\n"
                f"Широта: {latitude}\n"
                f"Долгота: {longitude}\n\n"
                "Поиск систем координат для этой точки будет реализован позже."
            )
            
            return States.WAITING_COORDINATES
            
        except ValueError as e:
            # Логируем ошибку парсинга
            self.log_access(user_id, 'coordinates_parse_error', {
                'input': text,
                'error': str(e)
            })
            
            # Отправляем сообщение об ошибке
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}\n"
                "Попробуйте еще раз или используйте /cancel для отмены."
            )
            return States.WAITING_COORDINATES
            
    def parse_coordinates(self, text: str) -> tuple:
        """
        Парсинг координат из текста
        
        Args:
            text: Текст с координатами
            
        Returns:
            Кортеж (широта, долгота)
            
        Raises:
            ValueError: Если координаты не удалось распознать
        """
        # Заменяем $ и % на ; для унификации разделителя
        text = text.replace('$', ';').replace('%', ';')
        
        # Удаляем пробелы вокруг разделителя
        text = re.sub(r'\s*;\s*', ';', text.strip())
        
        # Разбиваем на широту и долготу
        parts = text.split(';')
        if len(parts) != 2:
            raise ValueError(
                "Неверный формат ввода. Ожидается 'latitude;longitude' "
                "или 'latitude$longitude' или 'latitude%longitude'."
            )
            
        # Парсим каждую координату
        try:
            latitude = self.dms_to_decimal(parts[0])
            longitude = self.dms_to_decimal(parts[1])
            return latitude, longitude
        except ValueError as e:
            raise ValueError(f"Ошибка при разборе координат: {str(e)}")
            
    def dms_to_decimal(self, coord: str) -> float:
        """
        Преобразование координат из DMS в десятичные градусы
        
        Args:
            coord: Строка с координатой
            
        Returns:
            Десятичное значение координаты
            
        Raises:
            ValueError: Если координату не удалось распознать
        """
        try:
            # Очищаем строку и разбиваем на части
            coord = re.sub(r'\s+', ' ', coord.strip())
            parts = re.split(r'[\s°\'"]+', coord)
            parts = [p for p in parts if p]
            
            if not parts:
                raise ValueError("Пустая строка")
                
            # Парсим градусы
            degrees = float(parts[0])
            
            # Парсим минуты
            minutes = float(parts[1]) if len(parts) > 1 else 0
            
            # Парсим секунды
            seconds = float(parts[2]) if len(parts) > 2 else 0
            
            # Проверяем диапазоны
            if not (-90 <= degrees <= 90):
                raise ValueError("Градусы должны быть в диапазоне [-90, 90]")
            if not (0 <= minutes < 60):
                raise ValueError("Минуты должны быть в диапазоне [0, 60)")
            if not (0 <= seconds < 60):
                raise ValueError("Секунды должны быть в диапазоне [0, 60)")
                
            # Вычисляем десятичное значение
            decimal = degrees + minutes / 60 + seconds / 3600
            return decimal
            
        except ValueError as e:
            raise ValueError(f"Неверный формат координаты: {str(e)}")
        except Exception as e:
            raise ValueError(f"Ошибка при разборе координаты: {str(e)}") 