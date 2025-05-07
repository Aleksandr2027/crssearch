"""
Обработчик главного меню бота
"""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..states.conversation_states import States
from .base_handler import BaseHandler

class MenuHandler(BaseHandler):
    """Обработчик главного меню"""
    
    def __init__(self):
        """Инициализация обработчика меню"""
        super().__init__("menu_handler")
        
        # Константы для кнопок меню
        self.BUTTON_COORD_SEARCH = 'Поиск СК по Lat/Lon'
        self.BUTTON_DESC_SEARCH = 'Поиск СК по описанию'
        self.BUTTON_MENU = '🔙 Главное меню'
        
    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик выбора пункта меню"""
        return await self.handle_update(update, context)
        
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка выбора пункта меню
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        if not update.message or not update.message.text:
            return States.MAIN_MENU
            
        user_id = update.effective_user.id
        choice = update.message.text
        
        # Обработка выбора поиска по координатам
        if choice == self.BUTTON_COORD_SEARCH:
            self.log_access(user_id, 'coord_search_selected')
            self.metrics.increment('coord_search_selected')
            
            # Создаем клавиатуру с кнопкой возврата в меню
            keyboard = [[KeyboardButton(self.BUTTON_MENU)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Отправляем инструкции по вводу координат
            await update.message.reply_text(
                "📍 Введите координаты в формате 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'\n\n"
                "Поддерживаемые форматы ввода:\n"
                "1. Десятичные градусы: 55.7558;37.6173 или 55.7558$37.6173 или 55.7558%37.6173\n"
                "2. Градусы и минуты: 55 45.348;37 37.038 или 55 45.348$37 37.038 или 55 45.348%37 37.038\n"
                "3. Градусы, минуты и секунды: 55 45 20.88;37 37 2.28 или 55 45 20.88$37 37 2.28 или 55 45 20.88%37 37 2.28\n"
                "4. С обозначениями: 55°45'20.88\";37°37'2.28\" или 55°45'20.88\"$37°37'2.28\" или 55°45'20.88\"%37°37'2.28\"\n\n"
                "Разделитель между широтой и долготой - точка с запятой (;) или знак доллара ($) или знак процента (%)",
                reply_markup=reply_markup
            )
            return States.WAITING_COORDINATES
            
        # Обработка выбора поиска по описанию
        elif choice == self.BUTTON_DESC_SEARCH:
            self.log_access(user_id, 'desc_search_selected')
            self.metrics.increment('desc_search_selected')
            
            # Создаем клавиатуру с кнопкой возврата в меню
            keyboard = [[KeyboardButton(self.BUTTON_MENU)]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Отправляем основное сообщение с инструкциями
            await update.message.reply_text(
                "🔍 Как пользоваться поиском:\n\n"
                "1. Поиск по SRID:\n"
                "   - Отправьте номер системы координат\n"
                "   - Пример: 100000\n\n"
                "2. Поиск по названию:\n"
                "   - Отправьте часть названия\n"
                "   - Пример: MSK01z1\n\n"
                "3. Поиск по описанию:\n"
                "   - Отправьте часть описания\n"
                "   - Пример: Московская, Moskovskaya\n\n"
                "Результаты будут отсортированы по релевантности:\n"
                "- Сначала точные совпадения\n"
                "- Затем частичные совпадения",
                reply_markup=reply_markup
            )
            
            # Создаем inline клавиатуру с кнопкой быстрого поиска
            inline_keyboard = [[
                InlineKeyboardButton(
                    "🔍 Быстрый поиск в текущем чате",
                    switch_inline_query_current_chat=""
                )
            ]]
            inline_markup = InlineKeyboardMarkup(inline_keyboard)
            
            # Отправляем дополнительное сообщение с inline кнопкой
            await update.message.reply_text(
                "Нажмите кнопку ниже для быстрого поиска:",
                reply_markup=inline_markup
            )
            
            return States.WAITING_SEARCH
            
        # Возврат в главное меню
        elif choice == self.BUTTON_MENU:
            self.log_access(user_id, 'return_to_menu')
            
            # Создаем клавиатуру главного меню
            keyboard = [
                [KeyboardButton(self.BUTTON_COORD_SEARCH)],
                [KeyboardButton(self.BUTTON_DESC_SEARCH)]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "Выберите тип поиска:",
                reply_markup=reply_markup
            )
            return States.MAIN_MENU
            
        return States.MAIN_MENU