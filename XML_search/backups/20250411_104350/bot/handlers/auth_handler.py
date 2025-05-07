"""
Обработчик авторизации пользователей
"""

import time
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from ..states.conversation_states import States
from .base_handler import BaseHandler
from XML_search.config import TelegramConfig

class AuthHandler(BaseHandler):
    """Обработчик авторизации пользователей"""
    
    def __init__(self):
        """Инициализация обработчика авторизации"""
        super().__init__("auth_handler")
        self.authorized_users = set()
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Основной метод обработки запроса
        
        Args:
            update: Объект обновления от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        return await self._handle_update(update, context)
        
    async def check_access(self, update: Update) -> bool:
        """
        Проверка доступа пользователя
        
        Args:
            update: Объект обновления от Telegram
            
        Returns:
            True если пользователь авторизован, False в противном случае
        """
        user_id = update.effective_user.id
        
        # Проверяем авторизацию
        if user_id in self.authorized_users:
            return True
            
        # Отправляем сообщение о необходимости авторизации
        await update.message.reply_text(
            "🔐 Для доступа к боту введите пароль.\n"
            "Используйте команду /auth для авторизации."
        )
        return False
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /start"""
        return await self.handle_update(update, context)
        
    async def auth_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало процесса авторизации"""
        return await self.handle_update(update, context)
        
    async def auth_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Проверка пароля"""
        return await self.handle_update(update, context)
        
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена процесса авторизации"""
        return await self.handle_update(update, context)
        
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Обработка обновлений с логированием
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            Следующее состояние диалога
        """
        user_id = update.effective_user.id
        command = context.match.group(0) if context.match else update.message.text
        
        # Обработка команды /start
        if command == '/start':
            self.log_access(user_id, 'start_command')
            await update.message.reply_text(
                "🔐 Введите пароль для доступа к боту:",
                reply_markup=ReplyKeyboardRemove()
            )
            return States.AUTH
            
        # Обработка команды /auth
        elif command == '/auth':
            self.log_access(user_id, 'auth_command')
            await update.message.reply_text(
                "🔐 Введите пароль для доступа к боту:"
            )
            return States.AUTH
            
        # Обработка команды /cancel
        elif command == '/cancel':
            self.log_access(user_id, 'cancel_command')
            await update.message.reply_text(
                "❌ Авторизация отменена.\n"
                "Используйте /auth для повторной попытки."
            )
            return ConversationHandler.END
            
        # Проверка пароля
        else:
            password = update.message.text
            
            # Логируем попытку авторизации (без пароля!)
            self.log_access(user_id, 'auth_attempt')
            
            if password == TelegramConfig.ACCESS_PASSWORD:
                # Успешная авторизация
                self.authorized_users.add(user_id)
                self.log_access(user_id, 'auth_success')
                self.metrics.increment('auth_success')
                
                # Показываем главное меню
                keyboard = [
                    ['Поиск СК по Lat/Lon'],
                    ['Поиск СК по описанию']
                ]
                reply_markup = ReplyKeyboardRemove()
                
                await update.message.reply_text(
                    "✅ Авторизация успешна!\n"
                    "Выберите тип поиска:",
                    reply_markup=reply_markup
                )
                return States.MAIN_MENU
                
            else:
                # Неудачная попытка
                self.log_access(user_id, 'auth_failed')
                self.metrics.increment('auth_failed')
                
                await update.message.reply_text(
                    "❌ Неверный пароль.\n"
                    "Попробуйте еще раз или используйте /cancel для отмены."
                )
                return States.AUTH
                
    def check_auth(self, user_id: int) -> bool:
        """
        Проверка авторизации пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если пользователь авторизован
        """
        return user_id in self.authorized_users 