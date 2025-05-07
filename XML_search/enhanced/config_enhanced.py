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
            data['min_connections'] = int(data['min_connections'])
            data['max_connections'] = int(data['max_connections'])
            data['health_check_interval'] = int(data['health_check_interval'])
            data['port'] = int(data['port'])
            data['connect_timeout'] = float(data['connect_timeout'])
            data['statement_timeout'] = int(data['statement_timeout'])
            data['idle_in_transaction_session_timeout'] = int(data['idle_in_transaction_session_timeout'])
            # ... остальные числовые поля ...
            
            # Извлекаем конфигурации пула и SSL
            pool_data = data.pop('pool', {})
            ssl_data = data.pop('ssl', {})
            
            # Создаем основной объект конфигурации
            config = cls(**data)
            
            # Добавляем конфигурации пула и SSL
            config.pool = PoolConfig(**pool_data)
            config.ssl = SSLConfig(**ssl_data)
            
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
class EnhancedConfig:
    """Расширенная конфигурация"""
    config_path: str
    database: Optional[DatabaseConfig] = None
    metrics: Optional[MetricsConfig] = None
    logging: Optional[LogManagerConfig] = None
    cache: Optional[CacheManagerConfig] = None
    search: Optional[SearchConfig] = None

    def __post_init__(self):
        """Загрузка конфигурации после инициализации"""
        self._load_config()

    def _validate_json(self, data: Dict[str, Any]) -> None:
        """Валидация структуры JSON"""
        required_sections = {'database', 'metrics', 'logging', 'cache', 'search'}
        missing_sections = required_sections - set(data.keys())
        if missing_sections:
            raise ConfigValidationError(f"Отсутствуют обязательные секции: {missing_sections}")

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
            else:
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
                'database': self.database.to_dict(),
                'metrics': self.metrics.__dict__,
                'logging': self.logging.__dict__,
                'cache': self.cache.__dict__,
                'search': self.search.__dict__
            }
            
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