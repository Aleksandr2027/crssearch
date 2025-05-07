"""
Конфигурация Telegram бота
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import os
from XML_search.config import DBConfig
from XML_search.enhanced.config_enhanced import enhanced_config

@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str = os.getenv('TELEGRAM_TOKEN', '')
    admin_ids: List[int] = None
    access_password: str = os.getenv('ACCESS_PASSWORD', '123')
    db_config: Dict[str, Any] = None
    metrics_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Пост-инициализация конфигурации"""
        # Инициализация admin_ids
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        self.admin_ids = [int(id) for id in admin_ids_str.split(',') if id]
        
        # Конфигурация базы данных
        self.db_config = {
            "dbname": DBConfig.DB_NAME,
            "user": DBConfig.DB_USER,
            "password": DBConfig.DB_PASSWORD,
            "host": DBConfig.DB_HOST,
            "port": DBConfig.DB_PORT,
            "min_connections": enhanced_config.database.min_connections,
            "max_connections": enhanced_config.database.max_connections,
            "connection_timeout": enhanced_config.database.connection_timeout,
            "idle_timeout": enhanced_config.database.idle_timeout
        }
        
        # Конфигурация метрик
        self.metrics_config = {
            "enabled": enhanced_config.metrics.enabled,
            "cleanup_interval": enhanced_config.metrics.cleanup_interval,
            "max_age": enhanced_config.metrics.max_age,
            "cache_metrics": enhanced_config.metrics.cache_metrics,
            "log_metrics": enhanced_config.metrics.log_metrics,
            "metrics_dir": enhanced_config.metrics.metrics_dir
        }
        
    @property
    def is_configured(self) -> bool:
        """Проверка корректности конфигурации"""
        return bool(self.token and self.access_password) 