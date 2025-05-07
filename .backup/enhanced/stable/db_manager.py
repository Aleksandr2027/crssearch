from typing import Any, Optional, Dict, List, Tuple
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor, RealDictCursor
from contextlib import contextmanager
import threading
import time
from .config_enhanced import enhanced_config
from .log_manager import LogManager
from psycopg2.extensions import connection
from XML_search.config import DBConfig
from .db_pool import ConnectionPool
from .db_health import ConnectionHealth
from .db_retry import with_db_retry
import logging
from .metrics import MetricsCollector
from .exceptions import DatabaseError, ConnectionError, QueryError, PoolError
from threading import local

class DatabasePool:
    """Менеджер пула подключений к базе данных"""
    
    def __init__(self, min_connections: int, max_connections: int, health_check_interval: int, **db_params):
        self.config = enhanced_config.database
        self.logger = LogManager("db_pool")
        self._pool: Optional[ThreadedConnectionPool] = None
        self._lock = threading.Lock()
        self._active_connections = 0
        self._last_connection_check = time.time()
        self.metrics = MetricsCollector()
        
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.db_params = db_params
        
        self._initialize_pool()
        
        # Запуск фонового потока проверки соединений
        self._start_health_check_thread(health_check_interval)
    
    def _initialize_pool(self) -> None:
        """Инициализация пула соединений"""
        try:
            self._pool = ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                **self.db_params
            )
            self.logger.info(
                f"Создан пул соединений (min={self.min_connections}, "
                f"max={self.max_connections})"
            )
        except Exception as e:
            self.logger.error(f"Ошибка создания пула соединений: {e}")
            raise
    
    def _start_health_check_thread(self, health_check_interval: int) -> None:
        """Запуск фонового потока проверки соединений"""
        def health_check_worker():
            while True:
                time.sleep(health_check_interval)
                self.check_connections()
        
        thread = threading.Thread(target=health_check_worker, daemon=True)
        thread.start()
        self.logger.info("Запущен поток проверки соединений")
    
    def check_connections(self) -> None:
        """Проверка состояния соединений в пуле"""
        with self._lock:
            try:
                # Получаем соединение для проверки
                conn = self._pool.getconn()
                try:
                    # Проверяем соединение
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    self.logger.debug("Проверка соединений успешна")
                except Exception as e:
                    self.logger.error(f"Ошибка проверки соединения: {e}")
                    # Пересоздаем пул при проблемах
                    self._recreate_pool()
                finally:
                    self._pool.putconn(conn)
            except Exception as e:
                self.logger.error(f"Ошибка получения соединения для проверки: {e}")
                self._recreate_pool()
    
    def _recreate_pool(self) -> None:
        """Пересоздание пула соединений"""
        try:
            # Закрываем старый пул
            if self._pool:
                self._pool.closeall()
            
            # Создаем новый пул
            self._initialize_pool()
            self.logger.info("Пул соединений успешно пересоздан")
        except Exception as e:
            self.logger.error(f"Ошибка пересоздания пула: {e}")
            raise
    
    @contextmanager
    def connection(self):
        """Контекстный менеджер для получения соединения из пула"""
        conn = None
        try:
            conn = self._pool.getconn()
            with self._lock:
                self._active_connections += 1
            yield conn
        except Exception as e:
            self.logger.error(f"Ошибка работы с соединением: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
                with self._lock:
                    self._active_connections -= 1
    
    @contextmanager
    def cursor(self, cursor_factory=DictCursor):
        """Контекстный менеджер для получения курсора"""
        with self.connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Any:
        """Выполнение запроса с возвратом результата"""
        start_time = time.time()
        try:
            with self.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()
                self.metrics.observe('query_duration', time.time() - start_time)
                self.metrics.increment('queries_executed')
                return result
        except Exception as e:
            self.metrics.increment('query_errors')
            raise QueryError(f"Ошибка выполнения запроса: {e}")
    
    def execute_modification(self, query: str, params: Optional[tuple] = None) -> int:
        """Выполнение запроса-модификации с возвратом количества затронутых строк"""
        with self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount
    
    def get_stats(self) -> Dict[str, int]:
        """Получение статистики пула"""
        with self._lock:
            return {
                "active_connections": self._active_connections,
                "min_connections": self.min_connections,
                "max_connections": self.max_connections
            }
    
    def close(self) -> None:
        """Закрытие пула соединений"""
        if self._pool:
            self._pool.closeall()
            self.logger.info("Пул соединений закрыт")
    
    def __del__(self):
        """Деструктор класса"""
        self.close()

    def release_connection(self, conn: connection) -> None:
        """Возврат соединения в пул"""
        try:
            self._pool.putconn(conn)
        except Exception as e:
            self.logger.error(f"Ошибка при возврате соединения в пул: {e}")
            try:
                conn.close()
            except:
                pass

    def get_connection(self) -> Any:
        """Получение соединения из пула"""
        if not self._pool:
            self.metrics.increment('pool_errors')
            raise PoolError("Пул соединений не инициализирован")
            
        try:
            conn = self._pool.getconn()
            with self._lock:
                self._active_connections += 1
            self.metrics.increment('connections_acquired')
            return conn
        except Exception as e:
            self.metrics.increment('connection_errors')
            self.logger.error(f"Ошибка получения соединения: {e}")
            raise ConnectionError("Ошибка получения соединения", e)

    def put_connection(self, conn: Any) -> None:
        """Возвращение соединения в пул"""
        if not self._pool:
            return
            
        try:
            if conn and not conn.closed:
                self._pool.putconn(conn)
                with self._lock:
                    self._active_connections -= 1
                self.metrics.increment('connections_released')
            else:
                self.metrics.increment('closed_connection_returns')
                self.logger.warning("Попытка вернуть закрытое соединение в пул")
        except Exception as e:
            self.metrics.increment('connection_release_errors')
            self.logger.error(f"Ошибка при возврате соединения: {e}")

class DatabaseManager:
    """Класс для управления базой данных"""
    
    def __init__(self, config: DBConfig):
        """
        Инициализация менеджера базы данных
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.health = ConnectionHealth()
        self.metrics = MetricsCollector()
        self.logger = logging.getLogger(__name__)
        self._local = local()  # Для хранения соединений в контексте потока
        
        # Инициализация пула соединений
        self.pool = DatabasePool(
            min_connections=enhanced_config.database.min_connections,
            max_connections=enhanced_config.database.max_connections,
            health_check_interval=enhanced_config.database.health_check_interval,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT
        )
        self.logger.info("Пул соединений инициализирован")
        
    @property
    def connection(self) -> Optional[connection]:
        """Получить текущее соединение для потока"""
        return getattr(self._local, 'connection', None)
        
    @connection.setter 
    def connection(self, conn: Optional[connection]):
        """Установить соединение для потока"""
        self._local.connection = conn
        if conn:
            self.metrics.increment('thread_connections_set')
        else:
            self.metrics.increment('thread_connections_cleared')

    @with_db_retry()
    def get_connection(self) -> connection:
        """Получить соединение из пула или использовать существующее"""
        if self.connection and not self.connection.closed:
            self.metrics.increment('thread_connection_reused')
            return self.connection
            
        try:
            conn = self.pool.get_connection()
            self.connection = conn  # Сохраняем в контексте потока
            self.health.register_connection(conn)
            self.metrics.increment('db_connections')
            return conn
        except Exception as e:
            self.logger.error(f"Ошибка получения соединения: {e}")
            self.metrics.increment('db_connection_errors')
            raise DatabaseError(f"Ошибка получения соединения: {e}")

    def release_connection(self, conn: connection):
        """Освободить соединение только если оно не используется в текущем контексте"""
        if conn is self.connection:
            return  # Не освобождаем соединение, если оно еще используется в контексте
            
        try:
            self.pool.put_connection(conn)
            self.metrics.increment('db_connections_released')
        except Exception as e:
            self.logger.error(f"Ошибка освобождения соединения: {e}")
            self.metrics.increment('db_release_errors')
    
    @with_db_retry(max_attempts=3, delay=1.0)
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Выполнение SQL-запроса
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            
        Returns:
            Результаты запроса в виде списка словарей
        """
        with self.metrics.timing('query_execution'):
            try:
                result = self.pool.execute_query(query, params)
                self.metrics.increment('successful_queries')
                self.metrics.observe('result_size', len(result))
                return result
            except Exception as e:
                self.metrics.increment('failed_queries')
                raise
                
    @with_db_retry(max_attempts=3, delay=1.0)
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Выполнение SQL-запроса на обновление
        
        Args:
            query: SQL-запрос
            params: Параметры запроса
            
        Returns:
            Количество затронутых строк
        """
        with self.metrics.timing('update_execution'):
            try:
                affected_rows = self.pool.execute_query(query, params)
                self.metrics.increment('successful_updates')
                self.metrics.observe('affected_rows', affected_rows)
                return affected_rows
            except Exception as e:
                self.metrics.increment('failed_updates')
                raise
                
    def get_connection_stats(self) -> dict:
        """
        Получение статистики по соединениям
        
        Returns:
            Словарь со статистикой
        """
        pool_stats = self.pool.get_stats()
        health_stats = self.health.get_connection_stats()
        metrics_stats = self.metrics.get_metrics()
        
        return {
            "pool": pool_stats,
            "health": health_stats,
            "metrics": metrics_stats
        }
        
    def close(self) -> None:
        """Закрытие всех соединений"""
        try:
            if self.pool and hasattr(self.pool, '_pool') and self.pool._pool is not None:
                self.pool.close()
                self.logger.info("Пул соединений закрыт")
                self.metrics.increment('db_pool_closed')
        except Exception as e:
            if "connection pool is closed" not in str(e):
                self.logger.error(f"Ошибка при закрытии пула: {e}")
                self.metrics.increment('db_pool_close_errors')
            
    def __del__(self):
        """Деструктор класса"""
        self.close() 