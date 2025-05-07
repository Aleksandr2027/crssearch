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

# Импортируем компоненты поиска
from .core.search import SearchEngine, SearchTransliterator, SearchUtils

from .bot.bot_manager import BotManager

__all__ = [
    'BotManager',
    'ExportManager',
    'Civil3DExporter',
    'GMv20Exporter',
    'GMv25Exporter',
    'SearchEngine',
    'SearchTransliterator',
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