"""
Модульная структура бота
"""

from .bot_manager import BotManager
from .handlers import *
from .utils import *
from .keyboards import *
from .states import *

__all__ = [
    'BotManager',
    'handlers',
    'utils',
    'keyboards',
    'states'
] 