"""
Пример модульного подключения экспортеров
"""

import asyncio
from XML_search.enhanced.export.export_manager import ExportManager
from XML_search.enhanced.export.exporters.civil3d import Civil3DExporter
from XML_search.enhanced.export.exporters.gmv20 import GMv20Exporter
from XML_search.enhanced.export.exporters.gmv25 import GMv25Exporter
from XML_search.enhanced.log_manager import LogManager

async def main():
    # Инициализация логгера
    logger = LogManager().get_logger(__name__)
    logger.info("Запуск примера экспорта")

    # Создание менеджера экспорта
    export_manager = ExportManager()

    # Регистрация экспортеров с базовой конфигурацией
    exporters_config = {
        'xml_Civil3D': {
            'display_name': 'Civil3D XML',
            'description': 'Экспорт в формат Civil3D XML',
            'extension': '.xml',
            'format_name': 'xml_Civil3D'
        },
        'prj_GMv20': {
            'display_name': 'GMv20',
            'description': 'Экспорт в формат GMv20',
            'extension': '.prj',
            'format_name': 'prj_GMv20'
        },
        'prj_GMv25': {
            'display_name': 'GMv25',
            'description': 'Экспорт в формат GMv25',
            'extension': '.prj',
            'format_name': 'prj_GMv25'
        }
    }

    # Регистрация экспортеров
    export_manager.register_exporter('xml_Civil3D', Civil3DExporter(exporters_config['xml_Civil3D']))
    export_manager.register_exporter('prj_GMv20', GMv20Exporter(exporters_config['prj_GMv20']))
    export_manager.register_exporter('prj_GMv25', GMv25Exporter(exporters_config['prj_GMv25']))

    # Получение списка доступных форматов
    available_formats = export_manager.get_available_formats(32601)
    logger.info(f"Доступные форматы экспорта: {[fmt['id'] for fmt in available_formats]}")

    try:
        # Пример экспорта в разные форматы
        srid = 32601  # Пример SRID (UTM Zone 1N)

        # Экспорт в Civil3D
        civil3d_result = await export_manager.export(srid, 'xml_Civil3D')
        logger.info(f"Результат экспорта Civil3D: {civil3d_result}")

        # Экспорт в GMv20 с параметрами по умолчанию
        gmv20_result = await export_manager.export(srid, 'prj_GMv20')
        logger.info(f"Результат экспорта GMv20: {gmv20_result}")

        # Экспорт в GMv25 с дополнительными параметрами
        gmv25_params = {
            'encoding': 'UTF-8',
            'coordinate_order': 'EN'
        }
        gmv25_result = await export_manager.export(srid, 'prj_GMv25', gmv25_params)
        logger.info(f"Результат экспорта GMv25: {gmv25_result}")

    except Exception as e:
        logger.error(f"Ошибка при экспорте: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main()) 