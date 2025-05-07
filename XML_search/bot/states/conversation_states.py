"""
Состояния для ConversationHandler
"""

from enum import Enum, auto

class States(Enum):
    """Состояния диалога с ботом"""
    # Базовые состояния
    START = auto()  # Начальное состояние
    AUTH = auto()  # Авторизация
    MAIN_MENU = auto()  # Главное меню
    ERROR = auto()  # Общая ошибка
    UNKNOWN = auto()  # Неизвестное состояние
    
    # Состояния поиска
    SEARCH_INPUT = auto()  # Ввод поискового запроса
    SEARCH_RESULTS = auto()  # Результаты поиска
    SEARCH_ERROR = auto()  # Ошибка поиска
    
    # Состояния координат
    COORD_INPUT = auto()  # Ввод координат
    COORD_RESULTS = auto()  # Результаты поиска по координатам
    COORD_ERROR = auto()  # Ошибка обработки координат
    
    # Состояния экспорта
    WAITING_EXPORT = auto()  # Ожидание экспорта
    EXPORT_FORMAT = auto()  # Выбор формата экспорта
    EXPORT_PARAMS = auto()  # Параметры экспорта
    EXPORT_COMPLETE = auto()  # Экспорт завершен
    EXPORT_ERROR = auto()  # Ошибка экспорта
    EXPORT_VALIDATION_ERROR = auto()  # Ошибка валидации при экспорте

class StateData:
    """Данные состояния диалога"""
    def __init__(self):
        self.previous_state = None
        self.current_state = States.START
        self.context = {}
        
    def update_state(self, new_state: States) -> None:
        """
        Обновление состояния
        
        Args:
            new_state: Новое состояние
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        
    def add_context(self, key: str, value: any) -> None:
        """
        Добавление данных в контекст
        
        Args:
            key: Ключ
            value: Значение
        """
        self.context[key] = value
        
    def get_context(self, key: str, default: any = None) -> any:
        """
        Получение данных из контекста
        
        Args:
            key: Ключ
            default: Значение по умолчанию
            
        Returns:
            Значение из контекста
        """
        return self.context.get(key, default)
        
    def clear_context(self) -> None:
        """Очистка контекста"""
        self.context.clear()
        
    def rollback(self) -> None:
        """Возврат к предыдущему состоянию"""
        if self.previous_state:
            self.current_state = self.previous_state
            self.previous_state = None

    @classmethod
    def get_all_states(cls) -> list:
        """
        Получение списка всех состояний
        
        Returns:
            Список всех состояний
        """
        return [state for state in States] 