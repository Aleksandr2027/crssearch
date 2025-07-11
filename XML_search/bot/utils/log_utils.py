"""
Утилиты для логирования
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
from logging.handlers import RotatingFileHandler
import traceback
import sys
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager

class BotLogger:
    """Расширенный логгер для бота с поддержкой структурированного логирования"""

    def __init__(self, name: str = "bot"):
        """
        Инициализация логгера
        
        Args:
            name: Имя логгера
        """
        self.name = name
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)

        # Создаем директории для разных типов логов
        self.error_logs = self.logs_dir / "errors"
        self.access_logs = self.logs_dir / "access"
        self.debug_logs = self.logs_dir / "debug"
        self.metrics_logs = self.logs_dir / "metrics"

        for dir in [self.error_logs, self.access_logs, self.debug_logs, self.metrics_logs]:
            dir.mkdir(exist_ok=True)

        # Инициализация логгеров
        self.logger = self._setup_logger()
        self.error_logger = self._setup_error_logger()
        self.access_logger = self._setup_access_logger()
        self.debug_logger = self._setup_debug_logger()
        self.metrics_logger = self._setup_metrics_logger()

        # Метрики
        self.metrics = MetricsManager()

    def _setup_logger(self) -> logging.Logger:
        """
        Настройка логгера
        
        Returns:
            Настроенный логгер
        """
        # Создаем логгер
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)
        
        # Форматтер для логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Основной лог
        main_handler = RotatingFileHandler(
            self.logs_dir / "bot.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setFormatter(formatter)
        main_handler.setLevel(logging.INFO)
        logger.addHandler(main_handler)
        
        # Лог ошибок
        error_handler = RotatingFileHandler(
            self.error_logs / "errors.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
        
        # Лог доступа
        access_handler = RotatingFileHandler(
            self.access_logs / "access.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        access_handler.setFormatter(formatter)
        access_handler.setLevel(logging.INFO)
        logger.addHandler(access_handler)
        
        # Отладочный лог
        debug_handler = RotatingFileHandler(
            self.debug_logs / "debug.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)
        logger.addHandler(debug_handler)
        
        # Лог метрик
        metrics_handler = RotatingFileHandler(
            self.metrics_logs / "metrics.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        metrics_handler.setFormatter(formatter)
        metrics_handler.setLevel(logging.INFO)
        logger.addHandler(metrics_handler)
        
        return logger

    def _setup_error_logger(self) -> logging.Logger:
        """Настройка логгера ошибок"""
        logger = logging.getLogger("bot.error")
        logger.setLevel(logging.ERROR)

        handler = RotatingFileHandler(
            self.error_logs / "errors.log",
            maxBytes=10*1024*1024,
            backupCount=10,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s\n'
            'Stack trace:\n%(stack_trace)s\n'
        ))
        logger.addHandler(handler)
        return logger

    def _setup_access_logger(self) -> logging.Logger:
        """Настройка логгера доступа"""
        logger = logging.getLogger("bot.access")
        logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            self.access_logs / "access.log",
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def _setup_debug_logger(self) -> logging.Logger:
        """Настройка отладочного логгера"""
        logger = logging.getLogger("bot.debug")
        logger.setLevel(logging.DEBUG)

        handler = RotatingFileHandler(
            self.debug_logs / "debug.log",
            maxBytes=10*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def _setup_metrics_logger(self) -> logging.Logger:
        """Настройка логгера метрик"""
        logger = logging.getLogger("bot.metrics")
        logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            self.metrics_logs / "metrics.log",
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование ошибки
        
        Args:
            error: Исключение
            context: Контекст ошибки
        """
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'context': context or {}
        }
        
        self.logger.error(
            f"Ошибка: {error_info['type']} - {error_info['message']}",
            extra={'context': error_info['context']}
        )
        self.metrics.increment('errors_total')

    def log_access(self, user_id: int, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование действия пользователя
        
        Args:
            user_id: ID пользователя
            action: Тип действия
            details: Дополнительные детали
        """
        log_data = {
            'user_id': user_id,
            'action': action,
            'timestamp': datetime.now().isoformat()
        }
        if details:
            log_data.update(details)
            
        self.logger.info(f"Access log: {log_data}")
        self.metrics.increment(f'access_{action}')

    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Отладочное логирование
        
        Args:
            message: Сообщение
            data: Дополнительные данные
        """
        log_data = {'message': message}
        if data:
            log_data.update(data)
            
        self.logger.debug(f"Debug log: {log_data}")

    def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Логирование метрик
        
        Args:
            metrics: Словарь с метриками
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }
        
        self.logger.info(f"Metrics log: {log_data}")
        
        # Обновляем метрики
        for name, value in metrics.items():
            if isinstance(value, (int, float)):
                self.metrics.gauge(name, value)

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение последних ошибок
        
        Args:
            limit: Максимальное количество ошибок
            
        Returns:
            Список последних ошибок
        """
        errors = []
        error_files = sorted(self.error_logs.glob("error_*.json"), reverse=True)
        
        for file in error_files[:limit]:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    errors.append(json.load(f))
            except Exception as e:
                self.log_error(e, {'file': str(file)})
                
        return errors

    def cleanup_old_logs(self, days: int = 30) -> None:
        """
        Очистка старых логов
        
        Args:
            days: Количество дней хранения
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_dir in [self.error_logs, self.access_logs, self.debug_logs, self.metrics_logs]:
            for file in log_dir.glob("*"):
                if file.stat().st_mtime < cutoff:
                    try:
                        file.unlink()
                    except Exception as e:
                        self.log_error(e, {'file': str(file)})

# Создаем глобальный экземпляр логгера
bot_logger = BotLogger() 