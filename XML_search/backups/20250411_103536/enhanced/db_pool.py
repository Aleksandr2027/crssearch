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
from statistics import mean

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
    
    def __init__(self, config: DBConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._pool = None
        self._lock = Lock()
        self.health = ConnectionHealth()
        self.metrics = MetricsCollector()
        
        # Статистика соединений
        self._stats = {
            "created_connections": 0,
            "closed_connections": 0,
            "failed_connections": 0,
            "max_connections_used": 0,
            "last_health_check": None,
            "failed_health_checks": 0,
            "pool_recreations": 0,
            "connection_wait_time": [],
            "connection_lifetime": [],
            "query_execution_time": [],
            "retry_attempts": 0
        }
        
        self._initialize_pool()
        self._start_health_check_thread()
        
    def _initialize_pool(self) -> None:
        """Инициализация пула соединений"""
        try:
            self._pool = ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                **self.config.db_params
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
                    start_time = time.time()
                    cur.execute("SELECT 1")
                    check_time = time.time() - start_time
                    
                    with self._lock:
                        self._stats["last_health_check"] = time.time()
                    
                    self.metrics.gauge("pool.health_check.time", check_time)
                    self.metrics.increment("pool.health_check.success")
            finally:
                self._pool.putconn(conn)
        except Exception as e:
            with self._lock:
                self._stats["failed_health_checks"] += 1
            self.metrics.increment("pool.health_check.failed")
            raise ConnectionError("Ошибка проверки соединения", e)
            
    def get_connection(self) -> Any:
        """Получение соединения из пула"""
        if not self._pool:
            raise PoolError("Пул соединений не инициализирован")
            
        start_time = time.time()
        try:
            conn = self._pool.getconn()
            wait_time = time.time() - start_time
            
            with self._lock:
                self._stats["connection_wait_time"].append(wait_time)
                current_connections = len(self.get_active_connections())
                self._stats["max_connections_used"] = max(
                    self._stats["max_connections_used"], 
                    current_connections
                )
                
            self.metrics.gauge("pool.connections.active", current_connections)
            self.metrics.gauge("pool.connections.wait_time", wait_time)
            
            return conn
        except Exception as e:
            with self._lock:
                self._stats["failed_connections"] += 1
            self.metrics.increment("pool.connections.failed")
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

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики пула соединений"""
        with self._lock:
            active_connections = len(self.get_active_connections())
            total_connections = self._stats["created_connections"] - self._stats["closed_connections"]
            
            stats = {
                "connections": {
                    "active": active_connections,
                    "total": total_connections,
                    "max_used": self._stats["max_connections_used"],
                    "failed": self._stats["failed_connections"]
                },
                "health": {
                    "last_check": self._stats["last_health_check"],
                    "failed_checks": self._stats["failed_health_checks"],
                    "pool_recreations": self._stats["pool_recreations"]
                },
                "performance": {
                    "avg_wait_time": mean(self._stats["connection_wait_time"]) if self._stats["connection_wait_time"] else 0,
                    "avg_lifetime": mean(self._stats["connection_lifetime"]) if self._stats["connection_lifetime"] else 0,
                    "avg_query_time": mean(self._stats["query_execution_time"]) if self._stats["query_execution_time"] else 0,
                    "retry_attempts": self._stats["retry_attempts"]
                }
            }
            
            # Очистка накопленных данных
            self._stats["connection_wait_time"] = self._stats["connection_wait_time"][-1000:]
            self._stats["connection_lifetime"] = self._stats["connection_lifetime"][-1000:]
            self._stats["query_execution_time"] = self._stats["query_execution_time"][-1000:]
            
            return stats 