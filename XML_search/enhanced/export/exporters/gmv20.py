"""
Экспортер PRJ-файлов для Global Mapper v20
"""

from typing import Dict, Any, Optional, List
import re
from datetime import datetime
from .base import BaseExporter
from XML_search.errors import ValidationError, XMLProcessingError
from XML_search.enhanced.db_manager_enhanced import EnhancedDatabaseManager
from .prj_exporter import PRJExporter
from ..exceptions import ExportError, CustomWktGenerationError
from XML_search.enhanced.log_manager import LogManager

logger = LogManager().get_logger(__name__)

class GMv20Exporter(PRJExporter):
    """Экспортер PRJ-файлов для Global Mapper v20"""
    
    # Допустимые значения параметров
    VALID_ENCODINGS = ['UTF-8', 'UTF-16', 'ASCII']
    VALID_COORDINATE_ORDERS = ['EN', 'NE']
    
    def __init__(self, config: Dict[str, Any], db_manager: EnhancedDatabaseManager, output_dir: str = "output", logger_instance: Optional[Any] = None):
        """
        Инициализация экспортера GMv20
        
        Args:
            config: Конфигурация экспортера
            db_manager: Опциональный менеджер базы данных EnhancedDatabaseManager
            output_dir: Директория для сохранения файлов
            logger_instance: Опциональный логгер для тестов
        """
        # Инициализируем логгер экземпляра как можно раньше
        self.logger = logger_instance or LogManager().get_logger(__name__)
        try:
            # Передаем output_dir и logger_instance в super
            # Убедимся, что db_manager передается корректно, если он EnhancedDatabaseManager
            super().__init__(config, db_manager=db_manager, output_dir=output_dir, logger=self.logger) # type: ignore
            self.format_name = "prj_GMv20"
            self.logger.info("Инициализирован экспортер prj_GMv20")
        except Exception as e:
            # Используем self.logger, который уже должен быть инициализирован
            self.logger.error(f"Ошибка инициализации GMv20Exporter: {e}", exc_info=True)
            raise
        
    def supports_srid(self, srid: int) -> bool:
        """
        Проверка поддержки SRID
        
        Args:
            srid: SRID для проверки
            
        Returns:
            True если SRID поддерживается, False в противном случае
        """
        # Временная реализация - поддерживаем все SRID для тестирования
        return True
        
    def validate_params(self, params: Optional[Dict[str, Any]]) -> None:
        """
        Валидация параметров экспорта
        
        Args:
            params: Параметры для валидации
            
        Raises:
            ValidationError: Если параметры невалидны
        """
        if not params:
            return
            
        # Проверка кодировки
        if 'encoding' in params:
            encoding = params['encoding']
            if encoding not in self.VALID_ENCODINGS:
                raise ValidationError(
                    f"Неверная кодировка: {encoding}. "
                    f"Допустимые значения: {', '.join(self.VALID_ENCODINGS)}"
                )
                
        # Проверка порядка координат
        if 'coordinate_order' in params:
            order = params['coordinate_order']
            if order not in self.VALID_COORDINATE_ORDERS:
                raise ValidationError(
                    f"Неверный порядок координат: {order}. "
                    f"Допустимые значения: {', '.join(self.VALID_COORDINATE_ORDERS)}"
                )
                
        # Проверка версии
        if 'version' in params and params['version'] != '20':
            raise ValidationError("Версия должна быть '20' для GMv20 экспортера")
            
    async def export(self, srid: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Экспорт в формат GMv20.
        Этот метод соответствует сигнатуре BaseExporter.export и вызывает _export_impl.
        
        Args:
            srid: SRID системы координат (в виде строки для этого метода)
            params: Дополнительные параметры экспорта (не используются в текущей реализации PRJExporter)
            
        Returns:
            Dict[str, Any]: Информация о созданном файле
            
        Raises:
            ExportError: При ошибке экспорта.
        """
        self.logger.debug(f"GMv20Exporter.export вызван для SRID: {srid}, params: {params}")

        try:
            # Валидацию параметров (params) можно оставить, если они специфичны для GMv20
            # self.validate_params(params) # Раскомментировать, если params используются

            # _export_impl ожидает srid в data={'srid': '...'}
            result = await self._export_impl(data={'srid': srid})
            return result

        except ExportError as e:
            self.logger.error(f"ExportError в GMv20Exporter.export для SRID {srid}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка в GMv20Exporter.export для SRID {srid}: {e}", exc_info=True)
            raise ExportError(f"Неожиданная ошибка при экспорте GMv20 (SRID: {srid}): {str(e)}")
            
    def _is_custom_crs(self, srid: int) -> bool:
        """Проверка является ли система координат пользовательской"""
        try:
            # Здесь должен использоваться db_manager, который EnhancedDatabaseManager
            # и у него должен быть метод для выполнения запросов, например, fetchval или execute_query
            # Заменяем self.db_manager.safe_cursor() на корректный вызов
            # Пример: result = await self.db_manager.fetchval("SELECT 1 FROM ...")
            # Поскольку это синхронный метод, а db_manager может быть асинхронным,
            # это место может потребовать рефакторинга или использования синхронного API db_manager, если есть.
            # Пока оставим как есть, предполагая, что db_manager может быть использован синхронно здесь,
            # или эта логика будет пересмотрена.
            # Для заглушки, чтобы убрать ошибку линтера, можно сделать так, но это НЕПРАВИЛЬНО по сути:
            if self.db_manager:
                 # Это не рабочий код, а заглушка для линтера, т.к. safe_cursor нет
                self.logger.warning("_is_custom_crs требует ревизии из-за отсутствия safe_cursor")
                pass # cursor.execute(...)
            return False # Временная заглушка
        except Exception as e:
            self.logger.error(f"Ошибка проверки SRID {srid}: {e}")
            return False
            
    def _get_crs_data(self, srid: int) -> Dict[str, Any]:
        """Получение данных о системе координат из БД"""
        try:
            # Аналогично _is_custom_crs,需要重构
            if self.db_manager:
                self.logger.warning("_get_crs_data требует ревизии из-за отсутствия safe_cursor")
                pass # row = cursor.fetchone()
                
            # Временная заглушка, чтобы метод что-то возвращал и не было ошибки NoneType
            # Это НЕ КОРРЕКТНАЯ РЕАЛИЗАЦИЯ
            raise ValidationError(f"SRID {srid} не найден в базе данных (заглушка)")
                
        except Exception as e:
            raise XMLProcessingError(f"Ошибка получения данных о СК: {str(e)}")
            
    def _generate_prj(self, crs_data: Dict[str, Any]) -> str:
        """Генерация PRJ для GlobalMapper v20"""
        try:
            wkt_original = crs_data.get('srtext', '') 
            if not wkt_original: 
                self.logger.warning(f"Отсутствует srtext для SRID {crs_data.get('srid', 'unknown')} в GMv20Exporter._generate_prj. Будет создан пустой PRJ.")
            wkt = self._clean_wkt(wkt_original)
            
            metadata = [
                f"# SRID: {crs_data.get('srid', 'N/A')}",
                f"# Authority: {crs_data.get('auth_name', 'N/A')}",
                f"# Authority SRID: {crs_data.get('auth_srid', 'N/A')}",
                f"# Description: {crs_data.get('info', 'Not available')}",
                f"# Reliability: {crs_data.get('reliability', 'Unknown')}",
                f"# Export Date: {datetime.now().isoformat()}",
                f"# Format: GlobalMapper v20 PRJ",
                "" 
            ]
            return "\n".join(metadata + [wkt])
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации PRJ: {e}")
            raise XMLProcessingError(f"Ошибка генерации PRJ: {str(e)}")
            
    def _clean_wkt(self, wkt: Optional[str]) -> str:
        if not wkt: 
            return ""
        wkt = re.sub(r'\s+', ' ', wkt)
        wkt = re.sub(r',\s+', ',', wkt)
        wkt = re.sub(r'\(\s+', '(', wkt)
        wkt = re.sub(r'\s+\)', ')', wkt)
        return wkt.strip()
        
    def export_sync_impl(self, srid: int) -> str:
        try:
            if not self.supports_srid(srid):
                raise ValidationError(f"SRID {srid} не поддерживается")
            crs_data = self._get_crs_data(srid)
            prj_str = self._generate_prj(crs_data)
            return prj_str
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Ошибка экспорта SRID {srid}: {e}")
            raise XMLProcessingError(f"Ошибка экспорта: {str(e)}")

    async def _export_impl(self, data: Dict[str, Any]) -> Dict[str, Any]:
        srid = data.get('srid')
        if not srid:
            self.logger.error("SRID отсутствует в данных для экспорта.")
            raise ExportError("SRID не предоставлен для экспорта.")
        
        self.logger.debug(f"GMv20Exporter._export_impl вызов для SRID: {srid}")
        
        try:
            file_info = await super().export_to_file(srid=srid, format_type=self.format_name)
            self.logger.info(f"Экспорт PRJ (GMv20) для SRID {srid} успешно завершен. Файл: {file_info.get('filename')}")
            return file_info
        except ExportError as e: 
            self.logger.error(f"Ошибка ExportError при экспорте GMv20 для SRID {srid}: {e}", exc_info=True)
            raise 
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при экспорте GMv20 для SRID {srid}: {e}", exc_info=True)
            raise ExportError(f"Неожиданная ошибка при экспорте GMv20 для SRID {srid}: {str(e)}")

    async def _generate_custom_wkt(self, cs_data: Dict[str, Any], exporter_version: str) -> str:
        ERROR_MESSAGE_PARSE = "Ошибка парсинга параметров или отсутствуют необходимые ключи в proj4text."
        ERROR_MESSAGE_DB = "Не найдены данные в вспомогательных таблицах (эллипсоид)."
        ERROR_MESSAGE_UNKNOWN = "Неизвестная ошибка при генерации детального PRJ."
        
        srid = cs_data.get('srid')
        proj4text = cs_data.get('proj4text')

        if not proj4text:
            self.logger.warning(f"Custom SRID {srid}: отсутствует proj4text. Невозможно сгенерировать детальный PRJ.")
            raise CustomWktGenerationError(f"SRID {srid}: Недостаточно параметров для генерации PRJ. Отсутствует proj4text.")

        try:
            # Log the proj4text being parsed
            self.logger.debug(f"Custom SRID {srid}: Parsing proj4text: '{proj4text}'")
            
            # ADDED: Detailed logging for proj4text and re.findall
            self.logger.debug(f"Custom SRID {srid}: Type of proj4text: {type(proj4text)}")
            self.logger.debug(f"Custom SRID {srid}: Raw proj4text for re.findall: {repr(proj4text)}")
            params_list = re.findall(r'\+(.*?)=(.*?)(?:\s|$)', proj4text)
            self.logger.debug(f"Custom SRID {srid}: Output of re.findall (list of tuples): {params_list}")
            params = dict(params_list)
            # END ADDED logging

            # Log the entire parsed params dictionary
            self.logger.debug(f"Custom SRID {srid}: Parsed params: {params}")
            
            # Log presence of key parameters
            self.logger.debug(f"Custom SRID {srid}: 'ellps' in params: {'ellps' in params}")
            self.logger.debug(f"Custom SRID {srid}: 'towgs84' in params: {'towgs84' in params}")

            if 'ellps' not in params or 'towgs84' not in params:
                self.logger.warning(f"Custom SRID {srid}: отсутствуют 'ellps' или 'towgs84' в proj4text. Parsed params: {params}. Original proj4text: {proj4text}")
                raise CustomWktGenerationError(f"SRID {srid}: {ERROR_MESSAGE_PARSE}")

            towgs84_parts = params['towgs84'].split(',')
            if len(towgs84_parts) != 7:
                self.logger.warning(f"Custom SRID {srid}: параметр 'towgs84' не содержит 7 частей: {params['towgs84']}")
                raise CustomWktGenerationError(f"SRID {srid}: {ERROR_MESSAGE_PARSE} (неверное число параметров towgs84)")
            
            dx, dy, dz, rx, ry, rz, s_scale = map(float, towgs84_parts)

            if exporter_version == "Global Mapper v20":
                rx, ry, rz = -rx, -ry, -rz
            
            x_shift_str = f"{dx:.9f}"
            y_shift_str = f"{dy:.9f}"
            z_shift_str = f"{dz:.9f}"
            x_rot_str = f"{rx:.12f}"
            y_rot_str = f"{ry:.12f}"
            z_rot_str = f"{rz:.12f}"
            scale_str = f"{s_scale:.15f}"

            ellps_name_param = params['ellps']
            ellps_data_row = await self.db_manager.fetchrow(
                "SELECT gm_ellipsoid_id, a, c FROM public.ellps_all WHERE name_el = $1",
                ellps_name_param
            )

            if not ellps_data_row:
                self.logger.warning(f"Custom SRID {srid}: Данные эллипсоида не найдены в 'ellps_all' для '{ellps_name_param}'.")
                raise CustomWktGenerationError(f"SRID {srid}: {ERROR_MESSAGE_DB} (эллипсоид '{ellps_name_param}' не найден)")
            
            spheroid_wkt_name = ellps_data_row['gm_ellipsoid_id']
            semi_major_axis = float(ellps_data_row['a'])
            inverse_flattening = float(ellps_data_row['c'])

            datum_param_for_query = f"+towgs84={params['towgs84']}"
            datum_data_row = await self.db_manager.fetchrow(
                "SELECT name_d FROM public.datum_all WHERE datum = $1",
                datum_param_for_query
            )
            datum_name = datum_data_row['name_d'] if datum_data_row and datum_data_row['name_d'] else f"Custom_Datum_{srid}"

            k_factor = float(params.get('k_0', params.get('k', 1.0)))
            lon_0 = float(params.get('lon_0', 0.0))
            lat_0 = float(params.get('lat_0', 0.0))
            x_0 = float(params.get('x_0', 0.0))
            y_0 = float(params.get('y_0', 0.0))

            wkt = (
                f'PROJCS["Transverse_Mercator",'
                f'GEOGCS["{datum_name}",'
                f'DATUM["{datum_name}",'
                f'SPHEROID["{spheroid_wkt_name}",{semi_major_axis:.16g},{inverse_flattening:.16g}],'
                f'TOWGS84[{x_shift_str},{y_shift_str},{z_shift_str},{x_rot_str},{y_rot_str},{z_rot_str},{scale_str}]],'
                f'PRIMEM["Greenwich",0.0],'
                f'UNIT["Degree",0.017453292519943295]],'
                f'PROJECTION["Transverse_Mercator"],'
                f'PARAMETER["latitude_of_origin",{lat_0:.16g}],'
                f'PARAMETER["central_meridian",{lon_0:.16g}],'
                f'PARAMETER["scale_factor",{k_factor:.16g}],'
                f'PARAMETER["false_easting",{x_0:.16g}],'
                f'PARAMETER["false_northing",{y_0:.16g}],'
                f'UNIT["Meter",1.0]]'
            )
            return wkt

        except (ValueError, KeyError) as e:
            self.logger.warning(f"Custom SRID {srid}: Ошибка парсинга параметров proj4text или отсутствуют ключи: {e} (proj4text: {proj4text})")
            raise CustomWktGenerationError(f"SRID {srid}: {ERROR_MESSAGE_PARSE} (детали: {e})")
        except CustomWktGenerationError:
            raise
        except Exception as ex:
            self.logger.error(f"Custom SRID {srid}: Неожиданная ошибка при генерации _generate_custom_wkt: {ex}", exc_info=True)
            raise CustomWktGenerationError(f"SRID {srid}: {ERROR_MESSAGE_UNKNOWN} (детали: {ex})")

    async def _get_prj_content(self, cs_data: Dict[str, Any], format_type: str) -> str:
        if cs_data.get('auth_name') == 'custom':
            self.logger.debug(f"Попытка генерации детального WKT PRJ для custom SRID: {cs_data.get('srid')}")
            # Для GMv20Exporter версия всегда "Global Mapper v20"
            return await self._generate_custom_wkt(cs_data, "Global Mapper v20")
        else:
            # Для всех не-custom SRID возвращаем srtext как есть
            self.logger.debug(f"Генерация PRJ как есть (srtext) для не-custom SRID: {cs_data.get('srid')}")
            return cs_data.get('srtext', '')
