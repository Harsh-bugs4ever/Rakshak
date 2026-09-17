"""The DynamoDB access layer and the /health endpoint."""

import pytest

from src.common import config, store
from src.common.errors import NotFound, UpstreamError
from src.handlers.health import handler as health_handler
from tests.conftest import data_of, make_event


class TestConfig:
    def test_default_table_names(self, aws_env):
        assert config.table_name("faqs") == "FAQs"

    def test_env_override(self, aws_env, monkeypatch):
        monkeypatch.setenv("TABLE_FAQS", "FAQs-staging")
        assert config.table_name("faqs") == "FAQs-staging"

    def test_unknown_logical_table_raises(self, aws_env):
        with pytest.raises(KeyError):
            config.table_name("nope")

    def test_empty_endpoint_is_treated_as_unset(self, aws_env, monkeypatch):
        # `AWS_ENDPOINT_URL=""` in a SAM template must mean "use real AWS".
        monkeypatch.setenv("AWS_ENDPOINT_URL", "")
        assert config.dynamodb_endpoint() is None

    def test_endpoint_is_read_lazily(self, aws_env, monkeypatch):
        monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localhost:4566")
        assert config.dynamodb_endpoint() == "http://localhost:4566"

    def test_garbage_page_size_falls_back(self, aws_env, monkeypatch):
        monkeypatch.setenv("DEFAULT_PAGE_SIZE", "lots")
        assert config.default_limit() == 20

    def test_zero_page_size_is_floored_at_one(self, aws_env, monkeypatch):
        monkeypatch.setenv("MAX_PAGE_SIZE", "0")
        assert config.max_limit() == 1


class TestTypeConversion:
    def test_floats_become_decimals(self):
        # DynamoDB rejects floats outright.
        converted = store.to_dynamo({"geo": {"lat": 12.9433}})
        assert not isinstance(converted["geo"]["lat"], float)

    def test_nested_lists_are_converted(self):
        converted = store.to_dynamo({"points": [{"lat": 1.5}]})
        assert not isinstance(converted["points"][0]["lat"], float)

    def test_ints_and_strings_pass_through(self):
        assert store.to_dynamo({"order": 1, "id": "x"}) == {"order": 1, "id": "x"}

    def test_round_trip_preserves_value(self):
        assert store.from_dynamo(store.to_dynamo(12.9433)) == pytest.approx(12.9433)

    def test_integral_decimal_comes_back_as_int(self):
        assert store.from_dynamo(store.to_dynamo(3.0)) == 3
        assert isinstance(store.from_dynamo(store.to_dynamo(3.0)), int)

    def test_from_dynamo_recurses_into_dicts(self):
        converted = store.from_dynamo(store.to_dynamo({"geo": {"lat": 12.5}}))
        assert converted["geo"]["lat"] == pytest.approx(12.5)

    def test_from_dynamo_recurses_into_lists(self):
        converted = store.from_dynamo(store.to_dynamo([{"lat": 1.5}, {"lat": 2.5}]))
        assert [c["lat"] for c in converted] == pytest.approx([1.5, 2.5])

    def test_from_dynamo_passes_other_types_through(self):
        assert store.from_dynamo("not_breathing") == "not_breathing"
        assert store.from_dynamo(None) is None


class TestGetItem:
    def test_returns_the_item(self, dynamodb):
        item = store.get_item("emergency_protocols", {"scenario_id": "not_breathing"})
        assert item["title"]

    def test_missing_returns_none_by_default(self, dynamodb):
        assert store.get_item("emergency_protocols", {"scenario_id": "ghost"}) is None

    def test_missing_raises_when_required(self, dynamodb):
        with pytest.raises(NotFound, match="ghost"):
            store.get_item("emergency_protocols", {"scenario_id": "ghost"}, required=True)

    def test_client_error_becomes_upstream_error(self, no_tables):
        with pytest.raises(UpstreamError) as exc:
            store.get_item("faqs", {"faq_id": "x"})
        assert exc.value.status == 502
        assert exc.value.details["aws_error"] == "ResourceNotFoundException"


class TestScanAndQuery:
    def test_scan_returns_everything(self, dynamodb):
        assert len(store.scan_all("faqs")) == 15

    def test_scan_honours_limit(self, dynamodb):
        assert len(store.scan_all("faqs", limit=3)) == 3

    def test_scan_of_an_empty_table(self, empty_dynamodb):
        assert store.scan_all("emergency_protocols") == []

    def test_query_index_filters_by_topic(self, dynamodb):
        items = store.query_index("faqs", "topic-index", "topic", "fir")
        assert items and all(i["topic"] == "fir" for i in items)

    def test_query_index_for_an_unused_topic(self, dynamodb):
        assert store.query_index("faqs", "topic-index", "topic", "nothing") == []

    def test_query_on_a_missing_index_is_upstream_error(self, dynamodb):
        with pytest.raises(UpstreamError):
            store.query_index("faqs", "no-such-index", "topic", "fir")


class TestClientCaching:
    def test_resource_is_reused_across_calls(self, dynamodb):
        assert store.resource() is store.resource()

    def test_reset_drops_the_cache(self, dynamodb):
        first = store.resource()
        store.reset_clients()
        assert store.resource() is not first

    def test_table_cache_keys_on_the_physical_name(self, dynamodb, monkeypatch):
        # Keying on the logical name would hand back a stale binding when the
        # physical name changes via env var.
        default = store.table("faqs")
        monkeypatch.setenv("TABLE_FAQS", "FAQs-other")
        assert store.table("faqs").name != default.name


class TestHealth:
    def test_reports_healthy_with_row_counts(self, dynamodb):
        response = health_handler(make_event(path="/health"), None)
        assert response["statusCode"] == 200
        data = data_of(response)
        assert data["healthy"] is True
        assert data["tables"]["faqs"]["approx_items"] == 15

    def test_reports_503_when_tables_are_missing(self, no_tables):
        response = health_handler(make_event(path="/health"), None)
        assert response["statusCode"] == 503
        assert data_of(response)["healthy"] is False

    def test_partial_bootstrap_is_visible(self, empty_dynamodb):
        # Three tables exist, FAQs does not - this must not read as healthy.
        response = health_handler(make_event(path="/health"), None)
        data = data_of(response)
        assert data["healthy"] is False
        assert data["tables"]["faqs"]["status"] == "UNAVAILABLE"
        assert data["tables"]["resources"]["status"] == "ACTIVE"

    def test_health_never_raises(self, no_tables):
        # A health check that 500s tells you nothing about what is wrong.
        assert health_handler(make_event(path="/health"), None)["statusCode"] == 503

    def test_reports_the_endpoint_in_use(self, dynamodb):
        assert data_of(health_handler(make_event(path="/health"), None))["endpoint"] == "aws"
