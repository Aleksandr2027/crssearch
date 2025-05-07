"""
Клавиатура экспорта форматов
"""

from typing import Optional, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from .base import BaseKeyboard, KeyboardResult

class ExportKeyboard(BaseKeyboard):
    """Клавиатура для экспорта в разные форматы"""
    
    # Конфигурация форматов (как в ExportValidator)
    FORMATS = {
        'xml_Civil3D': {
            'label': 'xml_Civil3D',
            'requires_auth': False,
            'description': 'Экспорт в формат Civil 3D'
        },
        'prj_GMv20': {
            'label': 'prj_GMv20',
            'requires_auth': True,
            'description': 'Экспорт в формат GM v2.0'
        },
        'prj_GMv25': {
            'label': 'prj_GMv25',
            'requires_auth': True,
            'description': 'Экспорт в формат GM v2.5'
        }
    }
    
    def build(self, srid: int, user_id: Optional[int] = None) -> KeyboardResult:
        """
        Построение клавиатуры экспорта
        
        Args:
            srid: SRID системы координат
            user_id: ID пользователя для проверки прав
            
        Returns:
            Результат построения клавиатуры
            
        Raises:
            ValueError: Если SRID невалиден
        """
        try:
            # Валидация SRID
            if not isinstance(srid, int) or srid <= 0:
                raise ValueError(f"Невалидный SRID: {srid}")
            
            buttons = []
            row = []
            
            # Создаем кнопки для каждого формата
            for format_id, info in self.FORMATS.items():
                # Проверяем права доступа
                if not info['requires_auth'] or user_id is not None:
                    button = InlineKeyboardButton(
                        info['label'],
                        callback_data=f"export_{format_id}:{srid}"
                    )
                    row.append(button)
                    
                    # Формируем ряды по 2 кнопки
                    if len(row) == 2:
                        buttons.append(row)
                        row = []
            
            # Добавляем оставшиеся кнопки
            if row:
                buttons.append(row)
                
            # Добавляем кнопку возврата в меню
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
            self._track_build('export')
            
            return KeyboardResult(
                keyboard=InlineKeyboardMarkup(buttons),
                metadata={
                    'type': 'export',
                    'srid': srid,
                    'user_id': user_id,
                    'available_formats': [
                        format_id for format_id, info in self.FORMATS.items()
                        if not info['requires_auth'] or user_id is not None
                    ]
                }
            )
            
        except Exception as e:
            self._track_build('export', success=False)
            self.logger.error(f"Ошибка создания клавиатуры экспорта: {e}")
            raise 