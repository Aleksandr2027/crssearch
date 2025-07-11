"""
Улучшенный поисковый движок
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import logging
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.transliterator import Transliterator
from XML_search.crs_search import CrsSearchBot
from XML_search.enhanced.exceptions import DatabaseError
from .search_utils import SearchUtils
from XML_search.enhanced.config_enhanced import DatabaseConfig
import re # Добавлен re для _get_name_and_description

class EnhancedSearchEngine:
    """Улучшенный класс поискового движка с расширенной функциональностью"""
    
    def __init__(self, 
                 db_manager: Optional[DatabaseManager] = None, 
                 db_config: Optional[DatabaseConfig] = None,
                 metrics: Optional[MetricsManager] = None,
                 logger: Optional[Union[LogManager, logging.Logger]] = None,
                 cache: Optional[CacheManager] = None):
        """
        Инициализация поискового движка
        
        Args:
            db_manager: Готовый менеджер базы данных (приоритетный)
            db_config: Конфигурация базы данных (используется, если db_manager не предоставлен)
            metrics: Коллектор метрик
            logger: Логгер или менеджер логов
            cache: Менеджер кэша
        """
        self.logger_for_init = logging.getLogger(__name__ + ".EnhancedSearchEngineInit")

        if db_manager:
            self.db_manager = db_manager
        elif db_config:
            try:
                self.db_manager = DatabaseManager(config=db_config)
            except Exception as e:
                self.logger_for_init.error(f"Failed to initialize DatabaseManager with provided db_config: {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize DatabaseManager with provided db_config: {e}") from e
        else:
            err_msg = "EnhancedSearchEngine requires either a db_manager instance or a db_config."
            self.logger_for_init.error(err_msg)
            raise ValueError(err_msg)
        
        self.metrics = metrics if metrics is not None else MetricsManager()
        
        if isinstance(logger, LogManager):
            self.logger = logger.get_logger(__name__)
        elif isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.warning("Logger not provided to EnhancedSearchEngine, using default logger. Configure LogManager for enhanced logging.")

        self.cache = cache or CacheManager()
        self.search_utils = SearchUtils(logger=self.logger)
        self.transliterator = Transliterator()
        self.search_processor = CrsSearchBot(
            db_manager=self.db_manager,
            logger_instance=self.logger,
            cache_manager_instance=self.cache,
            transliterator_instance=self.transliterator
        )
        self.logger.info("EnhancedSearchEngine инициализирован.")
        
    async def _get_name_and_description(self, srid: int, auth_name_str: str, auth_srid_val: Optional[Any], srtext_from_db: str) -> Tuple[str, str]:
        name_to_return = str(auth_name_str) # По умолчанию имя - это auth_name из БД
        description_to_return = srtext_from_db # По умолчанию описание - это srtext из БД

        is_standard_authority = str(auth_name_str).upper() in ["EPSG", "ESRI"] # Дополнить при необходимости
        is_wkt_like = bool(srtext_from_db and srtext_from_db.upper().lstrip().startswith(("PROJCS", "GEOGCS", "GEOCCS", "VERT_CS", "COMPD_CS")))

        if is_standard_authority:
            name_to_return = f"{str(auth_name_str).upper()}:{auth_srid_val}" # Формируем имя типа "EPSG:4326"
            if is_wkt_like:
                parsed_wkt_name = self.search_utils.parse_wkt_name(srtext_from_db)
                description_to_return = parsed_wkt_name if parsed_wkt_name else srtext_from_db # Используем распарсенное имя или полный WKT, если парсинг не удался
            # Если srtext_from_db не WKT, то description_to_return уже содержит его (srtext_from_db).
            # Если srtext_from_db пустой для стандартного авторитета, нужен лучший fallback.
            if not description_to_return: # Если описание пустое (например, пустой srtext или неудачный парсинг WKT)
                 description_to_return = f"{name_to_return} (Описание отсутствует)"
        
        elif is_wkt_like: # Не стандартный авторитет, но srtext - это WKT (например, auth_name="МояСК", srtext=WKT-строка)
            # name_to_return уже равен auth_name_str (например, "МояСК")
            parsed_wkt_name = self.search_utils.parse_wkt_name(srtext_from_db)
            description_to_return = parsed_wkt_name if parsed_wkt_name else srtext_from_db # Используем распарсенное имя или полный WKT
            if not description_to_return: # Маловероятно, если is_wkt_like=True, но для страховки
                 description_to_return = name_to_return 
        else: # Не стандартный авторитет и srtext не WKT (например, custom_geom: auth_name="MSK01z1", srtext="МСК Адыгея зона 1 (3°)")
            # name_to_return уже равен auth_name_str (например, "MSK01z1")
            # description_to_return уже равен srtext_from_db (например, "МСК Адыгея зона 1 (3°)")
            if not description_to_return: # Если srtext_from_db (custom_geom.info) был пуст
                description_to_return = f"{name_to_return} (SRID: {srid})"

        # Финальная проверка на случай, если описание по какой-то причине осталось пустым
        if not description_to_return:
            description_to_return = f"{name_to_return} (SRID: {srid}, Описание не найдено)"

        if self.logger:
            self.logger.debug(f"_get_name_and_description: srid={srid}, auth_name='{auth_name_str}' -> name='{name_to_return}', desc='{description_to_return[:100]}...'")
                
        return name_to_return, description_to_return

    async def search(self, query: str, filters: Optional[Dict[str, bool]] = None, 
                    use_cache: bool = True, cache_ttl: int = 3600, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Выполнение поиска с расширенными опциями и приоритезированной обработкой вариантов.
        
        Args:
            query: Поисковый запрос
            filters: Фильтры поиска (используется is_srid_search)
            use_cache: Использовать ли кэширование
            cache_ttl: Время жизни кэша в секундах
            limit: Максимальное количество результатов для возврата
            
        Returns:
            Список результатов поиска
        """
        cache_key = f"search:{query}:{str(filters)}" # Включаем filters в ключ кэша
        if use_cache and self.cache:
            cached_results = await self.cache.get(cache_key)
            if cached_results is not None:
                if self.logger:
                    self.logger.debug(f"Результаты для запроса '{query}' с фильтрами '{filters}' найдены в кэше.")
                return cached_results

        # Блок для прямого поиска по SRID
        if filters and filters.get("is_srid_search", False):
            try:
                srid_val = int(query)
                if self.logger:
                    self.logger.debug(f"Прямой поиск по SRID: {srid_val} (is_srid_search=True)")
                
                async with self.db_manager.connection() as conn:
                    # Сначала ищем в custom_geom, так как там могут быть приоритетные/пользовательские данные
                    db_row = await conn.fetchrow(
                        "SELECT srid, 'custom' as auth_name, srid as auth_srid, srtext, proj4text FROM custom_geom WHERE srid = $1",
                        srid_val
                    )
                    # Если не нашли в custom_geom, ищем в spatial_ref_sys (для стандартных EPSG и других)
                    if not db_row:
                        db_row = await conn.fetchrow(
                            "SELECT srid, auth_name, auth_srid, srtext, proj4text FROM spatial_ref_sys WHERE srid = $1",
                            srid_val
                        )

                    if db_row:
                        self.logger.info(f"SRID {srid_val} найден напрямую при is_srid_search=True.")
                        # Обогащаем найденную запись полями name и description
                        name, description = await self._get_name_and_description(
                            srid=db_row['srid'],
                            auth_name_str=db_row['auth_name'],
                            auth_srid_val=db_row['auth_srid'], # Может быть None для non-EPSG из spatial_ref_sys
                            srtext_from_db=db_row['srtext']
                        )
                        result_item = dict(db_row) # Копируем все поля из найденной строки
                        result_item['name'] = name
                        result_item['description'] = description
                        # Устанавливаем максимальную релевантность, так как это прямой поиск по SRID
                        result_item['relevance'] = 2.0 
                        result_item['adjusted_relevance'] = 2.0 # Для совместимости с текстовым поиском
                        
                        srid_results = [result_item] # Результат - список с одним элементом
                        
                        if use_cache and self.cache:
                            await self.cache.set(cache_key, srid_results, ttl=cache_ttl)
                        return srid_results # Возвращаем результат прямого поиска
                    else:
                        # SRID искали целенаправленно (is_srid_search=True) и не нашли
                        self.logger.debug(f"SRID {srid_val} не найден при прямом поиске (is_srid_search=True).")
                        if use_cache and self.cache:
                            await self.cache.set(cache_key, [], ttl=cache_ttl) # Кэшируем пустой результат
                        return [] 
            except ValueError:
                # query не является числом, хотя is_srid_search=True.
                # Это означает, что пользователь выбрал из инлайн-результата что-то, что не парсится как SRID,
                # или фильтр is_srid_search был установлен ошибочно для нечислового запроса.
                # Логируем и позволяем выполниться текстовому поиску ниже.
                if self.logger:
                    self.logger.warning(f"Запрос '{query}' при is_srid_search=True не является валидным числовым SRID. Будет выполнен текстовый поиск.")
        
        # Если мы дошли сюда, значит:
        # 1. filters.get("is_srid_search") было False (или отсутствовало)
        # ИЛИ
        # 2. filters.get("is_srid_search") было True, НО query не было числом (произошел ValueError выше).
        # В этих случаях выполняется текстовый поиск.

        final_results_map: Dict[int, Dict[str, Any]] = {} # Используется для дедупликации в текстовом поиске
        
        if self.logger: # Логируем только если действительно начинаем текстовый поиск
            self.logger.debug(f"Начало текстового поиска для '{query}', лимит: {limit}")
        
        # 1. Генерация приоритезированных вариантов для поиска по имени/описанию
        prioritized_variants = self.transliterator.generate_prioritized_variants(query)
        
        # Обрабатываем каждый вариант
        processed_variants_for_cache_key = []

        for variant_tuple in prioritized_variants:
            variant_text, priority_level = variant_tuple
            processed_variants_for_cache_key.append(variant_text)

            if len(final_results_map) >= limit:
                if self.logger:
                    self.logger.info(f"Достигнут лимит результатов ({len(final_results_map)}) на приоритете {priority_level} для текстового поиска (вариант '{variant_text}'). Остановка.")
                break
            
            if not variant_text or variant_text.isspace():
                continue

            # Определяем тип системы для ТЕКУЩЕГО варианта текста
            current_system_type = self.transliterator.detect_system_type(variant_text)
            
            # Определяем поля для поиска на основе типа текущего варианта и оригинального запроса
            search_fields_for_query: List[str] = []
            if current_system_type in ['MSK', 'GSK', 'SK']:
                search_fields_for_query = ["name", "srid"]
            elif current_system_type == 'UTM':
                search_fields_for_query = ["name", "srid", "description"]
            # Если тип USK, USL, UNKNOWN ИЛИ оригинальный запрос (query) похож на описание (не только буквы/цифры)
            elif current_system_type in ['USK', 'USL', 'UNKNOWN'] or not query.replace("-", "").replace("_", "").replace(" ", "").isalnum():
                search_fields_for_query = ["name", "description", "srid"]
            else: # Общий случай для других типов или простых запросов
                search_fields_for_query = ["name", "srid", "description"]

            if not search_fields_for_query:
                if self.logger and isinstance(self.logger, logging.Logger):
                    self.logger.warning(f"Для system_type='{current_system_type}' и query='{variant_text}' не определены search_fields_for_query. Пропускаем.")
                continue
            
            current_variant_results = [] # Initialize before try block
            try:
                # Запрос к БД через search_utils
                # This block must be indented under 'try'
                _results = await self.search_utils.execute_search_query(
                    variant=variant_text,
                    db_manager=self.db_manager,
                    limit=limit, # Используем limit_for_variant
                    search_fields=search_fields_for_query
                )
                current_variant_results = _results # Assign if successful
            except ConnectionError as e:
                if self.logger and isinstance(self.logger, (logging.Logger, LogManager)):
                    log_message = f"Ошибка ConnectionError при выполнении поискового запроса для варианта '{variant_text}': {e}"
                    if hasattr(self.logger, 'error'): self.logger.error(log_message)
                    else: print(f"ERROR: {log_message}")
                # current_variant_results remains []
            except Exception as e:
                if self.logger and isinstance(self.logger, (logging.Logger, LogManager)):
                    log_message = f"Непредвиденная ошибка Exception при выполнении поискового запроса для варианта '{variant_text}': {e}"
                    if hasattr(self.logger, 'exception'): self.logger.exception(log_message)
                    elif hasattr(self.logger, 'error'): self.logger.error(log_message)
                    else: print(f"ERROR: {log_message}")
                # current_variant_results remains []

            processed_results_count = 0

            for res_item in current_variant_results:
                srid = res_item['srid']

                # Для КАЖДОГО результата из текстового поиска также получаем name и description
                name, description = await self._get_name_and_description(
                    srid=srid,
                    auth_name_str=res_item['auth_name'],
                    auth_srid_val=res_item['auth_srid'],
                    srtext_from_db=res_item['srtext']
                )

                original_relevance = res_item.get('relevance', 0.0) # Исходная релевантность от БД
                # Рассчитываем скорректированную релевантность
                adjusted_relevance = self.search_utils.calculate_adjusted_relevance(
                    original_relevance,
                    priority_level,
                    query, # Оригинальный запрос пользователя
                    name,  # Имя, полученное от _get_name_and_description
                    description # Описание, полученное от _get_name_and_description
                )

                res_item['name'] = name
                res_item['description'] = description
                res_item['relevance'] = original_relevance
                res_item['adjusted_relevance'] = adjusted_relevance
                res_item['priority_level'] = priority_level
                res_item['found_by_variant'] = variant_text # Сохраняем вариант, по которому нашли
                
                # Обновляем, только если новый результат более релевантен или это новый SRID
                if srid not in final_results_map or adjusted_relevance > final_results_map[srid].get('adjusted_relevance', -1.0):
                    final_results_map[srid] = res_item
            
            if self.logger:
                self.logger.info(f"SEARCH_DEBUG: Текстовый поиск: После приоритета {priority_level} всего уникальных результатов: {len(final_results_map)}")
        
        # Фильтрация (если нужна) и финальная сортировка результатов текстового поиска
        all_found_results_list = list(final_results_map.values())
        
        # Сортируем по adjusted_relevance, затем по srid для стабильности
        # self.search_utils.sort_results теперь должен принимать query
        sorted_results = self.search_utils.sort_results(all_found_results_list, query=query) 
        
        limited_results = sorted_results[:limit]

        if self.logger:
            self.logger.debug(f"SEARCH_DEBUG: Текстовый поиск: Возвращается {len(limited_results)} результатов для запроса '{query}'.")

        # Кэширование результатов текстового поиска
        if use_cache and self.cache:
             await self.cache.set(cache_key, limited_results, ttl=cache_ttl)
        return limited_results

    async def get_details(self, system_id: str) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о системе координат
        
        Args:
            system_id: Идентификатор системы координат
            
        Returns:
            Словарь с детальной информацией или None
        """
        try:
            # Проверяем кэш
            cache_key = f"details_{system_id}"
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                self.logger.debug(f"Найдены кэшированные детали для системы: {system_id}")
                return cached_result
                
            # Получаем детали
            self.logger.debug(f"Запрос деталей для системы: {system_id}")
            # Убедимся, что system_id - это число для search_by_srid
            srid_to_search = 0
            try:
                srid_to_search = int(system_id)
            except ValueError:
                self.logger.error(f"Некорректный system_id для get_details: '{system_id}'. Должен быть числом.")
                return None

            srid_results = await self.search_processor.search_by_srid(srid_to_search)
            details = srid_results[0] if srid_results else None
            self.logger.info(f"SEARCH_DEBUG: get_details вызвал search_by_srid для SRID {srid_to_search}, результат: {details}")

            # Кэшируем результат
            if details:
                self.logger.debug(f"Кэширование деталей для системы: {system_id}")
                await self.cache.set(cache_key, details, ttl=3600) # Используем cache_ttl из аргументов метода или конфига
                
            return details
            
        except Exception as e:
            error_msg = f"Ошибка при получении деталей: {str(e)}"
            self.logger.exception(error_msg)
            return None 