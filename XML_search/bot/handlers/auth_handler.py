"""
Модуль обработчика авторизации пользователей.
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from XML_search.bot.handlers.base_handler import BaseHandler
from XML_search.bot.config import BotConfig
from XML_search.bot.states import States
from XML_search.config import TelegramConfig
from XML_search.errors import AuthError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.log_manager import LogManager

class AuthHandler(BaseHandler):
    """Обработчик авторизации"""
    
    def __init__(self, config: BotConfig):
        """
        Инициализация обработчика
        
        Args:
            config: Конфигурация бота
        """
        super().__init__(config)
        self.messages = config.MESSAGES
        self.auth_config = config.AUTH_CONFIG
        self.attempts_cache = CacheManager(ttl=self.auth_config.BLOCK_TIME)
        
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработка команды /auth
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        """
        if not update.effective_user:
            return
            
        user_id = update.effective_user.id
        
        # Проверяем, не заблокирован ли пользователь
        if self._is_user_blocked(user_id):
            await update.message.reply_text(self.messages['auth_blocked'])
            return
            
        # Проверяем, авторизован ли пользователь
        if await self._is_user_authenticated(context):
            await update.message.reply_text(self.messages['auth_success'])
            return
            
        # Запрашиваем пароль
        await self.set_user_state(context, States.AUTH, update)
        await update.message.reply_text(self.messages['auth_required'])
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Обработка введенного пароля
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
        Returns:
            States: Следующее состояние ConversationHandler
        """
        self.logger.info(f"[handle_message] Вход: user_id={getattr(update.effective_user, 'id', None)}, text={getattr(update.message, 'text', None)}, state={context.user_data.get('state', None)}")
        try:
            if not update.effective_user or not update.message:
                self.logger.info("[handle_message] Нет пользователя или сообщения, возвращаю States.AUTH")
                return States.AUTH
            user_id = update.effective_user.id
            password = update.message.text
            # Проверяем пароль
            if password == self.auth_config.PASSWORD:
                await self._handle_successful_auth(update, context, user_id)
                self.logger.info("[handle_message] Успешная авторизация, возвращаю States.MAIN_MENU")
                return States.MAIN_MENU
            else:
                await self._handle_failed_auth(update, context, user_id)
                self.logger.info("[handle_message] Неудачная попытка, возвращаю States.AUTH")
                return States.AUTH
        except Exception as e:
            self.logger.error(f"Ошибка в handle_message: {e}", exc_info=True)
            await self._handle_error(update, context, e)
            self.logger.info("[handle_message] Исключение, возвращаю States.AUTH")
            return States.AUTH

    async def _handle_successful_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """
        Обработка успешной авторизации
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
            user_id: ID пользователя
        """
        # Очищаем попытки
        self.attempts_cache.delete(str(user_id))
        
        # Обновляем состояние
        await self.set_user_state(context, States.MAIN_MENU, update)
        
        # Сохраняем время авторизации
        await self._update_user_data(context, {
            'auth_time': time.time(),
            'authenticated': True,
            'auth': True
        })
        
        # Отправляем сообщение
        await update.message.reply_text(self.messages['auth_success'])
        
        # Логируем успешную авторизацию
        self.logger.info(f"Успешная авторизация пользователя {user_id}")
        self.metrics.increment('auth_success')
        
    async def _handle_failed_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
        """
        Обработка неудачной авторизации
        
        Args:
            update: Обновление от Telegram
            context: Контекст обновления
            user_id: ID пользователя
        """
        # Увеличиваем счетчик попыток
        attempts = self.attempts_cache.get(str(user_id)) or 0
        attempts += 1
        self.attempts_cache.set(str(user_id), attempts)
        
        # Проверяем, не превышен ли лимит попыток
        if attempts >= self.auth_config.MAX_ATTEMPTS:
            await update.message.reply_text(self.messages['auth_blocked'])
            self.logger.warning(f"Пользователь {user_id} заблокирован после {attempts} попыток")
            self.metrics.increment('auth_blocked')
        else:
            await update.message.reply_text(self.messages['auth_failed'])
            self.logger.info(f"Неудачная попытка авторизации пользователя {user_id} (попытка {attempts})")
            self.metrics.increment('auth_failed')
            
    def _is_user_blocked(self, user_id: int) -> bool:
        """
        Проверка блокировки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если пользователь заблокирован
        """
        attempts = self.attempts_cache.get(str(user_id))
        return attempts and attempts >= self.auth_config.MAX_ATTEMPTS
        
    async def _is_user_authenticated(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Проверка авторизации пользователя
        
        Args:
            context: Контекст обновления
            
        Returns:
            bool: True если пользователь авторизован
        """
        user_data = await self._get_user_data(context)
        if not user_data.get('authenticated'):
            return False
            
        # Проверяем время сессии
        auth_time = user_data.get('auth_time', 0)
        if time.time() - auth_time > self.auth_config.SESSION_TIMEOUT:
            await self._update_user_data(context, {'authenticated': False})
            return False
            
        return True
            
    async def check_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Проверка авторизации пользователя
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            bool: True если пользователь авторизован, False в противном случае
        """
        try:
            user_data = await self._get_user_data(context)
            is_authorized = user_data.get('authorized', False)
            
            if not is_authorized:
                await update.message.reply_text(
                    "⚠️ Необходима авторизация.\n"
                    "Пожалуйста, введите пароль:"
                )
                await self.set_user_state(context, States.AUTH, update)
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке авторизации: {e}")
            self.metrics.increment('auth.check_error')
            raise AuthError(f"Ошибка при проверке авторизации: {e}")
            
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Выход из системы
        
        Args:
            update: Обновление от Telegram
            context: Контекст обработчика
            
        Returns:
            States: Следующее состояние диалога
        """
        try:
            await self._update_user_data(context, {'authorized': False})
            self.metrics.increment('auth.logout')
            
            await update.message.reply_text(
                "👋 Вы успешно вышли из системы.\n"
                "Для продолжения работы необходимо авторизоваться."
            )
            return States.AUTH
            
        except Exception as e:
            self.logger.error(f"Ошибка при выходе из системы: {e}")
            self.metrics.increment('auth.logout_error')
            raise AuthError(f"Ошибка при выходе из системы: {e}")
            
    async def check_access(self, user_id: int) -> bool:
        """
        Проверка авторизации пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: True если пользователь авторизован, False в противном случае
        """
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT authorized_at 
                        FROM authorized_users 
                        WHERE user_id = %s
                    """, (user_id,))
                    result = await cur.fetchone()
                    
                    if not result:
                        return False
                        
                    authorized_at = result[0]
                    # Проверяем, что авторизация не устарела (24 часа)
                    if datetime.now() - authorized_at > timedelta(hours=24):
                        return False
                        
                    return True
                    
        except Exception as e:
            self.logger.error(f"Ошибка при проверке доступа: {str(e)}")
            return False 

    async def auth_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Публичный обработчик команды /auth для регистрации в BotManager
        """
        await self.handle(update, context) 

    async def auth_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> States:
        """
        Публичный обработчик для проверки пароля/авторизации в ConversationHandler
        Возвращает состояние для корректной работы PTB v20+
        """
        self.logger.info(f"[auth_check] Вход: user_id={getattr(update.effective_user, 'id', None)}, text={getattr(update.message, 'text', None)}, state={context.user_data.get('state', None)}")
        result = await self.handle_message(update, context)
        self.logger.info(f"[auth_check] Выход: возвращаю состояние {result}")
        return result 