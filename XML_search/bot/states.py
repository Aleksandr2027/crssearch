"""
Состояния диалога с ботом
"""

from enum import Enum, auto

class States(Enum):
    """Состояния диалога бота"""
    
    # ===== Начальные состояния =====
    START = auto()              # Начальное состояние
    AUTH = auto()               # Авторизация
    MAIN_MENU = auto()          # Главное меню
    
    # ===== Состояния поиска =====
    SEARCH_WAITING = auto()     # Ожидание ввода поискового запроса
    SEARCH_INPUT = auto()       # Ввод поискового запроса
    SEARCH_PROCESSING = auto()  # Обработка поискового запроса
    SEARCH_RESULTS = auto()     # Отображение результатов поиска
    SEARCH_ERROR = auto()       # Ошибка при поиске
    
    # ===== Состояния координат =====
    COORD_WAITING = auto()      # Ожидание ввода координат
    COORD_PROCESSING = auto()   # Обработка координат
    COORD_RESULTS = auto()      # Отображение результатов обработки
    COORD_ERROR = auto()        # Ошибка при обработке координат
    
    # ===== Состояния экспорта =====
    WAITING_EXPORT = auto()     # Ожидание выбора данных для экспорта
    EXPORT_FORMAT = auto()      # Выбор формата экспорта
    EXPORT_PARAMS = auto()      # Ввод параметров экспорта
    EXPORT_COMPLETE = auto()    # Экспорт завершен
    EXPORT_ERROR = auto()       # Ошибка при экспорте
    EXPORT_VALIDATION_ERROR = auto()  # Ошибка валидации параметров
    
    # ===== Состояния отмены =====
    CANCEL = auto()             # Отмена операции
    
    # ===== Помощь и настройки =====
    HELP = auto()               # Отображение справки
    SETTINGS = auto()           # Настройки бота
    
    # ===== Общие состояния =====
    ERROR = auto()              # Общая ошибка
    UNKNOWN = auto()            # Неизвестное состояние

    # ===== Новые состояния =====
    IDLE = auto()  # Ожидание команды
    WAITING_AUTH = auto()  # Ожидание авторизации
    AUTHENTICATED = auto()  # Пользователь авторизован
    
    # Состояния поиска
    SEARCH_MENU = auto()  # Меню поиска
    WAITING_COORDS = auto()  # Ожидание ввода координат
    WAITING_DESCRIPTION = auto()  # Ожидание ввода описания
    
    # Состояния экспорта
    EXPORT_MENU = auto()  # Меню экспорта
    WAITING_EXPORT_FORMAT = auto()  # Ожидание выбора формата экспорта

class StateData:
    """Класс для хранения данных состояния"""
    def __init__(self, state: States, context: dict = None):
        self.state = state
        self.context = context or {}
        
    def update_context(self, **kwargs):
        """Обновление контекста состояния"""
        self.context.update(kwargs)
        
    def clear_context(self):
        """Очистка контекста состояния"""
        self.context.clear()
        
    def get_context_value(self, key: str, default=None):
        """Получение значения из контекста"""
        return self.context.get(key, default)
        
    def set_context_value(self, key: str, value):
        """Установка значения в контекст"""
        self.context[key] = value 