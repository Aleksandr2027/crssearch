from typing import Optional, Dict, Any
import logging
from datetime import datetime
import os
from XML_search.config import XMLConfig

class GISGeobotError(Exception):
    """Базовый класс для ошибок бота"""
    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

class DatabaseError(GISGeobotError):
    """Базовое исключение для ошибок базы данных"""
    pass

class ConnectionError(DatabaseError):
    """Ошибка подключения к базе данных"""
    pass

class QueryError(DatabaseError):
    """Ошибка выполнения запроса к базе данных"""
    pass

class XMLProcessingError(GISGeobotError):
    """Ошибки при обработке XML"""
    pass

class ValidationError(GISGeobotError):
    """Ошибки валидации данных"""
    pass

class ExportError(GISGeobotError):
    """Ошибки при экспорте данных"""
    pass

class ConfigError(GISGeobotError):
    """Ошибки конфигурации"""
    pass

class AuthError(GISGeobotError):
    """Ошибки авторизации"""
    pass

class NotificationManager:
    def __init__(self):
        self.config = XMLConfig()
        self._setup_logging()
        
    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config.LOG_LEVEL)
        
        # Создаем директорию для логов, если она не существует
        os.makedirs(self.config.LOG_DIR, exist_ok=True)
        
        # Добавляем файловый обработчик
        log_file = os.path.join(
            self.config.LOG_DIR,
            f"gisgeobot_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(file_handler)
        
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Логирование ошибки"""
        error_info = {
            'type': type(error).__name__,
            'message': str(error),
            'context': context or {}
        }
        
        self.logger.error(
            f"Ошибка: {error_info['type']} - {error_info['message']}",
            extra={'context': error_info['context']}
        )
        
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Логирование предупреждения"""
        self.logger.warning(
            message,
            extra={'context': context or {}}
        )
        
    def log_info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Логирование информационного сообщения"""
        self.logger.info(
            message,
            extra={'context': context or {}}
        )
        
    def format_error_message(self, error: Exception) -> str:
        """Форматирование сообщения об ошибке для пользователя"""
        if isinstance(error, DatabaseError):
            return "Произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."
        elif isinstance(error, XMLProcessingError):
            return "Ошибка при обработке XML файла. Проверьте данные и попробуйте снова."
        elif isinstance(error, ValidationError):
            return f"Ошибка валидации: {str(error)}"
        else:
            return "Произошла непредвиденная ошибка. Пожалуйста, обратитесь к администратору."
            
    def cleanup_old_logs(self, days_to_keep: int = 7):
        """Очистка старых лог-файлов"""
        try:
            current_time = datetime.now()
            for filename in os.listdir(self.config.LOG_DIR):
                if filename.startswith('gisgeobot_') and filename.endswith('.log'):
                    file_path = os.path.join(self.config.LOG_DIR, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if (current_time - file_time).days > days_to_keep:
                        os.remove(file_path)
                        self.logger.info(f"Удален старый лог-файл: {filename}")
                        
        except Exception as e:
            self.logger.error(f"Ошибка при очистке лог-файлов: {str(e)}") 