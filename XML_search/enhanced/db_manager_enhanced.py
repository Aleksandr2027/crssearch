"""
Улучшенный менеджер базы данных
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
import asyncpg
from .config_enhanced import DatabaseConfig
from .db_pool import DatabasePool
from .exceptions import DatabaseError, QueryError, ConnectionError
from .log_manager import LogManager
from .metrics_manager import MetricsManager

logger = LogManager().get_logger(__name__)

class EnhancedDatabaseManager:
    """Улучшенный менеджер базы данных"""
    
    def __init__(self, config: DatabaseConfig):
        """
        Инициализация менеджера
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.pool = DatabasePool(config)
        self.metrics = MetricsManager()
        self._initialized = False
        
    async def initialize(self) -> None:
        """Инициализация менеджера"""
        try:
            await self.pool.init_pool()
            self._initialized = True
            logger.info("Менеджер базы данных успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации менеджера: {e}")
            raise DatabaseError(f"Ошибка инициализации менеджера: {e}")
            
    @asynccontextmanager
    async def connection(self):
        """Получение соединения из пула"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
        conn = None
        try:
            conn = await self.pool.acquire()
            yield conn
        except Exception as e:
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
                
    async def execute(self, query: str, *args, **kwargs) -> str:
        """Выполнение запроса"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
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
            
    async def fetch(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Выполнение запроса с возвратом результатов"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
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
            
    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Выполнение запроса с возвратом одной строки"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
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
            
    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """Выполнение запроса с возвратом одного значения"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
        start_time = self.metrics.start_operation('fetchval')
        try:
            async with self.connection() as conn:
                result = await conn.fetchval(query, *args, **kwargs)
                await self.metrics.record_operation('fetchval', start_time)
                return result
        except Exception as e:
            await self.metrics.record_error('fetchval', str(e))
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise QueryError(f"Ошибка выполнения запроса: {e}")
            
    async def execute_many(self, query: str, args_list: List[tuple]) -> None:
        """Выполнение пакетного запроса"""
        if not self._initialized:
            raise DatabaseError("Менеджер не инициализирован")
            
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
        """Проверка здоровья базы данных"""
        if not self._initialized:
            return False
            
        try:
            return await self.pool.check_connection()
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья: {e}")
            return False
            
    async def close(self) -> None:
        """Закрытие менеджера"""
        if self._initialized:
            try:
                await self.pool.close()
                self._initialized = False
                logger.info("Менеджер базы данных закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия менеджера: {e}")
                raise DatabaseError(f"Ошибка закрытия менеджера: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        if not self._initialized:
            return {}
            
        return {
            'pool': self.pool.get_stats(),
            'metrics': self.metrics.get_stats()
        } 