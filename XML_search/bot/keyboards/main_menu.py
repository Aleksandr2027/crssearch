"""
Клавиатура главного меню
"""

from typing import Dict
from telegram import ReplyKeyboardMarkup, KeyboardButton
from .base import BaseKeyboard, KeyboardResult

class MainMenuKeyboard(BaseKeyboard):
    """Клавиатура главного меню"""
    
    # Константы для кнопок
    BUTTONS: Dict[str, str] = {
        'coord_search': 'Поиск СК по Lat/Lon',
        'desc_search': 'Поиск СК по описанию',
        'menu': '🔙 Главное меню'
    }
    
    def build(self, **kwargs) -> KeyboardResult:
        """
        Построение клавиатуры главного меню
        
        Returns:
            Результат построения клавиатуры
        """
        try:
            # Создаем кнопки
            buttons = [
                [KeyboardButton(self.BUTTONS['coord_search'])],
                [KeyboardButton(self.BUTTONS['desc_search'])]
            ]
            
            # Валидируем кнопки
            if not self._validate_buttons(buttons):
                raise ValueError("Ошибка валидации кнопок")
            
            # Создаем клавиатуру
            keyboard = ReplyKeyboardMarkup(
                buttons,
                resize_keyboard=True,
                one_time_keyboard=False
            )
            
            # Отслеживаем создание
            self._track_build('main_menu')
            
            return KeyboardResult(
                keyboard=keyboard,
                metadata={'type': 'main_menu'}
            )
            
        except Exception as e:
            self._track_build('main_menu', success=False)
            raise ValueError(f"Ошибка создания клавиатуры главного меню: {e}") 