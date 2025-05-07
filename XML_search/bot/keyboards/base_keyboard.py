"""
Базовый класс для клавиатур бота
"""

from typing import List, Dict, Any
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

class BaseKeyboard:
    """Базовый класс для клавиатур"""
    
    def __init__(self):
        """Инициализация базовой клавиатуры"""
        pass
        
    def create_keyboard(self, buttons: List[List[Dict[str, str]]]) -> ReplyKeyboardMarkup:
        """
        Создание обычной клавиатуры
        
        Args:
            buttons: Список списков с описанием кнопок
            
        Returns:
            Объект клавиатуры
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                keyboard_row.append(button['text'])
            keyboard.append(keyboard_row)
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
    def create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
        """
        Создание inline-клавиатуры
        
        Args:
            buttons: Список списков с описанием кнопок
            
        Returns:
            Объект inline-клавиатуры
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                keyboard_row.append(
                    InlineKeyboardButton(
                        text=button['text'],
                        callback_data=button.get('callback_data'),
                        url=button.get('url'),
                        switch_inline_query=button.get('switch_inline_query'),
                        switch_inline_query_current_chat=button.get('switch_inline_query_current_chat')
                    )
                )
            keyboard.append(keyboard_row)
        return InlineKeyboardMarkup(keyboard) 