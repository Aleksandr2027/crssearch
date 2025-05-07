"""
Конфигурация приложения
"""

import os
from dotenv import load_dotenv
from pathlib import Path
import logging
from typing import Dict, Any
import json

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def find_dotenv() -> Path:
    """Поиск .env файла в возможных расположениях"""
    # Текущая директория модуля
    current_dir = Path(__file__).resolve().parent
    # Корневая директория проекта
    root_dir = current_dir.parent
    
    # Проверяем возможные расположения
    possible_locations = [
        current_dir / '.env',  # XML_search/.env
        root_dir / '.env',     # .searh/.env
    ]
    
    for location in possible_locations:
        if location.is_file():
            logger.info(f"Найден .env файл: {location}")
            return location
            
    # Если файл не найден, используем текущую директорию
    logger.warning(f"Файл .env не найден. Проверенные расположения: {[str(p) for p in possible_locations]}")
    return current_dir / '.env'

# Загрузка переменных окружения
env_path = find_dotenv()
load_dotenv(dotenv_path=env_path)

# Проверяем загрузку критических переменных
if os.getenv('TELEGRAM_TOKEN'):
    logger.info("TELEGRAM_TOKEN успешно загружен")
else:
    logger.error("TELEGRAM_TOKEN не найден в .env файле")

class DBConfig:
    """Конфигурация подключения к базе данных"""
    def __init__(self):
        """Инициализация конфигурации"""
        # Основные параметры подключения
        self.dbname = os.getenv('DB_NAME', 'gis')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'postgres')
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        
        # Параметры пула соединений
        self.min_connections = int(os.getenv('DB_MIN_CONNECTIONS', '2'))
        self.max_connections = int(os.getenv('DB_MAX_CONNECTIONS', '10'))
        self.connection_timeout = float(os.getenv('DB_CONNECTION_TIMEOUT', '30.0'))
        self.idle_timeout = float(os.getenv('DB_IDLE_TIMEOUT', '300.0'))
        self.health_check_interval = int(os.getenv('DB_HEALTH_CHECK_INTERVAL', '60'))
        
        # Дополнительные параметры
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        self.pool_pre_ping = True
        self.max_lifetime = float(os.getenv('DB_MAX_LIFETIME', '3600.0'))
        self.retry = {
            'max_attempts': 3,
            'delay': 1.0,
            'enabled': True,
            'backoff_factor': 2.0
        }
    
    @property
    def db_params(self) -> dict:
        """Параметры подключения к базе данных"""
        return {
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port
        }

class XMLConfig:
    """Конфигурация XML"""
    OUTPUT_DIR = os.getenv('XML_OUTPUT_DIR', 'output')
    TEMP_DIR = os.getenv('XML_TEMP_DIR', 'temp')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB
    XML_VERSION = '1.0'
    XML_ENCODING = 'UTF-8'
    XML_NAMESPACE = 'http://www.osgeo.org/mapguide/coordinatesystem'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class TelegramConfig:
    """Конфигурация Telegram бота"""
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN не найден в TelegramConfig")
    ACCESS_PASSWORD = os.getenv('ACCESS_PASSWORD', '')
    ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()]
    
    # Параметры подключения к БД
    DB_PARAMS = {
        "dbname": os.getenv('DB_NAME', 'gis'),
        "user": os.getenv('DB_USER', 'postgres'),
        "password": os.getenv('DB_PASSWORD', 'postgres'),
        "host": os.getenv('DB_HOST', 'localhost'),
        "port": os.getenv('DB_PORT', '5432'),
        "min_connections": int(os.getenv('DB_MIN_CONNECTIONS', 2)),
        "max_connections": int(os.getenv('DB_MAX_CONNECTIONS', 10)),
        "connect_timeout": float(os.getenv('DB_CONNECTION_TIMEOUT', 30.0)),
        "idle_timeout": float(os.getenv('DB_IDLE_TIMEOUT', 300.0)),
        "health_check_interval": int(os.getenv('DB_HEALTH_CHECK_INTERVAL', 60)),
    }

class LogConfig:
    """Конфигурация логирования"""
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    HTTPS_LOG_LEVEL = os.getenv('HTTPS_LOG_LEVEL', 'WARNING')

class CacheConfig:
    """Конфигурация кэширования"""
    CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'True').lower() == 'true'
    CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # 1 час
    CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', 1000))

class ThreadingConfig:
    """Конфигурация многопоточности"""
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 100))

# Настройки Telegram бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Настройки логирования
LOG_CONFIG = {
    'level': LogConfig.LOG_LEVEL,
    'format': LogConfig.LOG_FORMAT,
    'date_format': LogConfig.DATE_FORMAT,
    'https_level': LogConfig.HTTPS_LOG_LEVEL
}

# Настройки кэширования
CACHE_CONFIG = {
    'enabled': CacheConfig.CACHE_ENABLED,
    'ttl': CacheConfig.CACHE_TTL,
    'max_size': CacheConfig.CACHE_MAX_SIZE
}

# Настройки многопоточности
THREADING_CONFIG = {
    'max_workers': ThreadingConfig.MAX_WORKERS,
    'chunk_size': ThreadingConfig.CHUNK_SIZE
}

class Config:
    """Основные настройки приложения"""
    
    # Базовая директория проекта
    BASE_DIR = Path(__file__).resolve().parent
    
    # Настройки базы данных
    DB_CONFIG_PATH = BASE_DIR / 'config' / 'database.json'
    
    # Настройки экспорта
    EXPORT_CONFIG_PATH = BASE_DIR / 'config' / 'export_config.json'
    
    # Настройки логирования
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DIR = BASE_DIR / 'logs'
    
    # Настройки кэширования
    CACHE_TTL = 3600  # 1 час
    CACHE_MAX_SIZE = 1000
    
    # Настройки метрик
    METRICS_ENABLED = True
    METRICS_COLLECTION_INTERVAL = 60  # 1 минута
    
    @classmethod
    def load_json_config(cls, path: Path) -> Dict[str, Any]:
        """
        Загрузка конфигурации из JSON файла
        
        Args:
            path: Путь к файлу конфигурации
            
        Returns:
            Dict[str, Any]: Загруженная конфигурация
        """
        try:
            if not path.exists():
                raise FileNotFoundError(f"Файл конфигурации не найден: {path}")
                
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            raise ConfigError(f"Ошибка загрузки конфигурации: {str(e)}")
            
class ConfigError(Exception):
    """Исключение для ошибок конфигурации"""
    pass