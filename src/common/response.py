"""The single response envelope every endpoint returns.

    {"ok": bool, "data": ..., "error": ..., "meta": {...}}

Keeping this in one place means the frontend has exactly one shape to handle,
including on errors - which matters when the UI is rendering first-aid steps and
must degrade to bundled offline content rather than a blank screen.
"""

import json
import time
from decimal import Decimal

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-User-Role,X-User-Id",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


class DecimalEncoder(json.JSONEncoder):
    """DynamoDB hands back Decimal for every number.

    Plain json.dumps raises TypeError on those, which would turn a perfectly
    good trauma-centre record into a 500. Integral values serialise as int so
    that `order: 1` does not become `1.0` in the client.
    """

    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == o.to_integral_value() else float(o)
        if isinstance(o, set):
            return sorted(o)
        if isinstance(o, bytes):
            return o.decode("utf-8", "replace")
        return super().default(o)


def _envelope(body: dict, status: int, extra_headers=None) -> dict:
    headers = dict(CORS_HEADERS)
    headers["Content-Type"] = "application/json; charset=utf-8"
    headers["Cache-Control"] = "public, max-age=300" if status == 200 else "no-store"
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status,
        "headers": headers,
        # ensure_ascii=False keeps Devanagari readable on the wire.
        "body": json.dumps(body, cls=DecimalEncoder, ensure_ascii=False),
    }


def ok(data, *, meta=None, status=200, headers=None) -> dict:
    body = {
        "ok": True,
        "data": data,
        "error": None,
        "meta": _with_defaults(meta),
    }
    return _envelope(body, status, headers)


def fail(code: str, message: str, *, status=400, meta=None, details=None, headers=None) -> dict:
    error = {"code": code, "message": message}
    if details:
        error.update(details)
    body = {
        "ok": False,
        "data": None,
        "error": error,
        "meta": _with_defaults(meta),
    }
    return _envelope(body, status, headers)


def no_content(status=204) -> dict:
    """CORS preflight. No envelope - there is no body to put one in."""
    return {"statusCode": status, "headers": dict(CORS_HEADERS), "body": ""}


def _with_defaults(meta) -> dict:
    out = {"source": "unknown", "cached": False, "took_ms": 0}
    if meta:
        out.update(meta)
    return out


class Timer:
    """Wall-clock milliseconds, for the `took_ms` field."""

    def __init__(self):
        self._start = time.perf_counter()

    @property
    def ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)
