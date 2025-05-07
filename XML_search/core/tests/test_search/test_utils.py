"""
Тесты для утилит поиска
"""

import pytest
from XML_search.core.search import SearchUtils

class TestSearchUtils:
    """Тесты для утилит поиска"""
    
    @pytest.fixture
    def utils(self):
        """Фикстура для создания утилит"""
        return SearchUtils()
        
    @pytest.fixture
    def sample_results(self):
        """Фикстура с тестовыми результатами"""
        return [
            {
                'srid': 100001,
                'auth_name': 'custom',
                'auth_srid': 100001,
                'srtext': 'МСК-01',
                'deprecated': False
            },
            {
                'srid': 32601,
                'auth_name': 'EPSG',
                'auth_srid': 32601,
                'srtext': 'WGS 84 / UTM zone 1N',
                'deprecated': True
            },
            {
                'srid': 99999,
                'auth_name': 'custom',
                'auth_srid': 99999,
                'srtext': 'Старая МСК',
                'deprecated': True
            }
        ]
        
    def test_apply_filters_region(self, utils, sample_results):
        """Тест фильтрации по региону"""
        filters = {'region': True}
        results = utils.apply_filters(sample_results, filters)
        
        assert len(results) == 2
        assert all(r['auth_name'] == 'custom' for r in results)
        
    def test_apply_filters_custom(self, utils, sample_results):
        """Тест фильтрации по пользовательским СК"""
        filters = {'custom': True}
        results = utils.apply_filters(sample_results, filters)
        
        assert len(results) == 1
        assert results[0]['srid'] == 100001
        
    def test_apply_filters_active(self, utils, sample_results):
        """Тест фильтрации по активным СК"""
        filters = {'active': True}
        results = utils.apply_filters(sample_results, filters)
        
        assert len(results) == 1
        assert not results[0]['deprecated']
        
    def test_apply_filters_combined(self, utils, sample_results):
        """Тест комбинированной фильтрации"""
        filters = {
            'region': True,
            'active': True
        }
        results = utils.apply_filters(sample_results, filters)
        
        assert len(results) == 1
        assert results[0]['auth_name'] == 'custom'
        assert not results[0]['deprecated']
        
    def test_apply_filters_no_matches(self, utils, sample_results):
        """Тест фильтрации без совпадений"""
        filters = {
            'custom': True,
            'active': True,
            'region': True
        }
        results = utils.apply_filters(sample_results, filters)
        
        assert len(results) == 1
        assert results[0]['srid'] == 100001
        
    def test_fuzzy_search_exact_match(self, utils):
        """Тест нечеткого поиска с точным совпадением"""
        assert utils.fuzzy_search("мск", "мск")
        
    def test_fuzzy_search_close_match(self, utils):
        """Тест нечеткого поиска с близким совпадением"""
        assert utils.fuzzy_search("мск", "мск1")
        
    def test_fuzzy_search_no_match(self, utils):
        """Тест нечеткого поиска без совпадения"""
        assert not utils.fuzzy_search("мск", "utm")
        
    def test_fuzzy_search_case_insensitive(self, utils):
        """Тест нечеткого поиска без учета регистра"""
        assert utils.fuzzy_search("МСК", "мск")
        
    def test_fuzzy_search_custom_threshold(self, utils):
        """Тест нечеткого поиска с пользовательским порогом"""
        assert utils.fuzzy_search("мск", "мск123", threshold=0.5)
        assert not utils.fuzzy_search("мск", "мск123", threshold=0.9) 