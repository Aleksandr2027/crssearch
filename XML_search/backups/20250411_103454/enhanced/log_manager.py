import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime, timedelta
from typing import Optional
import glob
from .config_enhanced import enhanced_config

class LogManager:
    """Менеджер логирования с ротацией и очисткой"""
    
    def __init__(self, name: str = "enhanced_bot"):
        self.config = enhanced_config.logging
        self.logger = self._setup_logger(name)
        self._last_cleanup = datetime.now()
        self._loggers = {}
    
    def _setup_logger(self, name: str) -> logging.Logger:
        """Настройка логгера с ротацией файлов"""
        logger = logging.getLogger(name)
        logger.setLevel(self.config.log_level)
        
        # Форматтер для логов
        formatter = logging.Formatter(
            fmt=self.config.log_format,
            datefmt=self.config.date_format
        )
        
        # Создаем директорию для логов если её нет
        os.makedirs(self.config.log_dir, exist_ok=True)
        
        # Файловый обработчик с ротацией
        log_file = os.path.join(
            self.config.log_dir,
            self.config.file_name_template.format(
                date=datetime.now().strftime("%Y%m%d")
            )
        )
        
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _should_cleanup(self) -> bool:
        """Проверка необходимости очистки старых логов"""
        time_since_cleanup = datetime.now() - self._last_cleanup
        return time_since_cleanup.days >= 1
    
    def cleanup_old_logs(self, days: Optional[int] = None) -> None:
        """Очистка старых лог-файлов"""
        if days is None:
            days = self.config.clean_interval
            
        cutoff_date = datetime.now() - timedelta(days=days)
        log_pattern = os.path.join(
            self.config.log_dir,
            self.config.file_name_template.format(date="*")
        )
        
        for log_file in glob.glob(log_pattern):
            try:
                file_date_str = os.path.basename(log_file).split("_")[1].split(".")[0]
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    os.remove(log_file)
                    self.logger.info(f"Удален старый лог-файл: {log_file}")
            except (ValueError, IndexError) as e:
                self.logger.warning(f"Ошибка при обработке файла {log_file}: {e}")
                continue
        
        self._last_cleanup = datetime.now()
    
    def log(self, level: int, message: str, *args, **kwargs) -> None:
        """Логирование с автоматической очисткой старых логов"""
        if self._should_cleanup():
            self.cleanup_old_logs()
        self.logger.log(level, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Логирование с уровнем DEBUG"""
        self.log(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs) -> None:
        """Логирование с уровнем INFO"""
        self.log(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs) -> None:
        """Логирование с уровнем WARNING"""
        self.log(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs) -> None:
        """Логирование с уровнем ERROR"""
        self.log(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs) -> None:
        """Логирование с уровнем CRITICAL"""
        self.log(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, exc_info=True, **kwargs) -> None:
        """Логирование исключений"""
        self.log(logging.ERROR, message, *args, exc_info=exc_info, **kwargs)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Получение логгера по имени"""
        if name not in self._loggers:
            self._loggers[name] = self._setup_logger(name)
        return self._loggers[name] 