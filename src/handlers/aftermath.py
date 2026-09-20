"""Aftermath checklists and FAQ search, with optional OpenSearch retrieval."""

import re

from ..common import params
from ..common import search
from ..common.errors import UpstreamError
from ..common.authz import principal_from_event, require
from ..common.http import api_handler
from ..common.response import ok
from ..common.store import get_item, query_index, scan_all

STEPS_RESOURCE = "AftermathSteps"
FAQ_RESOURCE = "FAQs"

STAGES = ("hospital", "police", "insurance", "legal")
TOPICS = (
    "good_samaritan",
    "hospital",
    "fir",
    "insurance",
    "legal_aid",
    "compensation",
)

TOPIC_INDEX = "topic-index"

# Words too common in this corpus to carry signal - every FIR question contains
# "the" and half contain "accident".
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "does",
    "for", "from", "has", "have", "how", "i", "if", "in", "is", "it", "me", "my",
    "no", "not", "of", "on", "or", "our", "the", "to", "we", "what", "when",
    "where", "which", "who", "will", "with", "you", "your",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")

# People type the domain acronyms with periods far more often than without:
# "F.I.R.", "M.L.C.", "M.A.C.T.". Collapsed before tokenizing, because the
# single-character filter below would otherwise shred them into nothing.
ACRONYM_RE = re.compile(r"\b(?:[a-z]\.){2,}")


@api_handler
def handler(event, context, timer):
    principal = principal_from_event(event)
    path = _path(event)
    qs = params.query_params(event)

    if "/faqs" in path:
        require(principal, "search", FAQ_RESOURCE)
        return _faqs(qs, timer)

    require(principal, "read", STEPS_RESOURCE)
    return _steps(qs, timer)


def _steps(qs, timer):
    stage = params.get_enum(qs, "stage", STAGES)

    if stage:
        item = get_item(
            "aftermath_steps", {"stage_id": stage}, required=True, label=stage
        )
        return ok(item, meta={"source": "dynamodb", "took_ms": timer.ms})

    items = scan_all("aftermath_steps")
    # `order` is what puts hospital before police before insurance before legal.
    items.sort(key=lambda i: (_as_int(i.get("order"), 99), str(i.get("stage_id", ""))))
    return ok(
        {"items": items, "count": len(items)},
        meta={"source": "dynamodb", "took_ms": timer.ms},
    )


def _faqs(qs, timer):
    topic = params.get_enum(qs, "topic", TOPICS)
    text = params.get_query_text(qs)
    limit = params.get_limit(qs, default=10)

    if text and search.enabled():
        try:
            items = search.search(search.TOPICS_INDEX, search.build_faq_query(text, topic, limit))
            return ok(
                {"topic": topic, "query": text, "count": len(items), "items": items},
                meta={"source": "opensearch", "took_ms": timer.ms},
            )
        except UpstreamError:
            pass  # A search outage must not hide the database reference library.

    # Topic alone is an indexed lookup; free text needs the whole corpus.
    if topic and not text:
        items = query_index("faqs", TOPIC_INDEX, "topic", topic, limit=limit)
        items.sort(key=lambda i: str(i.get("faq_id", "")))
        return ok(
            {"topic": topic, "query": None, "count": len(items), "items": items},
            meta={"source": "dynamodb", "index": TOPIC_INDEX, "took_ms": timer.ms},
        )

    items = scan_all("faqs")
    if topic:
        items = [i for i in items if str(i.get("topic", "")).lower() == topic]

    if text:
        items = rank(items, text)[:limit]
        source = "scan+score"
    else:
        items.sort(key=lambda i: str(i.get("faq_id", "")))
        items = items[:limit]
        source = "dynamodb"

    return ok(
        {"topic": topic, "query": text, "count": len(items), "items": items},
        meta={"source": source, "took_ms": timer.ms},
    )


def tokenize(text: str):
    """Lowercase alphanumeric tokens with stopwords removed.

    Single characters are dropped too: a stray "s" from "police's" matches
    nothing useful and inflates scores. Dotted acronyms are collapsed first so
    that "F.I.R." survives that filter as "fir".
    """
    normalised = ACRONYM_RE.sub(
        lambda m: m.group(0).replace(".", ""), str(text).lower()
    )
    return [
        t for t in TOKEN_RE.findall(normalised)
        if t not in STOPWORDS and len(t) > 1
    ]


def score(item, tokens) -> float:
    """Relevance for one FAQ.

    Field weights mirror the OpenSearch query (question 3x, tags 2x, answer
    1x), although BM25 and this small-corpus scorer can rank differently.
    """
    if not tokens:
        return 0.0

    question = set(tokenize(item.get("question", "")))
    answer = set(tokenize(item.get("answer", "")))
    tags = {str(t).lower() for t in (item.get("tags") or [])}
    topic = str(item.get("topic", "")).lower()

    total = 0.0
    for token in tokens:
        if token in question:
            total += 3.0
        if token in tags or token in topic:
            total += 2.0
        if token in answer:
            total += 1.0
    # Reward covering more of the query rather than hammering one word.
    matched = sum(1 for t in set(tokens) if t in question or t in answer or t in tags)
    coverage = matched / len(set(tokens))
    return round(total * (0.5 + coverage), 3)


def rank(items, text):
    """Score, drop non-matches, sort by score then id for a stable order."""
    tokens = tokenize(text)
    scored = []
    for item in items:
        value = score(item, tokens)
        if value <= 0:
            continue
        enriched = dict(item)
        enriched["score"] = value
        scored.append(enriched)
    scored.sort(key=lambda i: (-i["score"], str(i.get("faq_id", ""))))
    return scored


def _as_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _path(event) -> str:
    event = event or {}
    raw = (
        event.get("path")
        or ((event.get("requestContext") or {}).get("http") or {}).get("path")
        or event.get("rawPath")
        or ""
    )
    return str(raw).rstrip("/")
