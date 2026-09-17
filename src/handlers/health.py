"""GET /health - is the stack actually up?

Used by the seed script and by the frontend to decide whether to fall back to
bundled offline content. Reports per-table row counts so a half-seeded database
is visible immediately rather than showing up as an empty list in the UI.
"""

from ..common import config
from ..common.http import api_handler
from ..common.response import ok
from ..common.store import resource

LOGICAL_TABLES = ("emergency_protocols", "aftermath_steps", "faqs", "resources")


@api_handler
def handler(event, context, timer):
    tables = {}
    healthy = True

    for logical in LOGICAL_TABLES:
        name = config.table_name(logical)
        try:
            desc = resource().meta.client.describe_table(TableName=name)["Table"]
            # ItemCount updates roughly every six hours in real DynamoDB, so it
            # is a hint, not a guarantee. LocalStack reports it live.
            tables[logical] = {
                "table": name,
                "status": desc.get("TableStatus"),
                "approx_items": desc.get("ItemCount", 0),
            }
            if desc.get("TableStatus") != "ACTIVE":
                healthy = False
        except Exception as exc:  # noqa: BLE001 - health must never raise
            healthy = False
            tables[logical] = {
                "table": name,
                "status": "UNAVAILABLE",
                "error": type(exc).__name__,
            }

    return ok(
        {
            "healthy": healthy,
            "endpoint": config.dynamodb_endpoint() or "aws",
            "region": config.region(),
            "tables": tables,
        },
        meta={"source": "dynamodb", "took_ms": timer.ms},
        status=200 if healthy else 503,
    )
