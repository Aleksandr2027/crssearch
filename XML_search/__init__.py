"""
Корневой пакет проекта
"""

__version__ = "1.0.0"

from .enhanced.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    PoolError,
    ConfigurationError,
    TransactionError,
    TimeoutError
)

from .errors import ConfigError, ValidationError, XMLProcessingError

# Импортируем экспортеры напрямую из их модулей
from .enhanced.export.exporters.civil3d import Civil3DExporter
from .enhanced.export.exporters.gmv20 import GMv20Exporter
from .enhanced.export.exporters.gmv25 import GMv25Exporter
from .enhanced.export.export_manager import ExportManager

# Импортируем улучшенные компоненты поиска
from .enhanced.transliterator import Transliterator
from .enhanced.search.search_engine import EnhancedSearchEngine
from .enhanced.search.search_utils import SearchUtils

# Импортируем компоненты поиска для обратной совместимости
from .core.search import SearchEngine, SearchTransliterator

from .bot.bot_manager import BotManager

__all__ = [
    'BotManager',
    'ExportManager',
    'Civil3DExporter',
    'GMv20Exporter',
    'GMv25Exporter',
    'SearchEngine',
    'SearchTransliterator',
    'EnhancedSearchEngine',
    'Transliterator',
    'SearchUtils',
    'DatabaseError',
    'ConnectionError',
    'QueryError',
    'PoolError',
    'ConfigurationError',
    'TransactionError',
    'TimeoutError',
    'ConfigError',
    'ValidationError',
    'XMLProcessingError'
] 