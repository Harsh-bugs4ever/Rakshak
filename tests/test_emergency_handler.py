"""GET /emergency/* - the endpoints a bystander hits at a crash scene."""

import pytest

from src.handlers.emergency import handler
from tests.conftest import body_of, data_of, error_of, make_event

PROTOCOLS = "/emergency/protocols"


def call(path=PROTOCOLS, **kwargs):
    return handler(make_event(path=path, **kwargs), None)


class TestSingleProtocol:
    def test_returns_the_requested_scenario(self, dynamodb):
        data = data_of(call(query={"scenario": "not_breathing"}))
        assert data["scenario_id"] == "not_breathing"
        assert data["severity"] == "critical"

    def test_steps_arrive_in_order_and_non_empty(self, dynamodb):
        steps = data_of(call(query={"scenario": "not_breathing"}))["steps"]
        assert len(steps) >= 3
        assert "112" in steps[1]  # calling for help is step two, always

    def test_do_not_list_is_present(self, dynamodb):
        assert data_of(call(query={"scenario": "not_breathing"}))["do_not"]

    def test_scenario_is_case_insensitive(self, dynamodb):
        assert data_of(call(query={"scenario": "NOT_BREATHING"}))["scenario_id"] == "not_breathing"

    def test_scenario_tolerates_whitespace(self, dynamodb):
        assert data_of(call(query={"scenario": " not_breathing "}))["scenario_id"] == "not_breathing"

    @pytest.mark.parametrize(
        "scenario",
        ["not_breathing", "breathing_injured", "heavy_bleeding", "unconscious_breathing"],
    )
    def test_every_seeded_scenario_is_reachable(self, dynamodb, scenario):
        assert call(query={"scenario": scenario})["statusCode"] == 200


class TestProtocolList:
    def test_no_scenario_lists_all(self, dynamodb):
        data = data_of(call())
        assert data["count"] == 4
        assert len(data["items"]) == 4

    def test_null_query_string_does_not_crash(self, dynamodb):
        assert call(query=None)["statusCode"] == 200

    def test_blank_scenario_is_treated_as_absent(self, dynamodb):
        assert data_of(call(query={"scenario": ""}))["count"] == 4

    def test_critical_protocols_sort_first(self, dynamodb):
        items = data_of(call())["items"]
        severities = [i["severity"] for i in items]
        assert severities[0] == "critical"
        assert severities == sorted(severities, key=lambda s: {"critical": 0, "high": 1}[s])

    def test_empty_table_returns_an_empty_list_not_an_error(self, empty_dynamodb):
        data = data_of(call())
        assert data == {"items": [], "count": 0}


class TestErrors:
    def test_unknown_scenario_is_404(self, dynamodb):
        response = call(query={"scenario": "abducted_by_aliens"})
        assert response["statusCode"] == 404
        assert error_of(response)["code"] == "NOT_FOUND"

    @pytest.mark.parametrize("bad", ["not breathing", "../../secrets", "a" * 100, "sce;nario"])
    def test_malformed_scenario_is_400(self, dynamodb, bad):
        response = call(query={"scenario": bad})
        assert response["statusCode"] == 400
        assert error_of(response)["code"] == "BAD_REQUEST"

    def test_missing_table_becomes_502_not_500(self, no_tables):
        # The failure is downstream of us, and the client should retry.
        response = call(query={"scenario": "not_breathing"})
        assert response["statusCode"] == 502
        assert error_of(response)["code"] == "UPSTREAM_ERROR"

    def test_upstream_error_never_leaks_internals(self, no_tables):
        assert "Traceback" not in call()["body"]

    def test_unexpected_exception_still_tells_the_user_to_call_112(self, dynamodb, monkeypatch):
        monkeypatch.setattr(
            "src.handlers.emergency.scan_all",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        response = call()
        assert response["statusCode"] == 500
        assert "112" in error_of(response)["message"]


class TestStaticRoutes:
    """These must work with the database down - they never touch DynamoDB."""

    def test_numbers_without_a_state(self, no_tables):
        data = data_of(call(path="/emergency/numbers"))
        assert data["ambulance"] == "108"
        assert data["unified"] == "112"
        assert data["matched"] is False

    def test_numbers_for_a_known_state(self, no_tables):
        data = data_of(call(path="/emergency/numbers", query={"state": "West Bengal"}))
        assert data["ambulance"] == "102"
        assert data["matched"] is True

    def test_state_match_is_case_insensitive(self, no_tables):
        assert data_of(call(path="/emergency/numbers", query={"state": "kErAlA"}))["matched"] is True

    def test_unknown_state_falls_back_instead_of_erroring(self, no_tables):
        # Refusing to show 112 over a spelling mismatch would be indefensible.
        data = data_of(call(path="/emergency/numbers", query={"state": "Wakanda"}))
        assert data["unified"] == "112"
        assert data["matched"] is False

    def test_good_samaritan_rights(self, no_tables):
        data = data_of(call(path="/emergency/good-samaritan"))
        assert len(data["points"]) >= 4
        assert any("identity" in p or "name" in p for p in data["points"])

    def test_static_routes_are_marked_cached(self, no_tables):
        assert body_of(call(path="/emergency/numbers"))["meta"]["source"] == "static"

    def test_trailing_slash_still_routes(self, no_tables):
        assert call(path="/emergency/good-samaritan/")["statusCode"] == 200

    def test_stage_prefixed_path_still_routes(self, no_tables):
        # SAM local serves under /Prod in a deployed stage.
        assert call(path="/Prod/emergency/numbers")["statusCode"] == 200


class TestEnvelopeAndHeaders:
    def test_meta_reports_dynamodb_as_the_source(self, dynamodb):
        assert body_of(call())["meta"]["source"] == "dynamodb"

    def test_meta_reports_elapsed_time(self, dynamodb):
        assert body_of(call())["meta"]["took_ms"] >= 0

    def test_cors_headers_on_success(self, dynamodb):
        assert call()["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_cors_headers_on_error(self, dynamodb):
        response = call(query={"scenario": "nope_not_here"})
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"

    def test_options_preflight_short_circuits(self, no_tables):
        # Must not require the database - the browser sends this first.
        assert call(method="OPTIONS")["statusCode"] == 204

    def test_context_argument_is_optional(self, dynamodb):
        assert handler(make_event(path=PROTOCOLS))["statusCode"] == 200


class TestAuthorization:
    def test_anonymous_can_read(self, dynamodb):
        assert call(headers={})["statusCode"] == 200

    def test_admin_can_also_read(self, dynamodb):
        assert call(headers={"X-User-Role": "admin"})["statusCode"] == 200

    def test_bogus_role_still_gets_read_access(self, dynamodb):
        # Reads are public; a junk role must not lock a bystander out.
        assert call(headers={"X-User-Role": "hacker"})["statusCode"] == 200
