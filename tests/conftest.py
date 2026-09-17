"""Shared fixtures.

Unit tests run entirely against moto - no Docker, no LocalStack, no network -
so `pytest` works on a laptop in a hackathon venue with bad wifi. The
integration tests in test_integration_localstack.py are the ones that need the
real local stack, and they are marked and skipped by default.
"""

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Fake credentials, and no endpoint override.

    AWS_ENDPOINT_URL must be cleared or moto's in-memory backend is bypassed in
    favour of a LocalStack that may not be running - which produces confusing
    connection errors instead of test failures.
    """
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
    monkeypatch.setenv("AWS_REGION", "ap-south-1")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("DEFAULT_PAGE_SIZE", raising=False)
    monkeypatch.delenv("MAX_PAGE_SIZE", raising=False)


@pytest.fixture
def seed_data():
    """The real content from data/*.json, keyed by logical table."""
    out = {}
    for logical in ("emergency_protocols", "aftermath_steps", "faqs", "resources"):
        path = DATA_DIR / f"{logical}.json"
        with path.open(encoding="utf-8") as fh:
            out[logical] = json.load(fh)
    return out


@pytest.fixture
def dynamodb(aws_env, seed_data):
    """Tables created and seeded with the production content.

    Seeding with the real data rather than fixtures means the tests also catch
    content regressions: delete a protocol from data/, and a test fails.
    """
    from moto import mock_aws

    from src.common import store

    with mock_aws():
        store.reset_clients()
        client = store.resource().meta.client

        client.create_table(
            TableName="EmergencyProtocols",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "scenario_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "scenario_id", "KeyType": "HASH"}],
        )
        client.create_table(
            TableName="AftermathSteps",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "stage_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "stage_id", "KeyType": "HASH"}],
        )
        client.create_table(
            TableName="FAQs",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "faq_id", "AttributeType": "S"},
                {"AttributeName": "topic", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "faq_id", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "topic-index",
                    "KeySchema": [{"AttributeName": "topic", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )
        client.create_table(
            TableName="Resources",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "resource_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "resource_id", "KeyType": "HASH"}],
        )

        for logical, records in seed_data.items():
            store.batch_put(logical, records)

        yield store
        store.reset_clients()


@pytest.fixture
def empty_dynamodb(aws_env):
    """Tables that exist but hold nothing - the half-bootstrapped case."""
    from moto import mock_aws

    from src.common import store

    with mock_aws():
        store.reset_clients()
        client = store.resource().meta.client
        client.create_table(
            TableName="EmergencyProtocols",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "scenario_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "scenario_id", "KeyType": "HASH"}],
        )
        client.create_table(
            TableName="AftermathSteps",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "stage_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "stage_id", "KeyType": "HASH"}],
        )
        client.create_table(
            TableName="Resources",
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "resource_id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "resource_id", "KeyType": "HASH"}],
        )
        yield store
        store.reset_clients()


@pytest.fixture
def no_tables(aws_env):
    """Mocked AWS with no tables at all - simulates DynamoDB being unusable."""
    from moto import mock_aws

    from src.common import store

    with mock_aws():
        store.reset_clients()
        yield store
        store.reset_clients()


# --- event helpers ----------------------------------------------------------

def make_event(path="/", method="GET", query=None, headers=None, body=None):
    """An API Gateway v1 proxy event.

    `query` of None becomes `queryStringParameters: None`, matching what API
    Gateway actually sends when there is no query string - a shape that has
    caused more NoneType crashes than any other in serverless code.
    """
    return {
        "path": path,
        "httpMethod": method,
        "queryStringParameters": query,
        "headers": headers or {},
        "pathParameters": None,
        "body": body,
        "isBase64Encoded": False,
        "requestContext": {"requestId": "test-request", "path": path},
    }


def body_of(response):
    """Parsed JSON body of a handler response."""
    return json.loads(response["body"])


def data_of(response):
    return body_of(response)["data"]


def error_of(response):
    return body_of(response)["error"]
