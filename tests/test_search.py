"""Search integration boundaries: filtering, provenance and outage fallback."""
from unittest.mock import Mock
import pytest
from src.common import search
from src.common.errors import UpstreamError
from src.handlers import aftermath, resources
from tests.conftest import body_of, make_event


def test_missing_geo_distance_is_json_safe():
    records = search.parse_hits({'hits': {'hits': [{'_source': {'name': 'National'}, 'sort': [float('inf')]}]}})
    assert records[0]['distance_km'] is None


def test_case_insensitive_and_non_city_specific_filters():
    query = search.build_resource_query(state='KARNATAKA', city='Bengaluru')
    filters = query['query']['bool']['filter']
    assert {'term': {'state': 'karnataka'}} in filters[0]['bool']['should']
    assert {'term': {'city': ''}} in filters[1]['bool']['should']


def test_faq_uses_search_without_database(monkeypatch):
    monkeypatch.setenv('OPENSEARCH_ENDPOINT', 'http://localhost:9200')
    client = Mock()
    client.search.return_value = {'hits': {'hits': [{'_source': {'faq_id': 'faq', 'question': 'FIR?'}}]}}
    monkeypatch.setattr(search, 'client', lambda: client)
    result = body_of(aftermath.handler(make_event('/aftermath/faqs', query={'q': 'FIR'}), None))
    assert result['meta']['source'] == 'opensearch'
    assert result['data']['items'][0]['faq_id'] == 'faq'


@pytest.mark.usefixtures('dynamodb')
def test_search_outage_falls_back_to_database(monkeypatch):
    monkeypatch.setenv('OPENSEARCH_ENDPOINT', 'http://localhost:9200')
    client = Mock()
    client.search.side_effect = ConnectionError()
    monkeypatch.setattr(search, 'client', lambda: client)
    result = body_of(aftermath.handler(make_event('/aftermath/faqs', query={'q': 'FIR'}), None))
    assert result['ok']
    assert result['meta']['source'] == 'scan+score'
    assert result['data']['items']
    result = body_of(resources.handler(make_event('/resources'), None))
    assert result['ok']
    assert result['meta']['source'] == 'dynamodb'


def test_resource_total_is_not_limited_count(monkeypatch):
    monkeypatch.setenv('OPENSEARCH_ENDPOINT', 'http://localhost:9200')
    client = Mock()
    client.search.return_value = {'hits': {'total': {'value': 12}, 'hits': [{'_source': {'resource_id': 'a'}}]}}
    monkeypatch.setattr(search, 'client', lambda: client)
    result = body_of(resources.handler(make_event('/resources', query={'limit': '1'}), None))
    assert result['meta']['source'] == 'opensearch'
    assert result['data']['total'] == 12
    assert result['data']['count'] == 1


def test_indexer_writes_documents_and_recreate_is_explicit(monkeypatch):
    from scripts import index_opensearch
    import opensearchpy.helpers
    client = Mock()
    client.indices.exists.return_value = False
    monkeypatch.setattr(search, 'client', lambda: client)
    monkeypatch.setattr(index_opensearch, 'build_documents', lambda index: [{'_id': 'one', '_source': {'name': 'test'}}])
    bulk = Mock()
    monkeypatch.setattr(opensearchpy.helpers, 'bulk', bulk)
    assert index_opensearch.main([]) == 0
    assert client.indices.create.call_count == 2
    assert bulk.call_count == 2
    client.indices.delete.assert_not_called()
    client.indices.exists.return_value = True
    assert index_opensearch.main(['--recreate']) == 0
    assert client.indices.delete.call_count == 2
