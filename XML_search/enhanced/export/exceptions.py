"""
Исключения для модуля экспорта
"""

class ExportError(Exception):
    """Базовое исключение для ошибок экспорта"""
    pass

class ValidationError(ExportError):
    """Исключение для ошибок валидации данных"""
    pass

class TemplateError(ExportError):
    """Исключение для ошибок работы с шаблонами"""
    pass

class FormatError(ExportError):
    """Исключение для ошибок форматирования данных"""
    pass

class ConfigError(ExportError):
    """Исключение для ошибок конфигурации"""
    pass

class ConfigurationError(ExportError):
    """Исключение для ошибок конфигурации (алиас для обратной совместимости)"""
    pass

class ExporterNotFoundError(ExportError):
    """Ошибка отсутствия экспортера"""
    pass

class ExportTimeoutError(ExportError):
    """Ошибка таймаута при экспорте"""
    pass

class ExporterError(ExportError):
    """Исключение для ошибок в экспортере"""
    pass

class XMLProcessingError(ExportError):
    """Исключение для ошибок обработки XML"""
    pass 