import pytest
from XML_search.enhanced.db_manager import DatabaseManager
from XML_search.config import DBConfig
from XML_search.enhanced.exceptions import QueryError, ConnectionError
from unittest.mock import MagicMock, patch

class TestDatabaseManager:
    @pytest.fixture
    def db_manager(self):
        config = DBConfig()
        return DatabaseManager(config)

    def test_safe_transaction_commit(self, db_manager):
        """Тест успешного выполнения транзакции"""
        test_query = "SELECT 1"
        
        with db_manager.safe_transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(test_query)
                result = cur.fetchone()
                assert result[0] == 1

    def test_safe_transaction_rollback(self, db_manager):
        """Тест автоматического отката при ошибке"""
        test_query = "SELECT invalid_column"  # Заведомо неверный запрос
        
        with pytest.raises(QueryError):
            with db_manager.safe_transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(test_query)

    def test_safe_query_execution(self, db_manager):
        """Тест безопасного выполнения запроса"""
        result = db_manager.execute_safe_query("SELECT 1 as test")
        assert result[0]['test'] == 1

    def test_safe_modification(self, db_manager):
        """Тест безопасной модификации данных"""
        # Создаем временную таблицу для теста
        create_table = """
        CREATE TEMPORARY TABLE test_table (
            id serial PRIMARY KEY,
            value text
        )
        """
        with db_manager.safe_transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table)

        # Тестируем вставку
        rows_affected = db_manager.execute_safe_modification(
            "INSERT INTO test_table (value) VALUES (%s) RETURNING id",
            ("test_value",)
        )
        assert rows_affected == 1

    def test_metrics_collection(self, db_manager):
        """Тест сбора метрик при работе с БД"""
        # Выполняем запрос
        db_manager.execute_safe_query("SELECT 1")
        
        # Проверяем метрики
        stats = db_manager.get_connection_stats()
        assert stats['metrics']['counters']['queries_executed'] > 0

    def test_connection_reuse(self, db_manager):
        """Тест переиспользования соединений"""
        # Выполняем несколько запросов
        for _ in range(5):
            db_manager.execute_safe_query("SELECT 1")
        
        # Проверяем статистику пула
        stats = db_manager.get_connection_stats()
        assert stats['pool']['total_created'] <= 5  # Должно быть меньше запросов

    def test_error_handling(self, db_manager):
        """Тест обработки ошибок"""
        with pytest.raises(QueryError):
            db_manager.execute_safe_query("SELECT * FROM non_existent_table")

    def test_connection_cleanup(self, db_manager):
        """Тест очистки соединений"""
        initial_stats = db_manager.get_connection_stats()
        
        # Выполняем запрос с ошибкой
        with pytest.raises(QueryError):
            db_manager.execute_safe_query("SELECT * FROM non_existent_table")
        
        # Проверяем, что все соединения были корректно возвращены в пул
        final_stats = db_manager.get_connection_stats()
        assert final_stats['pool']['active_connections'] == initial_stats['pool']['active_connections']

    def test_concurrent_transactions(self, db_manager):
        """Тест параллельных транзакций"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker():
            try:
                with db_manager.safe_transaction() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        results.put(True)
            except Exception as e:
                results.put(e)
        
        # Запускаем несколько параллельных транзакций
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Проверяем результаты
        while not results.empty():
            assert results.get() is True 