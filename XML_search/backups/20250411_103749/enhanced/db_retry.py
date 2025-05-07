import time
import functools
import logging
from typing import Callable, Any, Type
from psycopg2 import OperationalError, InterfaceError
from XML_search.errors import DatabaseError, ConnectionError

class DatabaseRetry:
    """Класс для управления повторными попытками подключения к базе данных"""
    
    def __init__(self, max_attempts: int = 3, delay: float = 1.0):
        """
        Инициализация параметров повторных попыток
        
        Args:
            max_attempts: Максимальное количество попыток
            delay: Задержка между попытками в секундах
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.logger = logging.getLogger(__name__)
        
    def __call__(self, func: Callable) -> Callable:
        """Декоратор для повторных попыток выполнения функции"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except (OperationalError, InterfaceError) as e:
                    last_exception = e
                    self.logger.warning(
                        f"Попытка {attempt}/{self.max_attempts} подключения к БД не удалась: {str(e)}"
                    )
                    
                    if attempt < self.max_attempts:
                        time.sleep(self.delay)
                    else:
                        self.logger.error(
                            f"Все {self.max_attempts} попыток подключения к БД не удались"
                        )
                        raise ConnectionError(
                            f"Не удалось подключиться к базе данных после {self.max_attempts} попыток"
                        ) from last_exception
                        
                except Exception as e:
                    self.logger.error(f"Непредвиденная ошибка при работе с БД: {str(e)}")
                    raise DatabaseError(f"Ошибка базы данных: {str(e)}") from e
                    
        return wrapper

def with_db_retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    """
    Декоратор для повторных попыток выполнения операций с базой данных
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками в секундах
        
    Returns:
        Декорированная функция
    """
    retry = DatabaseRetry(max_attempts, delay)
    return retry 