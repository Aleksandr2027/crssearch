import os
from dotenv import load_dotenv
from pathlib import Path
import logging

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
    DB_NAME = os.getenv('DB_NAME', 'gis')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    
    # Параметры пула соединений
    min_connections = int(os.getenv('DB_MIN_CONNECTIONS', '5'))
    max_connections = int(os.getenv('DB_MAX_CONNECTIONS', '20'))
    connection_timeout = float(os.getenv('DB_CONNECTION_TIMEOUT', '30.0'))
    idle_timeout = float(os.getenv('DB_IDLE_TIMEOUT', '600.0'))
    health_check_interval = int(os.getenv('DB_HEALTH_CHECK_INTERVAL', '300'))
    
    @property
    def dbname(self):
        return self.DB_NAME
        
    @property
    def user(self):
        return self.DB_USER
        
    @property
    def password(self):
        return self.DB_PASSWORD
        
    @property
    def host(self):
        return self.DB_HOST
        
    @property
    def port(self):
        return self.DB_PORT

    @property
    def db_params(self) -> dict:
        """Возвращает словарь с параметрами подключения к базе данных"""
        return {
            "dbname": self.DB_NAME,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "host": self.DB_HOST,
            "port": self.DB_PORT
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
    ACCESS_PASSWORD = os.getenv('ACCESS_PASSWORD', '123')
    
    # Параметры подключения к БД
    DB_PARAMS = {
        "dbname": "gis",
        "user": "postgres",
        "password": "postgres",
        "host": "localhost",
        "port": "5432",
    }
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

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