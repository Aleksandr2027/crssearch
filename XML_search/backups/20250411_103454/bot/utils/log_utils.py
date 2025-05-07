import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
from logging.handlers import RotatingFileHandler
import traceback
import sys
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector

class BotLogger:
    """Расширенный логгер для бота с поддержкой структурированного логирования"""

    def __init__(self, name: str = "bot"):
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
        self.logger = self._setup_main_logger(name)
        self.error_logger = self._setup_error_logger()
        self.access_logger = self._setup_access_logger()
        self.debug_logger = self._setup_debug_logger()
        self.metrics_logger = self._setup_metrics_logger()

        # Метрики
        self.metrics = MetricsCollector()

    def _setup_main_logger(self, name: str) -> logging.Logger:
        """Настройка основного логгера"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # Форматтер для основного лога
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Файловый обработчик
        file_handler = RotatingFileHandler(
            self.logs_dir / "bot.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

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
        Логирование ошибки с контекстом
        
        Args:
            error: Исключение
            context: Контекст ошибки
        """
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'stack_trace': ''.join(traceback.format_tb(error.__traceback__)),
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }

        # Логируем в файл ошибок
        self.error_logger.error(
            f"Error: {error_info['type']} - {error_info['message']}",
            extra={'stack_trace': error_info['stack_trace']}
        )

        # Сохраняем детальную информацию в JSON
        error_file = self.error_logs / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_info, f, ensure_ascii=False, indent=2)

        # Обновляем метрики
        self.metrics.increment('errors_total')
        self.metrics.increment(f'error_{error_info["type"]}')

    def log_access(self, user_id: int, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Логирование действий пользователя
        
        Args:
            user_id: ID пользователя
            action: Действие
            details: Детали действия
        """
        access_info = {
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }

        self.access_logger.info(json.dumps(access_info, ensure_ascii=False))
        self.metrics.increment(f'access_{action}')

    def log_debug(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Отладочное логирование
        
        Args:
            message: Сообщение
            data: Дополнительные данные
        """
        if data:
            message = f"{message} - {json.dumps(data, ensure_ascii=False)}"
        self.debug_logger.debug(message)

    def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Логирование метрик
        
        Args:
            metrics: Словарь с метриками
        """
        self.metrics_logger.info(json.dumps(metrics, ensure_ascii=False))

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