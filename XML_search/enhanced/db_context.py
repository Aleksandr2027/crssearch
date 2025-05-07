"""
Модуль для управления глобальным контекстом базы данных
"""

from typing import Optional
from .db_manager import DatabaseManager

_global_db_manager: Optional[DatabaseManager] = None

def get_db_manager() -> Optional[DatabaseManager]:
    """
    Получение глобального менеджера БД
    
    Returns:
        Глобальный менеджер БД или None, если он не инициализирован
    """
    return _global_db_manager

def set_db_manager(db_manager: DatabaseManager) -> None:
    """
    Установка глобального менеджера БД
    
    Args:
        db_manager: Менеджер БД для установки в качестве глобального
    """
    global _global_db_manager
    _global_db_manager = db_manager 