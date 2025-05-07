"""
Тесты для GMv20 экспортера
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.errors import ValidationError, XMLProcessingError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.config import DBConfig
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager

@pytest.fixture
def mock_db_manager():
    """Фикстура для создания мока DatabaseManager"""
    db_manager = MagicMock(spec=DatabaseManager)
    cursor = MagicMock()
    cursor.fetchone = MagicMock()
    cursor.execute = MagicMock()
    db_manager.safe_cursor.return_value.__enter__.return_value = cursor
    db_manager.close = MagicMock()
    return db_manager

@pytest.fixture
def mock_metrics():
    """Фикстура для мока метрик"""
    metrics = MagicMock(spec=MetricsManager)
    metrics.increment = MagicMock()
    return metrics

@pytest.fixture
def mock_logger():
    """Фикстура для мока логгера"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    return logger

@pytest.fixture
def exporter(mock_db_manager, mock_metrics, mock_logger):
    """Фикстура для создания экземпляра экспортера"""
    exporter = GMv20Exporter({
        'display_name': 'GMv20',
        'description': 'Экспорт в формат GMv20',
        'extension': '.prj',
        'format_name': 'prj_GMv20'
    }, db_manager=mock_db_manager, logger=mock_logger)
    exporter.metrics = mock_metrics
    return exporter

class TestGMv20Exporter:
    """Тесты для GMv20 экспортера"""

    def test_init_with_custom_db_manager(self, mock_db_manager):
        """Тест инициализации с пользовательским менеджером БД"""
        mock_logger = MagicMock()
        
        exporter = GMv20Exporter({
            'display_name': 'GMv20',
            'description': 'Экспорт в формат GMv20',
            'extension': '.prj',
            'format_name': 'prj_GMv20'
        }, db_manager=mock_db_manager, logger=mock_logger)
        
        assert exporter.db_manager == mock_db_manager
        mock_logger.info.assert_has_calls([
            call("Использован существующий DatabaseManager"),
            call("Инициализирован экспортер prj_GMv20")
        ], any_order=True)

    def test_init_without_db_manager(self):
        """Тест инициализации без менеджера БД"""
        mock_db = MagicMock(spec=DatabaseManager)
        mock_logger = MagicMock()
        
        with patch('XML_search.enhanced.db_manager.DatabaseManager', return_value=mock_db):
            exporter = GMv20Exporter({
                'display_name': 'GMv20',
                'description': 'Экспорт в формат GMv20',
                'extension': '.prj',
                'format_name': 'prj_GMv20'
            }, logger=mock_logger)
            
            assert isinstance(exporter.db_manager, DatabaseManager)
            mock_logger.info.assert_has_calls([
                call("Создан новый экземпляр DatabaseManager"),
                call("Инициализирован экспортер prj_GMv20")
            ], any_order=True)

    def test_db_manager_error_handling(self):
        """Тест обработки ошибок при создании DatabaseManager"""
        test_error = Exception("DB Error")
        mock_logger = MagicMock()
        
        with patch('XML_search.enhanced.export.exporters.base.DatabaseManager') as mock_db_cls:
            mock_db_cls.side_effect = test_error
            
            with pytest.raises(Exception) as exc_info:
                GMv20Exporter({
                    'display_name': 'GMv20',
                    'description': 'Экспорт в формат GMv20',
                    'extension': '.prj',
                    'format_name': 'prj_GMv20'
                }, logger=mock_logger)
                
            assert str(exc_info.value) == "DB Error"
            mock_logger.error.assert_called_with("Ошибка создания DatabaseManager: DB Error")

    @pytest.mark.asyncio
    async def test_export_success(self, exporter):
        """Тест успешного экспорта"""
        srid = 32601
        result = await exporter.export(srid)
        assert "✅ Экспорт в формат GMv20" in result
        assert f"SRID: {srid}" in result
        assert "Статус: Успешно" in result
        exporter.metrics.increment.assert_called_with('gmv20_export_success')

    @pytest.mark.asyncio
    async def test_export_with_params(self, exporter):
        """Тест экспорта с параметрами"""
        srid = 32601
        params = {
            'format': 'prj',
            'version': '20',
            'encoding': 'UTF-8',
            'coordinate_order': 'EN'  # Специфичный параметр для GMv20
        }
        result = await exporter.export(srid, params)
        assert "✅ Экспорт в формат GMv20" in result
        assert f"SRID: {srid}" in result
        assert "Статус: Успешно" in result
        assert str(params) in result

    @pytest.mark.asyncio
    async def test_export_validation_error(self, exporter):
        """Тест ошибки валидации при экспорте"""
        with pytest.raises(ValidationError):
            await exporter.export(-1)
        exporter.metrics.increment.assert_called_with('gmv20_export_errors')

    @pytest.mark.asyncio
    async def test_export_invalid_params(self, exporter):
        """Тест экспорта с неверными параметрами"""
        srid = 32601
        invalid_params = {
            'coordinate_order': 'invalid',  # Неверный порядок координат
            'encoding': 'invalid'  # Неверная кодировка
        }
        with pytest.raises(ValidationError):
            await exporter.export(srid, invalid_params)
        exporter.metrics.increment.assert_called_with('gmv20_export_errors')

    def test_supports_srid_temporary(self, exporter):
        """Тест временной реализации supports_srid"""
        assert exporter.supports_srid(32601) is True
        assert exporter.supports_srid(100001) is True
        assert exporter.supports_srid(-1) is True

    def test_validate_params(self, exporter):
        """Тест валидации параметров"""
        # Валидные параметры
        valid_params = {
            'format': 'prj',
            'version': '20',
            'encoding': 'UTF-8',
            'coordinate_order': 'EN'
        }
        assert exporter.validate_params(valid_params) is None

        # Неверный порядок координат
        invalid_order = valid_params.copy()
        invalid_order['coordinate_order'] = 'invalid'
        with pytest.raises(ValidationError):
            exporter.validate_params(invalid_order)

        # Неверная кодировка
        invalid_encoding = valid_params.copy()
        invalid_encoding['encoding'] = 'invalid'
        with pytest.raises(ValidationError):
            exporter.validate_params(invalid_encoding) 