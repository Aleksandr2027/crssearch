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
        Создание объекта InlineKeyboardMarkup.

        Args:
            buttons: Список рядов, где каждый ряд - это список словарей, описывающих кнопки.
            row_width: Максимальное количество кнопок в ряду (игнорируется, если структура buttons уже определяет ряды).

        Returns:
            Объект inline клавиатуры.
        """
        keyboard: List[List[InlineKeyboardButton]] = []
        for button_row_specs in buttons:  # Iterate over each list of button dicts (each list is a row)
            current_row_buttons: List[InlineKeyboardButton] = []
            for button_spec in button_row_specs:  # Iterate over each button dict in the current row
                current_row_buttons.append(
                    InlineKeyboardButton(
                        text=button_spec["text"],
                        callback_data=button_spec.get("callback_data"),
                        url=button_spec.get("url"),
                        switch_inline_query=button_spec.get("switch_inline_query"),
                        switch_inline_query_current_chat=button_spec.get("switch_inline_query_current_chat")
                    )
                )
            if current_row_buttons: # Add the constructed row of buttons to the keyboard
                keyboard.append(current_row_buttons)
        
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

# Новая standalone функция, адаптированная из метода класса
def get_export_keyboard_for_srid(srid_str: str) -> InlineKeyboardMarkup:
    """
    Получение клавиатуры экспорта для указанного SRID.
    
    Args:
        srid_str: SRID системы координат в виде строки.
        
    Returns:
        Объект inline клавиатуры.
    """
    # Внутренне можно создать временный экземпляр InlineKeyboard 
    # или просто скопировать логику создания кнопок, что проще здесь.
    
    # srid = int(srid_str) # Преобразование в int, если необходимо для callback_data, 
                         # но f-string справится со строкой.

    buttons_data = [[
        {
            'text': 'xml_Civil3D',
            'callback_data': f'export_xml:{srid_str}' # Используем srid_str напрямую
        },
        {
            'text': 'prj_GMv20',
            'callback_data': f'export_gmv20:{srid_str}'
        },
        {
            'text': 'prj_GMv25',
            'callback_data': f'export_gmv25:{srid_str}'
        }
    ]]
    
    # Логика создания InlineKeyboardMarkup из InlineKeyboard.create_inline_keyboard
    # Здесь мы можем ее упростить, так как структура кнопок фиксирована (одна строка)
    keyboard_buttons_row = []
    for button_def in buttons_data[0]: # У нас одна строка кнопок
        keyboard_buttons_row.append(
            InlineKeyboardButton(
                text=button_def["text"],
                callback_data=button_def.get("callback_data"),
                url=button_def.get("url"), # на случай если понадобится
                switch_inline_query=button_def.get("switch_inline_query"),
                switch_inline_query_current_chat=button_def.get("switch_inline_query_current_chat")
            )
        )
            
    return InlineKeyboardMarkup([keyboard_buttons_row]) 