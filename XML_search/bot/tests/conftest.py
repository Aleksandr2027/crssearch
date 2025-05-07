"""
Конфигурация для тестов pytest
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.config import DBConfig

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Конфигурация pytest с настройками asyncio"""
    config.option.asyncio_mode = "strict"
    config.option.asyncio_default_fixture_loop_scope = "function"

@pytest.fixture
def temp_config_dir(tmp_path):
    """Создание временной директории для конфигурации"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir

@pytest.fixture
def temp_config_file():
    """Создание временного конфигурационного файла"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / 'config'
        config_dir.mkdir()
        config_file = config_dir / 'export_config.json'
        
        config_data = {
            "version": "1.0.0",
            "formats": {
                "xml_Civil3D": {
                    "display_name": "Civil3D XML",
                    "description": "Тестовый экспортер",
                    "extension": ".xml",
                    "temp_solution": {
                        "enabled": True,
                        "message": "✅ Тестовый экспорт XML (SRID: {srid})"
                    }
                }
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
            
        yield config_file

@pytest.fixture
def mock_db_manager():
    """Мок для DatabaseManager"""
    db_manager = Mock(spec=DatabaseManager)
    cursor_mock = MagicMock()
    db_manager.safe_cursor.return_value.__enter__.return_value = cursor_mock
    return db_manager

@pytest.fixture
def mock_metrics():
    """Мок для MetricsCollector"""
    return {
        'increment': Mock(),
        'timing': Mock()
    }

@pytest.fixture
def mock_logger():
    """Мок для Logger"""
    return Mock()

@pytest.fixture
def temp_export_dir(tmp_path):
    """Создание временной директории для экспорта"""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir

@pytest.fixture
def cleanup_temp_files():
    """Очистка временных файлов после тестов"""
    yield
    # Очистка временных файлов
    temp_dir = tempfile.gettempdir()
    for item in os.listdir(temp_dir):
        if item.startswith('test_export_'):
            os.remove(os.path.join(temp_dir, item)) 