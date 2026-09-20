"""POST /ai/*: grounded reference guidance and optional local Strands selection."""

import json
import base64
import binascii
from uuid import uuid4

from ..agents import guidance
from ..common.authz import principal_from_event, require

from ..common.errors import BadRequest
from ..common.http import api_handler
from ..common.params import http_method
from ..common.response import ok

MAX_MESSAGE_LEN = 1000
MAX_SESSION_LEN = 64


@api_handler
def handler(event, context, timer):
    if http_method(event) != "POST":
        raise BadRequest("This endpoint accepts POST only.")

    request = parse_request(event)
    path = _path(event)
    if path not in ('/ai/emergency', '/ai/aftermath'):
        raise BadRequest('Unknown assistant route.')
    mode = path.rsplit('/', 1)[-1]
    principal = principal_from_event(event)
    for resource in (('EmergencyProtocols',) if mode == 'emergency' else ('FAQs', 'AftermathSteps', 'Resources')):
        require(principal, 'read', resource)
    answer, source = getattr(guidance, mode)(request['message'], request['context'])
    answer['session_id'] = request['session_id'] or str(uuid4())
    return ok(answer, headers={'Cache-Control': 'no-store'}, meta={'source': source, 'agent': 'strands' if source == 'strands+reference' else None, 'took_ms': timer.ms})



def parse_request(event) -> dict:
    """Validate the POST body against the contract in docs/api-spec.md.

    Validate before retrieval or optional model inference.
    """
    raw = (event or {}).get("body")
    if (event or {}).get('isBase64Encoded') and isinstance(raw, str):
        try:
            raw = base64.b64decode(raw, validate=True).decode('utf-8')
        except (ValueError, UnicodeError, binascii.Error):
            raise BadRequest('Request body must be valid base64 JSON.')
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
