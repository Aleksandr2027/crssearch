import psycopg2
from psycopg2.extras import DictCursor
import logging
from typing import List, Dict, Any
from XML_search.config import DBConfig
from XML_search.errors import DatabaseError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.transliterator import Transliterator
from XML_search.enhanced.config_enhanced import LogManagerConfig, CacheManagerConfig, MetricsConfig, EnhancedConfig
from contextlib import contextmanager

class CrsSearchBot:
    """Бот для поиска систем координат"""
    def __init__(self, db_manager: DatabaseManager):
        self.config = DBConfig()
        self.connection = None
        
        # Загрузка расширенной конфигурации
        self.enhanced_config = EnhancedConfig.load_from_file()
        
        # Инициализация компонентов
        self.db_manager = db_manager
        self.log_manager = LogManager(name="crs_search", config=self.enhanced_config.logging)
        self.cache_manager = CacheManager(
            ttl=self.enhanced_config.cache.ttl,
            max_size=self.enhanced_config.cache.max_size
        )
        self.metrics = MetricsManager()
        
        self.setup_logging()

    def setup_logging(self):
        """Настройка логирования"""
        self.logger = self.log_manager.get_logger(__name__)

    @contextmanager
    def get_connection(self):
        """Получение соединения с базой данных"""
        conn = None
        try:
            # Получаем соединение из пула
            conn = self.db_manager.get_connection()
            # Устанавливаем autocommit
            conn.autocommit = True
            self.logger.info("Успешное подключение к базе данных")
            yield conn
        except Exception as e:
            self.logger.error(f"Ошибка подключения к базе данных: {str(e)}")
            raise DatabaseError(f"Ошибка подключения к базе данных: {str(e)}")
        finally:
            if conn and not conn.closed:
                # Возвращаем соединение в пул вместо закрытия
                self.db_manager.release_connection(conn)
                self.logger.info("Соединение возвращено в пул")

    def get_cursor(self):
        """Получение курсора базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=DictCursor)
                return cursor
        except Exception as e:
            self.logger.error(f"Ошибка получения курсора: {str(e)}")
            raise DatabaseError(f"Ошибка получения курсора: {str(e)}")

    def search_coordinate_systems(self, search_variants: List[str]) -> List[Dict[str, Any]]:
        """Поиск систем координат по различным вариантам запроса"""
        try:
            results = []
            seen_srids = set()  # Для дедупликации результатов
            
            for query in search_variants:
                # Проверяем кэш
                cache_key = f"search_{query}"
                cached_results = self.cache_manager.get(cache_key)
                if cached_results:
                    self.logger.info(f"Найдены результаты в кэше для запроса: {query}")
                    for result in cached_results:
                        if result['srid'] not in seen_srids:
                            results.append(result)
                            seen_srids.add(result['srid'])
                    continue
                
                # Пробуем поиск по SRID
                try:
                    srid = int(query)
                    srid_results = self.search_by_srid(srid)
                    for result in srid_results:
                        if result['srid'] not in seen_srids:
                            results.append(result)
                            seen_srids.add(result['srid'])
                    continue
                except ValueError:
                    pass  # Не SRID, продолжаем поиск
                
                # Поиск с учетом транслитерации
                translit_results = self.search_with_transliteration(query)
                for result in translit_results:
                    if result['srid'] not in seen_srids:
                        results.append(result)
                        seen_srids.add(result['srid'])
                
                # Кэшируем результаты
                if results:
                    self.cache_manager.set(cache_key, results)
            
            # Сортируем результаты по релевантности
            results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске систем координат: {str(e)}")
            return []

    def print_results(self, results: List[Dict[str, Any]]) -> None:
        """Вывод результатов поиска"""
        if not results:
            print("\nСистемы координат не найдены.")
            return

        for result in results:
            print(f"\nSRID: {result['srid']}")
            print(f"Название: {result['srtext']}")
            if result['info']:
                print(f"Описание: {result['info']}")
            print("-" * 50)

    def run_interactive(self):
        """Запуск интерактивного режима бота"""
        print("\nДобро пожаловать в CrsSearchBot!")
        print("Для выхода введите 'q' или 'quit'\n")
        print("Введите SRID или название системы координат для поиска")
        print("Примеры:")
        print("- SRID: 100001")
        print("- Название: мск")
        print("-" * 50)

        while True:
            try:
                search_term = input("\nПоиск: ").strip()
                
                if search_term.lower() in ['q', 'quit', 'выход']:
                    print("\nЗавершение работы бота...")
                    break
                
                if not search_term:
                    print("Введите поисковый запрос!")
                    continue
                
                results = self.search_coordinate_systems([search_term])
                self.print_results(results)
                
            except KeyboardInterrupt:
                print("\nЗавершение работы бота...")
                break
            except Exception as e:
                print(f"\nПроизошла ошибка: {e}")
                continue

    def disconnect(self):
        """Закрытие соединения с базой данных"""
        try:
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
                self.logger.info("Соединение с базой данных закрыто")
        except Exception as e:
            self.logger.error(f"Ошибка отключения от базы данных: {e}")

    def __del__(self):
        """Деструктор класса"""
        self.disconnect()

    def search_with_transliteration(self, query: str) -> List[Dict[str, Any]]:
        """Поиск систем координат с учетом транслитерации"""
        try:
            results = []
            seen_srids = set()  # Для дедупликации результатов
            
            # Генерируем варианты транслитерации
            variants = self._generate_translit_variants(query)
            
            for variant in variants:
                # Проверяем кэш
                cache_key = f"translit_{variant}"
                cached_results = self.cache_manager.get(cache_key)
                if cached_results:
                    self.logger.info(f"Найдены результаты в кэше для транслитерированного запроса: {variant}")
                    for result in cached_results:
                        if result['srid'] not in seen_srids:
                            results.append(result)
                            seen_srids.add(result['srid'])
                    continue
                
                # Выполняем поиск в базе данных
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=DictCursor) as cursor:
                        cursor.execute("""
                            SELECT srid, auth_name, auth_srid, srtext, proj4text, 
                                   similarity(srtext, %s) as relevance
                            FROM spatial_ref_sys
                            WHERE (auth_name = 'custom' OR 
                                  (srid BETWEEN 32601 AND 32660))
                            AND srtext ILIKE %s
                            ORDER BY relevance DESC
                            LIMIT 10
                        """, (variant, f"%{variant}%"))
                        
                        variant_results = []
                        for row in cursor.fetchall():
                            if row['srid'] not in seen_srids:
                                result = {
                                    'srid': row['srid'],
                                    'auth_name': row['auth_name'],
                                    'auth_srid': row['auth_srid'],
                                    'srtext': row['srtext'],
                                    'proj4text': row['proj4text'],
                                    'relevance': float(row['relevance'])
                                }
                                results.append(result)
                                variant_results.append(result)
                                seen_srids.add(row['srid'])
                        
                        # Кэшируем результаты
                        if variant_results:
                            self.cache_manager.set(cache_key, variant_results)
            
            # Сортируем результаты по релевантности
            results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске с транслитерацией: {str(e)}")
            return []

    def search_by_srid(self, srid: int) -> List[Dict[str, Any]]:
        """
        Поиск координатной системы по SRID.
        
        Args:
            srid (int): SRID для поиска
            
        Returns:
            List[Dict[str, Any]]: Список найденных координатных систем
        """
        try:
            cache_key = f"srid_{srid}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT id, name, code, area, accuracy, datum, ellipsoid, 
                           projection, parameters, remarks, source, revision_date,
                           change_id, deprecated, bbox_min_lat, bbox_max_lat,
                           bbox_min_lon, bbox_max_lon
                    FROM coordinate_systems 
                    WHERE code = %s
                    """
                    cursor.execute(sql, (srid,))
                    row = cursor.fetchone()
                    
                    if row:
                        result = [{
                            'id': row[0],
                            'name': row[1],
                            'code': row[2],
                            'area': row[3],
                            'accuracy': row[4],
                            'datum': row[5],
                            'ellipsoid': row[6],
                            'projection': row[7],
                            'parameters': row[8],
                            'remarks': row[9],
                            'source': row[10],
                            'revision_date': row[11],
                            'change_id': row[12],
                            'deprecated': row[13],
                            'bbox_min_lat': row[14],
                            'bbox_max_lat': row[15],
                            'bbox_min_lon': row[16],
                            'bbox_max_lon': row[17]
                        }]
                        # Кэшируем результат
                        self.cache_manager.set(cache_key, result)
                        return result
                    
                    return []
                    
        except Exception as e:
            self.logger.error(f"Ошибка при поиске по SRID: {str(e)}")
            self.metrics.increment('search_errors')
            raise DatabaseError(f"Ошибка при поиске по SRID: {str(e)}")

    def _generate_translit_variants(self, query: str) -> List[str]:
        """Генерация вариантов транслитерации для поиска"""
        try:
            variants = set()
            variants.add(query)  # Добавляем оригинальный запрос
            
            # Добавляем транслитерированные варианты
            transliterator = Transliterator()
            transliterated = transliterator.transliterate(query)
            if transliterated != query:
                variants.add(transliterated)
            
            # Добавляем варианты с разными регистрами
            variants.add(query.upper())
            variants.add(query.title())
            
            # Добавляем варианты с заменой пробелов
            variants.add(query.replace(' ', '_'))
            variants.add(query.replace(' ', '-'))
            
            return list(variants)
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации вариантов транслитерации: {str(e)}")
            return [query]  # Возвращаем хотя бы оригинальный запрос

# Запуск бота
if __name__ == "__main__":
    bot = CrsSearchBot()
    try:
        bot.run_interactive()
    finally:
        bot.disconnect() 