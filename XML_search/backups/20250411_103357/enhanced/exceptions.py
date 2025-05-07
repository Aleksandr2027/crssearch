class DatabaseError(Exception):
    """Базовый класс для ошибок базы данных"""
    def __init__(self, message: str, original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)

class ConnectionError(DatabaseError):
    """Ошибка подключения к базе данных"""
    pass

class QueryError(DatabaseError):
    """Ошибка выполнения запроса"""
    pass

class PoolError(DatabaseError):
    """Ошибка работы с пулом соединений"""
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