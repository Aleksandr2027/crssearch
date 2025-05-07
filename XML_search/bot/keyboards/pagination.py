"""
Клавиатура пагинации
"""

from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from .base import BaseKeyboard, KeyboardResult

class PaginationKeyboard(BaseKeyboard):
    """Клавиатура для пагинации результатов"""
    
    def __init__(self):
        """Инициализация клавиатуры пагинации"""
        super().__init__("pagination")
        self.metrics = MetricsManager()
        self.logger = LogManager().get_logger(__name__)
        self.cache = CacheManager()
        
    def build(
        self,
        total_items: int,
        current_page: int,
        items_per_page: int = 10,
        **kwargs
    ) -> KeyboardResult:
        """
        Построение клавиатуры пагинации
        
        Args:
            total_items: Общее количество элементов
            current_page: Текущая страница
            items_per_page: Элементов на странице
            **kwargs: Дополнительные параметры
            
        Returns:
            Результат построения клавиатуры
        """
        try:
            # Проверяем кэш
            cache_key = f"pagination_{total_items}_{current_page}_{items_per_page}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.metrics.increment('keyboard_cache_hits')
                return cached_result
            
            # Вычисляем параметры пагинации
            total_pages = (total_items + items_per_page - 1) // items_per_page
            buttons = []
            
            # Добавляем навигационные кнопки
            nav_buttons = []
            
            # Кнопка "В начало"
            if current_page > 2:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "⏮",
                        callback_data="page:1"
                    )
                )
            
            # Кнопка "Назад"
            if current_page > 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "⬅️",
                        callback_data=f"page:{current_page-1}"
                    )
                )
            
            # Индикатор страницы
            nav_buttons.append(
                InlineKeyboardButton(
                    f"{current_page}/{total_pages}",
                    callback_data="current_page"
                )
            )
            
            # Кнопка "Вперед"
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "➡️",
                        callback_data=f"page:{current_page+1}"
                    )
                )
            
            # Кнопка "В конец"
            if current_page < total_pages - 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "⏭",
                        callback_data=f"page:{total_pages}"
                    )
                )
            
            buttons.append(nav_buttons)
            
            # Добавляем информацию о количестве элементов
            info_buttons = [
                InlineKeyboardButton(
                    f"Всего: {total_items}",
                    callback_data="total_items"
                )
            ]
            buttons.append(info_buttons)
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup(buttons)
            
            # Создаем результат
            result = KeyboardResult(
                keyboard=keyboard,
                metadata={
                    'total_items': total_items,
                    'current_page': current_page,
                    'total_pages': total_pages,
                    'items_per_page': items_per_page
                }
            )
            
            # Кэшируем результат
            self.cache.set(cache_key, result)
            self.metrics.increment('keyboard_cache_sets')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании клавиатуры пагинации: {e}")
            self.metrics.increment('keyboard_errors')
            # Возвращаем пустую клавиатуру в случае ошибки
            return KeyboardResult(
                keyboard=InlineKeyboardMarkup([[]]),
                metadata={}
            )
            
    def validate_callback_data(self, callback_data: str) -> bool:
        """
        Валидация callback_data
        
        Args:
            callback_data: Данные для проверки
            
        Returns:
            True если данные валидны
        """
        try:
            if not callback_data.startswith('page:'):
                return False
                
            # Проверяем номер страницы
            _, page = callback_data.split(':', 1)
            page = int(page)
            return page > 0
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации callback_data: {e}")
            return False
            
    def get_page_info(self, callback_data: str) -> Optional[Dict[str, Any]]:
        """
        Получение информации о странице из callback_data
        
        Args:
            callback_data: Данные callback
            
        Returns:
            Словарь с информацией о странице или None
        """
        try:
            if not self.validate_callback_data(callback_data):
                return None
                
            _, page = callback_data.split(':', 1)
            return {
                'page': int(page)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о странице: {e}")
            return None 