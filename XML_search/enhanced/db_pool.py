"""
Модуль для управления пулом соединений с базой данных
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from queue import Queue, Empty
from threading import Lock
import asyncpg
from psycopg2 import connect, OperationalError
from psycopg2.extensions import connection
from XML_search.config import DBConfig
from .db_health import ConnectionHealth
import threading
import time
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from .exceptions import DatabaseError, ConnectionError, QueryError, PoolError
from .log_manager import LogManager
from .metrics_manager import MetricsManager
from contextlib import asynccontextmanager
from .config_enhanced import DatabaseConfig

# Инициализация логгера
log_manager = LogManager()
logger = log_manager.get_logger(__name__)

class ConnectionPool:
    """Класс для управления пулом соединений с базой данных"""
    
    def __init__(self, config: DBConfig):
        """
        Инициализация пула соединений
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.log_manager = log_manager
        self.logger = logger
        self.pool = Queue(maxsize=config.max_connections)
        self.lock = Lock()
        self.health = ConnectionHealth()
        
        # Инициализация пула
        self._initialize_pool()
        
    def _initialize_pool(self) -> None:
        """Инициализация пула соединений"""
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_connection()
                self.pool.put(conn)
                self.health.register_connection(conn)
            except OperationalError as e:
                self.logger.error(f"Ошибка при создании соединения: {e}")
                
    def _create_connection(self) -> connection:
        """
        Создание нового соединения
        
        Returns:
            Новое соединение с базой данных
        """
        conn = connect(**self.config.db_params)
        conn.autocommit = True
        return conn

class DatabasePool:
    """Класс для управления пулом соединений с базой данных"""
    
    def __init__(self, config: DatabaseConfig):
        """
        Инициализация пула соединений
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self.metrics = MetricsManager()
        self._initialized = False
        
    async def init_pool(self) -> None:
        """Инициализация пула соединений"""
        if self._initialized:
            return
            
        try:
            # Формируем DSN
            dsn = self._build_dsn()
            
            # Получаем SSL конфигурацию
            ssl_config = self._get_ssl_config()
            
            # Создаем пул с оптимизированными параметрами для Docker
            self.pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=self.config.statement_timeout / 1000,  # конвертируем в секунды
                ssl=ssl_config,
                setup=self._setup_connection,
                # Дополнительные параметры для надежности в Docker
                max_inactive_connection_lifetime=self.config.pool.max_lifetime
            )
            
            self._initialized = True
            logger.info("Пул соединений успешно инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации пула: {e}")
            raise DatabaseError(f"Ошибка инициализации пула: {e}")
            
    def _build_dsn(self) -> str:
        """Построение строки подключения"""
        return f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.dbname}"
        
    def _get_ssl_config(self) -> Optional[Dict[str, Any]]:
        """Получение SSL конфигурации"""
        if not self.config.ssl.enabled:
            return None
            
        ssl_config = {
            'ssl': True,
            'verify': self.config.ssl.verify
        }
        
        if self.config.ssl.cert:
            ssl_config['cert'] = self.config.ssl.cert
        if self.config.ssl.key:
            ssl_config['key'] = self.config.ssl.key
        if self.config.ssl.ca:
            ssl_config['ca'] = self.config.ssl.ca
            
        return ssl_config
        
    async def _setup_connection(self, conn: asyncpg.Connection) -> None:
        """Настройка соединения"""
        await conn.execute(f"""
            SET application_name = '{self.config.application_name}';
            SET statement_timeout = {self.config.statement_timeout};
            SET idle_in_transaction_session_timeout = {self.config.idle_in_transaction_session_timeout};
        """)
        
    async def check_connection(self) -> bool:
        """Проверка соединения"""
        if not self._initialized:
            return False
            
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(self.config.pool.health_check_query)
                return result == 1
        except Exception as e:
            logger.error(f"Ошибка проверки соединения: {e}")
            return False
            
    async def acquire(self) -> asyncpg.Connection:
        """Получение соединения из пула"""
        if not self._initialized:
            raise DatabaseError("Пул не инициализирован")
            
        try:
            return await self.pool.acquire()
        except Exception as e:
            logger.error(f"Ошибка получения соединения: {e}")
            raise ConnectionError(f"Ошибка получения соединения: {e}")
            
    async def release(self, conn: asyncpg.Connection) -> None:
        """Освобождение соединения"""
        if not self._initialized:
            return
            
        try:
            await self.pool.release(conn)
        except Exception as e:
            logger.error(f"Ошибка освобождения соединения: {e}")
            
    async def close(self) -> None:
        """Закрытие пула"""
        if self._initialized:
            try:
                await self.pool.close()
                self._initialized = False
                logger.info("Пул соединений закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия пула: {e}")
                raise DatabaseError(f"Ошибка закрытия пула: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики пула"""
        if not self._initialized:
            return {}
            
        return {
            'min_size': self.config.min_connections,
            'max_size': self.config.max_connections,
            'size': self.pool.get_size() if self.pool else 0,
            'free': self.pool.get_active_size() if self.pool else 0
        } 