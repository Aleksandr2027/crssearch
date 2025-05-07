"""
Основная клавиатура бота
"""

from typing import List, Dict
from telegram import ReplyKeyboardMarkup, KeyboardButton
from .base_keyboard import BaseKeyboard

class MainKeyboard(BaseKeyboard):
    """Класс для основной клавиатуры бота"""
    
    def __init__(self):
        """Инициализация основной клавиатуры"""
        super().__init__()
        
        # Константы для кнопок
        self.BUTTON_COORD_SEARCH = 'Поиск СК по Lat/Lon'
        self.BUTTON_DESC_SEARCH = 'Поиск СК по описанию'
        self.BUTTON_MENU = '🔙 Главное меню'
        
    def get_keyboard(self) -> ReplyKeyboardMarkup:
        """
        Получение основной клавиатуры
        
        Returns:
            Объект клавиатуры
        """
        buttons = [
            [{'text': self.BUTTON_COORD_SEARCH}],
            [{'text': self.BUTTON_DESC_SEARCH}]
        ]
        return self.create_keyboard(buttons)
        
    def get_menu_keyboard(self) -> ReplyKeyboardMarkup:
        """
        Получение клавиатуры с кнопкой меню
        
        Returns:
            Объект клавиатуры
        """
        buttons = [[{'text': self.BUTTON_MENU}]]
        return self.create_keyboard(buttons)
        
    @classmethod
    def get_all_buttons(cls) -> List[str]:
        """
        Получение списка всех кнопок
        
        Returns:
            Список текстов кнопок
        """
        return [
            cls.BUTTON_COORD_SEARCH,
            cls.BUTTON_DESC_SEARCH,
            cls.BUTTON_MENU
        ] 