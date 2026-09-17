"""Tools the AftermathGuideAgent may call.

Same principle as the emergency tools: retrieval only, no reasoning. The agent
summarises what these return and cites the ids; it never authors process advice
of its own.
"""

from ...common.store import get_item, query_index, scan_all
from ...handlers.aftermath import STAGES, TOPICS, rank


def get_aftermath_steps(stage: str) -> dict:
    """The approved checklist for one stage of the process."""
    key = str(stage or "").strip().lower()
    if key not in STAGES:
        return {"found": False, "stage": key, "available": list(STAGES)}

    item = get_item("aftermath_steps", {"stage_id": key})
    if item is None:
        return {"found": False, "stage": key, "available": list(STAGES)}

    return {
        "found": True,
        "stage_id": item.get("stage_id"),
        "title": item.get("title"),
        "checklist": list(item.get("checklist") or []),
        "details": list(item.get("details") or []),
    }


def search_faqs(question: str, topic: str = None, limit: int = 3) -> list:
    """Most relevant approved answers for a free-text question.

    Uses the same scorer as GET /aftermath/faqs so the agent and the search box
    never disagree about what the best answer is.
    """
    text = str(question or "").strip()
    if not text:
        return []

    key = str(topic or "").strip().lower() or None
    if key and key in TOPICS:
        items = query_index("faqs", "topic-index", "topic", key)
    else:
        items = scan_all("faqs")

    return [
        {
            "faq_id": i.get("faq_id"),
            "question": i.get("question"),
            "answer": i.get("answer"),
            "topic": i.get("topic"),
            "score": i.get("score"),
        }
        for i in rank(items, text)[: max(1, int(limit))]
    ]


def search_resources(query: str = None, state: str = None, type: str = None, limit: int = 5) -> list:
    """Hospitals, legal aid offices, NGOs and schemes matching the filters.

    Nationwide entries always survive a state filter - NALSA is a valid answer
    everywhere, and an empty list would be a worse answer than a national one.
    """
    from ...handlers.resources import NATIONWIDE, _matches

    items = scan_all("resources")
    matched = [i for i in items if _matches(i, _norm(type), state, None, query)]
    matched.sort(key=lambda i: (str(i.get("state", "")).lower() == NATIONWIDE,
                                str(i.get("name", "")).lower()))

    return [
        {
            "resource_id": i.get("resource_id"),
            "name": i.get("name"),
            "type": i.get("type"),
            "state": i.get("state"),
            "city": i.get("city"),
            "contact": i.get("contact"),
            "description": i.get("description"),
        }
        for i in matched[: max(1, int(limit))]
    ]


def _norm(value):
    key = str(value or "").strip().lower()
    return key or None
