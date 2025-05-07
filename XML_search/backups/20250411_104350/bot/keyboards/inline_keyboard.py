"""
Inline-клавиатура бота
"""

from typing import List, Dict
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from .base_keyboard import BaseKeyboard

class InlineKeyboard(BaseKeyboard):
    """Класс для inline-клавиатуры бота"""
    
    def __init__(self):
        """Инициализация inline-клавиатуры"""
        super().__init__()
        
    def get_keyboard(self) -> InlineKeyboardMarkup:
        """
        Получение inline-клавиатуры
        
        Returns:
            Объект inline-клавиатуры
        """
        buttons = [[{
            'text': '🔍 Быстрый поиск в текущем чате',
            'switch_inline_query_current_chat': ''
        }]]
        return self.create_inline_keyboard(buttons)
        
    def get_export_keyboard(self, srid: int) -> InlineKeyboardMarkup:
        """
        Получение клавиатуры для экспорта
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Объект inline-клавиатуры
        """
        buttons = [[
            {
                'text': 'xml_Civil3D',
                'callback_data': f'export_xml:{srid}'
            },
            {
                'text': 'prj_GMv20',
                'callback_data': f'export_gmv20:{srid}'
            },
            {
                'text': 'prj_GMv25',
                'callback_data': f'export_gmv25:{srid}'
            }
        ]]
        return self.create_inline_keyboard(buttons)
        
    @classmethod
    def get_all_buttons(cls) -> List[str]:
        """
        Получение списка всех кнопок
        
        Returns:
            Список текстов кнопок
        """
        return [
            'xml_Civil3D',
            'prj_GMv20',
            'prj_GMv25'
        ]
        
    @classmethod
    def get_export_types(cls) -> Dict[str, str]:
        """
        Получение словаря типов экспорта
        
        Returns:
            Словарь {callback_prefix: button_text}
        """
        return {
            'export_xml': 'xml_Civil3D',
            'export_gmv20': 'prj_GMv20',
            'export_gmv25': 'prj_GMv25'
        } 