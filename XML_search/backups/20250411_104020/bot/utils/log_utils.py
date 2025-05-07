"""
Утилиты для логирования
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from XML_search.enhanced.log_manager import LogManager

# Создаем директории для логов
log_dirs = ['logs', 'logs/errors', 'logs/access', 'logs/debug', 'logs/metrics']
for dir in log_dirs:
    os.makedirs(dir, exist_ok=True)

# Инициализируем менеджер логирования
log_manager = LogManager()
bot_logger = log_manager.get_logger()

# Отключаем логирование HTTP-запросов
logging.getLogger('httpx').setLevel(logging.WARNING)

def log_debug(message: str, data: dict = None) -> None:
    """
    Отладочное логирование
    
    Args:
        message: Сообщение для логирования
        data: Дополнительные данные
    """
    bot_logger.debug(message, extra={'data': data} if data else None)

def log_access(user_id: int, action: str, details: dict = None) -> None:
    """
    Логирование действий пользователя
    
    Args:
        user_id: ID пользователя
        action: Действие
        details: Детали действия
    """
    log_data = {
        'user_id': user_id,
        'action': action,
        'timestamp': datetime.now().isoformat()
    }
    if details:
        log_data.update(details)
    bot_logger.info(f"User {user_id}: {action}", extra={'data': log_data})

def log_error(error: Exception, context: dict = None) -> None:
    """
    Логирование ошибок
    
    Args:
        error: Исключение
        context: Контекст ошибки
    """
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat()
    }
    if context:
        error_data.update(context)
    bot_logger.error(f"Error: {type(error).__name__} - {str(error)}", extra={'data': error_data})

def log_metrics(metrics: dict) -> None:
    """
    Логирование метрик
    
    Args:
        metrics: Словарь с метриками
    """
    metrics_data = {
        'timestamp': datetime.now().isoformat(),
        'metrics': metrics
    }
    bot_logger.info("Metrics collected", extra={'data': metrics_data}) 