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
    PASSWORD: str = os.getenv('ACCESS_PASSWORD', '123')
    MAX_ATTEMPTS: int = 3
    BLOCK_TIME: int = 300  # 5 минут
    SESSION_TIMEOUT: int = 3600  # 1 час

@dataclass
class BotConfig:
    """Конфигурация бота"""
    
    # Токен бота
    BOT_TOKEN: str = os.getenv('TELEGRAM_TOKEN', '')
    
    # Пути к конфигурационным файлам
    BASE_DIR: Path = Path(__file__).parent.parent
    DB_CONFIG_PATH: str = os.getenv('DB_CONFIG_PATH', str(BASE_DIR / "enhanced" / "config" / "database.json"))
    EXPORT_CONFIG_PATH: str = os.getenv('EXPORT_CONFIG_PATH', str(BASE_DIR / "config" / "export_config.json"))
    
    # Настройки базы данных
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', 5432))
    DB_NAME: str = os.getenv('DB_NAME', 'gis')
    DB_USER: str = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'postgres')
    DB_MIN_CONNECTIONS: int = int(os.getenv('DB_MIN_CONNECTIONS', 2))
    DB_MAX_CONNECTIONS: int = int(os.getenv('DB_MAX_CONNECTIONS', 10))
    DB_CONNECTION_TIMEOUT: float = float(os.getenv('DB_CONNECTION_TIMEOUT', 30.0))
    DB_IDLE_TIMEOUT: float = float(os.getenv('DB_IDLE_TIMEOUT', 300.0))
    DB_HEALTH_CHECK_INTERVAL: int = int(os.getenv('DB_HEALTH_CHECK_INTERVAL', 60))
    
    # Настройки логирования
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE', None)
    HTTPS_LOG_LEVEL: str = os.getenv('HTTPS_LOG_LEVEL', 'WARNING')
    LOG_DIR: str = os.getenv('LOG_DIR', 'logs')
    
    # Директории для файлов
    OUTPUT_DIR: str = os.getenv('OUTPUT_DIR', 'output')
    TEMP_DIR: str = os.getenv('TEMP_DIR', 'temp')
    
    # Настройки кэширования
    CACHE_ENABLED: bool = os.getenv('CACHE_ENABLED', 'True').lower() == 'true'
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', 3600))
    CACHE_MAX_SIZE: int = int(os.getenv('CACHE_MAX_SIZE', 1000))
    
    # Настройки поиска
    SEARCH_MAX_RESULTS: int = int(os.getenv('SEARCH_MAX_RESULTS', 100))
    SEARCH_TIMEOUT: int = int(os.getenv('SEARCH_TIMEOUT', 30))
    INLINE_CACHE_DURATION: int = int(os.getenv('INLINE_CACHE_DURATION', 60))
    DEFAULT_THUMB_URL: Optional[str] = os.getenv('DEFAULT_THUMB_URL', '')
    
    # Настройки Telegram Polling
    ALLOWED_UPDATES: list[str] = field(default_factory=lambda: os.getenv('ALLOWED_UPDATES', "message,edited_message,channel_post,edited_channel_post,inline_query,chosen_inline_result,callback_query,shipping_query,pre_checkout_query,poll,poll_answer,my_chat_member,chat_member,chat_join_request").split(','))
    DROP_PENDING_UPDATES: bool = os.getenv('DROP_PENDING_UPDATES', 'False').lower() == 'true'
    
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
    ACCESS_PASSWORD: str = os.getenv('ACCESS_PASSWORD', '123')
    AUTH_CONFIG: AuthConfig = field(default_factory=lambda: AuthConfig(PASSWORD=os.getenv('ACCESS_PASSWORD', '123')))
    
    # Telegram admin ids
    ADMIN_IDS: list = field(default_factory=lambda: [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip().isdigit()])
    
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
    
    # Тексты кнопок меню
    MENU_BUTTONS: Dict[str, str] = field(default_factory=lambda: {
        'search_coords': 'Поиск СК по Lat/Lon',
        'search_desc': 'Поиск СК по описанию',
        'export_results': 'Экспорт результатов',
        'help': 'Помощь',
        'back_to_main_menu': '🔙 Главное меню'
    })
    
    def __post_init__(self):
        """Валидация конфигурации после инициализации"""
        config_dir = Path(self.DB_CONFIG_PATH).parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не может быть пустым")
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
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.LOG_LEVEL not in valid_levels:
            raise ValueError(f"LOG_LEVEL должен быть одним из: {valid_levels}")
        if self.CACHE_TTL < 1:
            raise ValueError("CACHE_TTL должно быть больше 0")
        if self.CACHE_MAX_SIZE < 1:
            raise ValueError("CACHE_MAX_SIZE должно быть больше 0")
        if self.SEARCH_MAX_RESULTS < 1:
            raise ValueError("SEARCH_MAX_RESULTS должно быть больше 0")
        if self.SEARCH_TIMEOUT < 1:
            raise ValueError("SEARCH_TIMEOUT должно быть больше 0")
        if self.INLINE_CACHE_DURATION < 0:
            raise ValueError("INLINE_CACHE_DURATION не может быть отрицательным")
        
        # Проверка для ALLOWED_UPDATES (что это список строк)
        if not isinstance(self.ALLOWED_UPDATES, list) or not all(isinstance(item, str) for item in self.ALLOWED_UPDATES):
            raise ValueError("ALLOWED_UPDATES должен быть списком строк")

    @classmethod
    def get_export_config(cls, format_name: str) -> Dict[str, Any]:
        """Получение конфигурации экспортера по имени формата"""
        return cls.EXPORT_CONFIG.get(format_name, {}) 