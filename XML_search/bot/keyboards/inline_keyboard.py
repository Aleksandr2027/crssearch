"""
Inline клавиатура бота
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

class InlineKeyboard:
    """Inline клавиатура бота"""
    
    def create_inline_keyboard(
        self,
        buttons: List[List[Dict[str, Any]]],
        row_width: int = 3
    ) -> InlineKeyboardMarkup:
        """
        Создание inline клавиатуры
        
        Args:
            buttons: Список кнопок в формате [{"text": "text", "callback_data": "data"}]
            row_width: Количество кнопок в строке
            
        Returns:
            Объект inline клавиатуры
        """
        keyboard = []
        row = []
        
        for button in buttons:
            if len(row) >= row_width:
                keyboard.append(row)
                row = []
            row.append(
                InlineKeyboardButton(
                    text=button["text"],
                    callback_data=button.get("callback_data"),
                    url=button.get("url"),
                    switch_inline_query=button.get("switch_inline_query"),
                    switch_inline_query_current_chat=button.get("switch_inline_query_current_chat")
                )
            )
            
        if row:
            keyboard.append(row)
            
        return InlineKeyboardMarkup(keyboard)
    
    def get_search_keyboard(self) -> InlineKeyboardMarkup:
        """
        Получение клавиатуры быстрого поиска
        
        Returns:
            Объект inline клавиатуры
        """
        buttons = [[{
            'text': '🔍 Быстрый поиск в текущем чате',
            'switch_inline_query_current_chat': ''
        }]]
        return self.create_inline_keyboard(buttons)
    
    def get_export_keyboard(self, srid: int) -> InlineKeyboardMarkup:
        """
        Получение клавиатуры экспорта
        
        Args:
            srid: SRID системы координат
            
        Returns:
            Объект inline клавиатуры
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