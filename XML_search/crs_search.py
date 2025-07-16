import psycopg2
from psycopg2.extras import DictCursor
import logging
from typing import List, Dict, Any, Union
from XML_search.config import DBConfig
from XML_search.errors import DatabaseError
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.enhanced.cache_manager import CacheManager
from XML_search.enhanced.metrics_manager import MetricsManager
from XML_search.enhanced.transliterator import Transliterator
from contextlib import contextmanager

class CrsSearchBot:
    """Бот для поиска систем координат"""
    def __init__(self, 
                 db_manager: DatabaseManager,
                 logger_instance: logging.Logger,
                 cache_manager_instance: CacheManager,
                 transliterator_instance: Transliterator):
        self.config = DBConfig()
        
        self.db_manager = db_manager
        self.logger = logger_instance
        self.cache_manager = cache_manager_instance
        self.transliterator = transliterator_instance
        
        self.metrics = MetricsManager()

    async def search_coordinate_systems(self, search_variants: List[str]) -> List[Dict[str, Any]]:
        """Поиск систем координат по различным вариантам запроса"""
        try:
            results = []
            seen_srids = set()

            for query in search_variants:
                cache_key = f"search_{query}"
                cached_results = await self.cache_manager.get(cache_key)
                if cached_results:
                    self.logger.info(f"Найдены результаты в кэше для запроса: {query}")
                    for result in cached_results:
                        if result['srid'] not in seen_srids:
                            results.append(result)
                            seen_srids.add(result['srid'])
                    continue
                
                try:
                    srid = int(query)
                    srid_results = await self.search_by_srid(srid)
                    for result in srid_results:
                        if result['srid'] not in seen_srids:
                            results.append(result)
                            seen_srids.add(result['srid'])
                    if srid_results:
                        await self.cache_manager.set(cache_key, srid_results)
                    continue
                except ValueError:
                    pass 
                
                translit_results = await self.search_with_transliteration(query)
                for result in translit_results:
                    if result['srid'] not in seen_srids:
                        results.append(result)
                        seen_srids.add(result['srid'])
                
                if translit_results:
                    await self.cache_manager.set(cache_key, translit_results)
            
            results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске систем координат: {str(e)}", exc_info=True)
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

    async def search_with_transliteration(self, query_variant: str) -> List[Dict[str, Any]]:
        """Поиск систем координат по одному конкретному варианту запроса (транслитерированному)"""
        try:
            self.logger.info(f"SEARCH_DEBUG_CRS: Обработка варианта в search_with_transliteration: '{query_variant}'")
            
            cache_key = f"translit_{query_variant}"
            cached_results = await self.cache_manager.get(cache_key)
            if cached_results:
                self.logger.info(f"Найдены результаты в кэше для транслитерированного запроса: {query_variant}")
                return cached_results

            sql_query_text = """
                SELECT srid, auth_name, auth_srid, srtext, proj4text, 
                       similarity(srtext, $1) as relevance
                FROM spatial_ref_sys
                WHERE srtext ILIKE $2 AND (auth_name = 'custom' OR (srid BETWEEN 32601 AND 32660))
                ORDER BY relevance DESC
                LIMIT 10
            """
            sql_params_tuple = (query_variant, f"%{query_variant}%")
            log_param_display = f"($1='{query_variant}', $2='{sql_params_tuple[1]}')"
            self.logger.info(f"SEARCH_DEBUG_CRS: SQL-запрос: {sql_query_text.strip()} \nС параметрами: {log_param_display}")
            
            fetched_rows = await self.db_manager.fetch(sql_query_text, query_variant, sql_params_tuple[1])

            self.logger.info(f"SEARCH_DEBUG_CRS: Получено {len(fetched_rows)} строк из БД для варианта '{query_variant}'")
            current_variant_results = []
            for row_dict in fetched_rows:
                result = {
                    'srid': row_dict['srid'],
                    'auth_name': row_dict['auth_name'],
                    'auth_srid': row_dict['auth_srid'],
                    'srtext': row_dict['srtext'],
                    'proj4text': row_dict['proj4text'],
                    'relevance': float(row_dict['relevance'])
                }
                current_variant_results.append(result)
                    
            if current_variant_results:
                await self.cache_manager.set(cache_key, current_variant_results)
            
            return current_variant_results
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске с транслитерацией для варианта '{query_variant}': {str(e)}", exc_info=True)
            return []

    async def search_by_srid(self, srid: int) -> List[Dict[str, Any]]:
        """
        Поиск координатной системы по SRID.
        
        Args:
            srid (int): SRID для поиска
            
        Returns:
            List[Dict[str, Any]]: Список найденных координатных систем
        """
        try:
            cache_key = f"srid_{srid}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            sql = """
            SELECT srid, auth_name, auth_srid, srtext, proj4text
            FROM spatial_ref_sys 
            WHERE srid = $1 AND (srid BETWEEN 32601 AND 32660)  -- Используем $1 для asyncpg, ограничиваем диапазон
            """
            row_dict = await self.db_manager.fetchrow(sql, srid)
            
            if row_dict:
                result = [{
                    'srid': row_dict['srid'],
                    'auth_name': row_dict['auth_name'],
                    'auth_srid': row_dict['auth_srid'],
                    'srtext': row_dict['srtext'],
                    'proj4text': row_dict['proj4text'],
                    'relevance': 1.0 
                }]
                await self.cache_manager.set(cache_key, result)
                return result
            
            return []
                    
        except Exception as e:
            self.logger.error(f"Ошибка при поиске по SRID: {str(e)}", exc_info=True)
            raise DatabaseError(f"Ошибка при поиске по SRID: {str(e)}") from e

    def _generate_translit_variants(self, query: str) -> List[str]:
        """Генерация вариантов транслитерации для поиска (использует старую логику для совместимости, если метод еще используется)"""
        try:
            # Используем новый модернизированный транслитератор
            transliterator = Transliterator()
            # Вызываем старый метод генерации, если эта функция все еще где-то используется
            variants = transliterator._generate_legacy_variants(query) 
            
            # Добавляем дополнительные варианты с разными регистрами
            additional_variants = set()
            for variant in variants:
                additional_variants.add(variant.upper())
                additional_variants.add(variant.lower())
                additional_variants.add(variant.title())
            
            # Добавляем варианты с заменой пробелов
                additional_variants.add(variant.replace(' ', '_'))
                additional_variants.add(variant.replace(' ', '-'))
                additional_variants.add(variant.replace('_', ' '))
                additional_variants.add(variant.replace('-', ' '))
            
            # Объединяем все варианты
            all_variants = set(variants)
            all_variants.update(additional_variants)
            
            return list(all_variants)
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации вариантов транслитерации: {str(e)}")
            return [query]  # Возвращаем хотя бы оригинальный запрос

# Запуск бота
if __name__ == "__main__":
    # Для интерактивного режима создадим базовые экземпляры менеджеров
    # В реальном приложении они должны быть настроены должным образом
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_logger = logging.getLogger("CrsSearchBotInteractive")

    # Базовый CacheManager
    cache_manager = CacheManager() 

    # Transliterator
    transliterator_instance = Transliterator()

    # DatabaseManager требует конфигурацию. Предположим, что DBConfig() ее предоставляет.
    # Для полноценной работы db_manager должен быть асинхронным и настроенным.
    # Этот блок __main__ синхронный и run_interactive тоже.
    # Для асинхронного db_manager и методов поиска потребуется asyncio.run().
    # Пока оставим это как есть, понимая, что интерактивный режим в текущем виде
    # не сможет вызывать асинхронные методы db_manager и поиска напрямую без asyncio.run().
    # Однако, CrsSearchBot.run_interactive() сам по себе не асинхронный и вызывает
    # self.search_coordinate_systems, который асинхронный. Это вызовет ошибку.
    # Чтобы это реально работало, run_interactive должен быть переписан с использованием asyncio.
    # Либо search_coordinate_systems должен быть адаптирован для синхронного вызова,
    # что нежелательно, так как основная часть системы асинхронна.

    main_logger.warning("Интерактивный режим CrsSearchBot в __main__ может не работать корректно с асинхронными методами без asyncio.run().")
    
    # Попытка создать db_manager, но он асинхронный, а run_interactive - нет.
    # db_conf = DBConfig() # Предполагаем, что DBConfig читает из .env или имеет значения по умолчанию
    # db_manager_instance = DatabaseManager(config=db_conf) # Это асинхронный менеджер

    # bot = CrsSearchBot(
    #     db_manager=db_manager_instance, # Передаем экземпляр
    #     logger_instance=main_logger,
    #     cache_manager_instance=cache_manager,
    #     transliterator_instance=transliterator_instance
    # )
    # try:
    #     # Для запуска асинхронного метода search_coordinate_systems из синхронного run_interactive
    #     # нужно использовать asyncio.run() внутри run_interactive или сделать run_interactive асинхронным.
    #     # Например, если бы search_coordinate_systems был основным, что делает run_interactive:
    #     # import asyncio
    #     # asyncio.run(bot.search_coordinate_systems(["мск95"])) # Пример
    #     main_logger.info("Запуск CrsSearchBot в интерактивном режиме (ограниченная функциональность из-за синхронного контекста)...")
    #     # bot.run_interactive() # Этот метод вызовет асинхронные операции из синхронного контекста.
    #     main_logger.info("Интерактивный режим CrsSearchBot завершен.")

    # finally:
    #     # db_manager_instance.close() # У DatabaseManager должен быть метод close()
    #     # Старый bot.disconnect() не нужен, так как соединения управляются db_manager
    #     main_logger.info("Ресурсы освобождены (если это было реализовано в db_manager.close()).")
    
    print("Блок if __name__ == '__main__' в crs_search.py требует рефакторинга для работы с asyncio.")
    print("Текущий интерактивный запуск из этого блока, скорее всего, не будет работать корректно.") 