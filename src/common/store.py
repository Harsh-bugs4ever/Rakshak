"""DynamoDB access layer.

Clients are cached at module level: a warm Lambda reuses the connection, which
removes roughly 100-300ms of TLS handshake from every call after the first.
Tests call `reset_clients()` so moto can intercept a fresh client per test.
"""

import decimal
import threading
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from . import config
from .errors import NotFound, UpstreamError

_lock = threading.Lock()
_resource = None
_tables = {}

# DynamoDB rejects floats outright. Seed data carries lat/lon as floats, so it
# is converted on the way in. 10 significant digits is ~1cm of latitude - far
# more precision than a phone GPS gives.
_CTX = decimal.Context(prec=10)


def reset_clients():
    """Drop cached boto3 objects. Used by tests between moto mocks."""
    global _resource, _tables
    with _lock:
        _resource = None
        _tables = {}


def resource():
    global _resource
    if _resource is None:
        with _lock:
            if _resource is None:
                _resource = boto3.resource(
                    "dynamodb",
                    region_name=config.region(),
                    endpoint_url=config.dynamodb_endpoint(),
                    config=Config(
                        retries={"max_attempts": 3, "mode": "standard"},
                        connect_timeout=2,
                        read_timeout=5,
                    ),
                )
    return _resource


def table(logical: str):
    name = config.table_name(logical)
    # Key on the physical name: tests change table names via env vars between
    # cases, and keying on the logical name would hand back a stale binding.
    if name not in _tables:
        _tables[name] = resource().Table(name)
    return _tables[name]


def to_dynamo(value):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(value, float):
        return _CTX.create_decimal_from_float(value)
    if isinstance(value, dict):
        return {k: to_dynamo(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dynamo(v) for v in value]
    return value


def from_dynamo(value):
    """Convert Decimal back to int/float for anything that is not JSON-encoded."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: from_dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_dynamo(v) for v in value]
    return value


def _wrap(operation: str):
    """Translate boto exceptions into an UpstreamError with a useful message."""

    class _Ctx:
        def __enter__(self_inner):
            return self_inner

        def __exit__(self_inner, exc_type, exc, tb):
            if exc is None:
                return False
            if isinstance(exc, ClientError):
                aws_code = exc.response.get("Error", {}).get("Code", "Unknown")
                raise UpstreamError(
                    f"Database error during {operation}.",
                    details={"aws_error": aws_code},
                ) from exc
            if isinstance(exc, BotoCoreError):
                raise UpstreamError(f"Database unreachable during {operation}.") from exc
            return False

    return _Ctx()


def get_item(logical: str, key: dict, *, required=False, label=None):
    """Fetch one item. Returns None when absent unless `required` is set."""
    with _wrap(f"get {logical}"):
        result = table(logical).get_item(Key=key)
    item = result.get("Item")
    if item is None and required:
        what = label or next(iter(key.values()), "item")
        raise NotFound(f"No record found for {what!r}.")
    return item


def scan_all(logical: str, *, limit=None):
    """Scan a whole table, following pagination.

    A scan is the right call here: these are reference tables with 4-15 rows
    each that change only when an admin edits content. Anything cleverer would
    be complexity without a payoff.
    """
    items = []
    kwargs = {}
    with _wrap(f"scan {logical}"):
        while True:
            page = table(logical).scan(**kwargs)
            items.extend(page.get("Items", []))
            last = page.get("LastEvaluatedKey")
            if not last or (limit is not None and len(items) >= limit):
                break
            kwargs["ExclusiveStartKey"] = last
    return items[:limit] if limit is not None else items


def query_index(logical: str, index: str, key_name: str, key_value, *, limit=None):
    """Query a GSI by its partition key."""
    from boto3.dynamodb.conditions import Key

    items = []
    kwargs = {
        "IndexName": index,
        "KeyConditionExpression": Key(key_name).eq(key_value),
    }
    with _wrap(f"query {logical}.{index}"):
        while True:
            page = table(logical).query(**kwargs)
            items.extend(page.get("Items", []))
            last = page.get("LastEvaluatedKey")
            if not last or (limit is not None and len(items) >= limit):
                break
            kwargs["ExclusiveStartKey"] = last
    return items[:limit] if limit is not None else items


def put_item(logical: str, item: dict):
    with _wrap(f"put {logical}"):
        table(logical).put_item(Item=to_dynamo(item))
    return item


def batch_put(logical: str, items):
    """Write many items. Used by the seeder."""
    count = 0
    with _wrap(f"batch put {logical}"):
        with table(logical).batch_writer() as batch:
            for item in items:
                batch.put_item(Item=to_dynamo(item))
                count += 1
    return count
