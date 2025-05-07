"""
Тесты для утилит работы с клавиатурами
"""
import pytest
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from XML_search.bot.utils.keyboard_utils import (
    create_main_keyboard,
    create_search_keyboard,
    create_export_keyboard,
    create_inline_search_keyboard
)
from XML_search.bot.keyboards.main_keyboard import (
    BUTTON_COORD_SEARCH,
    BUTTON_DESC_SEARCH,
    BUTTON_MENU
)

class TestKeyboardUtils:
    """Тесты для утилит создания клавиатур"""
    
    def test_create_main_keyboard(self):
        """Тест создания главной клавиатуры"""
        keyboard = create_main_keyboard()
        assert isinstance(keyboard, ReplyKeyboardMarkup)
        keyboard_buttons = [[btn.text for btn in row] for row in keyboard.keyboard]
        assert [BUTTON_COORD_SEARCH] in keyboard_buttons
        assert [BUTTON_DESC_SEARCH] in keyboard_buttons
        assert keyboard.resize_keyboard is True
        
    def test_create_search_keyboard(self):
        """Тест создания клавиатуры поиска"""
        keyboard = create_search_keyboard()
        assert isinstance(keyboard, ReplyKeyboardMarkup)
        keyboard_buttons = [[btn.text for btn in row] for row in keyboard.keyboard]
        assert [BUTTON_MENU] in keyboard_buttons
        assert keyboard.resize_keyboard is True
        
    def test_create_export_keyboard(self):
        """Тест создания клавиатуры экспорта"""
        srid = 100000
        keyboard = create_export_keyboard(srid)
        assert isinstance(keyboard, InlineKeyboardMarkup)
        buttons = keyboard.inline_keyboard[0]
        
        # Проверяем тексты кнопок
        button_texts = [btn.text for btn in buttons]
        assert "xml_Civil3D" in button_texts
        assert "prj_GMv20" in button_texts
        assert "prj_GMv25" in button_texts
        
        # Проверяем callback_data
        for button in buttons:
            assert button.callback_data.startswith('export_')
            assert str(srid) in button.callback_data
        
    def test_create_inline_search_keyboard(self):
        """Тест создания inline клавиатуры поиска"""
        keyboard = create_inline_search_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)
        button = keyboard.inline_keyboard[0][0]
        assert button.switch_inline_query_current_chat == ""
        assert "Быстрый поиск" in button.text
        
    def test_main_keyboard_layout(self):
        """Тест расположения кнопок в главной клавиатуре"""
        keyboard = create_main_keyboard()
        keyboard_buttons = [[btn.text for btn in row] for row in keyboard.keyboard]
        # Проверяем, что кнопки находятся в правильных строках
        assert len(keyboard_buttons) == 2  # Две строки
        assert [BUTTON_COORD_SEARCH] == keyboard_buttons[0]  # Первая кнопка в первой строке
        assert [BUTTON_DESC_SEARCH] == keyboard_buttons[1]  # Вторая кнопка во второй строке
        
    def test_search_keyboard_with_custom_text(self):
        """Тест создания клавиатуры поиска с пользовательским текстом"""
        custom_text = "Тестовая кнопка"
        keyboard = create_search_keyboard(menu_button_text=custom_text)
        keyboard_buttons = [[btn.text for btn in row] for row in keyboard.keyboard]
        assert [custom_text] in keyboard_buttons
        
    def test_inline_keyboard_button_attributes(self):
        """Тест атрибутов кнопок inline клавиатуры"""
        keyboard = create_inline_search_keyboard()
        for row in keyboard.inline_keyboard:
            for button in row:
                assert isinstance(button, InlineKeyboardButton)
                assert button.text  # Проверяем наличие текста
                assert button.switch_inline_query_current_chat is not None 