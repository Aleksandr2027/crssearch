"""
Экспортер для формата GMv20
"""

from typing import Dict, Any, Optional, List
import re
from datetime import datetime
from .base import BaseExporter
from XML_search.errors import ValidationError, XMLProcessingError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager

class GMv20Exporter(BaseExporter):
    """Экспортер для формата GMv20"""
    
    # Допустимые значения параметров
    VALID_ENCODINGS = ['UTF-8', 'UTF-16', 'ASCII']
    VALID_COORDINATE_ORDERS = ['EN', 'NE']
    
    def __init__(self, config: Dict[str, Any], db_manager: Optional[DatabaseManager] = None, logger: Optional[Any] = None):
        """
        Инициализация экспортера GMv20
        
        Args:
            config: Конфигурация экспортера
            db_manager: Опциональный менеджер базы данных
            logger: Опциональный логгер для тестов
        """
        try:
            super().__init__(config, db_manager=db_manager, logger=logger)
            self.metrics = MetricsManager()
            self.format_name = "prj_GMv20"
            self.logger.info("Инициализирован экспортер prj_GMv20")
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
            
    async def export(self, srid: int, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Экспорт в формат GMv20
        
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
            
            with self._track_export_timing('gmv20'):
                # Получаем параметры с значениями по умолчанию
                export_params = {
                    'format': 'prj',
                    'version': '20',
                    'encoding': 'UTF-8',
                    'coordinate_order': 'EN'
                }
                if params:
                    export_params.update(params)
                
                # Временное сообщение об успешном экспорте
                message = (
                    f"✅ Экспорт в формат GMv20\n"
                    f"SRID: {srid}\n"
                    f"Статус: Успешно\n"
                    f"Формат: {self.config.get('display_name', 'GMv20')}\n"
                    f"Параметры: {export_params}"
                )
                
            self.metrics.increment('gmv20_export_success')
            return message
            
        except ValidationError as e:
            self.metrics.increment('gmv20_export_errors')
            self.logger.error(f"Ошибка валидации при экспорте GMv20 для SRID {srid}: {e}")
            raise
        except Exception as e:
            self.metrics.increment('gmv20_export_errors')
            self.logger.error(f"Ошибка экспорта GMv20 для SRID {srid}: {e}")
            raise
            
    def _is_custom_crs(self, srid: int) -> bool:
        """Проверка является ли система координат пользовательской"""
        try:
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute("""
                    SELECT 1 FROM spatial_ref_sys 
                    WHERE srid = %s AND auth_name = 'custom'
                """, (srid,))
                return bool(cursor.fetchone())
        except Exception as e:
            self.logger.error(f"Ошибка проверки SRID {srid}: {e}")
            return False
            
    def _get_crs_data(self, srid: int) -> Dict[str, Any]:
        """Получение данных о системе координат из БД"""
        try:
            with self.db_manager.safe_cursor() as cursor:
                cursor.execute("""
                    SELECT s.srid, s.auth_name, s.auth_srid, s.srtext, s.proj4text,
                           c.info, c.p as reliability
                    FROM spatial_ref_sys s
                    LEFT JOIN custom_geom c ON s.srid = c.srid
                    WHERE s.srid = %s
                """, (srid,))
                row = cursor.fetchone()
                
                if not row:
                    raise ValidationError(f"SRID {srid} не найден в базе данных")
                    
                return {
                    'srid': row[0],
                    'auth_name': row[1],
                    'auth_srid': row[2],
                    'srtext': row[3],
                    'proj4text': row[4],
                    'info': row[5],
                    'reliability': row[6]
                }
                
        except Exception as e:
            raise XMLProcessingError(f"Ошибка получения данных о СК: {str(e)}")
            
    def _generate_prj(self, crs_data: Dict[str, Any]) -> str:
        """Генерация PRJ для GlobalMapper v20"""
        try:
            # Очищаем WKT от лишних пробелов и переносов строк
            wkt = self._clean_wkt(crs_data['srtext'])
            
            # Формируем комментарии с метаданными
            metadata = [
                f"# SRID: {crs_data['srid']}",
                f"# Authority: {crs_data['auth_name']}",
                f"# Authority SRID: {crs_data['auth_srid']}",
                f"# Description: {crs_data['info'] or 'Not available'}",
                f"# Reliability: {crs_data['reliability'] or 'Unknown'}",
                f"# Export Date: {datetime.now().isoformat()}",
                f"# Format: GlobalMapper v20 PRJ",
                ""  # Пустая строка для разделения метаданных и WKT
            ]
            
            # Объединяем метаданные и WKT
            return "\n".join(metadata + [wkt])
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации PRJ: {e}")
            raise XMLProcessingError(f"Ошибка генерации PRJ: {str(e)}")
            
    def _clean_wkt(self, wkt: str) -> str:
        """
        Очистка WKT от лишних пробелов и переносов строк
        
        Args:
            wkt: WKT строка для очистки
            
        Returns:
            Очищенная WKT строка
        """
        # Удаляем лишние пробелы и переносы строк
        wkt = re.sub(r'\s+', ' ', wkt)
        # Удаляем пробелы после запятых
        wkt = re.sub(r',\s+', ',', wkt)
        # Удаляем пробелы после скобок
        wkt = re.sub(r'\(\s+', '(', wkt)
        wkt = re.sub(r'\s+\)', ')', wkt)
        return wkt.strip()
        
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
                self.metrics.increment('gmv20_export_validation_errors')
                raise ValidationError(f"SRID {srid} не поддерживается")
                
            # Получаем данные о системе координат
            crs_data = self._get_crs_data(srid)
            
            # Генерируем PRJ
            prj_str = self._generate_prj(crs_data)
            
            # Обновляем метрики
            self.metrics.increment('gmv20_export_success')
            
            return prj_str
            
        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Ошибка экспорта SRID {srid}: {e}")
            self.metrics.increment('gmv20_export_errors')
            raise XMLProcessingError(f"Ошибка экспорта: {str(e)}")
