"""
Модуль для управления конфигурацией
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
from .log_manager import LogManager
import os
import re

logger = LogManager().get_logger(__name__)

class ConfigError(Exception):
    """Базовый класс для ошибок конфигурации"""
    pass

class ConfigLoadError(ConfigError):
    """Ошибка загрузки конфигурации"""
    pass

class ConfigValidationError(ConfigError):
    """Ошибка валидации конфигурации"""
    pass

@dataclass
class PoolConfig:
    """Конфигурация пула соединений"""
    retries: int = 3
    backoff_factor: float = 1.5
    backoff_max: int = 30
    health_check_query: str = "SELECT 1"
    health_check_timeout: int = 5
    max_lifetime: int = 3600
    max_idle_time: int = 300

    def __post_init__(self):
        self.retries = int(self.retries)
        self.backoff_factor = float(self.backoff_factor)
        self.backoff_max = int(self.backoff_max)
        self.health_check_timeout = int(self.health_check_timeout)
        self.max_lifetime = int(self.max_lifetime)
        self.max_idle_time = int(self.max_idle_time)
        if self.retries < 0:
            raise ConfigValidationError("retries должно быть неотрицательным")
        if self.backoff_factor <= 0:
            raise ConfigValidationError("backoff_factor должно быть положительным")
        if self.backoff_max < 0:
            raise ConfigValidationError("backoff_max должно быть неотрицательным")
        if self.health_check_timeout < 1:
            raise ConfigValidationError("health_check_timeout должно быть больше 0")
        if self.max_lifetime < 0:
            raise ConfigValidationError("max_lifetime должно быть неотрицательным")
        if self.max_idle_time < 0:
            raise ConfigValidationError("max_idle_time должно быть неотрицательным")

@dataclass
class SSLConfig:
    """Конфигурация SSL"""
    enabled: bool = False
    verify: bool = True
    cert: Optional[str] = None
    key: Optional[str] = None
    ca: Optional[str] = None

    def __post_init__(self):
        self.enabled = bool(self.enabled) if not isinstance(self.enabled, bool) else self.enabled
        self.verify = bool(self.verify) if not isinstance(self.verify, bool) else self.verify

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    min_connections: int
    max_connections: int
    health_check_interval: int
    host: str
    port: int
    dbname: str
    user: str
    password: str
    connect_timeout: float
    application_name: str
    statement_timeout: int
    idle_in_transaction_session_timeout: int
    pool: PoolConfig = field(default_factory=PoolConfig)
    ssl: SSLConfig = field(default_factory=SSLConfig)

    def __post_init__(self):
        """Валидация параметров конфигурации"""
        # Явное приведение типов
        try:
            self.min_connections = int(self.min_connections)
            self.max_connections = int(self.max_connections)
            self.health_check_interval = int(self.health_check_interval)
            self.port = int(self.port)
            self.connect_timeout = float(self.connect_timeout)
            self.statement_timeout = int(self.statement_timeout)
            self.idle_in_transaction_session_timeout = int(self.idle_in_transaction_session_timeout)
            # ... остальные числовые поля ...
        except Exception as e:
            raise ValueError(f"Ошибка приведения типов в DatabaseConfig: {e}")
        if self.min_connections < 1:
            raise ValueError("min_connections должно быть >= 1")
        if self.max_connections < self.min_connections:
            raise ValueError("max_connections должно быть >= min_connections")
        if not isinstance(self.port, int) or not (1024 <= self.port <= 65535):
            raise ConfigValidationError("port должен быть числом от 1024 до 65535")
        if not self.dbname:
            raise ConfigValidationError("dbname не может быть пустым")
        if not self.user:
            raise ConfigValidationError("user не может быть пустым")
        if not self.password:
            raise ConfigValidationError("password не может быть пустым")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        """Создание конфигурации из словаря"""
        try:
            # Приведение типов до создания экземпляра
            data = dict(data)  # копия
            
            # Извлекаем конфигурации пула и SSL
            pool_data = data.pop('pool', {})
            ssl_data = data.pop('ssl', {})
            
            # Проверяем, где находятся поля, которые должны быть в DatabaseConfig, а не в PoolConfig
            # Если они в pool_data, перемещаем их в основные данные
            if 'min_connections' not in data and 'min_connections' in pool_data:
                data['min_connections'] = pool_data['min_connections']
            if 'max_connections' not in data and 'max_connections' in pool_data:
                data['max_connections'] = pool_data['max_connections']
            if 'health_check_interval' not in data and 'health_check_interval' in pool_data:
                data['health_check_interval'] = pool_data['health_check_interval']
            
            # Удаляем поля из pool_data, которые не принадлежат PoolConfig
            pool_data.pop('min_connections', None)
            pool_data.pop('max_connections', None)
            pool_data.pop('health_check_interval', None)
            
            # Приведение типов
            data['min_connections'] = int(data['min_connections'])
            data['max_connections'] = int(data['max_connections'])
            data['health_check_interval'] = int(data['health_check_interval'])
            data['port'] = int(data['port'])
            data['connect_timeout'] = float(data['connect_timeout'])
            data['statement_timeout'] = int(data['statement_timeout'])
            data['idle_in_transaction_session_timeout'] = int(data['idle_in_transaction_session_timeout'])
            # ... остальные числовые поля ...

            # Создаем основной объект конфигурации
            config = cls(
                pool=PoolConfig(**pool_data),
                ssl=SSLConfig(**ssl_data),
                **data
            )
            return config
        except Exception as e:
            raise ConfigValidationError(f"Ошибка создания DatabaseConfig: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование конфигурации в словарь"""
        return {
            'min_connections': self.min_connections,
            'max_connections': self.max_connections,
            'health_check_interval': self.health_check_interval,
            'host': self.host,
            'port': self.port,
            'dbname': self.dbname,
            'user': self.user,
            'password': self.password,
            'connect_timeout': self.connect_timeout,
            'application_name': self.application_name,
            'statement_timeout': self.statement_timeout,
            'idle_in_transaction_session_timeout': self.idle_in_transaction_session_timeout,
            'pool': self.pool.__dict__,
            'ssl': self.ssl.__dict__
        }

@dataclass
class MetricsConfig:
    """Конфигурация метрик"""
    enabled: bool = True
    collection_interval: int = 60
    retention_period: int = 86400

    def __post_init__(self):
        self.enabled = bool(self.enabled) if not isinstance(self.enabled, bool) else self.enabled
        self.collection_interval = int(self.collection_interval)
        self.retention_period = int(self.retention_period)
        if self.collection_interval < 1:
            raise ConfigValidationError("collection_interval должно быть больше 0")
        if self.retention_period < self.collection_interval:
            raise ConfigValidationError("retention_period должно быть больше collection_interval")

@dataclass
class LogManagerConfig:
    """Конфигурация логирования"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None

    def __post_init__(self):
        self.level = str(self.level)
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level not in valid_levels:
            raise ConfigValidationError(f"level должен быть одним из: {valid_levels}")

@dataclass
class CacheManagerConfig:
    """Конфигурация кэширования"""
    enabled: bool = True
    max_size: int = 1000
    ttl: int = 3600

    def __post_init__(self):
        self.enabled = bool(self.enabled) if not isinstance(self.enabled, bool) else self.enabled
        self.max_size = int(self.max_size)
        self.ttl = int(self.ttl)
        if self.max_size < 1:
            raise ConfigValidationError("max_size должно быть больше 0")
        if self.ttl < 1:
            raise ConfigValidationError("ttl должно быть больше 0")

@dataclass
class SearchConfig:
    """Конфигурация поиска"""
    max_results: int = 100
    timeout: int = 30
    cache_enabled: bool = True

    def __post_init__(self):
        self.max_results = int(self.max_results)
        self.timeout = int(self.timeout)
        self.cache_enabled = bool(self.cache_enabled) if not isinstance(self.cache_enabled, bool) else self.cache_enabled
        if self.max_results < 1:
            raise ConfigValidationError("max_results должно быть больше 0")
        if self.timeout < 1:
            raise ConfigValidationError("timeout должно быть больше 0")

@dataclass
class ConnectionPoolLimitsConfig:
    """Конфигурация лимитов для HTTPX Connection Pool"""
    max_connections: Optional[int] = None # Максимальное количество одновременных подключений
    max_keepalive_connections: Optional[int] = None # Максимальное количество keep-alive соединений
    keepalive_expiry: Optional[float] = None # Время жизни keep-alive соединения в секундах

    def __post_init__(self):
        if self.max_connections is not None:
            self.max_connections = int(self.max_connections)
            if self.max_connections < 1:
                raise ConfigValidationError("max_connections в ConnectionPoolLimitsConfig должно быть больше 0, если указано")
        if self.max_keepalive_connections is not None:
            self.max_keepalive_connections = int(self.max_keepalive_connections)
            if self.max_keepalive_connections < 0: # Может быть 0, если не используется
                raise ConfigValidationError("max_keepalive_connections в ConnectionPoolLimitsConfig должно быть неотрицательным, если указано")
        if self.keepalive_expiry is not None:
            self.keepalive_expiry = float(self.keepalive_expiry)
            if self.keepalive_expiry < 0:
                raise ConfigValidationError("keepalive_expiry в ConnectionPoolLimitsConfig должно быть неотрицательным, если указано")

@dataclass
class TelegramBotConfig:
    """Конфигурация специфичных настроек Telegram бота"""
    connection_pool: Optional[ConnectionPoolLimitsConfig] = field(default_factory=ConnectionPoolLimitsConfig)
    connect_timeout: Optional[float] = 10.0
    read_timeout: Optional[float] = 20.0
    write_timeout: Optional[float] = 10.0
    concurrent_updates: Optional[int] = None # None означает значение по умолчанию PTB
    rate_limiter: Optional[Dict[str, Any]] = None # Заглушка для будущей конфигурации RateLimiter

    def __post_init__(self):
        if self.connect_timeout is not None:
            self.connect_timeout = float(self.connect_timeout)
            if self.connect_timeout <= 0:
                raise ConfigValidationError("connect_timeout в TelegramBotConfig должен быть положительным, если указан")
        if self.read_timeout is not None:
            self.read_timeout = float(self.read_timeout)
            if self.read_timeout <= 0:
                raise ConfigValidationError("read_timeout в TelegramBotConfig должен быть положительным, если указан")
        if self.write_timeout is not None:
            self.write_timeout = float(self.write_timeout)
            if self.write_timeout <= 0:
                raise ConfigValidationError("write_timeout в TelegramBotConfig должен быть положительным, если указан")
        if self.concurrent_updates is not None:
            self.concurrent_updates = int(self.concurrent_updates)
            if self.concurrent_updates < 1:
                 raise ConfigValidationError("concurrent_updates в TelegramBotConfig должно быть больше 0, если указано")

@dataclass
class EnhancedConfig:
    """Расширенная конфигурация"""
    config_path: str
    database: Optional[DatabaseConfig] = None
    metrics: Optional[MetricsConfig] = None
    logging: Optional[LogManagerConfig] = None
    cache: Optional[CacheManagerConfig] = None
    search: Optional[SearchConfig] = None
    telegram_bot: Optional[TelegramBotConfig] = None # Новый атрибут

    def __post_init__(self):
        """Загрузка конфигурации после инициализации"""
        self._load_config()

    def _validate_json(self, data: Dict[str, Any]) -> None:
        """Валидация структуры JSON"""
        required_sections = {'database', 'metrics', 'logging', 'cache', 'search'} # telegram_bot - опционален
        missing_sections = required_sections - set(data.keys())
        if missing_sections:
            raise ConfigValidationError(f"Отсутствуют обязательные секции: {missing_sections}")
        
        # Дополнительная валидация для опциональной секции telegram_bot, если она есть
        if 'telegram_bot' in data and not isinstance(data['telegram_bot'], dict):
            raise ConfigValidationError("Секция 'telegram_bot' должна быть словарем, если присутствует.")

    def substitute_env_vars(self, obj):
        """
        Рекурсивно заменяет строки вида ${ENV_VAR} на значения из переменных окружения.
        """
        if isinstance(obj, dict):
            return {k: self.substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.substitute_env_vars(v) for v in obj]
        elif isinstance(obj, str):
            match = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", obj)
            if match:
                env_var = match.group(1)
                value = os.getenv(env_var)
                if value is None:
                    raise ValueError(f"Переменная окружения {env_var} не задана, требуется для конфигурации")
                return value
            return obj
        else:
            return obj

    def _load_config(self) -> None:
        """Загрузка конфигурации из файла"""
        try:
            config_path = Path(self.config_path)
            if not config_path.exists():
                raise ConfigLoadError(f"Файл конфигурации не найден: {self.config_path}")

            with open(config_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ConfigLoadError(f"Ошибка парсинга JSON: {e}")

            # Подстановка переменных окружения
            data = self.substitute_env_vars(data)

            self._validate_json(data)
                
            # Загружаем конфигурации из JSON
            if 'database' in data:
                self.database = DatabaseConfig.from_dict(data['database'])
            else: # Эта ветка теперь не должна достигаться из-за _validate_json, но оставим для надежности
                raise ConfigValidationError("Секция 'database' отсутствует в конфиге")
            
            if 'metrics' in data:
                self.metrics = MetricsConfig(**data['metrics'])
            else:
                raise ConfigValidationError("Секция 'metrics' отсутствует в конфиге")

            if 'logging' in data:
                self.logging = LogManagerConfig(**data['logging'])
            else:
                raise ConfigValidationError("Секция 'logging' отсутствует в конфиге")

            if 'cache' in data:
                self.cache = CacheManagerConfig(**data['cache'])
            else:
                raise ConfigValidationError("Секция 'cache' отсутствует в конфиге")

            if 'search' in data:
                self.search = SearchConfig(**data['search'])
            else:
                raise ConfigValidationError("Секция 'search' отсутствует в конфиге")
            
            # Загрузка опциональной секции telegram_bot
            if 'telegram_bot' in data:
                pool_data = data['telegram_bot'].pop('connection_pool', {})
                self.telegram_bot = TelegramBotConfig(
                    connection_pool=ConnectionPoolLimitsConfig(**pool_data) if pool_data else None,
                    **data['telegram_bot']
                )
            else:
                self.telegram_bot = None # или TelegramBotConfig() для значений по умолчанию
                
            logger.info("Конфигурация успешно загружена")
            
        except ConfigError as e:
            logger.error(f"Ошибка конфигурации: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке конфигурации: {e}")
            raise ConfigLoadError(f"Неожиданная ошибка: {e}")

    def save(self) -> None:
        """Сохранение конфигурации в файл"""
        try:
            data = {
                'database': self.database.to_dict() if self.database else None,
                'metrics': self.metrics.__dict__ if self.metrics else None,
                'logging': self.logging.__dict__ if self.logging else None,
                'cache': self.cache.__dict__ if self.cache else None,
                'search': self.search.__dict__ if self.search else None,
                'telegram_bot': None # Инициализируем как None
            }
            if self.telegram_bot:
                data['telegram_bot'] = {
                    'connection_pool': self.telegram_bot.connection_pool.__dict__ if self.telegram_bot.connection_pool else None,
                    'connect_timeout': self.telegram_bot.connect_timeout,
                    'read_timeout': self.telegram_bot.read_timeout,
                    'write_timeout': self.telegram_bot.write_timeout,
                    'concurrent_updates': self.telegram_bot.concurrent_updates,
                    'rate_limiter': self.telegram_bot.rate_limiter
                }
                # Убираем None значения из telegram_bot для чистоты JSON
                current_telegram_bot_data = data['telegram_bot'] # Сохраняем ссылку
                if current_telegram_bot_data is not None: # Дополнительная проверка для линтера
                    data['telegram_bot'] = {k: v for k, v in current_telegram_bot_data.items() if v is not None}
                
                if not data['telegram_bot']: # Если все поля None, то и сам telegram_bot None
                    data['telegram_bot'] = None

            # Удаляем ключи с None значениями из верхнего уровня для чистоты JSON
            data = {k: v for k, v in data.items() if v is not None}
            
            config_path = Path(self.config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            logger.info("Конфигурация успешно сохранена")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            raise ConfigLoadError(f"Ошибка сохранения: {e}")

# Создаем глобальный экземпляр конфигурации
try:
    enhanced_config = EnhancedConfig('XML_search/enhanced/config/database.json')
except ConfigError as e:
    logger.error(f"Ошибка инициализации конфигурации: {e}")
    raise

__all__ = ['EnhancedConfig', 'enhanced_config', 'ConfigError', 'ConfigLoadError', 'ConfigValidationError'] 