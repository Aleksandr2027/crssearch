"""
Клавиатура главного меню
"""

from typing import List
from telegram import ReplyKeyboardMarkup, KeyboardButton
from .base_keyboard import BaseKeyboard

# Кнопки главного меню
BUTTON_COORD_SEARCH = 'Поиск СК по Lat/Lon'
BUTTON_DESC_SEARCH = 'Поиск СК по описанию'

# Кнопки экспорта
BUTTON_EXPORT_CIVIL3D = 'xml_Civil3D'
BUTTON_EXPORT_GMV20 = 'prj_GMv20'
BUTTON_EXPORT_GMV25 = 'prj_GMv25'

class MainKeyboard(BaseKeyboard):
    """Класс для работы с основной клавиатурой"""
    
    # Константы для кнопок
    BUTTON_SEARCH = '/search - Поиск систем координат'
    BUTTON_EXPORT = '/export - Экспорт результатов'
    BUTTON_HELP = '/help - Помощь'
    BUTTON_SETTINGS = '/settings - Настройки'
    BUTTON_MENU = '🔙 Главное меню'  # Исправлено - используем правильную константу

    # Добавленные константы на основе логов и ошибок линтера
    BUTTON_SEARCH_COORD = 'Поиск СК по Lat/Lon'
    BUTTON_SEARCH_TEXT = 'Поиск СК по описанию'
    BUTTON_DESC_SEARCH = 'Поиск СК по описанию'
    
    def get_keyboard(self) -> ReplyKeyboardMarkup:
        """
        Получение клавиатуры главного меню
        
        Returns:
            ReplyKeyboardMarkup: Клавиатура с кнопками
        """
        keyboard = [
            [KeyboardButton(self.BUTTON_SEARCH)],
            [KeyboardButton(self.BUTTON_EXPORT)],
            [KeyboardButton(self.BUTTON_HELP), KeyboardButton(self.BUTTON_SETTINGS)]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
    def get_back_keyboard(self) -> ReplyKeyboardMarkup:
        """
        Получение клавиатуры с кнопкой возврата в меню
        
        Returns:
            ReplyKeyboardMarkup: Клавиатура с кнопкой возврата
        """
        keyboard = [[KeyboardButton(self.BUTTON_MENU)]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
    @classmethod
    def get_all_buttons(cls) -> List[str]:
        """
        Получение списка всех кнопок
        
        Returns:
            Список текстов кнопок
        """
        return [
            cls.BUTTON_SEARCH_COORD,
            cls.BUTTON_DESC_SEARCH,
            cls.BUTTON_MENU
        ] 