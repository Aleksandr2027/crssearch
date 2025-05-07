import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
from XML_search.config import DBConfig, LogConfig, CacheConfig
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MetricsConfig:
    """Конфигурация метрик"""
    cleanup_interval: int = 300
    max_age: int = 3600
    enabled: bool = True
    cache_metrics: bool = True
    log_metrics: bool = True
    metrics_dir: str = "metrics"

    def __post_init__(self):
        # Создание директории для метрик, если она не существует
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Валидация значений
        if self.cleanup_interval < 1:
            logger.warning("cleanup_interval не может быть меньше 1 секунды, установлено значение 1")
            self.cleanup_interval = 1
            
        if self.max_age < 1:
            logger.warning("max_age не может быть меньше 1 секунды, установлено значение 1")
            self.max_age = 1

@dataclass
class DatabasePoolConfig:
    """Конфигурация пула подключений к БД"""
    min_connections: int = 1
    max_connections: int = 20
    connection_timeout: float = 30.0
    idle_timeout: float = 600.0  # 10 минут
    max_lifetime: float = 3600.0  # 1 час
    pool_recycle: int = 3600  # 1 час
    pool_pre_ping: bool = True
    db_params: Dict[str, Any] = None

    def __post_init__(self):
        self.db_params = {
            "dbname": DBConfig.DB_NAME,
            "user": DBConfig.DB_USER,
            "password": DBConfig.DB_PASSWORD,
            "host": DBConfig.DB_HOST,
            "port": DBConfig.DB_PORT
        }
        
        # Валидация значений
        if self.min_connections < 1:
            logger.warning("min_connections не может быть меньше 1, установлено значение 1")
            self.min_connections = 1
            
        if self.max_connections < self.min_connections:
            logger.warning("max_connections не может быть меньше min_connections, установлено значение min_connections")
            self.max_connections = self.min_connections
            
        if self.connection_timeout < 1:
            logger.warning("connection_timeout не может быть меньше 1 секунды, установлено значение 1")
            self.connection_timeout = 1.0

@dataclass
class LogManagerConfig:
    """Расширенная конфигурация логирования"""
    log_dir: str = "logs"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    log_level: str = LogConfig.LOG_LEVEL
    log_format: str = LogConfig.LOG_FORMAT
    date_format: str = LogConfig.DATE_FORMAT
    file_name_template: str = "bot_{date}.log"
    clean_interval: int = 7  # дней

    def __post_init__(self):
        # Создание директории для логов, если она не существует
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Валидация значений
        if self.max_bytes < 1024:  # Минимум 1KB
            logger.warning("max_bytes не может быть меньше 1KB, установлено значение 1KB")
            self.max_bytes = 1024
            
        if self.backup_count < 1:
            logger.warning("backup_count не может быть меньше 1, установлено значение 1")
            self.backup_count = 1
            
        if self.clean_interval < 1:
            logger.warning("clean_interval не может быть меньше 1 дня, установлено значение 1")
            self.clean_interval = 1

@dataclass
class CacheManagerConfig:
    """Расширенная конфигурация кэширования"""
    enabled: bool = CacheConfig.CACHE_ENABLED
    ttl: int = CacheConfig.CACHE_TTL
    max_size: int = CacheConfig.CACHE_MAX_SIZE
    cleanup_interval: int = 3600  # 1 час
    min_cleanup_size: int = int(CacheConfig.CACHE_MAX_SIZE * 0.8)  # 80% от максимума

    def __post_init__(self):
        # Валидация значений
        if self.ttl < 1:
            logger.warning("ttl не может быть меньше 1 секунды, установлено значение 1")
            self.ttl = 1
            
        if self.max_size < 1:
            logger.warning("max_size не может быть меньше 1, установлено значение 1")
            self.max_size = 1
            
        if self.cleanup_interval < 1:
            logger.warning("cleanup_interval не может быть меньше 1 секунды, установлено значение 1")
            self.cleanup_interval = 1
            
        if self.min_cleanup_size < 1:
            logger.warning("min_cleanup_size не может быть меньше 1, установлено значение 1")
            self.min_cleanup_size = 1

@dataclass
class MaintenanceConfig:
    """Конфигурация обслуживания"""
    enabled: bool = True
    interval: int = 3600  # 1 час
    tasks: Dict[str, int] = None
    max_task_duration: int = 300  # 5 минут

    def __post_init__(self):
        self.tasks = {
            "clean_logs": 86400,        # 24 часа
            "clean_cache": 3600,        # 1 час
            "check_connections": 300,    # 5 минут
            "collect_metrics": 60        # 1 минута
        }

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: float = 30.0
    idle_timeout: float = 600.0
    health_check_interval: int = 300
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    max_lifetime: float = 3600.0
    retry: Dict[str, Any] = None

    def __post_init__(self):
        if self.retry is None:
            self.retry = {
                "max_attempts": 3,
                "delay": 1.0,
                "enabled": True
            }

@dataclass
class CacheConfig:
    """Конфигурация кэширования"""
    enabled: bool = True
    ttl: int = 3600
    max_size: int = 1000
    cleanup_interval: int = 300
    min_cleanup_size: int = 800

@dataclass
class SearchConfig:
    """Конфигурация поиска"""
    max_results: int = 20
    fuzzy_threshold: float = 0.85
    transliteration_enabled: bool = True

@dataclass
class LoggingConfig:
    """Конфигурация логирования"""
    log_dir: str = "logs"
    max_bytes: int = 10485760
    backup_count: int = 5
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_name_template: str = "bot_{date}.log"
    clean_interval: int = 7

@dataclass
class EnhancedConfig:
    """Расширенная конфигурация приложения"""
    metrics: MetricsConfig
    database: DatabaseConfig
    cache: CacheConfig
    search: SearchConfig
    logging: LoggingConfig

    @classmethod
    def load_from_file(cls, config_file: str = "config/enhanced_config.json") -> 'EnhancedConfig':
        """Загрузка конфигурации из файла"""
        try:
            if not os.path.exists(config_file):
                logger.warning(f"Файл конфигурации {config_file} не существует, создание с настройками по умолчанию...")
                config = cls._create_default_config()
                cls._save_config(config_file, config)
                return config

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            return cls(
                metrics=MetricsConfig(**config_data.get('metrics', {})),
                database=DatabaseConfig(**config_data.get('database', {})),
                cache=CacheConfig(**config_data.get('cache', {})),
                search=SearchConfig(**config_data.get('search', {})),
                logging=LoggingConfig(**config_data.get('logging', {}))
            )

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            logger.warning("Использование конфигурации по умолчанию")
            return cls._create_default_config()

    @classmethod
    def _create_default_config(cls) -> 'EnhancedConfig':
        """Создание конфигурации по умолчанию"""
        return cls(
            metrics=MetricsConfig(),
            database=DatabaseConfig(),
            cache=CacheConfig(),
            search=SearchConfig(),
            logging=LoggingConfig()
        )

    @classmethod
    def _save_config(cls, config_file: str, config: 'EnhancedConfig') -> None:
        """Сохранение конфигурации в файл"""
        try:
            config_data = {
                'metrics': {
                    'cleanup_interval': config.metrics.cleanup_interval,
                    'max_age': config.metrics.max_age,
                    'enabled': config.metrics.enabled,
                    'cache_metrics': config.metrics.cache_metrics,
                    'log_metrics': config.metrics.log_metrics,
                    'metrics_dir': config.metrics.metrics_dir
                },
                'database': {
                    'min_connections': config.database.min_connections,
                    'max_connections': config.database.max_connections,
                    'connection_timeout': config.database.connection_timeout,
                    'idle_timeout': config.database.idle_timeout,
                    'health_check_interval': config.database.health_check_interval,
                    'pool_recycle': config.database.pool_recycle,
                    'pool_pre_ping': config.database.pool_pre_ping,
                    'max_lifetime': config.database.max_lifetime,
                    'retry': config.database.retry
                },
                'cache': {
                    'enabled': config.cache.enabled,
                    'ttl': config.cache.ttl,
                    'max_size': config.cache.max_size,
                    'cleanup_interval': config.cache.cleanup_interval,
                    'min_cleanup_size': config.cache.min_cleanup_size
                },
                'search': {
                    'max_results': config.search.max_results,
                    'fuzzy_threshold': config.search.fuzzy_threshold,
                    'transliteration_enabled': config.search.transliteration_enabled
                },
                'logging': {
                    'log_dir': config.logging.log_dir,
                    'max_bytes': config.logging.max_bytes,
                    'backup_count': config.logging.backup_count,
                    'log_level': config.logging.log_level,
                    'log_format': config.logging.log_format,
                    'date_format': config.logging.date_format,
                    'file_name_template': config.logging.file_name_template,
                    'clean_interval': config.logging.clean_interval
                }
            }

            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")

# Создаем глобальный экземпляр конфигурации
enhanced_config = EnhancedConfig.load_from_file()

__all__ = ['EnhancedConfig', 'enhanced_config'] 