"""
Модуль для реализации механизма повторных попыток подключения к БД
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, Type, TypeVar
from .exceptions import DatabaseError, ConnectionError
from .log_manager import LogManager
from .metrics_manager import MetricsManager

logger = LogManager().get_logger(__name__)
metrics = MetricsManager()

# Тип для возвращаемого значения функции
T = TypeVar('T')

def with_db_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (ConnectionError, DatabaseError)
) -> Callable:
    """
    Декоратор для повторных попыток выполнения операций с базой данных
    
    Args:
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка между попытками в секундах
        max_delay: Максимальная задержка между попытками в секундах
        backoff_factor: Множитель для увеличения задержки
        exceptions: Кортеж исключений, при которых нужно повторять попытки
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            operation_name = func.__name__
            start_time = metrics.start_operation(f'db_retry_{operation_name}')
            
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    result = await func(*args, **kwargs)
                    await metrics.record_operation(f'db_retry_{operation_name}', start_time)
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    await metrics.record_error(f'db_retry_{operation_name}', str(e))
                    
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Попытка {attempt + 1}/{max_retries} не удалась для {operation_name}. "
                            f"Ошибка: {str(e)}. Повтор через {delay} сек."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"Все попытки выполнения {operation_name} исчерпаны. "
                            f"Последняя ошибка: {str(e)}"
                        )
                        
            # Если все попытки исчерпаны, выбрасываем последнее исключение
            if last_exception:
                raise last_exception
                
            return None  # Для типизации
            
        return wrapper
    return decorator

def with_transaction_retry(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Callable:
    """
    Декоратор для повторных попыток выполнения транзакций
    
    Args:
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка между попытками в секундах
        max_delay: Максимальная задержка между попытками в секундах
        backoff_factor: Множитель для увеличения задержки
        
    Returns:
        Callable: Декорированная функция
    """
    return with_db_retry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        exceptions=(ConnectionError, DatabaseError)
    ) 