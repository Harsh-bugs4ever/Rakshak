"""Optional OpenSearch retrieval with bounded requests and query builders."""

import os
import math
from functools import lru_cache

from .errors import UpstreamError

RESOURCES_INDEX = os.environ.get("OPENSEARCH_RESOURCES_INDEX", "resources")
TOPICS_INDEX = os.environ.get("OPENSEARCH_TOPICS_INDEX", "aftermath_topics")

QUESTION_BOOST = 3
TAGS_BOOST = 2
ANSWER_BOOST = 1


def endpoint():
    return os.environ.get("OPENSEARCH_ENDPOINT") or "http://localhost:9200"


def enabled():
    return bool(os.environ.get("OPENSEARCH_ENDPOINT"))


def client():
    """Reuse a client per configured endpoint."""
    return _client(endpoint())


@lru_cache(maxsize=4)
def _client(url):
    from opensearchpy import OpenSearch

    return OpenSearch(hosts=[url], http_compress=True, timeout=2,
                      max_retries=0, retry_on_timeout=False)


def build_faq_query(text: str, topic: str = None, limit: int = 10) -> dict:
    """The FAQ search query. Mirrors the Day 1 scorer's weighting."""
    tokens = [t for t in str(text or "").lower().split() if t]
    query = {
        "size": max(1, int(limit)),
        "query": {
            "bool": {
                "should": [
                    {"match": {"question": {"query": text, "boost": QUESTION_BOOST}}},
                    {"match": {"answer": {"query": text, "boost": ANSWER_BOOST}}},
                    {"terms": {"tags": tokens, "boost": TAGS_BOOST}},
                ],
                "minimum_should_match": 1,
            }
        },
    }
    if topic:
        query["query"]["bool"]["filter"] = [{"term": {"topic": topic}}]
    return query


def build_resource_query(text=None, type=None, state=None, city=None,
                         coords=None, limit=20) -> dict:
    """Resource search, optionally sorted by distance.

    Nationwide entries are OR-ed into the state filter rather than excluded by
    it - NALSA is a valid answer in every state.
    """
    must, filters = [], []

    if text:
        must.append(
            {
                "multi_match": {
                    "query": text,
                    "fields": ["name^3", "tags^2", "description", "address"],
                    "operator": "and",
                }
            }
        )
    if type:
        filters.append({"term": {"type": type}})
    if state:
        filters.append(
            {"bool": {"should": [
                {"term": {"state": state.strip().lower()}},
                {"term": {"state": "all india"}},
            ], "minimum_should_match": 1}}
        )
    if city:
        filters.append({"bool": {"should": [
            {"term": {"city": city.strip().lower()}},
            {"term": {"city": ""}},
            {"bool": {"must_not": [{"exists": {"field": "city"}}]}},
        ], "minimum_should_match": 1}})

    query = {
        "size": max(1, int(limit)),
        "track_total_hits": True,
        "query": {"bool": {"must": must or [{"match_all": {}}], "filter": filters}},
    }

    if coords:
        lat, lon = coords
        query["sort"] = [
            {
                "_geo_distance": {
                    "geo": {"lat": lat, "lon": lon},
                    "order": "asc",
                    "unit": "km",
                    # Records with no coordinates sort last instead of vanishing.
                    "ignore_unmapped": True,
                }
            }
        ]
    elif not text:
        query["sort"] = [{"name.raw": "asc"}, {"resource_id": "asc"}]

    return query


def parse_hits(response: dict) -> list:
    """Flatten an OpenSearch response into plain records carrying their score."""
    hits = ((response or {}).get("hits") or {}).get("hits") or []
    out = []
    for hit in hits:
        record = dict(hit.get("_source") or {})
        if hit.get("_score") is not None:
            record["score"] = round(float(hit["_score"]), 3)
        sort = hit.get("sort") or []
        if sort and isinstance(sort[0], (int, float)):
            value = float(sort[0])
            record["distance_km"] = round(value, 2) if math.isfinite(value) else None
        out.append(record)
    return out


def search(index: str, query: dict) -> list:
    """Run a query. Wraps failures so a search outage never 500s the API."""
    try:
        return parse_hits(client().search(index=index, body=query))
    except Exception as exc:  # noqa: BLE001
        raise UpstreamError("Search is unavailable.") from exc


def search_with_total(index: str, query: dict):
    try:
        response = client().search(index=index, body=query)
        total = response.get("hits", {}).get("total", 0)
        if isinstance(total, dict):
            total = total.get("value", 0)
        return parse_hits(response), int(total)
    except Exception as exc:
        raise UpstreamError("Search is unavailable.") from exc
