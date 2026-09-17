"""Failure modes that are hard to reach through the happy path.

These are the ones that bite during a live demo: LocalStack not running, a scan
that paginates, a record edited by hand into a bad shape.
"""

import pytest

from src.common import store
from src.common.errors import (
    ApiError,
    BadRequest,
    Forbidden,
    NotFound,
    RateLimited,
    UpstreamError,
)
from src.common.http import api_handler
from src.handlers.aftermath import _as_int
from tests.conftest import body_of, data_of, error_of, make_event


class TestLocalStackDown:
    """The single most common hackathon failure: forgot to start Docker."""

    @pytest.fixture
    def unreachable(self, aws_env, monkeypatch):
        # Port 1 refuses instantly, so this stays fast.
        monkeypatch.setenv("AWS_ENDPOINT_URL", "http://127.0.0.1:1")
        store.reset_clients()
        yield
        store.reset_clients()

    def test_connection_failure_becomes_upstream_error(self, unreachable):
        with pytest.raises(UpstreamError) as exc:
            store.scan_all("faqs")
        assert exc.value.status == 502

    def test_handler_returns_502_not_a_stack_trace(self, unreachable):
        from src.handlers.resources import handler

        response = handler(make_event(path="/resources"), None)
        assert response["statusCode"] == 502
        assert "Traceback" not in response["body"]
        assert error_of(response)["code"] == "UPSTREAM_ERROR"

    def test_static_emergency_numbers_still_work(self, unreachable):
        # The whole point of serving these from memory.
        from src.handlers.emergency import handler

        response = handler(make_event(path="/emergency/numbers"), None)
        assert response["statusCode"] == 200
        assert data_of(response)["unified"] == "112"

    def test_health_reports_unhealthy_rather_than_hanging(self, unreachable):
        from src.handlers.health import handler

        response = handler(make_event(path="/health"), None)
        assert response["statusCode"] == 503
        assert data_of(response)["healthy"] is False


class TestPagination:
    """DynamoDB caps a page at 1MB and returns LastEvaluatedKey for the rest.

    Missing the continuation is a silent bug: the list simply looks shorter.
    """

    class FakePage:
        def __init__(self, pages):
            self.pages = pages
            self.calls = []

        def scan(self, **kwargs):
            self.calls.append(kwargs)
            return self.pages[len(self.calls) - 1]

        def query(self, **kwargs):
            self.calls.append(kwargs)
            return self.pages[len(self.calls) - 1]

    def _install(self, monkeypatch, pages):
        fake = self.FakePage(pages)
        monkeypatch.setattr(store, "table", lambda logical: fake)
        return fake

    def test_scan_follows_the_continuation_key(self, aws_env, monkeypatch):
        fake = self._install(
            monkeypatch,
            [
                {"Items": [{"id": "a"}], "LastEvaluatedKey": {"id": "a"}},
                {"Items": [{"id": "b"}]},
            ],
        )
        assert len(store.scan_all("faqs")) == 2
        assert fake.calls[1]["ExclusiveStartKey"] == {"id": "a"}

    def test_scan_stops_early_once_the_limit_is_met(self, aws_env, monkeypatch):
        fake = self._install(
            monkeypatch,
            [{"Items": [{"id": "a"}, {"id": "b"}], "LastEvaluatedKey": {"id": "b"}}],
        )
        assert len(store.scan_all("faqs", limit=2)) == 2
        assert len(fake.calls) == 1  # no needless second round trip

    def test_scan_truncates_to_the_limit(self, aws_env, monkeypatch):
        self._install(monkeypatch, [{"Items": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}])
        assert len(store.scan_all("faqs", limit=2)) == 2

    def test_query_follows_the_continuation_key(self, aws_env, monkeypatch):
        fake = self._install(
            monkeypatch,
            [
                {"Items": [{"id": "a"}], "LastEvaluatedKey": {"id": "a"}},
                {"Items": [{"id": "b"}]},
            ],
        )
        assert len(store.query_index("faqs", "topic-index", "topic", "fir")) == 2
        assert fake.calls[1]["ExclusiveStartKey"] == {"id": "a"}

    def test_empty_page_is_not_an_error(self, aws_env, monkeypatch):
        self._install(monkeypatch, [{"Items": []}])
        assert store.scan_all("faqs") == []

    def test_missing_items_key_is_tolerated(self, aws_env, monkeypatch):
        self._install(monkeypatch, [{}])
        assert store.scan_all("faqs") == []


class TestErrorWrapping:
    def test_non_boto_exceptions_are_not_swallowed(self, aws_env, monkeypatch):
        """The wrapper translates boto failures only.

        If it caught everything, a genuine bug inside the data layer would be
        reported to the client as "database unreachable" and we would spend the
        demo restarting Docker for no reason.
        """
        class Exploding:
            def scan(self, **kwargs):
                raise RuntimeError("a real bug, not a database problem")

        monkeypatch.setattr(store, "table", lambda logical: Exploding())
        with pytest.raises(RuntimeError, match="a real bug"):
            store.scan_all("faqs")


class TestWrites:
    def test_put_item_round_trips(self, dynamodb):
        store.put_item(
            "emergency_protocols",
            {"scenario_id": "test_case", "title": "T", "steps": ["Call 112."]},
        )
        assert store.get_item("emergency_protocols", {"scenario_id": "test_case"})["title"] == "T"

    def test_put_item_converts_floats(self, dynamodb):
        # A raw float would be rejected by DynamoDB outright.
        store.put_item("resources", {"resource_id": "t", "geo": {"lat": 12.5, "lon": 77.5}})
        item = store.get_item("resources", {"resource_id": "t"})
        assert float(item["geo"]["lat"]) == pytest.approx(12.5)

    def test_put_overwrites_by_key(self, dynamodb):
        for title in ("first", "second"):
            store.put_item("aftermath_steps", {"stage_id": "hospital", "title": title})
        assert store.get_item("aftermath_steps", {"stage_id": "hospital"})["title"] == "second"

    def test_batch_put_reports_its_count(self, dynamodb):
        records = [{"faq_id": f"bulk_{i}", "question": "q?", "answer": "a", "topic": "fir"}
                   for i in range(5)]
        assert store.batch_put("faqs", records) == 5

    def test_batch_put_of_nothing(self, dynamodb):
        assert store.batch_put("faqs", []) == 0

    def test_seeding_is_idempotent(self, dynamodb, seed_data):
        # bootstrap.py is documented as rerunnable; prove it.
        before = len(store.scan_all("faqs"))
        store.batch_put("faqs", seed_data["faqs"])
        assert len(store.scan_all("faqs")) == before


class TestMalformedStoredRecords:
    """Content edited by hand into a bad shape must not 500 the endpoint."""

    def test_missing_order_sorts_last_rather_than_crashing(self, dynamodb):
        from src.handlers.aftermath import handler

        store.put_item("aftermath_steps", {"stage_id": "extra", "title": "No order"})
        data = data_of(handler(make_event(path="/aftermath/steps"), None))
        assert data["count"] == 5
        assert data["items"][-1]["stage_id"] == "extra"

    def test_non_numeric_order_does_not_crash(self, dynamodb):
        from src.handlers.aftermath import handler

        store.put_item("aftermath_steps", {"stage_id": "extra", "title": "T", "order": "first"})
        assert handler(make_event(path="/aftermath/steps"), None)["statusCode"] == 200

    @pytest.mark.parametrize(("value", "expected"), [("3", 3), (3, 3), (None, 99), ("x", 99), ([], 99)])
    def test_as_int_fallback(self, value, expected):
        assert _as_int(value, 99) == expected

    def test_protocol_with_unknown_severity_still_lists(self, dynamodb):
        from src.handlers.emergency import handler

        store.put_item(
            "emergency_protocols",
            {"scenario_id": "odd", "title": "T", "steps": ["x"], "severity": "spicy"},
        )
        data = data_of(handler(make_event(path="/emergency/protocols"), None))
        assert data["count"] == 5
        assert data["items"][-1]["scenario_id"] == "odd"  # unknown severity sorts last

    def test_resource_with_broken_geo_is_kept_not_dropped(self, dynamodb):
        from src.handlers.resources import handler

        store.put_item(
            "resources",
            {"resource_id": "broken", "name": "Zzz Clinic", "type": "hospital",
             "state": "Karnataka", "geo": {"lat": "north"}},
        )
        event = make_event(path="/resources", query={"lat": "12.97", "lon": "77.59"})
        items = data_of(handler(event, None))["items"]
        broken = next(i for i in items if i["resource_id"] == "broken")
        assert broken["distance_km"] is None


class TestErrorTypes:
    @pytest.mark.parametrize(
        ("cls", "status", "code"),
        [
            (BadRequest, 400, "BAD_REQUEST"),
            (Forbidden, 403, "FORBIDDEN"),
            (NotFound, 404, "NOT_FOUND"),
            (RateLimited, 429, "RATE_LIMITED"),
            (UpstreamError, 502, "UPSTREAM_ERROR"),
            (ApiError, 500, "INTERNAL_ERROR"),
        ],
    )
    def test_status_and_code_mapping(self, cls, status, code):
        error = cls("message")
        assert (error.status, error.code) == (status, code)

    def test_details_merge_into_the_error_body(self):
        assert NotFound("x", details={"hint": "y"}).to_error()["hint"] == "y"

    def test_status_and_code_can_be_overridden_per_instance(self):
        error = ApiError("m", status=418, code="TEAPOT")
        assert (error.status, error.code) == (418, "TEAPOT")

    def test_message_survives_str(self):
        assert str(BadRequest("bad thing")) == "bad thing"


class TestHandlerDecorator:
    def test_unexpected_exception_becomes_a_500_envelope(self):
        @api_handler
        def boom(event, context, timer):
            raise RuntimeError("internal detail that must not leak")

        response = boom(make_event(), None)
        assert response["statusCode"] == 500
        assert "internal detail" not in response["body"]
        assert body_of(response)["ok"] is False

    def test_500_message_still_points_at_112(self):
        @api_handler
        def boom(event, context, timer):
            raise RuntimeError("x")

        assert "112" in error_of(boom(make_event(), None))["message"]

    def test_api_errors_keep_their_status(self):
        @api_handler
        def missing(event, context, timer):
            raise NotFound("no such thing")

        assert missing(make_event(), None)["statusCode"] == 404

    def test_preflight_never_reaches_the_body(self):
        @api_handler
        def boom(event, context, timer):
            raise AssertionError("should not run")

        assert boom(make_event(method="OPTIONS"), None)["statusCode"] == 204

    def test_timer_is_passed_through(self):
        @api_handler
        def echo(event, context, timer):
            from src.common.response import ok

            return ok({"ms": timer.ms})

        assert data_of(echo(make_event(), None))["ms"] >= 0

    def test_none_event_does_not_crash_the_decorator(self):
        @api_handler
        def echo(event, context, timer):
            from src.common.response import ok

            return ok("fine")

        assert echo(None, None)["statusCode"] == 200
