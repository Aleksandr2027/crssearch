"""
Модуль конфигурации бота
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from XML_search.config import TelegramConfig, LogConfig, CacheConfig
from XML_search.enhanced.config_enhanced import enhanced_config

@dataclass
class AuthConfig:
    """Конфигурация авторизации"""
    PASSWORD: str = os.getenv('BOT_PASSWORD', 'default_password')
    MAX_ATTEMPTS: int = 3
    BLOCK_TIME: int = 300  # 5 минут
    SESSION_TIMEOUT: int = 3600  # 1 час

@dataclass
class BotConfig:
    """Конфигурация бота"""
    
    # Токен бота
    BOT_TOKEN: str = "7805203567:AAEYMeCWrU6f9OnzY3xgvVDpPrClnLeQcEI"
    
    # Пути к конфигурационным файлам
    BASE_DIR: Path = Path(__file__).parent.parent
    DB_CONFIG_PATH: str = str(BASE_DIR / "enhanced" / "config" / "database.json")
    
    # Настройки базы данных
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "gis"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
    # Настройки логирования
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # Настройки кэширования
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    CACHE_MAX_SIZE: int = 1000
    
    # Настройки поиска
    SEARCH_MAX_RESULTS: int = 100
    SEARCH_TIMEOUT: int = 30
    
    # Настройки базы данных
    DB_CONFIG = enhanced_config.database
    
    # Настройки метрик
    METRICS_CONFIG = enhanced_config.metrics
    
    # Настройки поиска
    SEARCH_CONFIG = enhanced_config.search
    
    # Настройки экспорта
    EXPORT_CONFIG = {
        'xml_Civil3D': {
            'display_name': 'Civil3D XML',
            'description': 'Экспорт в формат Civil3D XML',
            'extension': '.xml',
            'format_name': 'xml_Civil3D'
        },
        'prj_GMv20': {
            'display_name': 'GMv20',
            'description': 'Экспорт в формат GMv20',
            'extension': '.prj',
            'format_name': 'prj_GMv20'
        },
        'prj_GMv25': {
            'display_name': 'GMv25',
            'description': 'Экспорт в формат GMv25',
            'extension': '.prj',
            'format_name': 'prj_GMv25'
        }
    }
    
    # Настройки авторизации
    AUTH_CONFIG: AuthConfig = field(default_factory=AuthConfig)
    
    # Настройки сообщений
    MESSAGES: Dict[str, str] = field(default_factory=lambda: {
        'welcome': 'Добро пожаловать! Используйте /auth для авторизации.',
        'auth_required': 'Требуется авторизация. Используйте /auth.',
        'auth_success': 'Авторизация успешна!',
        'auth_failed': 'Неверный пароль. Попробуйте еще раз.',
        'auth_blocked': 'Слишком много попыток. Попробуйте позже.',
        'error': 'Произошла ошибка: {error}',
        'help': 'Справка по командам:\n/auth - авторизация\n/search - поиск\n/export - экспорт\n/help - справка'
    })
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации"""
        # Проверяем существование директории конфигурации
        config_dir = Path(self.DB_CONFIG_PATH).parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
            
        # Проверяем токен бота
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не может быть пустым")
            
        # Проверяем настройки базы данных
        if not self.DB_HOST:
            raise ValueError("DB_HOST не может быть пустым")
        if not isinstance(self.DB_PORT, int) or not (1024 <= self.DB_PORT <= 65535):
            raise ValueError("DB_PORT должен быть числом от 1024 до 65535")
        if not self.DB_NAME:
            raise ValueError("DB_NAME не может быть пустым")
        if not self.DB_USER:
            raise ValueError("DB_USER не может быть пустым")
        if not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD не может быть пустым")
            
        # Проверяем настройки логирования
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.LOG_LEVEL not in valid_levels:
            raise ValueError(f"LOG_LEVEL должен быть одним из: {valid_levels}")
            
        # Проверяем настройки кэширования
        if self.CACHE_TTL < 1:
            raise ValueError("CACHE_TTL должно быть больше 0")
        if self.CACHE_MAX_SIZE < 1:
            raise ValueError("CACHE_MAX_SIZE должно быть больше 0")
            
        # Проверяем настройки поиска
        if self.SEARCH_MAX_RESULTS < 1:
            raise ValueError("SEARCH_MAX_RESULTS должно быть больше 0")
        if self.SEARCH_TIMEOUT < 1:
            raise ValueError("SEARCH_TIMEOUT должно быть больше 0")
    
    @classmethod
    def get_export_config(cls, format_name: str) -> Dict[str, Any]:
        """Получение конфигурации экспортера по имени формата"""
        return cls.EXPORT_CONFIG.get(format_name, {}) 