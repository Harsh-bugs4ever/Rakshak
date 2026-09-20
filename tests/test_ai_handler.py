"""Assistant request validation; grounded reply coverage lives in test_guidance.py."""

import json

import pytest

from src.handlers.ai import handler, parse_request
from tests.conftest import body_of, error_of, make_event


def call(path="/ai/emergency", payload=None, method="POST", raw=None):
    body = raw if raw is not None else (json.dumps(payload) if payload is not None else None)
    return handler(make_event(path=path, method=method, body=body), None)




class TestMethodValidation:
    @pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
    def test_non_post_is_400(self, method):
        response = call(method=method, payload={"message": "hi"})
        assert response["statusCode"] == 400
        assert "POST" in error_of(response)["message"]


class TestRequestValidation:
    """Enforced from Day 1 so the client cannot drift into a shape Day 2 rejects."""

    def test_accepts_a_minimal_valid_body(self):
        assert parse_request(make_event(body='{"message":"help"}'))["message"] == "help"

    def test_trims_the_message(self):
        assert parse_request(make_event(body='{"message":"  help  "}'))["message"] == "help"

    def test_defaults_context_to_an_empty_dict(self):
        assert parse_request(make_event(body='{"message":"x"}'))["context"] == {}

    def test_session_id_defaults_to_none(self):
        assert parse_request(make_event(body='{"message":"x"}'))["session_id"] is None

    def test_accepts_an_already_parsed_dict_body(self):
        # Some test harnesses and SAM configurations hand over a dict.
        assert parse_request(make_event(body={"message": "x"}))["message"] == "x"

    def test_keeps_the_context_object(self):
        event = make_event(body='{"message":"x","context":{"stage":"hospital"}}')
        assert parse_request(event)["context"] == {"stage": "hospital"}

    @pytest.mark.parametrize("body", [None, "", "   "])
    def test_missing_body_is_400(self, body):
        assert call(raw=body)["statusCode"] == 400

    @pytest.mark.parametrize("body", ["not json", "{broken", "[1,2,3"])
    def test_malformed_json_is_400(self, body):
        response = call(raw=body)
        assert response["statusCode"] == 400
        assert "valid JSON" in error_of(response)["message"]

    @pytest.mark.parametrize("body", ['"a string"', "[1,2,3]", "42"])
    def test_non_object_json_is_400(self, body):
        response = call(raw=body)
        assert response["statusCode"] == 400
        assert "JSON object" in error_of(response)["message"]

    @pytest.mark.parametrize(
        "payload",
        [{}, {"message": None}, {"message": ""}, {"message": "   "}, {"message": 42}],
    )
    def test_missing_or_empty_message_is_400(self, payload):
        response = call(payload=payload)
        assert response["statusCode"] == 400
        assert "message" in error_of(response)["message"]

    def test_over_long_message_is_400(self):
        response = call(payload={"message": "x" * 1001})
        assert response["statusCode"] == 400
        assert "too long" in error_of(response)["message"]

    def test_message_at_the_limit_is_accepted(self):
        assert call(payload={"message": "x" * 1000})["statusCode"] == 200

    @pytest.mark.parametrize("session", [123, "x" * 65, {"id": 1}])
    def test_bad_session_id_is_400(self, session):
        assert call(payload={"message": "x", "session_id": session})["statusCode"] == 400

    def test_blank_session_id_becomes_none(self):
        assert parse_request(make_event(body='{"message":"x","session_id":"  "}'))["session_id"] is None

    @pytest.mark.parametrize("context", ["hospital", 42, [1, 2]])
    def test_non_object_context_is_400(self, context):
        response = call(payload={"message": "x", "context": context})
        assert response["statusCode"] == 400
        assert "context" in error_of(response)["message"]

    def test_unicode_message_survives(self):
        assert parse_request(make_event(body='{"message":"मदद चाहिए"}'))["message"] == "मदद चाहिए"
