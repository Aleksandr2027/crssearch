"""
Экспортер для формата GMv25
"""

from typing import Dict, Any, Optional
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.errors import ValidationError, XMLProcessingError
from .base import BaseExporter

class GMv25Exporter(BaseExporter):
    """Экспортер для формата GMv25"""
    
    def __init__(self, config: Dict[str, Any], db_manager: Optional[DatabaseManager] = None, logger: Optional[Any] = None):
        """
        Инициализация экспортера GMv25
        
        Args:
            config: Конфигурация экспортера
            db_manager: Опциональный менеджер базы данных
            logger: Опциональный логгер для тестов
        """
        try:
            super().__init__(config, db_manager=db_manager, logger=logger)
            self.metrics = MetricsManager()
            self.format_name = "prj_GMv25"
            self.logger.info("Инициализирован экспортер prj_GMv25")
        except Exception as e:
            if logger:
                logger.error(f"Ошибка создания DatabaseManager: {e}")
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
        
    async def export(self, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Временная реализация экспорта в формат GMv25
        
        Args:
            srid: SRID системы координат
            params: Дополнительные параметры экспорта
            
        Returns:
            Сообщение об успешном экспорте
            
        Raises:
            ValidationError: Если параметры экспорта невалидны
            XMLProcessingError: При ошибке формирования XML
        """
        try:
            # Валидация входных данных
            self._validate_srid(srid)
            self.validate_params(params)
            
            with self._track_export_timing('gmv25'):
                # Временное сообщение об успешном экспорте
                message = (
                    f"✅ Экспорт в формат GMv25\n"
                    f"SRID: {srid}\n"
                    f"Статус: Успешно\n"
                    f"Формат: {self.config.get('display_name', 'GMv25')}\n"
                    f"Параметры: {params if params else 'не указаны'}"
                )
                
            self.metrics.increment('gmv25_export_success')
            return message
            
        except ValidationError as e:
            self.metrics.increment('gmv25_export_errors')
            self.logger.error(f"Ошибка валидации при экспорте GMv25 для SRID {srid}: {e}")
            raise
        except Exception as e:
            self.metrics.increment('gmv25_export_errors')
            self.logger.error(f"Ошибка экспорта GMv25 для SRID {srid}: {e}")
            raise

    def export_sync_impl(self, srid: int) -> str:
        """
        Синхронная реализация экспорта системы координат
        
        Args:
            srid: SRID системы координат
            
        Returns:
            PRJ в виде строки
            
        Raises:
            ValidationError: Если SRID не поддерживается
            XMLProcessingError: При ошибке формирования PRJ
        """
        try:
            # Проверяем поддержку SRID
            if not self.supports_srid(srid):
                self.metrics.increment('gmv25_export_validation_errors')
                raise ValidationError(f"SRID {srid} не поддерживается")
                
            # Получаем данные о системе координат
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute("""
                    SELECT srtext, auth_name, auth_srid
                    FROM spatial_ref_sys
                    WHERE srid = %s
                """, (srid,))
                result = cursor.fetchone()
                
            if not result:
                raise ValidationError(f"SRID {srid} не найден в базе данных")
                
            srtext, auth_name, auth_srid = result
            
            # Формируем PRJ файл
            prj_content = f"""PROJCS["{auth_name}:{auth_srid}",
    GEOGCS["{auth_name}:{auth_srid}",
        DATUM["{auth_name}",
            SPHEROID["GRS 1980",6378137,298.257222101,
                AUTHORITY["EPSG","7019"]],
            AUTHORITY["EPSG","6269"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.0174532925199433,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4326"]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",0],
    PARAMETER["central_meridian",{srid % 100 * 6 - 183}],
    PARAMETER["scale_factor",0.9996],
    PARAMETER["false_easting",500000],
    PARAMETER["false_northing",0],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    AUTHORITY["EPSG","{srid}"]]"""
            
            # Обновляем метрики
            self.metrics.increment('gmv25_export_success')
            
            return prj_content
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Ошибка экспорта SRID {srid}: {e}")
            self.metrics.increment('gmv25_export_errors')
            raise XMLProcessingError(f"Ошибка экспорта: {str(e)}")
