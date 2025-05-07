"""
Исключения для обработчиков бота
"""

class HandlerError(Exception):
    """Базовый класс для ошибок обработчиков"""
    pass

class ExportError(HandlerError):
    """Ошибка при экспорте"""
    pass

class ValidationError(HandlerError):
    """Ошибка валидации"""
    pass

class ExporterError(HandlerError):
    """Ошибка экспортера"""
    pass 