"""
Состояния диалога бота
"""

from enum import IntEnum, auto

class States(IntEnum):
    """Состояния диалога бота"""
    
    # Состояния авторизации
    AUTH = auto()  # Ожидание ввода пароля
    
    # Состояния меню
    MAIN_MENU = auto()  # Главное меню
    
    # Состояния поиска
    WAITING_COORDINATES = auto()  # Ожидание ввода координат
    WAITING_SEARCH = auto()  # Ожидание поискового запроса
    
    # Состояния экспорта
    EXPORT_SELECTION = auto()  # Выбор формата экспорта
    
    # Состояния ошибок
    ERROR = auto()  # Состояние ошибки

    @classmethod
    def get_all_states(cls) -> list:
        """Получение списка всех состояний"""
        return [
            cls.AUTH,
            cls.MAIN_MENU,
            cls.WAITING_COORDINATES,
            cls.WAITING_SEARCH,
            cls.EXPORT_SELECTION,
            cls.ERROR
        ] 