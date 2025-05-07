import logging
from typing import Optional, List, Dict, Any, Tuple
from queue import Queue, Empty
from threading import Lock
from psycopg2 import connect, OperationalError
from psycopg2.extensions import connection
from XML_search.config import DBConfig
from .db_health import ConnectionHealth
import threading
import time
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from .exceptions import DatabaseError, ConnectionError, QueryError, PoolError
from .metrics import MetricsCollector
from .config_enhanced import EnhancedConfig

class ConnectionPool:
    """Класс для управления пулом соединений с базой данных"""
    
    def __init__(self, config: DBConfig):
        """
        Инициализация пула соединений
        
        Args:
            config: Конфигурация базы данных
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
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
        
    def get_connection(self, timeout: float = 5.0) -> connection:
        """Получение соединения из пула"""
        try:
            # Проверка необходимости очистки неактивных соединений
            if self.health.should_check():
                stale_conns = self.health.cleanup_stale_connections()
                for conn in stale_conns:
                    try:
                        conn.close()
                    except:
                        pass
                        
            # Попытка получить соединение из пула
            try:
                conn = self.pool.get(timeout=timeout)
                # Проверяем состояние соединения
                if not self.health.check_connection(conn):
                    try:
                        conn.close()
                    except:
                        pass
                    conn = self._create_connection()
                    self.health.register_connection(conn)
                return conn
            except Empty:
                # Если пул пуст, создаем новое соединение
                if self.pool.qsize() < self.config.max_connections:
                    self.logger.warning("Пул соединений пуст, создаем новое соединение")
                    conn = self._create_connection()
                    self.health.register_connection(conn)
                    return conn
                else:
                    raise Exception("Достигнут максимальный размер пула соединений")
            
        except OperationalError as e:
            self.logger.error(f"Ошибка при получении соединения: {e}")
            raise
            
    def release_connection(self, conn: connection) -> None:
        """Возвращение соединения в пул"""
        if conn and not conn.closed:
            try:
                self.health.update_connection_activity(conn)
                if self.pool.qsize() < self.config.max_connections:
                    self.pool.put(conn)
                else:
                    conn.close()
            except Exception as e:
                self.logger.error(f"Ошибка при возврате соединения в пул: {e}")
                try:
                    conn.close()
                except:
                    pass
            
    def close_all(self) -> None:
        """Закрытие всех соединений в пуле"""
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    if not conn.closed:
                        conn.close()
                except:
                    continue
                    
    def get_pool_stats(self) -> dict:
        """
        Получение статистики пула соединений
        
        Returns:
            Словарь со статистикой
        """
        stats = self.health.get_connection_stats()
        stats.update({
            "pool_size": self.pool.qsize(),
            "max_size": self.config.max_connections
        })
        return stats 

class DatabasePool:
    """Класс для управления пулом соединений с базой данных"""
    
    def __init__(self, 
                 min_connections: int = 5,
                 max_connections: int = 20,
                 health_check_interval: int = 300,
                 **connection_params):
        """
        Инициализация пула соединений
        
        Args:
            min_connections: Минимальное количество соединений
            max_connections: Максимальное количество соединений
            health_check_interval: Интервал проверки соединений в секундах
            connection_params: Параметры подключения к базе данных
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.connection_params = connection_params
        self.metrics = MetricsCollector()
        
        self._pool: Optional[ThreadedConnectionPool] = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_check = threading.Event()
        self._wait_timeout = 30  # Максимальное время ожидания соединения в секундах
        
        self._initialize_pool()
        self._start_health_check_thread()
        
    def _initialize_pool(self) -> None:
        """Инициализация пула соединений"""
        try:
            self._pool = ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                **self.connection_params
            )
            self.metrics.increment('pool_initialized')
        except Exception as e:
            raise PoolError("Ошибка инициализации пула соединений", e)
            
    def _start_health_check_thread(self) -> None:
        """Запуск потока для проверки состояния соединений"""
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        
    def _health_check_loop(self) -> None:
        """Цикл проверки состояния соединений"""
        while not self._stop_health_check.is_set():
            try:
                self.check_connections()
            except Exception as e:
                self.metrics.increment('health_check_errors')
            time.sleep(self.health_check_interval)
            
    def check_connections(self) -> None:
        """Проверка состояния всех соединений в пуле"""
        if not self._pool:
            return
            
        try:
            conn = self._pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    self.metrics.increment('health_check_success')
            finally:
                self._pool.putconn(conn)
        except Exception as e:
            self.metrics.increment('health_check_failed')
            raise ConnectionError("Ошибка проверки соединения", e)
            
    def get_connection(self) -> Any:
        """Получение соединения из пула"""
        if not self._pool:
            raise PoolError("Пул соединений не инициализирован")
            
        try:
            with self.metrics.timing('get_connection_time'):
                # Пробуем получить соединение с одной попыткой и увеличенным таймаутом
                conn = self._pool.getconn(timeout=5)  # Увеличиваем таймаут до 5 секунд
                if not conn or conn.closed:
                    # Если соединение недействительно, пробуем создать новое
                    if self._pool._pool.qsize() < self.max_connections:
                        conn = connect(**self.connection_params)
                        conn.autocommit = True
                self.metrics.increment('connections_acquired')
                return conn
                        
        except Exception as e:
            self.metrics.increment('connection_errors')
            raise ConnectionError("Ошибка получения соединения", e)
            
    def put_connection(self, conn: Any) -> None:
        """Возвращение соединения в пул"""
        if not self._pool:
            return
            
        try:
            if conn and not conn.closed:
                self._pool.putconn(conn)
                self.metrics.increment('connections_released')
            else:
                self.metrics.increment('invalid_connections')
        except Exception as e:
            self.metrics.increment('connection_errors')
            try:
                conn.close()  # Пытаемся закрыть недействительное соединение
            except:
                pass
            raise ConnectionError("Ошибка возвращения соединения", e)
            
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        Выполнение запроса с использованием соединения из пула
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Результат выполнения запроса
        """
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                with self.metrics.timing('query_execution_time'):
                    cur.execute(query, params)
                    if cur.description:
                        return cur.fetchall()
                    return None
        except Exception as e:
            self.metrics.increment('query_errors')
            raise ConnectionError("Ошибка выполнения запроса", e)
        finally:
            if conn:
                self.put_connection(conn)
                
    def close(self) -> None:
        """Закрытие пула соединений"""
        self._stop_health_check.set()
        if self._health_check_thread:
            self._health_check_thread.join()
            
        if self._pool and hasattr(self._pool, '_pool') and self._pool._pool is not None:
            try:
                self._pool.closeall()
                self._pool = None
                self.metrics.increment('pool_closed')
            except Exception as e:
                if "connection pool is closed" not in str(e):
                    self.logger.error(f"Ошибка закрытия пула: {e}")
        else:
            self.logger.error("Пул соединений не инициализирован") 