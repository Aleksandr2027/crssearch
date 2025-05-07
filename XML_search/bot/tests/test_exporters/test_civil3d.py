"""
Тесты для экспортера Civil3D
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.errors import ValidationError, XMLProcessingError, ExportError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.config import DBConfig
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector
import xml.etree.ElementTree as ET
from datetime import datetime

@pytest.fixture
def mock_db_manager():
    """Фикстура для создания мока DatabaseManager"""
    db_manager = MagicMock(spec=DatabaseManager)
    cursor = MagicMock()
    cursor.fetchone = MagicMock()
    cursor.execute = MagicMock()
    db_manager.safe_cursor = MagicMock(return_value=cursor)
    return db_manager

@pytest.fixture
def mock_logger():
    """Фикстура для создания мока логгера"""
    logger = MagicMock(spec=LogManager)
    return logger

@pytest.fixture
def mock_metrics():
    """Фикстура для создания мока сборщика метрик"""
    metrics = MagicMock(spec=MetricsCollector)
    return metrics

@pytest.fixture
def config():
    """Фикстура для создания конфигурации"""
    return {
        'db': {
            'host': 'test_host',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        },
        'export': {
            'temp_dir': '/tmp/test'
        }
    }

@pytest.fixture
def exporter(config, mock_db_manager, mock_logger, mock_metrics):
    """Фикстура для создания экспортера"""
    with patch('XML_search.enhanced.log_manager.LogManager', return_value=mock_logger), \
         patch('XML_search.enhanced.metrics.MetricsCollector', return_value=mock_metrics):
        return Civil3DExporter(config, db_manager=mock_db_manager)

class TestCivil3DExporter:
    """Тесты для Civil3D экспортера"""

    def test_init_with_custom_db_manager(self, config, mock_db_manager, mock_logger, mock_metrics):
        """Тест инициализации с пользовательским менеджером БД"""
        with patch('XML_search.enhanced.log_manager.LogManager', return_value=mock_logger), \
             patch('XML_search.enhanced.metrics.MetricsCollector', return_value=mock_metrics):
            exporter = Civil3DExporter(config, db_manager=mock_db_manager)
            
            assert exporter.db_manager == mock_db_manager
            mock_logger.info.assert_has_calls([
                call("Инициализация Civil3D экспортера"),
                call("Использование существующего менеджера БД")
            ])

    def test_init_without_db_manager(self, config, mock_logger, mock_metrics):
        """Тест инициализации без менеджера БД"""
        mock_db = MagicMock(spec=DatabaseManager)
        
        with patch('XML_search.enhanced.log_manager.LogManager', return_value=mock_logger), \
             patch('XML_search.enhanced.metrics.MetricsCollector', return_value=mock_metrics), \
             patch('XML_search.enhanced.db_manager.DatabaseManager', return_value=mock_db):
            
            exporter = Civil3DExporter(config)
            
            assert isinstance(exporter.db_manager, DatabaseManager)
            mock_logger.info.assert_has_calls([
                call("Инициализация Civil3D экспортера"),
                call("Создание нового менеджера БД")
            ])

    def test_db_manager_error_handling(self, config, mock_logger, mock_metrics):
        """Тест обработки ошибок при создании менеджера БД"""
        with patch('XML_search.enhanced.log_manager.LogManager', return_value=mock_logger), \
             patch('XML_search.enhanced.metrics.MetricsCollector', return_value=mock_metrics), \
             patch('XML_search.enhanced.db_manager.DatabaseManager', side_effect=Exception("DB Error")):
            
            with pytest.raises(ExportError) as exc_info:
                Civil3DExporter(config)
            
            assert str(exc_info.value) == "Ошибка при создании менеджера БД: DB Error"
            mock_logger.error.assert_called_once_with("Ошибка при создании менеджера БД: DB Error")

    def test_cleanup_on_deletion(self, exporter):
        """Тест очистки при удалении"""
        exporter.__del__()
        exporter.logger.info.assert_called_with("Соединение с базой данных закрыто")
        exporter.db_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_temporary_export(self, exporter, mock_metrics):
        """Тест временного решения для экспорта"""
        srid = 100000
        exporter.supports_srid = MagicMock(return_value=True)
        exporter._get_crs_data = MagicMock(return_value={
            'srid': srid,
            'auth_name': 'CUSTOM',
            'auth_srid': srid,
            'srtext': 'test',
            'proj4text': 'test',
            'info': 'test',
            'reliability': 'test',
            'deg': 6,
            'name': 'test'
        })
        
        result = await exporter.export(srid)
        assert isinstance(result, str)
        mock_metrics.increment.assert_called_with('civil3d_export_success')

    @pytest.mark.asyncio
    async def test_temporary_export_error(self, exporter, mock_metrics):
        """Тест временного решения при ошибке"""
        srid = 100000
        exporter.supports_srid = MagicMock(return_value=False)
        
        with pytest.raises(ValidationError) as exc_info:
            await exporter.export(srid)
        assert str(exc_info.value) == f"SRID {srid} не поддерживается"
        mock_metrics.increment.assert_called_with('civil3d_export_validation_errors')

    def test_generate_xml(self, exporter):
        """Тест генерации XML"""
        test_data = {
            'srid': 32601,
            'auth_name': 'EPSG',
            'auth_srid': 32601,
            'srtext': 'PROJCS["WGS 84 / UTM zone 1N",GEOGCS["WGS 84"...]',
            'proj4text': '+proj=utm +zone=1 +datum=WGS84 +units=m +no_defs',
            'info': 'UTM Zone 1N',
            'reliability': 'EPSG',
            'deg': 6,
            'name': 'UTM zone 1N'
        }
        
        xml_str = exporter._generate_xml(test_data)
        root = ET.fromstring(xml_str)
        
        # Проверяем namespace
        assert root.tag.endswith('CoordinateSystem')
        
        # Проверяем SRID
        metadata = root.find('.//{*}Metadata')
        assert metadata is not None
        srid_elem = metadata.find('.//{*}SRID')
        assert srid_elem is not None
        assert srid_elem.text == '32601'

    def test_generate_xml_error(self, exporter):
        """Тест ошибки генерации XML"""
        test_data = {}  # Пустой словарь вызовет ошибку
        with pytest.raises(XMLProcessingError) as exc_info:
            exporter._generate_xml(test_data)
        assert "Отсутствуют обязательные поля" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_export_validation_error(self, exporter, mock_metrics):
        """Тест экспорта с ошибкой валидации"""
        srid = -1
        exporter.supports_srid = MagicMock(return_value=False)
        
        with pytest.raises(ValidationError) as exc_info:
            await exporter.export(srid)
        assert str(exc_info.value) == f"SRID {srid} не поддерживается"
        mock_metrics.increment.assert_called_with('civil3d_export_validation_errors')

    def test_supports_srid_custom(self, exporter):
        """Тест поддержки пользовательского SRID"""
        srid = 100000
        cursor = exporter.db_manager.safe_cursor().__enter__()
        cursor.fetchone.return_value = [1]
        
        result = exporter.supports_srid(srid)
        assert result is True
        cursor.execute.assert_called_once()

    def test_supports_srid_utm(self, exporter):
        """Тест поддержки UTM зон"""
        srid = 32601
        cursor = exporter.db_manager.safe_cursor().__enter__()
        cursor.fetchone.return_value = [1]
        
        result = exporter.supports_srid(srid)
        assert result is True
        cursor.execute.assert_not_called()

    def test_supports_srid_unsupported(self, exporter):
        """Тест неподдерживаемого SRID"""
        srid = 4326
        cursor = exporter.db_manager.safe_cursor().__enter__()
        cursor.fetchone.return_value = None
        
        result = exporter.supports_srid(srid)
        assert result is False
        cursor.execute.assert_called_once()

    def test_is_custom_crs(self, exporter):
        """Тест проверки пользовательской СК"""
        cursor = exporter.db_manager.safe_cursor().__enter__()
        cursor.fetchone.return_value = (1,)
        assert exporter._is_custom_crs(100001) is True
        cursor.execute.assert_called_once()

    def test_get_crs_data(self, exporter):
        """Тест получения данных о системе координат"""
        cursor = exporter.db_manager.safe_cursor().__enter__()
        test_data = (
            32601,              # srid
            'EPSG',            # auth_name
            32601,             # auth_srid
            'PROJCS["WGS 84 / UTM zone 1N",GEOGCS["WGS 84"...]', # srtext
            '+proj=utm +zone=1 +datum=WGS84 +units=m +no_defs', # proj4text
            'UTM Zone 1N',     # info
            'EPSG',            # reliability
            6,                 # deg
            'UTM zone 1N'      # name
        )
        cursor.fetchone.return_value = test_data
        result = exporter._get_crs_data(32601)
        assert result['srid'] == 32601
        assert result['auth_name'] == 'EPSG'
        cursor.execute.assert_called_once()

    @pytest.mark.parametrize("srid,expected", [
        (32601, True),   # UTM зона
        (32660, True),   # UTM зона
        (100001, False), # Обычный SRID
        (-1, False),     # Невалидный SRID
    ])
    def test_supports_srid(self, exporter, srid, expected):
        """Тест проверки поддержки SRID"""
        # Мокаем _is_custom_crs для тестовых случаев
        exporter._is_custom_crs = MagicMock(return_value=False)
        assert exporter.supports_srid(srid) == expected 