"""
Базовый класс для клавиатур
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup

class BaseKeyboard(ABC):
    """Базовый класс для всех клавиатур"""
    
    def __init__(self):
        """Инициализация базовой клавиатуры"""
        pass
        
    @abstractmethod
    def get_keyboard(self) -> ReplyKeyboardMarkup:
        """
        Получение клавиатуры
        
        Returns:
            Объект клавиатуры
        """
        pass
        
    def create_keyboard(
        self,
        buttons: List[List[Dict[str, str]]],
        resize_keyboard: bool = True,
        one_time_keyboard: bool = False,
        selective: bool = False
    ) -> ReplyKeyboardMarkup:
        """
        Создание клавиатуры из списка кнопок
        
        Args:
            buttons: Список списков кнопок
            resize_keyboard: Флаг изменения размера клавиатуры
            one_time_keyboard: Флаг одноразовой клавиатуры
            selective: Флаг выборочного отображения
            
        Returns:
            Объект клавиатуры
        """
        return ReplyKeyboardMarkup(
            [[button['text'] for button in row] for row in buttons],
            resize_keyboard=resize_keyboard,
            one_time_keyboard=one_time_keyboard,
            selective=selective
        )
        
    def create_inline_keyboard(
        self,
        buttons: List[List[Dict[str, str]]],
        resize_keyboard: bool = True
    ) -> InlineKeyboardMarkup:
        """
        Создание inline-клавиатуры из списка кнопок
        
        Args:
            buttons: Список списков кнопок
            resize_keyboard: Флаг изменения размера клавиатуры
            
        Returns:
            Объект inline-клавиатуры
        """
        return InlineKeyboardMarkup(
            [[button['text'] for button in row] for row in buttons],
            resize_keyboard=resize_keyboard
        ) 