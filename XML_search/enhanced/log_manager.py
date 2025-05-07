"""
Менеджер логирования
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from .exceptions import LoggingError
from XML_search.config import Config

class LogManager:
    """Менеджер логирования"""
    
    def __init__(self):
        """Инициализация менеджера логирования"""
        self.log_dir = Config.LOG_DIR
        self.log_level = getattr(logging, Config.LOG_LEVEL.upper())
        self.log_format = Config.LOG_FORMAT
        self.loggers = {}
        self.logger = logging.getLogger(__name__)
        
    def setup(self) -> None:
        """Настройка логирования"""
        try:
            # Создаем директорию для логов если её нет
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Настраиваем корневой логгер
            root_logger = logging.getLogger()
            root_logger.setLevel(self.log_level)
            
            # Добавляем обработчик для вывода в консоль
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(self.log_format))
            root_logger.addHandler(console_handler)
            
            # Добавляем обработчик для записи в файл
            file_handler = logging.handlers.RotatingFileHandler(
                filename=os.path.join(self.log_dir, 'app.log'),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(self.log_format))
            root_logger.addHandler(file_handler)
            
            self.logger.info("Логирование успешно настроено")
            
        except Exception as e:
            raise LoggingError(f"Ошибка настройки логирования: {str(e)}")
            
    def get_logger(self, name: str) -> logging.Logger:
        """
        Получение логгера по имени
        
        Args:
            name: Имя логгера
            
        Returns:
            logging.Logger: Логгер
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            logger.setLevel(self.log_level)
            self.loggers[name] = logger
            
        return self.loggers[name]
        
    def set_level(self, level: str) -> None:
        """
        Установка уровня логирования
        
        Args:
            level: Уровень логирования
        """
        try:
            log_level = getattr(logging, level.upper())
            self.log_level = log_level
            
            # Обновляем уровень для всех логгеров
            for logger in self.loggers.values():
                logger.setLevel(log_level)
                
        except AttributeError:
            raise LoggingError(f"Неверный уровень логирования: {level}")
            
    def add_file_handler(self, name: str, filename: str) -> None:
        """
        Добавление обработчика для записи в файл
        
        Args:
            name: Имя логгера
            filename: Имя файла
        """
        try:
            logger = self.get_logger(name)
            
            # Создаем обработчик
            handler = logging.handlers.RotatingFileHandler(
                filename=os.path.join(self.log_dir, filename),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding='utf-8'
            )
            handler.setFormatter(logging.Formatter(self.log_format))
            
            # Добавляем обработчик
            logger.addHandler(handler)
            
        except Exception as e:
            raise LoggingError(f"Ошибка добавления обработчика: {str(e)}")
            
    def remove_handlers(self, name: str) -> None:
        """
        Удаление всех обработчиков логгера
        
        Args:
            name: Имя логгера
        """
        logger = self.get_logger(name)
        
        while logger.handlers:
            handler = logger.handlers[0]
            handler.close()
            logger.removeHandler(handler)

    def setup_logging(
        self,
        level: str = "INFO",
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_file: Optional[str] = None
    ) -> None:
        """
        Настройка логирования
        
        Args:
            level: Уровень логирования
            format: Формат сообщений
            log_file: Путь к файлу лога
        """
        try:
            # Создаем директорию для логов если её нет
            if log_file:
                log_dir = Path(log_file).parent
                log_dir.mkdir(parents=True, exist_ok=True)
                
            # Настраиваем корневой логгер
            root_logger = logging.getLogger()
            root_logger.setLevel(level)
            
            # Создаем форматтер
            formatter = logging.Formatter(format)
            
            # Добавляем обработчик для вывода в консоль
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            
            # Добавляем обработчик для записи в файл если указан
            if log_file:
                file_handler = logging.handlers.RotatingFileHandler(
                    filename=log_file,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5,
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                
            self.logger.info(f"Логирование настроено. Уровень: {level}")
            
        except Exception as e:
            raise LoggingError(f"Ошибка настройки логирования: {str(e)}") 