"""
Модуль поискового движка
"""

from .search_engine import SearchEngine
from .transliterator import SearchTransliterator
from .utils import SearchUtils

_global_db_manager = None

def get_db_manager():
    """Получение глобального менеджера БД"""
    return _global_db_manager

def set_db_manager(db_manager):
    """Установка глобального менеджера БД"""
    global _global_db_manager
    _global_db_manager = db_manager

__all__ = [
    'SearchEngine',
    'SearchTransliterator',
    'SearchUtils',
    'get_db_manager',
    'set_db_manager'
] 