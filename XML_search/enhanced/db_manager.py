"""
Модуль для работы с базой данных
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
import asyncpg
from .exceptions import DatabaseError, ConnectionError, QueryError
from .log_manager import LogManager
from .metrics_manager import MetricsManager
from .config_enhanced import DatabaseConfig
from .db_retry import with_db_retry, with_transaction_retry

logger = LogManager().get_logger(__name__)

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, config: DatabaseConfig):
        """
        Инициализация менеджера базы данных
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self.metrics = MetricsManager()
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Инициализация пула соединений"""
        if self._initialized:
            return
            
        try:
            async with self._lock:
                if not self._initialized:  # Двойная проверка для избежания race condition
                    self.pool = await asyncpg.create_pool(
                        host=self.config.host,
                        port=self.config.port,
                        user=self.config.user,
                        password=self.config.password,
                        database=self.config.dbname,
                        min_size=self.config.pool.min_connections,
                        max_size=self.config.pool.max_connections,
                        command_timeout=self.config.statement_timeout / 1000,  # конвертируем в секунды
                        statement_timeout=self.config.statement_timeout,
                        max_inactive_connection_lifetime=self.config.pool.max_lifetime,
                        max_inactive_connection_timeout=self.config.pool.max_idle_time,
                        # Параметры для автоматического переподключения
                        retry_interval=1.0,  # интервал между попытками переподключения
                        max_retries=3,  # максимальное количество попыток
                        # Параметры для проверки соединения
                        health_check_interval=self.config.pool.health_check_interval,
                        health_check_timeout=self.config.pool.health_check_timeout
                    )
                    self._initialized = True
                    logger.info("Пул соединений успешно инициализирован")
                    
        except Exception as e:
            logger.error(f"Ошибка инициализации пула соединений: {e}")
            raise DatabaseError(f"Ошибка инициализации пула соединений: {e}")
            
    @asynccontextmanager
    async def connection(self):
        """Получение соединения из пула"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
        conn = None
        start_time = self.metrics.start_operation('get_connection')
        try:
            conn = await self.pool.acquire()
            await self.metrics.record_operation('get_connection', start_time)
            yield conn
        except Exception as e:
            await self.metrics.record_error('get_connection', str(e))
            logger.error(f"Ошибка получения соединения: {e}")
            raise ConnectionError(f"Ошибка получения соединения: {e}")
        finally:
            if conn:
                await self.pool.release(conn)
                
    @asynccontextmanager
    async def transaction(self):
        """Получение транзакции"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
        async with self.connection() as conn:
            async with conn.transaction() as tr:
                yield tr
                
    @with_db_retry()
    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        Выполнение запроса
        
        Args:
            query: SQL запрос
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            str: Результат выполнения запроса
        """
        start_time = self.metrics.start_operation('execute')
        try:
            async with self.connection() as conn:
                result = await conn.execute(query, *args, **kwargs)
                await self.metrics.record_operation('execute', start_time)
                return result
        except Exception as e:
            await self.metrics.record_error('execute', str(e))
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise QueryError(f"Ошибка выполнения запроса: {e}")
            
    @with_db_retry()
    async def fetch(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Выполнение запроса с возвратом результатов
        
        Args:
            query: SQL запрос
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            List[Dict[str, Any]]: Список результатов
        """
        start_time = self.metrics.start_operation('fetch')
        try:
            async with self.connection() as conn:
                result = await conn.fetch(query, *args, **kwargs)
                await self.metrics.record_operation('fetch', start_time)
                return [dict(row) for row in result]
        except Exception as e:
            await self.metrics.record_error('fetch', str(e))
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise QueryError(f"Ошибка выполнения запроса: {e}")
            
    @with_db_retry()
    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Выполнение запроса с возвратом одной строки
        
        Args:
            query: SQL запрос
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            Optional[Dict[str, Any]]: Результат или None
        """
        start_time = self.metrics.start_operation('fetchrow')
        try:
            async with self.connection() as conn:
                result = await conn.fetchrow(query, *args, **kwargs)
                await self.metrics.record_operation('fetchrow', start_time)
                return dict(result) if result else None
        except Exception as e:
            await self.metrics.record_error('fetchrow', str(e))
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise QueryError(f"Ошибка выполнения запроса: {e}")
            
    @with_transaction_retry()
    async def execute_many(self, query: str, args_list: List[tuple]) -> None:
        """
        Выполнение пакетного запроса
        
        Args:
            query: SQL запрос
            args_list: Список аргументов
        """
        start_time = self.metrics.start_operation('execute_many')
        try:
            async with self.transaction() as tr:
                for args in args_list:
                    await tr.execute(query, *args)
                await self.metrics.record_operation('execute_many', start_time)
        except Exception as e:
            await self.metrics.record_error('execute_many', str(e))
            logger.error(f"Ошибка выполнения пакетного запроса: {e}")
            raise QueryError(f"Ошибка выполнения пакетного запроса: {e}")
            
    async def check_health(self) -> bool:
        """
        Проверка здоровья базы данных
        
        Returns:
            bool: True если база данных доступна
        """
        if not self._initialized:
            return False
            
        try:
            async with self.connection() as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья: {e}")
            return False
            
    async def close(self) -> None:
        """Закрытие менеджера"""
        if self._initialized and self.pool:
            start_time = self.metrics.start_operation('close')
            try:
                await self.pool.close()
                self._initialized = False
                await self.metrics.record_operation('close', start_time)
                logger.info("Менеджер базы данных закрыт")
            except Exception as e:
                await self.metrics.record_error('close', str(e))
                logger.error(f"Ошибка закрытия менеджера: {e}")
                raise DatabaseError(f"Ошибка закрытия менеджера: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики менеджера
        
        Returns:
            Dict[str, Any]: Статистика работы менеджера
        """
        return {
            'initialized': self._initialized,
            'pool_size': self.pool.get_size() if self.pool else 0,
            'active_connections': self.pool.get_active_size() if self.pool else 0,
            'metrics': self.metrics.get_stats()
        } 