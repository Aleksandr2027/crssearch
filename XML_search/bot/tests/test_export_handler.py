"""
Тесты для обработчика экспорта с временным решением
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from telegram import Update, CallbackQuery, User, Message
from telegram.ext import ContextTypes
from XML_search.bot.handlers.export_handler import ExportHandler
from XML_search.bot.handlers.exceptions import ExportError, ValidationError, ExporterError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics import MetricsCollector
from XML_search.enhanced.export.export_manager import ExportManager
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter

class TestExportHandler:
    @pytest.fixture
    def setup(self):
        """Подготовка окружения для тестов"""
        # Создаем моки для зависимостей
        self.db_manager = Mock(spec=DatabaseManager)
        
        # Создаем обработчик
        with patch('XML_search.enhanced.metrics.MetricsCollector') as metrics_mock, \
             patch('XML_search.enhanced.cache_manager.CacheManager') as cache_mock, \
             patch('XML_search.enhanced.log_manager.LogManager') as log_mock, \
             patch('XML_search.bot.utils.validation_utils.ValidationManager') as validation_mock, \
             patch('XML_search.bot.utils.keyboard_utils.KeyboardManager') as keyboard_mock, \
             patch('XML_search.enhanced.export.export_manager.ExportManager') as export_manager_mock:
            
            self.handler = ExportHandler(db_manager=self.db_manager)
            
            # Настраиваем моки
            self.handler.metrics = metrics_mock
            self.handler.cache = cache_mock
            self.handler.logger = log_mock.return_value.get_logger.return_value
            self.handler.validator = validation_mock.return_value
            self.handler.keyboard_manager = keyboard_mock.return_value
            self.handler.export_manager = export_manager_mock.return_value
            
            # Настраиваем поведение моков
            self.handler.keyboard_manager.validate_export_access.return_value = True
            self.handler.validator.validate_export_params.return_value = MagicMock(is_valid=True)
            self.handler.export_manager.get_exporter = Mock()
        
        # Создаем моки для Update и Context
        self.user = Mock(spec=User)
        self.user.id = 12345
        
        self.callback_query = AsyncMock(spec=CallbackQuery)
        self.callback_query.from_user = self.user
        
        self.update = Mock(spec=Update)
        self.update.callback_query = self.callback_query
        self.update.effective_user = self.user
        
        self.context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.bot = AsyncMock()
        
    @pytest.mark.asyncio
    async def test_handle_export_callback_civil3d(self, setup):
        """
        Тест обработки callback запроса на экспорт в формат Civil3D
        Проверяем временное сообщение об успешном экспорте
        """
        # Подготовка данных
        self.callback_query.data = "export_xml:100000"
        
        # Мокируем export_format
        self.handler.export_format = AsyncMock(return_value=Mock(file="test_file", filename="test.xml"))
        
        # Выполнение
        await self.handler.handle_export_callback(self.update, self.context)
        
        # Проверки
        self.handler.keyboard_manager.validate_export_access.assert_called_once_with("xml", self.user.id)
        self.handler.export_format.assert_called_once_with(100000, "xml")
        self.context.bot.send_document.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            document="test_file",
            filename="test.xml",
            caption="✅ Экспорт SRID 100000 в формат xml"
        )
        self.handler.metrics.increment.assert_called_with('export_success_xml')
        
    @pytest.mark.asyncio
    async def test_handle_export_callback_gmv20(self, setup):
        """
        Тест обработки callback запроса на экспорт в формат GMv20
        Проверяем временное сообщение об успешном экспорте
        """
        # Подготовка данных
        self.callback_query.data = "export_gmv20:100000"
        
        # Мокируем export_format
        self.handler.export_format = AsyncMock(return_value=Mock(file="test_file", filename="test.prj"))
        
        # Выполнение
        await self.handler.handle_export_callback(self.update, self.context)
        
        # Проверки
        self.handler.keyboard_manager.validate_export_access.assert_called_once_with("gmv20", self.user.id)
        self.handler.export_format.assert_called_once_with(100000, "gmv20")
        self.context.bot.send_document.assert_called_once_with(
            chat_id=self.update.effective_chat.id,
            document="test_file",
            filename="test.prj",
            caption="✅ Экспорт SRID 100000 в формат gmv20"
        )
        self.handler.metrics.increment.assert_called_with('export_success_gmv20')
        
    @pytest.mark.asyncio
    async def test_handle_export_callback_invalid_srid(self, setup):
        """
        Тест обработки callback запроса с некорректным SRID
        Проверяем сообщение об ошибке
        """
        # Подготовка данных с некорректным SRID
        self.callback_query.data = "export_xml:invalid"
        
        # Выполнение
        await self.handler.handle_export_callback(self.update, self.context)
        
        # Проверки
        self.callback_query.answer.assert_called_with(
            "❌ Неверный формат данных",
            show_alert=True
        )
        self.handler.metrics.increment.assert_called_with('export_callback_format_errors')
        
    @pytest.mark.asyncio
    async def test_handle_export_callback_access_denied(self, setup):
        """
        Тест обработки callback запроса при отсутствии прав
        Проверяем сообщение об отказе в доступе
        """
        # Подготовка данных
        self.callback_query.data = "export_xml:100000"
        self.handler.keyboard_manager.validate_export_access.return_value = False
        
        # Выполнение
        await self.handler.handle_export_callback(self.update, self.context)
        
        # Проверки
        self.callback_query.answer.assert_called_once_with(
            "⛔ Недостаточно прав для этого формата",
            show_alert=True
        )
        self.handler.metrics.increment.assert_called_with('export_access_denied')
        
    @pytest.mark.asyncio
    async def test_handle_export_callback_metrics(self, setup):
        """
        Тест сбора метрик при экспорте
        Проверяем все необходимые метрики
        """
        # Подготовка данных
        self.callback_query.data = "export_xml:100000"
        
        # Мокируем export_format
        self.handler.export_format = AsyncMock(return_value=Mock(file="test_file", filename="test.xml"))
        
        # Выполнение
        await self.handler.handle_export_callback(self.update, self.context)
        
        # Проверяем все необходимые метрики
        self.handler.metrics.increment.assert_called_with('export_success_xml')
            
    @pytest.mark.asyncio
    async def test_handle_export_callback_invalid_format(self, setup):
        """
        Тест обработки callback запроса с некорректным форматом
        Проверяем сообщение об ошибке
        """
        # Подготовка данных с некорректным форматом
        self.callback_query.data = "export_invalid:100000"
        
        # Мокируем export_format чтобы вызвать ошибку
        self.handler.export_format = AsyncMock(side_effect=ExportError("Неверный формат экспорта"))
        
        # Выполнение
        await self.handler.handle_export_callback(self.update, self.context)
        
        # Проверки
        self.callback_query.answer.assert_called_with(
            "❌ Произошла ошибка при экспорте",
            show_alert=True
        )
        self.handler.metrics.increment.assert_called_with('export_errors')
        
    @pytest.mark.asyncio
    async def test_export_format_validation(self, setup):
        """
        Тест валидации параметров экспорта
        """
        # Подготовка данных
        srid = 100000
        format_type = "xml"
        
        # Мокируем валидатор
        validation_result = MagicMock()
        validation_result.is_valid = False
        validation_result.error_message = "Invalid params"
        self.handler.validator.validate_export_params.return_value = validation_result
        
        # Мокируем cache
        self.handler.cache.get.return_value = None
        
        # Выполнение и проверка исключения
        with pytest.raises(ExportError) as exc_info:
            await self.handler.export_format(srid, format_type)
            
        # Проверяем сообщение об ошибке
        assert str(exc_info.value) == "Invalid params"
            
        # Проверяем метрики
        self.handler.metrics.increment.assert_called_with('export_validation_errors')
        
        # Проверяем, что валидатор был вызван, а экспортер - нет
        self.handler.validator.validate_export_params.assert_called_once_with(
            srid=srid,
            format_type=format_type
        )
        self.handler.export_manager.get_exporter.assert_not_called()
        
        # Проверяем, что кэш проверялся
        self.handler.cache.get.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_export_format_cache(self, setup):
        """
        Тест использования кэша при экспорте
        """
        # Подготовка данных
        srid = 100000
        format_type = "xml"
        cached_result = Mock(file="cached_file", filename="cached.xml")
        
        # Мокируем кэш
        self.handler.cache.get.return_value = cached_result
        
        # Выполнение
        result = await self.handler.export_format(srid, format_type)
        
        # Проверки
        assert result == cached_result
        self.handler.metrics.increment.assert_called_with('export_cache_hits')
        self.handler.export_manager.get_exporter.assert_not_called() 