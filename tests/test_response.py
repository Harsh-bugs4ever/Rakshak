"""The response envelope - the one shape the whole frontend depends on."""

import json
from decimal import Decimal

import pytest

from src.common.response import DecimalEncoder, Timer, fail, no_content, ok
from tests.conftest import body_of


class TestEnvelope:
    def test_success_envelope_has_all_four_keys(self):
        body = body_of(ok({"hello": "world"}))
        assert set(body) == {"ok", "data", "error", "meta"}
        assert body["ok"] is True
        assert body["error"] is None

    def test_error_envelope_keeps_data_null(self):
        body = body_of(fail("NOT_FOUND", "gone", status=404))
        assert body["ok"] is False
        assert body["data"] is None
        assert body["error"] == {"code": "NOT_FOUND", "message": "gone"}

    def test_meta_always_has_defaults(self):
        assert body_of(ok(1))["meta"] == {"source": "unknown", "cached": False, "took_ms": 0}

    def test_meta_overrides_merge_rather_than_replace(self):
        meta = body_of(ok(1, meta={"source": "dynamodb"}))["meta"]
        assert meta["source"] == "dynamodb"
        assert meta["cached"] is False  # default survived

    def test_error_details_merge_into_error_object(self):
        error = body_of(fail("FORBIDDEN", "no", details={"cedar": {"decision": "Deny"}}))["error"]
        assert error["cedar"] == {"decision": "Deny"}

    @pytest.mark.parametrize("status", [200, 201, 400, 403, 404, 500, 502])
    def test_status_code_is_passed_through(self, status):
        response = ok(1, status=status) if status < 400 else fail("X", "y", status=status)
        assert response["statusCode"] == status


class TestHeaders:
    def test_cors_headers_present_on_success_and_failure(self):
        for response in (ok(1), fail("X", "y")):
            assert response["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_successful_reads_are_cacheable(self):
        assert "max-age" in ok(1)["headers"]["Cache-Control"]

    def test_errors_are_never_cached(self):
        # A cached 404 would keep showing "no protocol" after the fix ships.
        assert fail("X", "y")["headers"]["Cache-Control"] == "no-store"

    def test_charset_is_declared(self):
        assert "charset=utf-8" in ok(1)["headers"]["Content-Type"]

    def test_extra_headers_are_merged(self):
        response = ok(1, headers={"X-Trace": "abc"})
        assert response["headers"]["X-Trace"] == "abc"
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"


class TestDecimalEncoding:
    """DynamoDB returns Decimal for every number. Unhandled, this is a 500."""

    def test_integral_decimal_serialises_as_int(self):
        assert json.loads(json.dumps({"n": Decimal("1")}, cls=DecimalEncoder))["n"] == 1

    def test_integral_decimal_is_not_a_float(self):
        # `"order": 1.0` in JSON would render as "1.0" in a list position badge.
        assert "1.0" not in json.dumps({"n": Decimal("1")}, cls=DecimalEncoder)

    def test_fractional_decimal_keeps_precision(self):
        encoded = json.loads(json.dumps({"lat": Decimal("12.9433")}, cls=DecimalEncoder))
        assert encoded["lat"] == pytest.approx(12.9433)

    def test_negative_decimal(self):
        assert json.loads(json.dumps(Decimal("-77.59"), cls=DecimalEncoder)) == pytest.approx(-77.59)

    def test_nested_decimals_inside_a_real_response(self):
        payload = {"geo": {"lat": Decimal("12.9433"), "lon": Decimal("77.5964")}}
        assert body_of(ok(payload))["data"]["geo"]["lat"] == pytest.approx(12.9433)

    def test_sets_become_sorted_lists(self):
        # DynamoDB string sets arrive as Python sets.
        assert json.loads(json.dumps({"t": {"b", "a"}}, cls=DecimalEncoder))["t"] == ["a", "b"]

    def test_bytes_are_decoded(self):
        assert json.loads(json.dumps(b"hi", cls=DecimalEncoder)) == "hi"

    def test_unserialisable_type_still_raises(self):
        with pytest.raises(TypeError):
            json.dumps(object(), cls=DecimalEncoder)


class TestUnicode:
    def test_devanagari_survives_unescaped(self):
        response = ok({"title": "रक्षक"})
        assert "रक्षक" in response["body"]

    def test_devanagari_round_trips(self):
        assert body_of(ok({"t": "रक्षक"}))["data"]["t"] == "रक्षक"


class TestPreflight:
    def test_no_content_has_cors_and_empty_body(self):
        response = no_content()
        assert response["statusCode"] == 204
        assert response["body"] == ""
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"


class TestTimer:
    def test_reports_non_negative_milliseconds(self):
        assert Timer().ms >= 0

    def test_is_monotonic(self):
        timer = Timer()
        first = timer.ms
        for _ in range(50_000):
            pass
        assert timer.ms >= first
