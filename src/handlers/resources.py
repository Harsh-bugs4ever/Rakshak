"""Resource filtering and distance search with an optional OpenSearch backend."""

from ..common import params
from ..common import search
from ..common.errors import UpstreamError
from ..common.authz import principal_from_event, require
from ..common.geo import extract_point, haversine_km
from ..common.http import api_handler
from ..common.response import ok
from ..common.store import scan_all

RESOURCE = "Resources"

TYPES = ("hospital", "legal_aid", "ngo", "scheme")

# Nationwide entries (NALSA, the Solatium scheme) carry this as their state and
# must survive any state filter - they are valid answers everywhere.
NATIONWIDE = "all india"


@api_handler
def handler(event, context, timer):
    require(principal_from_event(event), "search", RESOURCE)

    qs = params.query_params(event)
    type_filter = params.get_enum(qs, "type", TYPES)
    state = params.get_str(qs, "state", max_len=64)
    city = params.get_str(qs, "city", max_len=64)
    text = params.get_query_text(qs)
    coords = params.get_coords(qs)
    limit = params.get_limit(qs)

    if search.enabled():
        try:
            items, total = search.search_with_total(
                search.RESOURCES_INDEX,
                search.build_resource_query(text, type_filter, state, city, coords, limit),
            )
            if coords:
                items = _with_distance(items, coords)
            return ok(
                {"count": len(items), "total": total, "items": items},
                meta={"source": "opensearch", "took_ms": timer.ms},
            )
        except UpstreamError:
            pass

    items = scan_all("resources")
    items = [i for i in items if _matches(i, type_filter, state, city, text)]

    if coords:
        items = _with_distance(items, coords)
    else:
        items.sort(key=lambda i: str(i.get("name", "")).lower())

    total = len(items)
    items = items[:limit]

    return ok(
        {"count": len(items), "total": total, "items": items},
        meta={"source": "dynamodb", "took_ms": timer.ms},
    )


def _matches(item, type_filter, state, city, text) -> bool:
    if type_filter and str(item.get("type", "")).lower() != type_filter:
        return False

    if state:
        item_state = str(item.get("state", "")).strip().lower()
        if item_state not in (state.strip().lower(), NATIONWIDE):
            return False

    if city:
        item_city = str(item.get("city", "")).strip().lower()
        # A blank city means the record is not city-specific (a state authority,
        # a national scheme), so it stays in the results.
        if item_city and item_city != city.strip().lower():
            return False

    if text:
        haystack = " ".join(
            [
                str(item.get("name", "")),
                str(item.get("description", "")),
                str(item.get("address", "")),
                str(item.get("city", "")),
                " ".join(str(t) for t in (item.get("tags") or [])),
            ]
        ).lower()
        # Every word must appear somewhere: "24x7 trauma" should not match a
        # record that is merely 24x7.
        if not all(word in haystack for word in text.lower().split()):
            return False

    return True


def _with_distance(items, coords):
    """Annotate with distance_km and sort nearest first.

    Records without coordinates keep their place at the end rather than being
    dropped - a legal aid office with no lat/lon is still the right answer.
    """
    lat, lon = coords
    located, unlocated = [], []

    for item in items:
        point = extract_point(item)
        enriched = dict(item)
        if point is None:
            enriched["distance_km"] = None
            unlocated.append(enriched)
        else:
            enriched["distance_km"] = haversine_km(lat, lon, point[0], point[1])
            located.append(enriched)

    located.sort(key=lambda i: (i["distance_km"], str(i.get("name", "")).lower()))
    unlocated.sort(key=lambda i: str(i.get("name", "")).lower())
    return located + unlocated
