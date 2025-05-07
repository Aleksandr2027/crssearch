"""
Базовые классы для клавиатур
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from telegram import InlineKeyboardMarkup
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager

@dataclass
class KeyboardResult:
    """Результат построения клавиатуры"""
    keyboard: InlineKeyboardMarkup
    metadata: Dict[str, Any]

class BaseKeyboard:
    """Базовый класс для клавиатур"""
    
    def __init__(self, keyboard_type: str):
        """
        Инициализация базовой клавиатуры
        
        Args:
            keyboard_type: Тип клавиатуры
        """
        self.keyboard_type = keyboard_type
        self.metrics = MetricsManager()
        self.logger = LogManager().get_logger(__name__)
        
    def build(self, **kwargs) -> KeyboardResult:
        """
        Построение клавиатуры
        
        Args:
            **kwargs: Параметры для построения
            
        Returns:
            Результат построения клавиатуры
            
        Raises:
            NotImplementedError: Если метод не переопределен
        """
        raise NotImplementedError("Метод build должен быть переопределен")
        
    def validate_callback_data(self, callback_data: str) -> bool:
        """
        Валидация callback_data
        
        Args:
            callback_data: Данные для проверки
            
        Returns:
            True если данные валидны
            
        Raises:
            NotImplementedError: Если метод не переопределен
        """
        raise NotImplementedError("Метод validate_callback_data должен быть переопределен")
        
    def _validate_buttons(self, buttons: List[List[Dict[str, Any]]]) -> bool:
        """
        Валидация кнопок клавиатуры
        
        Args:
            buttons: Список кнопок для проверки
            
        Returns:
            True если все кнопки валидны
        """
        try:
            # Проверяем наличие обязательных полей
            for row in buttons:
                for button in row:
                    if not isinstance(button, dict):
                        return False
                    if 'text' not in button:
                        return False
                    if 'callback_data' in button and len(button['callback_data']) > 64:
                        return False
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации кнопок: {e}")
            return False
            
    def _track_build(self, keyboard_type: str, success: bool = True) -> None:
        """
        Отслеживание метрик построения клавиатуры
        
        Args:
            keyboard_type: Тип клавиатуры
            success: Успешность построения
        """
        try:
            metric_name = f"keyboard_build.{keyboard_type}"
            if success:
                self.metrics.increment(f"{metric_name}.success")
            else:
                self.metrics.increment(f"{metric_name}.error")
                
        except Exception as e:
            self.logger.error(f"Ошибка отслеживания метрик: {e}")
            
    def _sanitize_text(self, text: str, max_length: int = 64) -> str:
        """
        Санитизация текста кнопки
        
        Args:
            text: Текст для очистки
            max_length: Максимальная длина
            
        Returns:
            Очищенный текст
        """
        try:
            # Удаляем спецсимволы
            sanitized = ''.join(c for c in text if c.isprintable())
            # Обрезаем до максимальной длины
            return sanitized[:max_length]
            
        except Exception as e:
            self.logger.error(f"Ошибка санитизации текста: {e}")
            return text[:max_length]  # Возвращаем обрезанный текст в случае ошибки
            
    def _get_metadata(self) -> Dict[str, Any]:
        """
        Получение метаданных клавиатуры
        
        Returns:
            Словарь с метаданными
        """
        return {
            'type': self.keyboard_type,
            'timestamp': self.metrics.get_current_timestamp()
        } 