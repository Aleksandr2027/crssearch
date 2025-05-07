"""Тесты для конфигурации экспорта"""

import pytest
import os
import json
from XML_search.enhanced.export.export_config import ExportConfig
from XML_search.enhanced.export.exceptions import ConfigurationError

class TestExportConfig:
    @pytest.fixture
    def setup(self, tmp_path):
        """Подготовка тестового окружения"""
        # Создаем временный файл конфигурации
        config_file = tmp_path / "export_config.json"
        test_config = {
            "version": "1.0.0",
            "temp_solution": {
                "enabled": True,
                "log_level": "INFO",
                "metrics_enabled": True
            },
            "formats": {
                "xml_Civil3D": {
                    "display_name": "Civil3D XML",
                    "description": "Экспорт в формат XML для Civil3D",
                    "extension": ".xml",
                    "enabled": True,
                    "temp_solution": {
                        "enabled": True,
                        "message": "✅ Тестовый экспорт XML (SRID: {srid})",
                        "error_message": "❌ Тестовая ошибка XML (SRID: {srid}): {error}"
                    }
                }
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
            
        return config_file
        
    def test_load_config(self, setup):
        """Тест загрузки конфигурации"""
        config = ExportConfig(str(setup))
        assert config.config["version"] == "1.0.0"
        assert config.config["temp_solution"]["enabled"] is True
        assert "xml_Civil3D" in config.config["formats"]
        
    def test_get_format_config(self, setup):
        """Тест получения конфигурации формата"""
        config = ExportConfig(str(setup))
        format_config = config.get_format_config("xml_Civil3D")
        assert format_config["display_name"] == "Civil3D XML"
        assert format_config["extension"] == ".xml"
        
    def test_temp_solution_enabled(self, setup):
        """Тест проверки включения временного решения"""
        config = ExportConfig(str(setup))
        assert config.is_temp_solution_enabled("xml_Civil3D") is True
        
    def test_get_temp_message(self, setup):
        """Тест получения временного сообщения"""
        config = ExportConfig(str(setup))
        # Тест успешного сообщения
        success_msg = config.get_temp_message("xml_Civil3D", 100000)
        assert "✅" in success_msg
        assert "100000" in success_msg
        
        # Тест сообщения об ошибке
        error_msg = config.get_temp_message("xml_Civil3D", 100000, "Test error")
        assert "❌" in error_msg
        assert "100000" in error_msg
        assert "Test error" in error_msg
        
    def test_invalid_config_file(self, tmp_path):
        """Тест обработки невалидного файла конфигурации"""
        config_file = tmp_path / "invalid_config.json"
        with open(config_file, 'w') as f:
            f.write("invalid json")
            
        with pytest.raises(ConfigurationError):
            ExportConfig(str(config_file))
            
    def test_missing_config_file(self, tmp_path):
        """Тест обработки отсутствующего файла конфигурации"""
        config_file = tmp_path / "missing_config.json"
        config = ExportConfig(str(config_file))
        
        # Должна быть загружена конфигурация по умолчанию
        assert config.config["version"] == "1.0.0"
        assert config.config["temp_solution"]["enabled"] is True
        assert isinstance(config.config["formats"], dict)
        
    def test_get_metrics_config(self, setup):
        """Тест получения конфигурации метрик"""
        config = ExportConfig(str(setup))
        metrics_config = config.get_metrics_config()
        assert isinstance(metrics_config, dict)
        
    def test_get_logging_config(self, setup):
        """Тест получения конфигурации логирования"""
        config = ExportConfig(str(setup))
        logging_config = config.get_logging_config()
        assert isinstance(logging_config, dict)
        
    def test_get_error_handling_config(self, setup):
        """Тест получения конфигурации обработки ошибок"""
        config = ExportConfig(str(setup))
        error_config = config.get_error_handling_config()
        assert isinstance(error_config, dict) 