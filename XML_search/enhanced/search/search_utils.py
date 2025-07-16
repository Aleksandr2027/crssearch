"""
Улучшенные утилиты для поиска
"""

from typing import List, Dict, Any, Optional, Tuple
from Levenshtein import ratio
import logging
from XML_search.enhanced.db_manager import DatabaseManager # Убедитесь, что этот импорт корректен
import re

class SearchUtils:
    """Расширенные утилиты для поиска с улучшенной функциональностью"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Инициализация утилит поиска
        
        Args:
            logger: Логгер
        """
        self.logger = logger or logging.getLogger(__name__)

    async def execute_search_query(self, variant: str, db_manager: DatabaseManager, limit: int, search_fields: List[str]) -> List[Dict[str, Any]]:
        """
        Выполняет поисковый запрос к базе данных, используя ILIKE для текстовых полей.
        Ищет в таблицах custom_geom и spatial_ref_sys.

        Args:
            variant: Вариант поискового запроса.
            db_manager: Менеджер базы данных.
            limit: Максимальное количество результатов.
            search_fields: Список абстрактных полей для поиска (e.g., ['name', 'description', 'srid']).
        """
        results: List[Dict[str, Any]] = []
        if not db_manager:
            if self.logger:
                self.logger.error("execute_search_query: db_manager не предоставлен.")
            return results

        params_custom: List[Any] = []
        params_spatial: List[Any] = []

        # --- Query for custom_geom ---
        cg_wheres: List[str] = []
        cg_params_count = 0
        if "name" in search_fields: 
            cg_wheres.append(f"name ILIKE ${cg_params_count + 1}")
            params_custom.append(f"%{variant}%")
            cg_params_count += 1
        if "description" in search_fields: 
            cg_wheres.append(f"info ILIKE ${cg_params_count + 1}")
            params_custom.append(f"%{variant}%")
            cg_params_count += 1
        if "srid" in search_fields: 
            cg_wheres.append(f"CAST(srid AS TEXT) ILIKE ${cg_params_count + 1}")
            params_custom.append(f"%{variant}%")
            cg_params_count += 1
        
        custom_geom_query_part = ""
        if cg_wheres:
            # Формируем часть запроса для custom_geom
            # Используем поля name, srid, info из custom_geom для соответствующих
            # колонок auth_name, auth_srid, srtext в UNION-запросе.
            # Для колонки 'type' подставляем строковый литерал 'custom'.
            custom_geom_query_part = (
                f"(SELECT srid, "
                f"       name AS auth_name, "
                f"       srid AS auth_srid, "
                f"       info AS srtext, "
                f"       name, "
                f"       info, "
                f"       'custom' AS type, "  # Используем 'custom' как значение для type
                f"       CAST('custom_geom' AS TEXT) as source_table "
                f" FROM custom_geom "\
                f" WHERE ({' OR '.join(cg_wheres)}) AND (srid BETWEEN 100000 AND 101500))"\
            )
            # params_custom (параметры для cg_wheres) должны быть уже заполнены выше

        # --- Query for spatial_ref_sys ---
        srs_wheres: List[str] = []
        srs_params_count = 0
        base_idx_srs = srs_params_count + 1 # Для нумерации плейсхолдеров в srs_wheres
        if "name" in search_fields: 
            srs_wheres.append(f"auth_name ILIKE ${base_idx_srs + len(srs_wheres)}")
        if "description" in search_fields: 
            srs_wheres.append(f"srtext ILIKE ${base_idx_srs + len(srs_wheres)}")
        if "srid" in search_fields: 
            srs_wheres.append(f"CAST(srid AS TEXT) ILIKE ${base_idx_srs + len(srs_wheres)}")
            # srs_wheres.append(f"CAST(auth_srid AS TEXT) ILIKE ${base_idx_srs + len(srs_wheres)}") # Если нужно искать и по auth_srid

        spatial_ref_sys_query_part = ""
        if srs_wheres:
            srs_params_count = len(srs_wheres)
            spatial_ref_sys_query_part = f"SELECT srid, auth_name, auth_srid, srtext, CAST(NULL AS TEXT) as name, CAST(NULL AS TEXT) as info, CAST(NULL AS TEXT) as type, CAST('spatial_ref_sys' AS TEXT) as source_table FROM spatial_ref_sys WHERE ({' OR '.join(srs_wheres)}) AND (srid BETWEEN 32601 AND 32660)"
            params_spatial.extend([f"%{variant}%"] * srs_params_count)
        
        # --- Combine queries ---
        full_query = ""
        params: List[Any] = []

        if custom_geom_query_part and spatial_ref_sys_query_part:
            # Переиндексация плейсхолдеров для spatial_ref_sys_query_part, если есть custom_geom_query_part
            placeholder_offset = cg_params_count
            reindexed_srs_wheres: List[str] = []
            srs_param_idx_start = placeholder_offset + 1
            if "name" in search_fields: reindexed_srs_wheres.append(f"auth_name ILIKE ${srs_param_idx_start + len(reindexed_srs_wheres)}")
            if "description" in search_fields: reindexed_srs_wheres.append(f"srtext ILIKE ${srs_param_idx_start + len(reindexed_srs_wheres)}")
            if "srid" in search_fields: reindexed_srs_wheres.append(f"CAST(srid AS TEXT) ILIKE ${srs_param_idx_start + len(reindexed_srs_wheres)}")
            
            if reindexed_srs_wheres: # Только если есть что искать в srs
                spatial_ref_sys_query_part_reindexed = f"SELECT srid, auth_name, auth_srid, srtext, CAST(NULL AS TEXT) as name, CAST(NULL AS TEXT) as info, CAST(NULL AS TEXT) as type, CAST('spatial_ref_sys' AS TEXT) as source_table FROM spatial_ref_sys WHERE ({' OR '.join(reindexed_srs_wheres)}) AND (srid BETWEEN 32601 AND 32660)"
                full_query = f"({custom_geom_query_part}) UNION ALL ({spatial_ref_sys_query_part_reindexed})"
            else: # Если в srs нечего искать, используем только custom_geom
                 full_query = custom_geom_query_part
            params = params_custom + params_spatial
        elif custom_geom_query_part:
            full_query = custom_geom_query_part
            params = params_custom
        elif spatial_ref_sys_query_part:
            full_query = spatial_ref_sys_query_part
            params = params_spatial
        
        if full_query:
            if limit > 0:
                full_query += f" LIMIT {limit}"
            
            # Добавляем специальную отладку для 4ertovo ПЕРЕД выполнением
            if "4ertovo" in variant.lower() or "chert" in variant.lower():
                self.logger.info(f"[4ERTOVO DEBUG] Выполняю запрос для термина: '{variant}'")
                self.logger.info(f"[4ERTOVO DEBUG] SQL: {full_query}")
                self.logger.info(f"[4ERTOVO DEBUG] Параметры: {params}")
                self.logger.info(f"[4ERTOVO DEBUG] Поля поиска: {search_fields}")
            
            try:
                async with db_manager.connection() as conn: # Используем connection()
                    # self.logger.debug(f"Executing combined search query: {full_query} with params: {params}")
                    db_results = await conn.fetch(full_query, *params) # Используем conn.fetch и распаковку параметров
                    
                    # Отладка результатов для 4ertovo
                    if "4ertovo" in variant.lower() or "chert" in variant.lower():
                        self.logger.info(f"[4ERTOVO DEBUG] Получено результатов: {len(db_results) if db_results else 0}")
                        if db_results:
                            for i, row in enumerate(db_results[:3]):  # Показываем первые 3 результата
                                self.logger.info(f"[4ERTOVO DEBUG] Результат {i+1}: {dict(row)}")
                    
                    if db_results:
                        results.extend([dict(row) for row in db_results]) # Преобразуем строки в словари
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка при выполнении поискового запроса для варианта '{variant}': {e}", exc_info=True)
                    self.logger.error(f"Failed query: {full_query} with params: {params}")
        
        return results
    
    def apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, bool]) -> List[Dict[str, Any]]:
        if not filters:
            return results
            
        filtered_results = results.copy()
        
        try:
            if filters.get('region'):
                filtered_results = [r for r in filtered_results if self._is_region(r)]
                self.logger.debug(f"После применения фильтра 'region': {len(filtered_results)} результатов")
                
            if filters.get('custom'):
                filtered_results = [r for r in filtered_results if self._is_custom(r)]
                self.logger.debug(f"После применения фильтра 'custom': {len(filtered_results)} результатов")
                
            if filters.get('active'):
                filtered_results = [r for r in filtered_results if not r.get('deprecated')]
                self.logger.debug(f"После применения фильтра 'active': {len(filtered_results)} результатов")
            
            if filters.get('utm'):
                filtered_results = [r for r in filtered_results if 'utm' in r.get('name', '').lower()]
                self.logger.debug(f"После применения фильтра 'utm': {len(filtered_results)} результатов")
                
            if filters.get('msk'):
                filtered_results = [r for r in filtered_results if r.get('name', '').lower().startswith(('msk', 'мск'))]
                self.logger.debug(f"После применения фильтра 'msk': {len(filtered_results)} результатов")
                
            if filters.get('gsk'):
                filtered_results = [r for r in filtered_results if r.get('name', '').lower().startswith(('gsk', 'гск'))]
                self.logger.debug(f"После применения фильтра 'gsk': {len(filtered_results)} результатов")
                
        except Exception as e:
            self.logger.error(f"Ошибка при применении фильтров: {str(e)}")
            return results
        
        return filtered_results
        
    def fuzzy_search(self, search_term: str, target: str, threshold: float = 0.85) -> bool:
        if not search_term or not target:
            return False
        try:
            similarity = ratio(search_term.lower(), target.lower())
            return similarity >= threshold
        except Exception as e:
            self.logger.error(f"Ошибка при нечетком поиске: {str(e)}")
            return False
        
    def _is_region(self, result: Dict[str, Any]) -> bool:
        return result.get('auth_name') == 'custom'
        
    def _is_custom(self, result: Dict[str, Any]) -> bool:
        return result.get('auth_name') == 'custom' and result.get('auth_srid', 0) >= 100000 
        
    def sort_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Сортировка результатов по релевантности.
        Ожидается, что поле 'adjusted_relevance' уже рассчитано и присутствует в результатах.
        """
        if not results:
            return []
            
        try:
            # Сортируем по 'adjusted_relevance' (рассчитанному в EnhancedSearchEngine), 
            # затем по SRID для стабильности
            sorted_results = sorted(
                results, 
                key=lambda x: (x.get('adjusted_relevance', -1.0), x.get('srid', 0)), 
                reverse=True # Сортируем по убыванию релевантности
            )
            return sorted_results
            
        except Exception as e:
            self.logger.error(f"Ошибка при сортировке результатов: {str(e)}")
            return results

    def calculate_adjusted_relevance(self, original_relevance_from_db: float, 
                                     priority_level: int, 
                                     original_query: str, 
                                     name_from_cs: str, 
                                     description_from_cs: str) -> float:
        """
        Расчет скорректированной релевантности с учетом приоритета варианта 
        и схожести с оригинальным запросом.
        """
        relevance_to_name = ratio(original_query.lower(), name_from_cs.lower())
        relevance_to_description = ratio(original_query.lower(), description_from_cs.lower())
        
        textual_similarity_score = max(relevance_to_name, relevance_to_description)
        db_score = original_relevance_from_db if original_relevance_from_db is not None else 0.0

        # Веса для компонентов
        w_db = 0.3 
        w_textual = 0.5 
        
        # Модификатор приоритета
        # priority_level 0 (оригинал) -> 1.0
        # priority_level 1 (ошибка раскладки) -> 0.9
        # priority_level 2 (транслит/спец) -> 0.8
        # priority_level 3 (ошибка раскладки на L2) -> 0.7
        # priority_level 4 (общий/разделители) -> 0.6
        priority_modifier = 1.0 - (priority_level * 0.1)
        priority_modifier = max(0.5, priority_modifier) # Минимум 0.5

        # Комбинированная оценка на основе схожести от БД и текстовой схожести
        if (w_db + w_textual) > 0:
            combined_score = (db_score * w_db + textual_similarity_score * w_textual) / (w_db + w_textual)
        else:
            combined_score = 0 # Если веса нулевые, базовый score тоже ноль

        # Применяем модификатор приоритета
        adjusted_score = combined_score * priority_modifier
        
        # Бонусы за точное или частичное совпадение с оригинальным запросом
        if original_query.lower() == name_from_cs.lower() or original_query.lower() == description_from_cs.lower():
            adjusted_score += 0.25 
        elif name_from_cs.lower().startswith(original_query.lower()) or \
             description_from_cs.lower().startswith(original_query.lower()):
            adjusted_score += 0.15

        final_relevance = min(2.0, adjusted_score) # Ограничиваем максимум (2.0 как у прямого поиска по SRID)
        
        # Для отладки можно раскомментировать:
        # self.logger.debug(
        #     f"AdjustedRelevance: query='{original_query}', name='{name_from_cs[:20]}...', "
        #     f"db_score={db_score:.2f}, txt_sim={textual_similarity_score:.2f}, "
        #     f"prio_lvl={priority_level}, prio_mod={priority_modifier:.2f}, combined_score={combined_score:.2f} -> final={final_relevance:.2f}"
        # )
        return final_relevance

    def parse_wkt_name(self, wkt_string: str) -> Optional[str]:
        """
        Пытается извлечь имя проекции/ГСК из WKT строки.
        Пример: PROJCS["Pulkovo_1942_GK_Zone_5", GEOGCS["GCS_Pulkovo_1942", ...]] -> "Pulkovo_1942_GK_Zone_5"
        """
        if not wkt_string:
            return None
        try:
            # Ищет имя в кавычках сразу после PROJCS[, GEOGCS[, COMPD_CS[, VERT_CS[, GEOCCS[
            # Учитывает возможные пробелы вокруг ключевых слов и скобок.
            # Захватывает содержимое двойных кавычек.
            match = re.search(
                r"^(?:PROJCS|GEOGCS|COMPD_CS|VERT_CS|GEOCCS)"
                r"\s*\[\s*\"(?P<name>[^\"]+)\"",
                wkt_string,
                re.IGNORECASE
            )
            if match:
                return match.group("name")
        except Exception as e:
            logger = self.logger if hasattr(self, 'logger') and self.logger else logging.getLogger(__name__)
            # Используем repr(wkt_string[:100]) чтобы показать возможные спецсимволы, которые могли вызвать ошибку
            logger.error(f"Ошибка парсинга WKT имени из строки {repr(wkt_string[:100])}...': {e}")
        return None