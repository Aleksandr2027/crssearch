"""
Тесты для примера модульного подключения экспортеров
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from XML_search.bot.examples.export_example import main
from XML_search.enhanced.export.export_manager import ExportManager
from XML_search.enhanced.log_manager import LogManager

@pytest.mark.asyncio
async def test_export_example():
    """Тест примера модульного подключения экспортеров"""
    # Создаем моки
    mock_logger = MagicMock()
    mock_export_manager = MagicMock(spec=ExportManager)
    
    # Настраиваем моки для асинхронных методов
    mock_export_manager.export = AsyncMock(return_value="Успешный экспорт")
    mock_export_manager.get_available_formats.return_value = [
        {'id': 'xml_Civil3D'},
        {'id': 'prj_GMv20'},
        {'id': 'prj_GMv25'}
    ]
    
    # Патчим необходимые компоненты
    with patch('XML_search.bot.examples.export_example.LogManager') as mock_log_manager, \
         patch('XML_search.bot.examples.export_example.ExportManager', return_value=mock_export_manager), \
         patch('XML_search.bot.examples.export_example.Civil3DExporter') as mock_civil3d, \
         patch('XML_search.bot.examples.export_example.GMv20Exporter') as mock_gmv20, \
         patch('XML_search.bot.examples.export_example.GMv25Exporter') as mock_gmv25:
        
        # Настраиваем мок логгера
        mock_log_manager.return_value.get_logger.return_value = mock_logger
        
        # Запускаем пример
        await main()
        
        # Проверяем, что все экспортеры были зарегистрированы
        assert mock_export_manager.register_exporter.call_count == 3
        
        # Проверяем, что был запрос на получение доступных форматов
        mock_export_manager.get_available_formats.assert_called_once_with(32601)
        
        # Проверяем, что были вызваны все три экспорта
        assert mock_export_manager.export.call_count == 3
        
        # Проверяем параметры вызовов export
        mock_export_manager.export.assert_any_call(32601, 'xml_Civil3D')
        mock_export_manager.export.assert_any_call(32601, 'prj_GMv20')
        mock_export_manager.export.assert_any_call(32601, 'prj_GMv25', {
            'encoding': 'UTF-8',
            'coordinate_order': 'EN'
        })
        
        # Проверяем логирование
        assert mock_logger.info.call_count >= 4  # Минимум 4 информационных сообщения
        assert mock_logger.error.call_count == 0  # Не должно быть ошибок

@pytest.mark.asyncio
async def test_export_example_error_handling():
    """Тест обработки ошибок в примере"""
    # Создаем моки
    mock_logger = MagicMock()
    mock_export_manager = MagicMock(spec=ExportManager)
    
    # Настраиваем мок для генерации ошибки в асинхронном методе
    test_error = Exception("Тестовая ошибка экспорта")
    mock_export_manager.export = AsyncMock(side_effect=test_error)
    
    # Патчим необходимые компоненты
    with patch('XML_search.bot.examples.export_example.LogManager') as mock_log_manager, \
         patch('XML_search.bot.examples.export_example.ExportManager', return_value=mock_export_manager), \
         patch('XML_search.bot.examples.export_example.Civil3DExporter'), \
         patch('XML_search.bot.examples.export_example.GMv20Exporter'), \
         patch('XML_search.bot.examples.export_example.GMv25Exporter'):
        
        # Настраиваем мок логгера
        mock_log_manager.return_value.get_logger.return_value = mock_logger
        
        # Проверяем, что ошибка обрабатывается корректно
        with pytest.raises(Exception) as exc_info:
            await main()
            
        assert str(exc_info.value) == "Тестовая ошибка экспорта"
        mock_logger.error.assert_called_once_with("Ошибка при экспорте: Тестовая ошибка экспорта") 