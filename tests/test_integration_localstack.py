"""End-to-end tests against a real LocalStack.

Skipped unless LocalStack is reachable, so `pytest` stays green on a laptop with
nothing running. To include them:

    docker run -d -p 4566:4566 localstack/localstack
    python scripts/bootstrap.py
    pytest -m integration

These catch what moto cannot: that the table definitions in bootstrap.py are
accepted by a real DynamoDB, that the GSI actually works, and that float->Decimal
conversion survives a genuine round trip.
"""

import json
import os
import socket

import pytest

ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")


def localstack_up() -> bool:
    host, _, port = ENDPOINT.split("//")[1].partition(":")
    try:
        with socket.create_connection((host, int(port or 4566)), timeout=1):
            return True
    except OSError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not localstack_up(), reason=f"LocalStack not reachable at {ENDPOINT}"),
]


@pytest.fixture
def live_store(monkeypatch):
    from src.common import store

    monkeypatch.setenv("AWS_ENDPOINT_URL", ENDPOINT)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    store.reset_clients()
    yield store
    store.reset_clients()


class TestBootstrappedStack:
    def test_all_four_tables_are_active(self, live_store):
        from src.handlers.health import handler

        body = json.loads(handler({"path": "/health", "httpMethod": "GET"}, None)["body"])
        assert body["data"]["healthy"] is True, (
            "Run `python scripts/bootstrap.py` first."
        )

    def test_protocols_round_trip(self, live_store):
        item = live_store.get_item(
            "emergency_protocols", {"scenario_id": "not_breathing"}, required=True
        )
        assert item["steps"]

    def test_gsi_query_works_on_real_dynamodb(self, live_store):
        items = live_store.query_index("faqs", "topic-index", "topic", "fir")
        assert items and all(i["topic"] == "fir" for i in items)

    def test_float_coordinates_survive_the_round_trip(self, live_store):
        from src.common.geo import extract_point

        item = live_store.get_item("resources", {"resource_id": "res_nimhans_trauma_blr"})
        assert extract_point(item) == pytest.approx((12.9433, 77.5964))

    def test_handlers_work_against_live_data(self, live_store):
        from src.handlers.resources import handler

        event = {
            "path": "/resources",
            "httpMethod": "GET",
            "queryStringParameters": {"type": "hospital", "lat": "12.9716", "lon": "77.5946"},
            "headers": {},
        }
        body = json.loads(handler(event, None)["body"])
        assert body["ok"] is True
        assert body["data"]["items"][0]["distance_km"] < 10
