from dataclasses import dataclass
from typing import Dict, Any, Optional
import json
import logging
from pathlib import Path
from ...config import XMLConfig

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
    exporters: Dict[str, ExporterConfig] = None
    cache_dir: str = "cache/exports"
    output_dir: str = "output/exports"
    temp_dir: str = "temp/exports"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    def __post_init__(self):
        if self.exporters is None:
            self.exporters = {
                "xml_Civil3D": ExporterConfig(
                    enabled=True,
                    display_name="XML для Civil3D",
                    description="Экспорт в формат XML для AutoCAD Civil3D",
                    handler="civil3d_exporter"
                ),
                "prj_GMv20": ExporterConfig(
                    enabled=True,
                    display_name="PRJ для GMv20",
                    description="Экспорт в формат PRJ для GlobalMapper v20",
                    handler="gmv20_exporter"
                ),
                "prj_GMv25": ExporterConfig(
                    enabled=True,
                    display_name="PRJ для GMv25",
                    description="Экспорт в формат PRJ для GlobalMapper v25",
                    handler="gmv25_exporter"
                )
            }
        
        # Создаем необходимые директории
        for dir_path in [self.cache_dir, self.output_dir, self.temp_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_from_file(cls, config_file: str = "config/export_config.json") -> 'ExportConfig':
        """Загрузка конфигурации из файла"""
        try:
            if not Path(config_file).exists():
                logger.warning(f"Файл конфигурации {config_file} не существует, создание с настройками по умолчанию...")
                config = cls()
                cls._save_config(config_file, config)
                return config

            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            exporters = {}
            for name, exp_data in config_data.get('exporters', {}).items():
                exporters[name] = ExporterConfig(**exp_data)

            return cls(
                exporters=exporters,
                cache_dir=config_data.get('cache_dir', "cache/exports"),
                output_dir=config_data.get('output_dir', "output/exports"),
                temp_dir=config_data.get('temp_dir', "temp/exports"),
                max_file_size=config_data.get('max_file_size', 10 * 1024 * 1024)
            )

        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации экспорта: {e}")
            logger.warning("Использование конфигурации по умолчанию")
            return cls()

    @classmethod
    def _save_config(cls, config_file: str, config: 'ExportConfig') -> None:
        """Сохранение конфигурации в файл"""
        try:
            config_data = {
                'exporters': {
                    name: {
                        'enabled': exp.enabled,
                        'display_name': exp.display_name,
                        'description': exp.description,
                        'handler': exp.handler,
                        'cache_enabled': exp.cache_enabled,
                        'cache_ttl': exp.cache_ttl,
                        'max_retries': exp.max_retries,
                        'retry_delay': exp.retry_delay
                    }
                    for name, exp in config.exporters.items()
                },
                'cache_dir': config.cache_dir,
                'output_dir': config.output_dir,
                'temp_dir': config.temp_dir,
                'max_file_size': config.max_file_size
            }

            Path(config_file).parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации экспорта: {e}")

# Создаем глобальный экземпляр конфигурации
export_config = ExportConfig.load_from_file()

__all__ = ['ExportConfig', 'ExporterConfig', 'export_config']
