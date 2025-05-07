"""
Тесты для менеджера экспорта
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from XML_search.enhanced.export.export_manager import ExportManager
from XML_search.enhanced.export.exceptions import ExporterError, ValidationError
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter

class TestExportManager:
    @pytest.fixture
    def setup(self):
        """Подготовка окружения для тестов"""
        # Создаем моки для экспортеров
        self.civil3d_exporter = Mock(spec=Civil3DExporter)
        self.gmv20_exporter = Mock(spec=GMv20Exporter)
        self.gmv25_exporter = Mock(spec=GMv25Exporter)
        
        # Создаем менеджер экспорта
        self.manager = ExportManager()
        
        # Регистрируем экспортеры
        self.manager.register_exporter('xml_Civil3D', self.civil3d_exporter)
        self.manager.register_exporter('prj_GMv20', self.gmv20_exporter)
        self.manager.register_exporter('prj_GMv25', self.gmv25_exporter)
        
        yield
        
    def test_register_exporter(self, setup):
        """Тест регистрации экспортера"""
        # Подготовка
        test_exporter = Mock()
        
        # Выполнение
        self.manager.register_exporter('test', test_exporter)
        
        # Проверка
        assert self.manager.get_exporter('test') == test_exporter
        
    def test_get_nonexistent_exporter(self, setup):
        """Тест получения несуществующего экспортера"""
        assert self.manager.get_exporter('nonexistent') is None
        
    def test_get_available_formats(self, setup):
        """Тест получения доступных форматов"""
        # Подготовка
        srid = 100000
        self.civil3d_exporter.supports_srid.return_value = True
        self.gmv20_exporter.supports_srid.return_value = True
        self.gmv25_exporter.supports_srid.return_value = False
        
        # Настройка информации о форматах
        self.civil3d_exporter.get_format_info.return_value = {
            'display_name': 'Civil3D XML',
            'description': 'XML формат для Civil3D'
        }
        self.gmv20_exporter.get_format_info.return_value = {
            'display_name': 'GMv20 PRJ',
            'description': 'PRJ формат для GlobalMapper v20'
        }
        
        # Выполнение
        formats = self.manager.get_available_formats(srid)
        
        # Проверка
        assert len(formats) == 2
        assert any(f['id'] == 'xml_Civil3D' for f in formats)
        assert any(f['id'] == 'prj_GMv20' for f in formats)
        assert not any(f['id'] == 'prj_GMv25' for f in formats)
        
    @pytest.mark.asyncio
    async def test_export_civil3d(self, setup):
        """Тест экспорта в формат Civil3D"""
        # Подготовка
        srid = 100000
        format_type = 'xml_Civil3D'
        expected_result = Mock(file="test_file", filename="test.xml")
        self.civil3d_exporter.export = AsyncMock(return_value=expected_result)
        
        # Выполнение
        result = await self.manager.export(srid, format_type)
        
        # Проверка
        assert result == expected_result
        self.civil3d_exporter.export.assert_called_once_with(srid)
        
    @pytest.mark.asyncio
    async def test_export_gmv20(self, setup):
        """Тест экспорта в формат GMv20"""
        # Подготовка
        srid = 100000
        format_type = 'prj_GMv20'
        expected_result = Mock(file="test_file", filename="test.prj")
        self.gmv20_exporter.export = AsyncMock(return_value=expected_result)
        
        # Выполнение
        result = await self.manager.export(srid, format_type)
        
        # Проверка
        assert result == expected_result
        self.gmv20_exporter.export.assert_called_once_with(srid)
        
    @pytest.mark.asyncio
    async def test_export_invalid_format(self, setup):
        """Тест экспорта в неподдерживаемый формат"""
        # Подготовка
        srid = 100000
        format_type = 'invalid_format'
        
        # Выполнение и проверка
        with pytest.raises(ExporterError) as exc_info:
            await self.manager.export(srid, format_type)
        assert "Формат экспорта не поддерживается" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_export_validation_error(self, setup):
        """Тест ошибки валидации при экспорте"""
        # Подготовка
        srid = 100000
        format_type = 'xml_Civil3D'
        error_message = "Invalid params"
        self.civil3d_exporter.export = AsyncMock(side_effect=ValidationError(error_message))
        
        # Выполнение и проверка
        with pytest.raises(ExporterError) as exc_info:
            await self.manager.export(srid, format_type)
        assert error_message in str(exc_info.value)
        
    def test_validate_format_type(self, setup):
        """Тест валидации типа формата"""
        # Проверка валидных форматов
        assert self.manager.validate_format_type('xml_Civil3D')
        assert self.manager.validate_format_type('prj_GMv20')
        assert self.manager.validate_format_type('prj_GMv25')
        
        # Проверка невалидного формата
        with pytest.raises(ValidationError) as exc_info:
            self.manager.validate_format_type('invalid_format')
        assert "Неподдерживаемый формат" in str(exc_info.value)
        
    def test_validate_srid(self, setup):
        """Тест валидации SRID"""
        # Подготовка
        self.civil3d_exporter.supports_srid.return_value = True
        
        # Проверка валидного SRID
        assert self.manager.validate_srid(100000, 'xml_Civil3D')
        
        # Проверка невалидного SRID
        self.civil3d_exporter.supports_srid.return_value = False
        with pytest.raises(ValidationError) as exc_info:
            self.manager.validate_srid(999999, 'xml_Civil3D')
        assert "не поддерживается" in str(exc_info.value)
        
    def test_metrics_collection(self, setup):
        """Тест сбора метрик"""
        # Подготовка
        metrics_mock = Mock()
        self.manager.metrics = metrics_mock
        
        # Выполнение
        self.manager.register_exporter('test', Mock())
        
        # Проверка
        metrics_mock.increment.assert_called_with('export_formats_registered')

    def test_temporary_export_civil3d(self, setup):
        """Тест временного решения для Civil3D"""
        result = setup.export(100000, 'xml_Civil3D')
        assert "успешно выполнен" in result
        assert "Civil3D" in result
        assert "100000" in result
        
    def test_temporary_export_gmv20(self, setup):
        """Тест временного решения для GMv20"""
        result = setup.export(100000, 'prj_GMv20')
        assert "успешно выполнен" in result
        assert "GMv20" in result
        assert "100000" in result
        
    def test_temporary_export_gmv25(self, setup):
        """Тест временного решения для GMv25"""
        result = setup.export(100000, 'prj_GMv25')
        assert "успешно выполнен" in result
        assert "GMv25" in result
        assert "100000" in result
        
    def test_invalid_format(self, setup):
        """Тест обработки неверного формата"""
        with pytest.raises(ValidationError) as exc:
            setup.export(100000, 'invalid_format')
        assert "не поддерживается" in str(exc.value)
        
    def test_get_available_formats(self, setup):
        """Тест получения списка доступных форматов"""
        formats = setup.get_available_formats(100000)
        assert len(formats) == 3
        
        format_ids = [f['id'] for f in formats]
        assert 'xml_Civil3D' in format_ids
        assert 'prj_GMv20' in format_ids
        assert 'prj_GMv25' in format_ids 