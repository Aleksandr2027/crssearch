"""
Клавиатура поиска и фильтров
"""

from typing import Optional, Dict, Any
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from .base import BaseKeyboard, KeyboardResult

class SearchKeyboard(BaseKeyboard):
    """Клавиатура поиска и фильтров"""
    
    # Конфигурация фильтров
    FILTERS = {
        'type': {
            'label': '🏷 Тип СК',
            'callback': 'filter_type',
            'description': 'Фильтр по типу системы координат'
        },
        'region': {
            'label': '🌍 Регион',
            'callback': 'filter_region',
            'description': 'Фильтр по региону'
        },
        'zone': {
            'label': '📍 Зона',
            'callback': 'filter_zone',
            'description': 'Фильтр по зоне'
        }
    }
    
    def build(self, filters: Optional[Dict[str, Any]] = None) -> KeyboardResult:
        """
        Построение клавиатуры поиска
        
        Args:
            filters: Текущие активные фильтры
            
        Returns:
            Результат построения клавиатуры
        """
        try:
            buttons = [
                # Кнопка быстрого поиска
                [InlineKeyboardButton(
                    "🔍 Быстрый поиск",
                    switch_inline_query_current_chat=""
                )]
            ]
            
            # Добавляем кнопки фильтров
            for filter_id, info in self.FILTERS.items():
                # Проверяем активен ли фильтр
                is_active = filters and filters.get(filter_id)
                label = f"{info['label']} ✓" if is_active else info['label']
                
                buttons.append([
                    InlineKeyboardButton(
                        label,
                        callback_data=f"{info['callback']}"
                    )
                ])
            
            # Кнопка сброса фильтров если есть активные
            if filters and any(filters.values()):
                buttons.append([
                    InlineKeyboardButton(
                        "🔄 Сбросить фильтры",
                        callback_data="reset_filters"
                    )
                ])
            
            # Кнопка возврата в меню
            buttons.append([
                InlineKeyboardButton(
                    "🔙 Назад",
                    callback_data="menu"
                )
            ])
            
            # Валидируем кнопки
            for row in buttons:
                if not self._validate_buttons([row]):
                    raise ValueError("Ошибка валидации кнопок")
            
            # Отслеживаем метрики
            self._track_build('search')
            
            return KeyboardResult(
                keyboard=InlineKeyboardMarkup(buttons),
                metadata={
                    'type': 'search',
                    'filters': filters,
                    'active_filters': [
                        filter_id for filter_id, value in (filters or {}).items()
                        if value
                    ]
                }
            )
            
        except Exception as e:
            self._track_build('search', success=False)
            self.logger.error(f"Ошибка создания клавиатуры поиска: {e}")
            raise 