"""
Базовый класс для экспорта PRJ-файлов
"""

import os
import asyncio
from typing import Dict, Any, Optional
from ..exceptions import ExportError
from .base_exporter import BaseExporter
from XML_search.enhanced.log_manager import LogManager
import re

logger = LogManager().get_logger(__name__)

class PRJExporter(BaseExporter):
    """Базовый класс для экспорта PRJ-файлов"""
    
    def _sanitize_filename(self, name: str) -> str:
        """Очищает имя файла от недопустимых символов."""
        if not name:
            return "unknown_cs"
        # Удаляем или заменяем символы, нежелательные в именах файлов
        name = re.sub(r'[\\/:"*?<>|\\s]+', '_', name) # Заменяем пробелы и спецсимволы на '_'
        name = re.sub(r'_+', '_', name) # Удаляем множественные подчеркивания
        name = name.strip('_') # Убираем подчеркивания по краям
        # Ограничиваем длину, чтобы избежать слишком длинных имен файлов
        return name[:100] if len(name) > 100 else name

    async def export_to_file(self, srid: str, format_type: str) -> Dict[str, Any]:
        """
        Экспорт системы координат в PRJ-файл
        
        Args:
            srid: SRID системы координат
            format_type: Тип формата экспорта
            
        Returns:
            Dict[str, Any]: Информация о созданном файле
        """
        try:
            # Получаем данные системы координат
            cs_data = await self._get_coordinate_system(srid)
            
            # Проверка наличия данных и srtext перед экспортом
            if cs_data is None:
                logger.error(f"Данные для SRID {srid} не найдены. Экспорт PRJ невозможен.")
                raise ExportError(f"Данные для SRID {srid} не найдены. Невозможно экспортировать PRJ.")

            srtext = cs_data.get('srtext')
            if not srtext:
                # Если srtext отсутствует или пуст, пытаемся использовать proj4text
                proj4text = cs_data.get('proj4text')
                if proj4text:
                    logger.warning(f"srtext отсутствует для SRID {srid}. Используется proj4text для экспорта.")
                    # В данном контексте PRJ экспортеры ожидают WKT (srtext).
                    # Если его нет, но есть proj4text, то это все равно ошибка для PRJ.
                    # Однако, это место для потенциальной будущей конвертации proj4->wkt если понадобится.
                    # Пока что, если нет srtext, это ошибка.
                    logger.error(f"Отсутствует WKT (srtext) для SRID {srid}. Экспорт PRJ невозможен, даже если есть proj4text.")
                    raise ExportError(f"Отсутствует WKT (srtext) для SRID {srid}. Невозможно экспортировать PRJ.")
                else:
                    logger.error(f"Отсутствуют и WKT (srtext), и proj4text для SRID {srid}. Экспорт PRJ невозможен.")
                    raise ExportError(f"Отсутствуют данные для генерации PRJ для SRID {srid} (srtext и proj4text). Невозможно экспортировать PRJ.")
            
            # Получаем содержимое PRJ-файла
            prj_content = await self._get_prj_content(cs_data, format_type)
            
            # Определяем имя файла
            filename = await self._get_filename(cs_data, format_type)
            
            # Создаем директорию, если она не существует
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Формируем полный путь к файлу
            file_path = os.path.join(self.output_dir, filename)
            
            # Записываем данные в файл
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(prj_content)
                
            return {
                'file_path': file_path,
                'filename': filename,
                'format': format_type,
                'srid': srid
            }
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте PRJ-файла: {e}")
            raise ExportError(f"Ошибка при экспорте PRJ-файла: {str(e)}")
            
    async def _get_prj_content(self, cs_data: Dict[str, Any], format_type: str) -> str:
        """
        Получение содержимого PRJ-файла
        
        Args:
            cs_data: Данные системы координат
            format_type: Тип формата экспорта
            
        Returns:
            str: Содержимое PRJ-файла
        """
        # Если это 'custom' СК, то содержимое уже будет специфичным WKT, сгенерированным в GMv20/25Exporter
        # Если это не 'custom', то это будет оригинальный srtext
        # Поэтому здесь логика _generate_custom_wkt или вызов srtext остается корректной в дочерних классах
        if cs_data.get('auth_name') == 'custom':
             # Дочерние классы GMv20Exporter и GMv25Exporter переопределяют этот метод
             # и вызывают _generate_custom_wkt.
             # Эта базовая реализация вызовется, только если дочерний класс не переопределил _get_prj_content,
             # что для GMv20/v25 не так. Но для общности, если вдруг кастомная СК, но не GM, то так:
            logger.debug(f"PRJExporter._get_prj_content для custom SRID {cs_data.get('srid')}, вероятно, должен быть переопределен наследником для генерации WKT.")
            # Возвращаем proj4text если он есть и srtext пуст, для отладки или как заглушка
            return cs_data.get('proj4text') or cs_data.get('srtext', '') # ВАЖНО: для custom СК тут должен быть детальный WKT
        
        return cs_data.get('srtext', '') # Для не-custom СК возвращаем srtext
        
    async def _get_filename(self, cs_data: Dict[str, Any], format_type: str) -> str:
        """
        Получение имени файла
        
        Args:
            cs_data: Данные системы координат
            format_type: Тип формата экспорта (например, 'prj_GMv20', 'prj_GMv25')
            
        Returns:
            str: Имя файла
        """
        srid = str(cs_data.get('srid'))
        auth_name = cs_data.get('auth_name')
        srtext = cs_data.get('srtext', '')

        # 1. Обработка для UTM-зон (стандартные SRID)
        try:
            srid_int = int(srid)
            if 32601 <= srid_int <= 32660: # Северное полушарие
                utm_zone = srid_int - 32600
                return f"UTM_zone_{utm_zone:02d}N.prj"
            elif 32701 <= srid_int <= 32760: # Южное полушарие
                utm_zone = srid_int - 32700
                return f"UTM_zone_{utm_zone:02d}S.prj"
        except ValueError:
            logger.warning(f"SRID '{srid}' не является целым числом, не могу проверить на UTM.")

        # 2. Новая логика для "custom" систем координат
        if auth_name == 'custom':
            base_name_from_srtext = self._sanitize_filename(srtext) if srtext else f"custom_srid_{srid}"
            
            version_suffix = ""
            if format_type == "prj_GMv20":
                version_suffix = "_v20"
            elif format_type == "prj_GMv25":
                version_suffix = "_v25"
            # Если format_type другой, суффикс не добавляется, что может быть нежелательно.
            # Можно добавить _unknown_format или использовать srid как часть имени для уникальности.
            # Пока оставляем так, предполагая, что format_type будет одним из ожидаемых.
            
            return f"{base_name_from_srtext}{version_suffix}.prj"

        # 3. Обработка для других систем (не UTM и не custom)
        # Попытка сформировать имя из auth_name и auth_srid (или srid)
        # Это может быть полезно для EPSG кодов, которые не UTM.
        # auth_srid здесь может быть равен srid, если он не указан отдельно.
        name_prefix = auth_name if auth_name and auth_name.upper() != "EPSG" else "EPSG"
        identifier = cs_data.get('auth_srid', srid) # Используем auth_srid если есть, иначе srid

        # Если имя все еще выглядит как просто номер SRID, или auth_name неинформативен,
        # попробуем извлечь имя из PROJCS или GEOGCS в srtext (если он есть).
        # Это для случаев, когда auth_name это просто "EPSG" или сам номер srid.
        if (name_prefix == "EPSG" or name_prefix == srid) and srtext:
            try:
                parsed_name_from_wkt = ""
                # Ищем PROJCS[...] или GEOGCS[...]
                match = re.search(r'(PROJCS|GEOGCS)\["([^"]+)"', srtext, re.IGNORECASE)
                if match and match.group(2):
                    parsed_name_from_wkt = self._sanitize_filename(match.group(2))
                
                if parsed_name_from_wkt: # Если удалось что-то извлечь из WKT
                    return f"{parsed_name_from_wkt}_{identifier}.prj"
                # Если из WKT не удалось извлечь имя, возвращаемся к name_prefix_identifier
            except Exception as e:
                logger.debug(f"Не удалось извлечь имя из srtext для SRID {srid}: {e}")
        
        # Если не удалось извлечь из WKT или это не тот случай, используем auth_name/auth_srid
        # или EPSG/srid
        if name_prefix and identifier:
             final_prefix = self._sanitize_filename(str(name_prefix))
             final_identifier = self._sanitize_filename(str(identifier))
             return f"{final_prefix}_{final_identifier}.prj"

        # 4. Крайний случай, если ничего не подошло (маловероятно при текущей логике)
        # Формируем имя из srtext (если есть и он короткий) или из srid
        fallback_name_base = self._sanitize_filename(srtext) if srtext and len(srtext) < 50 else f"cs_{srid}"
        return f"{fallback_name_base}.prj" 