"""POST /ai/emergency and /ai/aftermath - the Strands Agents endpoints.

Day 1 status: the routes exist and validate their input, but the agents are not
wired up yet, so they answer 501 NOT_IMPLEMENTED in the standard envelope.

That is deliberate. A route that 404s would force the frontend to special-case
its absence and then special-case its arrival; a route that returns a
well-formed 501 lets the UI ship its "assistant unavailable, here are the
protocol steps" fallback now and keep working unchanged when Day 2 lands.

Request validation is live already, so the client contract is enforced from the
start rather than discovered later.
"""

import json

from ..common.errors import BadRequest
from ..common.http import api_handler
from ..common.params import http_method
from ..common.response import fail

MAX_MESSAGE_LEN = 1000
MAX_SESSION_LEN = 64


@api_handler
def handler(event, context, timer):
    if http_method(event) != "POST":
        raise BadRequest("This endpoint accepts POST only.")

    request = parse_request(event)
    mode = "emergency" if "/emergency" in _path(event) else "aftermath"

    return fail(
        "NOT_IMPLEMENTED",
        "The assistant is not available yet. Use the protocol steps in the app.",
        status=501,
        details={
            "mode": mode,
            "session_id": request["session_id"],
            # Tells the UI to render bundled guidance rather than retrying.
            "retryable": False,
        },
        meta={"source": "stub", "agent": None, "took_ms": timer.ms},
    )


def parse_request(event) -> dict:
    """Validate the POST body against the contract in docs/api-spec.md.

    Enforced now so the frontend cannot drift into a shape the agents will
    reject on Day 2.
    """
    raw = (event or {}).get("body")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise BadRequest("A JSON body with a 'message' field is required.")

    if isinstance(raw, dict):
        payload = raw
    else:
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            raise BadRequest("Request body must be valid JSON.")

    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a JSON object.")

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise BadRequest("Field 'message' is required and must be a non-empty string.")
    message = message.strip()
    if len(message) > MAX_MESSAGE_LEN:
        raise BadRequest(f"Field 'message' is too long (max {MAX_MESSAGE_LEN} characters).")

    session_id = payload.get("session_id")
    if session_id is not None:
        if not isinstance(session_id, str) or len(session_id) > MAX_SESSION_LEN:
            raise BadRequest("Field 'session_id' must be a short string.")
        session_id = session_id.strip() or None

    context_obj = payload.get("context")
    if context_obj is not None and not isinstance(context_obj, dict):
        raise BadRequest("Field 'context' must be an object.")

    return {
        "message": message,
        "session_id": session_id,
        "context": context_obj or {},
    }


def _path(event) -> str:
    event = event or {}
    raw = (
        event.get("path")
        or ((event.get("requestContext") or {}).get("http") or {}).get("path")
        or event.get("rawPath")
        or ""
    )
    return str(raw).rstrip("/")
