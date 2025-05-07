"""
Тесты для обработчика экспорта
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from XML_search.enhanced.export.export_manager import ExportManager
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter
from XML_search.bot.handlers.export_handler import ExportHandler
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.bot.states import States
from XML_search.enhanced.export.exceptions import ExportError, ValidationError

@pytest.fixture
def mock_metrics():
    """Мок для сборщика метрик"""
    metrics = MagicMock(spec=MetricsCollector)
    metrics.increment = MagicMock()
    metrics.timing = MagicMock()
    # Добавляем контекстный менеджер для timing
    metrics.timing.return_value.__enter__ = MagicMock()
    metrics.timing.return_value.__exit__ = MagicMock()
    return metrics

@pytest.fixture
def mock_logger():
    """Мок для логгера"""
    logger = MagicMock(spec=LogManager)
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.info = MagicMock()
    return logger

@pytest.fixture
def mock_cache():
    """Мок для кэша"""
    cache = MagicMock(spec=CacheManager)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache

@pytest.fixture
def mock_db_manager():
    """Мок для менеджера БД"""
    db_manager = MagicMock(spec=DatabaseManager)
    db_manager.execute_query = AsyncMock(return_value=[])
    return db_manager

@pytest.fixture
def mock_export_manager():
    """Мок для менеджера экспорта"""
    export_manager = MagicMock(spec=ExportManager)
    export_manager.export = AsyncMock(return_value="exported_data")
    return export_manager

@pytest.fixture
def mock_update():
    """Мок для объекта Update"""
    update = MagicMock()
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.data = "civil3d"
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.id = 12345
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    return update

@pytest.fixture
def mock_context():
    """Мок для объекта Context"""
    context = MagicMock()
    context.user_data = {
        'export_data': {
            'srid': 100001,
            'format': 'civil3d'
        }
    }
    return context

@pytest.fixture
def export_handler(mock_db_manager, mock_export_manager, mock_metrics, mock_logger, mock_cache):
    """Фикстура для создания обработчика экспорта"""
    handler = ExportHandler(
        db_manager=mock_db_manager,
        export_manager=mock_export_manager,
        metrics=mock_metrics,
        logger=mock_logger,
        cache=mock_cache
    )
    return handler

class TestExportIntegration:
    """Интеграционные тесты для экспортеров"""

    @pytest.mark.asyncio
    async def test_civil3d_export(self, export_handler, mock_update, mock_context):
        """Тест экспорта в Civil 3D"""
        # Подготовка
        mock_update.callback_query.data = "civil3d"
        export_handler.export_manager.export.return_value = "exported_data.xml"

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_COMPLETE
        export_handler.export_manager.export.assert_called_once_with(
            srid=100001,
            format_id="civil3d"
        )
        export_handler.metrics.increment.assert_any_call('export_success')

    @pytest.mark.asyncio
    async def test_gmv20_export(self, export_handler, mock_update, mock_context):
        """Тест экспорта в GMv20"""
        # Подготовка
        mock_update.callback_query.data = "gmv20"
        export_handler.export_manager.export.return_value = "exported_data.prj"

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_COMPLETE
        export_handler.export_manager.export.assert_called_once_with(
            srid=100001,
            format_id="gmv20"
        )
        export_handler.metrics.increment.assert_any_call('export_success')

    @pytest.mark.asyncio
    async def test_gmv25_export(self, export_handler, mock_update, mock_context):
        """Тест экспорта в GMv25"""
        # Подготовка
        mock_update.callback_query.data = "gmv25"
        export_handler.export_manager.export.return_value = "exported_data.prj"

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_COMPLETE
        export_handler.export_manager.export.assert_called_once_with(
            srid=100001,
            format_id="gmv25"
        )
        export_handler.metrics.increment.assert_any_call('export_success')

    @pytest.mark.asyncio
    async def test_export_error_handling(self, export_handler, mock_update, mock_context):
        """Тест обработки ошибок при экспорте"""
        # Подготовка
        test_data = {
            "srid": 100001,
            "name": "МСК"
        }
        mock_context.user_data['export_data'] = test_data
        mock_update.callback_query.data = "civil3d"
        export_handler.export_manager.export.side_effect = Exception("Export error")

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_ERROR
        export_handler.metrics.increment.assert_called_with('export_errors')
        export_handler.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_metrics_collection(self, export_handler, mock_update, mock_context):
        """Тест сбора метрик при экспорте"""
        # Подготовка
        mock_update.callback_query.data = "civil3d"
        export_handler.export_manager.export.return_value = "exported_data.xml"

        # Выполнение
        await export_handler._handle_update(mock_update, mock_context)

        # Проверка сбора метрик
        export_handler.metrics.increment.assert_any_call('export_success')

    @pytest.mark.asyncio
    async def test_civil3d_validation(self, export_handler, mock_update, mock_context):
        """Тест валидации параметров для Civil 3D"""
        # Подготовка
        mock_update.callback_query.data = "civil3d"
        export_handler.export_manager.export.side_effect = ValidationError("Invalid projection type")

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_VALIDATION_ERROR
        export_handler.metrics.increment.assert_any_call('export_validation_errors')
        export_handler.logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_gmv20_specific_parameters(self, export_handler, mock_update, mock_context):
        """Тест специфичных параметров для GMv20"""
        # Подготовка
        mock_context.user_data['export_data'].update({
            "parameters": {
                "ellipsoid": "PZ-90",
                "datum": "PZ-90.02",
                "height_system": "Балтийская система высот"
            }
        })
        mock_update.callback_query.data = "gmv20"
        export_handler.export_manager.export.return_value = "exported_data.prj"

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_COMPLETE
        export_handler.export_manager.export.assert_called_once_with(
            srid=100001,
            format_id="gmv20"
        )
        export_handler.metrics.increment.assert_any_call('export_success')

    @pytest.mark.asyncio
    async def test_gmv25_specific_parameters(self, export_handler, mock_update, mock_context):
        """Тест специфичных параметров для GMv25"""
        # Подготовка
        mock_context.user_data['export_data'].update({
            "parameters": {
                "ellipsoid": "Krassowsky",
                "datum": "Pulkovo-1942",
                "vertical_datum": "Baltic Sea"
            }
        })
        mock_update.callback_query.data = "gmv25"
        export_handler.export_manager.export.return_value = "exported_data.prj"

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_COMPLETE
        export_handler.export_manager.export.assert_called_once_with(
            srid=100001,
            format_id="gmv25"
        )
        export_handler.metrics.increment.assert_any_call('export_success')

    @pytest.mark.asyncio
    async def test_export_cache(self, export_handler, mock_update, mock_context):
        """Тест кэширования результатов экспорта"""
        # Подготовка
        test_data = {
            "srid": 100001,
            "name": "МСК"
        }
        mock_context.user_data['export_data'] = test_data
        mock_update.callback_query.data = "civil3d"
        cached_result = "cached_data.xml"
        export_handler.cache.get.return_value = cached_result

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_COMPLETE
        export_handler.cache.get.assert_called_once()
        export_handler.export_manager.export.assert_not_called()
        assert mock_context.user_data['export_result'] == cached_result

    @pytest.mark.asyncio
    async def test_export_with_missing_parameters(self, export_handler, mock_update, mock_context):
        """Тест экспорта с отсутствующими параметрами"""
        # Подготовка
        context = MagicMock()
        context.user_data = {}  # Пустые данные

        # Выполнение
        result = await export_handler._handle_update(mock_update, context)

        # Проверка
        assert result == States.EXPORT_ERROR
        export_handler.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_with_invalid_srid(self, export_handler, mock_update, mock_context):
        """Тест экспорта с некорректным SRID"""
        # Подготовка
        mock_context.user_data['export_data']['srid'] = -1
        mock_update.callback_query.data = "civil3d"
        export_handler.export_manager.export.side_effect = ValidationError("Invalid SRID")

        # Выполнение
        result = await export_handler._handle_update(mock_update, mock_context)

        # Проверка
        assert result == States.EXPORT_VALIDATION_ERROR
        export_handler.metrics.increment.assert_any_call('export_validation_errors') 