"""
Утилиты для валидации данных
"""

import re
from typing import Optional, Dict, Any, List, Union, Tuple, Set
from dataclasses import dataclass
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.db_manager import DatabaseManager
from .format_utils import MessageFormatter
from .coord_utils import CoordinateParser, Coordinates

@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    error_message: Optional[str] = None
    normalized_value: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None

class DataValidator:
    """Базовый класс для валидации данных"""
    
    def __init__(self):
        self.logger = LogManager().get_logger(__name__)
        self.metrics = MetricsManager()
        
    def validate(self, value: Any) -> ValidationResult:
        """
        Базовый метод валидации
        
        Args:
            value: Значение для валидации
            
        Returns:
            Результат валидации
        """
        raise NotImplementedError("Метод должен быть переопределен")

class SRIDValidator(DataValidator):
    """Валидатор SRID"""
    
    # Допустимые диапазоны SRID
    CUSTOM_RANGE = (100000, 199999)  # Пользовательские СК
    UTM_RANGE = (32601, 32660)       # UTM зоны
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        
    def validate(self, srid: Union[str, int]) -> ValidationResult:
        """
        Валидация SRID
        
        Args:
            srid: SRID для проверки
            
        Returns:
            Результат валидации
        """
        try:
            # Проверка формата
            if isinstance(srid, str):
                if not srid.isdigit():
                    return ValidationResult(
                        is_valid=False,
                        error_message="SRID должен быть числом"
                    )
                srid = int(srid)
            
            # Проверка диапазонов
            is_custom = self.CUSTOM_RANGE[0] <= srid <= self.CUSTOM_RANGE[1]
            is_utm = self.UTM_RANGE[0] <= srid <= self.UTM_RANGE[1]
            
            if not (is_custom or is_utm):
                return ValidationResult(
                    is_valid=False,
                    error_message="SRID вне допустимого диапазона"
                )
            
            # Проверка существования в БД
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS(SELECT 1 FROM spatial_ref_sys WHERE srid = %s)",
                    (srid,)
                )
                exists = cursor.fetchone()[0]
                
                if not exists:
                    return ValidationResult(
                        is_valid=False,
                        error_message="SRID не найден в базе данных"
                    )
            
            # Собираем метаданные
            metadata = {
                'is_custom': is_custom,
                'is_utm': is_utm,
                'source': 'custom' if is_custom else 'epsg'
            }
            
            return ValidationResult(
                is_valid=True,
                normalized_value=srid,
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации SRID: {e}")
            import asyncio
            asyncio.create_task(self.metrics.record_error('srid_validation', str(e)))
            return ValidationResult(
                is_valid=False,
                error_message=f"Ошибка валидации: {str(e)}"
            )

class NameValidator(DataValidator):
    """Валидатор названий"""
    
    # Конфигурация валидации
    MIN_LENGTH = 2
    MAX_LENGTH = 100
    ALLOWED_SPECIAL_CHARS = set('-_()[]., ')
    
    def validate(self, name: str) -> ValidationResult:
        """
        Валидация названия
        
        Args:
            name: Название для проверки
            
        Returns:
            Результат валидации
        """
        try:
            # Проверка длины
            if len(name) < self.MIN_LENGTH:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Название слишком короткое (минимум {self.MIN_LENGTH} символа)"
                )
                
            if len(name) > self.MAX_LENGTH:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Название слишком длинное (максимум {self.MAX_LENGTH} символов)"
                )
            
            # Проверка спецсимволов
            special_chars = set(c for c in name if not c.isalnum() and c not in self.ALLOWED_SPECIAL_CHARS)
            if special_chars:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Недопустимые символы: {', '.join(special_chars)}"
                )
            
            # Нормализация
            normalized = self._normalize_name(name)
            
            return ValidationResult(
                is_valid=True,
                normalized_value=normalized
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации названия: {e}")
            import asyncio
            asyncio.create_task(self.metrics.record_error('name_validation', str(e)))
            return ValidationResult(
                is_valid=False,
                error_message=f"Ошибка валидации: {str(e)}"
            )
    
    def _normalize_name(self, name: str) -> str:
        """Нормализация названия"""
        # Удаляем лишние пробелы
        normalized = ' '.join(name.split())
        # Заменяем множественные спецсимволы
        normalized = re.sub(r'[-_\s]+', ' ', normalized)
        return normalized.strip()

class CoordinateValidator(DataValidator):
    """Валидатор координат"""
    
    def __init__(self):
        super().__init__()
        self.coord_parser = CoordinateParser()
        
    def validate(self, coord_str: str) -> ValidationResult:
        """
        Валидация координат
        
        Args:
            coord_str: Строка с координатами
            
        Returns:
            Результат валидации
        """
        try:
            # Используем существующий парсер
            coords = self.coord_parser.parse(coord_str)
            
            return ValidationResult(
                is_valid=True,
                normalized_value=coords,
                metadata={
                    'format': coords.original_format,
                    'latitude': coords.latitude,
                    'longitude': coords.longitude
                }
            )
            
        except ValueError as e:
            return ValidationResult(
                is_valid=False,
                error_message=str(e)
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации координат: {e}")
            import asyncio
            asyncio.create_task(self.metrics.record_error('coordinate_validation', str(e)))
            return ValidationResult(
                is_valid=False,
                error_message=f"Ошибка валидации: {str(e)}"
            )

class ExportValidator(DataValidator):
    """Валидатор экспорта"""
    
    # Поддерживаемые форматы
    FORMATS = {
        'xml_Civil3D': {'extension': '.xml', 'requires_auth': False},
        'prj_GMv20': {'extension': '.prj', 'requires_auth': True},
        'prj_GMv25': {'extension': '.prj', 'requires_auth': True}
    }
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.srid_validator = SRIDValidator(db_manager)
    
    def validate(
        self, 
        srid: int, 
        format_type: str,
        user_id: Optional[int] = None
    ) -> ValidationResult:
        """
        Валидация экспорта
        
        Args:
            srid: SRID системы координат
            format_type: Тип формата экспорта
            user_id: ID пользователя (для проверки прав)
            
        Returns:
            Результат валидации
        """
        try:
            # Проверка формата
            if format_type not in self.FORMATS:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Неподдерживаемый формат: {format_type}"
                )
            
            format_info = self.FORMATS[format_type]
            
            # Проверка прав доступа
            if format_info['requires_auth'] and user_id is None:
                return ValidationResult(
                    is_valid=False,
                    error_message="Требуется авторизация для этого формата"
                )
            
            # Проверка SRID
            srid_result = self.srid_validator.validate(srid)
            if not srid_result.is_valid:
                return srid_result
            
            # Собираем метаданные
            metadata = {
                'requires_auth': format_info['requires_auth'],
                'user_id': user_id,
                'srid_info': srid_result.metadata
            }
            
            return ValidationResult(
                is_valid=True,
                normalized_value={
                    'srid': srid,
                    'format': format_type,
                    'extension': format_info['extension']
                },
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации экспорта: {e}")
            import asyncio
            asyncio.create_task(self.metrics.record_error('export_validation', str(e)))
            return ValidationResult(
                is_valid=False,
                error_message=f"Ошибка валидации: {str(e)}"
            )

class ValidationManager:
    """Менеджер валидации"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.formatter = MessageFormatter()
        self.logger = LogManager().get_logger(__name__)
        self.metrics = MetricsManager()
        
        # Инициализация валидаторов
        self.srid_validator = SRIDValidator(db_manager)
        self.name_validator = NameValidator()
        self.coord_validator = CoordinateValidator()
        self.export_validator = ExportValidator(db_manager)
    
    def validate_srid(self, srid: Union[str, int]) -> ValidationResult:
        """Валидация SRID"""
        return self.srid_validator.validate(srid)
    
    def validate_name(self, name: str) -> ValidationResult:
        """Валидация названия"""
        return self.name_validator.validate(name)
    
    def validate_coordinates(self, coord_str: str) -> ValidationResult:
        """Валидация координат"""
        return self.coord_validator.validate(coord_str)
    
    def validate_export(
        self, 
        srid: int,
        format_type: str,
        user_id: Optional[int] = None
    ) -> ValidationResult:
        """Валидация экспорта"""
        return self.export_validator.validate(srid, format_type, user_id)

    def validate_search_params(self, query: str, filters: Dict[str, bool]) -> bool:
        """
        Валидация параметров поиска
        
        Args:
            query: Поисковый запрос
            filters: Словарь фильтров
            
        Returns:
            True если параметры валидны, False иначе
        """
        try:
            # Проверяем запрос
            if not query or not isinstance(query, str):
                return False
                
            # Проверяем длину запроса
            if len(query.strip()) == 0 or len(query) > 100:
                return False
                
            # Проверяем допустимые символы в запросе
            allowed_pattern = r'^[a-zA-Z0-9а-яА-ЯёЁ\s\-_\.]+$'
            if not re.match(allowed_pattern, query):
                return False
                
            # Проверяем фильтры
            if not isinstance(filters, dict):
                return False
                
            # Проверяем значения фильтров
            for value in filters.values():
                if not isinstance(value, bool):
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации параметров поиска: {e}")
            import asyncio
            asyncio.create_task(self.metrics.record_error('search_params_validation', str(e)))
            return False

def validate_srid(srid: Union[int, str]) -> bool:
    """
    Валидация SRID
    
    Args:
        srid: SRID для проверки
        
    Returns:
        True если SRID валиден, False иначе
    """
    try:
        srid = int(srid)
        # Проверяем диапазон для UTM зон
        if 32601 <= srid <= 32660:
            return True
        # Проверяем диапазон для пользовательских СК
        if srid >= 100000:
            return True
        return False
    except (ValueError, TypeError):
        return False

def validate_search_query(query: str) -> bool:
    """
    Валидация поискового запроса
    
    Args:
        query: Поисковый запрос
        
    Returns:
        True если запрос валиден, False иначе
    """
    if not query or not isinstance(query, str):
        return False
        
    # Проверяем длину запроса
    if len(query.strip()) == 0 or len(query) > 100:
        return False
        
    # Проверяем допустимые символы
    allowed_pattern = r'^[a-zA-Z0-9а-яА-ЯёЁ\s\-_\.]+$'
    return bool(re.match(allowed_pattern, query))

def validate_export_format(format: str) -> bool:
    """
    Валидация формата экспорта
    
    Args:
        format: Формат для проверки
        
    Returns:
        True если формат валиден, False иначе
    """
    valid_formats = {'xml_Civil3D', 'prj_GMv20', 'prj_GMv25'}
    return format in valid_formats

def validate_user_access(user_id: int, authorized_users: Set[int]) -> bool:
    """
    Валидация доступа пользователя
    
    Args:
        user_id: ID пользователя
        authorized_users: Множество ID авторизованных пользователей
        
    Returns:
        True если пользователь имеет доступ, False иначе
    """
    return user_id in authorized_users 