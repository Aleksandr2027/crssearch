import logging
from typing import Optional, Dict, Any
import threading
import time
from queue import Queue, Empty
from psycopg2 import connect, OperationalError
from psycopg2.extensions import connection
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from .config_enhanced import enhanced_config
from .log_manager import LogManager

class EnhancedConnectionPool:
    """Улучшенный пул соединений с автоматическим управлением и мониторингом"""
    
    def __init__(self):
        self.config = enhanced_config.database
        self.logger = LogManager("db_pool")
        self._pool: Optional[ThreadedConnectionPool] = None
        self._lock = threading.Lock()
        self._active_connections = 0
        self._last_connection_check = time.time()
        self._connection_stats = {
            "created": 0,
            "closed": 0,
            "errors": 0,
            "last_error": None
        }
        
        self._initialize_pool()
        self._start_health_check_thread()
        self._start_metrics_collection_thread()
    
    def _initialize_pool(self) -> None:
        """Инициализация пула соединений"""
        try:
            self._pool = ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                **self._get_connection_params()
            )
            self.logger.info(
                f"Создан пул соединений (min={self.config.min_connections}, "
                f"max={self.config.max_connections})"
            )
        except Exception as e:
            self.logger.error(f"Ошибка создания пула соединений: {e}")
            self._connection_stats["errors"] += 1
            self._connection_stats["last_error"] = str(e)
            raise
    
    def _get_connection_params(self) -> Dict[str, Any]:
        """Получение параметров подключения"""
        return {
            "dbname": enhanced_config.db_params["dbname"],
            "user": enhanced_config.db_params["user"],
            "password": enhanced_config.db_params["password"],
            "host": enhanced_config.db_params["host"],
            "port": enhanced_config.db_params["port"]
        }
    
    def _start_health_check_thread(self) -> None:
        """Запуск фонового потока проверки соединений"""
        def health_check_worker():
            while True:
                time.sleep(self.config.health_check_interval)
                self._check_connections()
        
        thread = threading.Thread(target=health_check_worker, daemon=True)
        thread.start()
        self.logger.info("Запущен поток проверки соединений")
    
    def _start_metrics_collection_thread(self) -> None:
        """Запуск фонового потока сбора метрик"""
        def metrics_worker():
            while True:
                time.sleep(60)  # Сбор метрик каждую минуту
                self._collect_metrics()
        
        thread = threading.Thread(target=metrics_worker, daemon=True)
        thread.start()
        self.logger.info("Запущен поток сбора метрик")
    
    def _check_connections(self) -> None:
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
                    self._connection_stats["errors"] += 1
                    self._connection_stats["last_error"] = str(e)
                    self._recreate_pool()
                finally:
                    self._pool.putconn(conn)
            except Exception as e:
                self.logger.error(f"Ошибка получения соединения для проверки: {e}")
                self._connection_stats["errors"] += 1
                self._connection_stats["last_error"] = str(e)
                self._recreate_pool()
    
    def _recreate_pool(self) -> None:
        """Пересоздание пула соединений"""
        try:
            # Закрываем старый пул
            if self._pool:
                self._pool.closeall()
                self._connection_stats["closed"] += self._active_connections
            
            # Создаем новый пул
            self._initialize_pool()
            self._connection_stats["created"] += self.config.min_connections
            self.logger.info("Пул соединений успешно пересоздан")
        except Exception as e:
            self.logger.error(f"Ошибка пересоздания пула: {e}")
            self._connection_stats["errors"] += 1
            self._connection_stats["last_error"] = str(e)
            raise
    
    def _collect_metrics(self) -> None:
        """Сбор метрик пула соединений"""
        with self._lock:
            metrics = {
                "active_connections": self._active_connections,
                "total_created": self._connection_stats["created"],
                "total_closed": self._connection_stats["closed"],
                "total_errors": self._connection_stats["errors"],
                "last_error": self._connection_stats["last_error"],
                "pool_size": self._pool._pool.qsize() if self._pool else 0
            }
            self.logger.info(f"Метрики пула соединений: {metrics}")
    
    @contextmanager
    def get_connection(self):
        """Получение соединения из пула"""
        conn = None
        try:
            conn = self._pool.getconn()
            with self._lock:
                self._active_connections += 1
            yield conn
        except Exception as e:
            self.logger.error(f"Ошибка получения соединения: {e}")
            self._connection_stats["errors"] += 1
            self._connection_stats["last_error"] = str(e)
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
                with self._lock:
                    self._active_connections -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики пула"""
        with self._lock:
            return {
                "active_connections": self._active_connections,
                "min_connections": self.config.min_connections,
                "max_connections": self.config.max_connections,
                "total_created": self._connection_stats["created"],
                "total_closed": self._connection_stats["closed"],
                "total_errors": self._connection_stats["errors"],
                "last_error": self._connection_stats["last_error"],
                "pool_size": self._pool._pool.qsize() if self._pool else 0
            }
    
    def close(self) -> None:
        """Закрытие пула соединений"""
        if self._pool:
            self._pool.closeall()
            self._connection_stats["closed"] += self._active_connections
            self._active_connections = 0
            self.logger.info("Пул соединений закрыт")
    
    def __del__(self):
        """Деструктор класса"""
        self.close() 