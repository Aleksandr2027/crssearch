"""
Утилиты для работы с клавиатурами бота
"""

from typing import List, Dict, Any, Optional, Union
from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.bot.keyboards.main_keyboard import (
    MainKeyboard,
    BUTTON_COORD_SEARCH,
    BUTTON_DESC_SEARCH,
    BUTTON_EXPORT_CIVIL3D,
    BUTTON_EXPORT_GMV20,
    BUTTON_EXPORT_GMV25
)

class KeyboardManager:
    """Менеджер клавиатур"""
    
    def __init__(self):
        """Инициализация менеджера клавиатур"""
        self.metrics = MetricsManager()
        self.logger = LogManager().get_logger(__name__)
        self.cache = CacheManager()
        
        # Права доступа к форматам экспорта
        self.export_access = {
            'xml_Civil3D': lambda user_id: True,  # Доступен всем
            'prj_GMv20': self._check_gmv_access,  # Требует проверки
            'prj_GMv25': self._check_gmv_access   # Требует проверки
        }
        
    def get_export_keyboard(self, srid: int, user_id: Optional[int] = None) -> InlineKeyboardMarkup:
        """
        Получить клавиатуру для экспорта
        
        Args:
            srid: SRID системы координат
            user_id: ID пользователя для проверки прав
            
        Returns:
            Клавиатура с кнопками экспорта
        """
        try:
            # Проверяем кэш
            cache_key = f"export_keyboard_{srid}_{user_id}"
            cached_keyboard = self.cache.get(cache_key)
            if cached_keyboard:
                self.metrics.increment('keyboard_cache_hits')
                return cached_keyboard
            
            # Создаем кнопки с учетом прав доступа
            buttons = []
            for format_type, access_check in self.export_access.items():
                if user_id is None or access_check(user_id):
                    buttons.append(
                        InlineKeyboardButton(
                            format_type,
                            callback_data=f"export_{format_type}:{srid}"
                        )
                    )
            
            # Группируем кнопки по 2 в ряд
            keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
            markup = InlineKeyboardMarkup(keyboard)
            
            # Кэшируем результат
            self.cache.set(cache_key, markup)
            self.metrics.increment('keyboard_cache_sets')
            
            return markup
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании клавиатуры экспорта: {e}")
            self.metrics.increment('keyboard_errors')
            # Возвращаем пустую клавиатуру в случае ошибки
            return InlineKeyboardMarkup([[]])
            
    def get_search_keyboard(self, filters: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
        """
        Получить клавиатуру для поиска
        
        Args:
            filters: Текущие фильтры поиска
            
        Returns:
            Клавиатура с кнопками поиска
        """
        try:
            # Проверяем кэш
            cache_key = f"search_keyboard_{hash(str(filters))}"
            cached_keyboard = self.cache.get(cache_key)
            if cached_keyboard:
                self.metrics.increment('keyboard_cache_hits')
                return cached_keyboard
            
            # Создаем кнопки фильтров
            buttons = []
            if filters:
                for filter_name, filter_value in filters.items():
                    buttons.append([
                        InlineKeyboardButton(
                            f"{'✅' if filter_value else '❌'} {filter_name}",
                            callback_data=f"filter_{filter_name}"
                        )
                    ])
            
            # Добавляем кнопку быстрого поиска
            buttons.append([
                InlineKeyboardButton(
                    "🔍 Быстрый поиск",
                    switch_inline_query_current_chat=""
                )
            ])
            
            # Добавляем кнопку сброса фильтров
            if filters:
                buttons.append([
                    InlineKeyboardButton(
                        "🔄 Сбросить фильтры",
                        callback_data="reset_filters"
                    )
                ])
            
            markup = InlineKeyboardMarkup(buttons)
            
            # Кэшируем результат
            self.cache.set(cache_key, markup)
            self.metrics.increment('keyboard_cache_sets')
            
            return markup
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании клавиатуры поиска: {e}")
            self.metrics.increment('keyboard_errors')
            return InlineKeyboardMarkup([[]])
            
    def get_pagination_keyboard(
        self,
        total_items: int,
        current_page: int,
        items_per_page: int = 10
    ) -> InlineKeyboardMarkup:
        """
        Получить клавиатуру пагинации
        
        Args:
            total_items: Общее количество элементов
            current_page: Текущая страница
            items_per_page: Элементов на странице
            
        Returns:
            Клавиатура с кнопками пагинации
        """
        try:
            # Проверяем кэш
            cache_key = f"pagination_keyboard_{total_items}_{current_page}_{items_per_page}"
            cached_keyboard = self.cache.get(cache_key)
            if cached_keyboard:
                self.metrics.increment('keyboard_cache_hits')
                return cached_keyboard
            
            # Вычисляем параметры пагинации
            total_pages = (total_items + items_per_page - 1) // items_per_page
            buttons = []
            
            # Добавляем навигационные кнопки
            nav_buttons = []
            if current_page > 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "⬅️",
                        callback_data=f"page:{current_page-1}"
                    )
                )
            
            nav_buttons.append(
                InlineKeyboardButton(
                    f"{current_page}/{total_pages}",
                    callback_data="current_page"
                )
            )
            
            if current_page < total_pages:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "➡️",
                        callback_data=f"page:{current_page+1}"
                    )
                )
            
            buttons.append(nav_buttons)
            
            markup = InlineKeyboardMarkup(buttons)
            
            # Кэшируем результат
            self.cache.set(cache_key, markup)
            self.metrics.increment('keyboard_cache_sets')
            
            return markup
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании клавиатуры пагинации: {e}")
            self.metrics.increment('keyboard_errors')
            return InlineKeyboardMarkup([[]])
            
    def validate_export_access(self, format_type: str, user_id: int) -> bool:
        """
        Проверить права доступа к формату экспорта
        
        Args:
            format_type: Тип формата
            user_id: ID пользователя
            
        Returns:
            True если доступ разрешен, False иначе
        """
        try:
            access_check = self.export_access.get(format_type)
            if access_check:
                return access_check(user_id)
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при проверке прав доступа: {e}")
            self.metrics.increment('access_check_errors')
            return False
            
    def _check_gmv_access(self, user_id: int) -> bool:
        """
        Проверить права доступа к форматам GMv
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если доступ разрешен, False иначе
        """
        # TODO: Реализовать проверку прав доступа к GMv форматам
        return True  # Временно разрешаем всем 

def create_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Создание главной клавиатуры бота
    
    Returns:
        ReplyKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [
        [KeyboardButton(BUTTON_COORD_SEARCH)],
        [KeyboardButton(BUTTON_DESC_SEARCH)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_search_keyboard(menu_button_text: str = MainKeyboard.BUTTON_MENU) -> ReplyKeyboardMarkup:
    """
    Создание клавиатуры поиска
    
    Args:
        menu_button_text: Текст кнопки меню
        
    Returns:
        ReplyKeyboardMarkup: Объект клавиатуры
    """
    keyboard = [[KeyboardButton(menu_button_text)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_export_keyboard(srid: int) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры экспорта
    
    Args:
        srid: SRID системы координат
        
    Returns:
        InlineKeyboardMarkup: Объект inline-клавиатуры
    """
    buttons = [
        InlineKeyboardButton(
            "xml_Civil3D",
            callback_data=f"export_xml:{srid}"
        ),
        InlineKeyboardButton(
            "prj_GMv20",
            callback_data=f"export_gmv20:{srid}"
        ),
        InlineKeyboardButton(
            "prj_GMv25",
            callback_data=f"export_gmv25:{srid}"
        )
    ]
    return InlineKeyboardMarkup([buttons])

def create_inline_search_keyboard() -> InlineKeyboardMarkup:
    """
    Создание inline-клавиатуры для быстрого поиска
    
    Returns:
        InlineKeyboardMarkup: Объект inline-клавиатуры
    """
    button = InlineKeyboardButton(
        "🔍 Быстрый поиск в текущем чате",
        switch_inline_query_current_chat=""
    )
    return InlineKeyboardMarkup([[button]]) 