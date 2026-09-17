"""OpenSearch client and query builders - Day 2.

The query builders are implemented now because they are pure functions and they
encode a decision that must not drift: the field weighting here (question 3x,
tags 2x, answer 1x) is the same weighting `handlers/aftermath.py` uses in its
Day 1 scorer. Switching engines must not reorder results under the UI.

`client()` raises until the OpenSearch dependency is added, so nothing can
silently half-work.
"""

import os

from .errors import UpstreamError

RESOURCES_INDEX = os.environ.get("OPENSEARCH_RESOURCES_INDEX", "resources")
TOPICS_INDEX = os.environ.get("OPENSEARCH_TOPICS_INDEX", "aftermath_topics")

QUESTION_BOOST = 3
TAGS_BOOST = 2
ANSWER_BOOST = 1


def endpoint():
    return os.environ.get("OPENSEARCH_ENDPOINT") or "http://localhost:4566"


def client():
    """OpenSearch client. Not implemented until Day 2.

    Day 2: `pip install opensearch-py`, then

        from opensearchpy import OpenSearch
        return OpenSearch(hosts=[endpoint()], http_compress=True)
    """
    raise NotImplementedError(
        "OpenSearch is not wired up yet. Search falls back to the DynamoDB "
        "scorer in handlers/aftermath.py; meta.source reports which engine ran."
    )


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
                {"term": {"state": state}},
                {"term": {"state": "All India"}},
            ], "minimum_should_match": 1}}
        )
    if city:
        filters.append({"term": {"city": city}})

    query = {
        "size": max(1, int(limit)),
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
            record["distance_km"] = round(float(sort[0]), 2)
        out.append(record)
    return out


def search(index: str, query: dict) -> list:
    """Run a query. Wraps failures so a search outage never 500s the API."""
    try:
        return parse_hits(client().search(index=index, body=query))
    except NotImplementedError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UpstreamError("Search is unavailable.") from exc
