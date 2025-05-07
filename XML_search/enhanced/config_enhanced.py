"""
Модуль для управления конфигурацией
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
from .log_manager import LogManager

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

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    min_connections: int = 2
    max_connections: int = 10
    health_check_interval: int = 60
    host: str = "localhost"
    port: int = 5432
    dbname: str = "gis"
    user: str = "postgres"
    password: str = "postgres"
    connect_timeout: int = 10
    application_name: str = "telegram_bot"
    statement_timeout: int = 30000
    idle_in_transaction_session_timeout: int = 30000
    pool: PoolConfig = field(default_factory=PoolConfig)
    ssl: SSLConfig = field(default_factory=SSLConfig)

    def __post_init__(self):
        """Валидация параметров конфигурации"""
        if self.min_connections < 1:
            raise ConfigValidationError("min_connections должно быть больше 0")
        if self.max_connections < self.min_connections:
            raise ConfigValidationError("max_connections должно быть больше или равно min_connections")
        if self.health_check_interval < 1:
            raise ConfigValidationError("health_check_interval должно быть больше 0")
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
        if self.max_results < 1:
            raise ConfigValidationError("max_results должно быть больше 0")
        if self.timeout < 1:
            raise ConfigValidationError("timeout должно быть больше 0")

@dataclass
class EnhancedConfig:
    """Расширенная конфигурация"""
    config_path: str
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    logging: LogManagerConfig = field(default_factory=LogManagerConfig)
    cache: CacheManagerConfig = field(default_factory=CacheManagerConfig)
    search: SearchConfig = field(default_factory=SearchConfig)

    def __post_init__(self):
        """Загрузка конфигурации после инициализации"""
        self._load_config()

    def _validate_json(self, data: Dict[str, Any]) -> None:
        """Валидация структуры JSON"""
        required_sections = {'database', 'metrics', 'logging', 'cache', 'search'}
        missing_sections = required_sections - set(data.keys())
        if missing_sections:
            raise ConfigValidationError(f"Отсутствуют обязательные секции: {missing_sections}")

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

            self._validate_json(data)
                
            # Загружаем конфигурации из JSON
            if 'database' in data:
                self.database = DatabaseConfig.from_dict(data['database'])
            if 'metrics' in data:
                self.metrics = MetricsConfig(**data['metrics'])
            if 'logging' in data:
                self.logging = LogManagerConfig(**data['logging'])
            if 'cache' in data:
                self.cache = CacheManagerConfig(**data['cache'])
            if 'search' in data:
                self.search = SearchConfig(**data['search'])
                
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