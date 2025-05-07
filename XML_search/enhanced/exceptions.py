"""
Общие исключения проекта
"""

class BaseError(Exception):
    """Базовое исключение проекта"""
    pass

class DatabaseError(BaseError):
    """Исключение для ошибок базы данных"""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class ConnectionError(DatabaseError):
    """Исключение для ошибок соединения с базой данных"""
    pass

class QueryError(DatabaseError):
    """Исключение для ошибок выполнения запросов"""
    pass

class PoolError(DatabaseError):
    """Исключение для ошибок пула соединений"""
    pass

class CacheError(BaseError):
    """Исключение для ошибок кэширования"""
    pass

class MetricsError(BaseError):
    """Исключение для ошибок сбора метрик"""
    pass

class LoggingError(BaseError):
    """Исключение для ошибок логирования"""
    pass

class ConfigError(BaseError):
    """Исключение для ошибок конфигурации"""
    pass

class ValidationError(BaseError):
    """Исключение для ошибок валидации"""
    pass

class AuthError(BaseError):
    """Исключение для ошибок аутентификации"""
    pass

class ExportError(BaseError):
    """Исключение для ошибок экспорта"""
    pass

class ConfigurationError(DatabaseError):
    """Ошибка конфигурации базы данных"""
    pass

class TransactionError(DatabaseError):
    """Ошибка выполнения транзакции"""
    pass

class TimeoutError(DatabaseError):
    """Ошибка таймаута при работе с базой данных"""
    pass 