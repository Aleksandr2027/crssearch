from dataclasses import dataclass
from typing import Dict, Any, Optional, Type, List
import json
import logging
from pathlib import Path
import os

from XML_search.config import XMLConfig
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.export.exceptions import ConfigurationError
from XML_search.enhanced.export.exporters.base import BaseExporter

logger = logging.getLogger(__name__)

@dataclass
class ExporterConfig:
    """Конфигурация отдельного экспортера"""
    enabled: bool = True
    display_name: str = ""
    description: str = ""
    handler: str = ""
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 час
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class ExportConfig:
    """Конфигурация экспорта"""
    # Поддерживаемые форматы экспорта
    supported_formats: List[str] = ('json', 'xml', 'csv')
    
    # Директории для экспорта
    output_dir: str = 'output'
    temp_dir: str = 'temp'
    
    # Максимальный размер файла (10MB)
    max_file_size: int = 10 * 1024 * 1024
    
    # Настройки форматирования
    json_indent: int = 2
    csv_delimiter: str = ','
    xml_encoding: str = 'utf-8'
    
    # Настройки кэширования
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 час
    
    def __post_init__(self):
        """Инициализация после создания объекта"""
        # Создаем необходимые директории
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Преобразуем пути в Path объекты
        self.output_dir = Path(self.output_dir)
        self.temp_dir = Path(self.temp_dir)

class ExportConfigManager:
    """Класс для работы с конфигурацией экспорта"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации экспорта
        
        Args:
            config_path: Путь к файлу конфигурации (опционально)
        """
        self.logger = logging.getLogger(__name__)
        
        # Определяем путь к конфигурации
        if config_path is None:
            base_dir = Path(__file__).parent.parent.parent
            self.config_path = str(base_dir / 'config' / 'export_config.json')
        else:
            self.config_path = config_path
            
        # Загружаем конфигурацию
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Загрузка конфигурации из файла
        
        Returns:
            Словарь с конфигурацией
            
        Raises:
            ConfigurationError: При ошибке загрузки конфигурации
        """
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"Файл конфигурации {self.config_path} не найден")
                return {"formats": {}}
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.info(f"Конфигурация успешно загружена из {self.config_path}")
                return config
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON: {e}")
            raise ConfigurationError(f"Ошибка декодирования JSON: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфигурации: {e}")
            raise ConfigurationError(f"Ошибка загрузки конфигурации: {e}")
            
    def get_formats(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение списка доступных форматов
        
        Returns:
            Словарь с конфигурацией форматов
        """
        return self.config.get('formats', {})
        
    def get_format_config(self, format_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение конфигурации формата
        
        Args:
            format_name: Название формата
            
        Returns:
            Конфигурация формата или None, если формат не найден
        """
        return self.get_formats().get(format_name)
        
    def get_exporter_class(self, format_name: str) -> Optional[Type[BaseExporter]]:
        """
        Получение класса экспортера для формата
        
        Args:
            format_name: Название формата
            
        Returns:
            Класс экспортера или None, если формат не поддерживается
        """
        format_config = self.get_format_config(format_name)
        if not format_config or not format_config.get('enabled', True):
            return None
            
        # Определяем класс экспортера на основе формата
        exporter_map = {
            'xml_Civil3D': 'XML_search.enhanced.export.exporters.civil3d.Civil3DExporter',
            'prj_GMv20': 'XML_search.enhanced.export.exporters.gmv20.GMv20Exporter',
            'prj_GMv25': 'XML_search.enhanced.export.exporters.gmv25.GMv25Exporter'
        }
        
        exporter_path = exporter_map.get(format_name)
        if not exporter_path:
            return None
            
        try:
            # Импортируем класс экспортера
            module_path, class_name = exporter_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            exporter_class = getattr(module, class_name)
            
            # Проверяем, что класс является подклассом BaseExporter
            if not issubclass(exporter_class, BaseExporter):
                self.logger.error(f"Класс {exporter_path} не является подклассом BaseExporter")
                return None
                
            return exporter_class
            
        except ImportError as e:
            self.logger.error(f"Ошибка импорта экспортера {exporter_path}: {e}")
            return None
        except AttributeError as e:
            self.logger.error(f"Класс {exporter_path} не найден: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка получения класса экспортера: {e}")
            return None
            
    def validate_format(self, format_name: str) -> bool:
        """
        Проверка валидности формата
        
        Args:
            format_name: Название формата
            
        Returns:
            True если формат валиден, False в противном случае
        """
        format_config = self.get_format_config(format_name)
        if not format_config:
            return False
            
        required_fields = ['display_name', 'description', 'extension', 'enabled']
        return all(field in format_config for field in required_fields)
        
    def get_format_info(self, format_name: str) -> Dict[str, str]:
        """
        Получение информации о формате
        
        Args:
            format_name: Название формата
            
        Returns:
            Словарь с информацией о формате
        """
        format_config = self.get_format_config(format_name)
        if not format_config:
            return {}
            
        return {
            'display_name': format_config.get('display_name', ''),
            'description': format_config.get('description', ''),
            'extension': format_config.get('extension', '')
        }
        
    def get_validation_config(self, format_name: str) -> Dict[str, Any]:
        """
        Получение конфигурации валидации для формата
        
        Args:
            format_name: Название формата
            
        Returns:
            Словарь с конфигурацией валидации
        """
        format_config = self.get_format_config(format_name)
        if not format_config:
            return {}
            
        return format_config.get('validation', {})
        
    def get_output_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации вывода
        
        Returns:
            Словарь с конфигурацией вывода
        """
        return self.config.get('output', {})
        
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации логирования
        
        Returns:
            Словарь с конфигурацией логирования
        """
        return self.config.get('logging', {})
        
    def get_error_handling_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации обработки ошибок
        
        Returns:
            Словарь с конфигурацией обработки ошибок
        """
        return self.config.get('error_handling', {})

# Создаем глобальный экземпляр конфигурации
export_config = ExportConfigManager()

__all__ = ['ExportConfig', 'ExporterConfig', 'export_config']
