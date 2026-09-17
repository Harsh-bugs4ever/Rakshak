"""GET /emergency/* - the bystander endpoints.

Everything here is on the critical path for someone standing at a crash scene,
so the handlers stay boring: no cleverness, no chained lookups, and static
fallbacks that work with the database down.
"""

from ..common import params, static_content
from ..common.authz import principal_from_event, require
from ..common.http import api_handler
from ..common.response import ok
from ..common.store import get_item, scan_all

RESOURCE = "EmergencyProtocols"

# Severity drives the badge colour in the UI; ordering puts the critical
# protocols first in the list response.
SEVERITY_ORDER = {"critical": 0, "high": 1, "moderate": 2}


@api_handler
def handler(event, context, timer):
    principal = principal_from_event(event)
    path = _path(event)

    if path.endswith("/numbers"):
        qs = params.query_params(event)
        state = params.get_str(qs, "state", max_len=64)
        return ok(
            static_content.emergency_numbers(state),
            meta={"source": "static", "cached": True, "took_ms": timer.ms},
        )

    if path.endswith("/good-samaritan"):
        return ok(
            static_content.good_samaritan(),
            meta={"source": "static", "cached": True, "took_ms": timer.ms},
        )

    # Default: /emergency/protocols
    require(principal, "read", RESOURCE)
    qs = params.query_params(event)
    scenario = params.get_slug(qs, "scenario")

    if scenario:
        item = get_item(
            "emergency_protocols",
            {"scenario_id": scenario},
            required=True,
            label=scenario,
        )
        return ok(item, meta={"source": "dynamodb", "took_ms": timer.ms})

    items = scan_all("emergency_protocols")
    items.sort(key=_sort_key)
    return ok(
        {"items": items, "count": len(items)},
        meta={"source": "dynamodb", "took_ms": timer.ms},
    )


def _sort_key(item):
    severity = str(item.get("severity", "")).lower()
    return (SEVERITY_ORDER.get(severity, 99), str(item.get("scenario_id", "")))


def _path(event) -> str:
    event = event or {}
    raw = (
        event.get("path")
        or ((event.get("requestContext") or {}).get("http") or {}).get("path")
        or event.get("rawPath")
        or ""
    )
    # Trailing slashes make `/numbers` and `/numbers/` behave differently
    # otherwise, which is a needless 404.
    return str(raw).rstrip("/")
