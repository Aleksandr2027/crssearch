import time
import logging
from typing import Dict, List, Optional
from psycopg2 import OperationalError
from psycopg2.extensions import connection
from XML_search.errors import DatabaseError

class ConnectionHealth:
    """Класс для мониторинга состояния соединений с базой данных"""
    
    def __init__(self, check_interval: float = 60.0, max_idle_time: float = 300.0):
        """
        Инициализация параметров мониторинга
        
        Args:
            check_interval: Интервал проверки соединений в секундах
            max_idle_time: Максимальное время простоя соединения в секундах
        """
        self.check_interval = check_interval
        self.max_idle_time = max_idle_time
        self.logger = logging.getLogger(__name__)
        self.connections: Dict[connection, float] = {}
        self.last_check = 0.0
        
    def register_connection(self, conn: connection) -> None:
        """Регистрация нового соединения"""
        self.connections[conn] = time.time()
        
    def unregister_connection(self, conn: connection) -> None:
        """Удаление соединения из мониторинга"""
        if conn in self.connections:
            del self.connections[conn]
            
    def check_connection(self, conn: connection) -> bool:
        """
        Проверка состояния соединения
        
        Args:
            conn: Соединение для проверки
            
        Returns:
            True если соединение активно, False в противном случае
        """
        try:
            if conn.closed:
                return False
                
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
                
        except OperationalError:
            return False
            
    def cleanup_stale_connections(self) -> List[connection]:
        """
        Очистка неактивных соединений
        
        Returns:
            Список закрытых соединений
        """
        current_time = time.time()
        stale_connections = []
        
        for conn, last_used in list(self.connections.items()):
            if (current_time - last_used > self.max_idle_time or 
                not self.check_connection(conn)):
                stale_connections.append(conn)
                self.unregister_connection(conn)
                
        return stale_connections
        
    def update_connection_activity(self, conn: connection) -> None:
        """Обновление времени последней активности соединения"""
        if conn in self.connections:
            self.connections[conn] = time.time()
            
    def get_active_connections(self) -> List[connection]:
        """Получение списка активных соединений"""
        return [conn for conn in self.connections.keys() 
                if not conn.closed and self.check_connection(conn)]
                
    def get_connection_stats(self) -> Dict[str, int]:
        """
        Получение статистики по соединениям
        
        Returns:
            Словарь со статистикой
        """
        active = len(self.get_active_connections())
        total = len(self.connections)
        stale = total - active
        
        return {
            "total": total,
            "active": active,
            "stale": stale
        }
        
    def should_check(self) -> bool:
        """Проверка необходимости выполнения проверки"""
        current_time = time.time()
        if current_time - self.last_check >= self.check_interval:
            self.last_check = current_time
            return True
        return False 