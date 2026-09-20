"""Emergency reference formatting and optional local Strands construction."""
import os
from .prompts import EMERGENCY_DISCLAIMER, EMERGENCY_SYSTEM_PROMPT
from .tools import EMERGENCY_TOOLS

MODEL_ID = os.environ.get('OLLAMA_MODEL_ID', '')
TEMPERATURE = 0
MAX_STEPS = 4


def build_agent():
    """Construct a fresh local Strands selector."""
    from .model import build_selector
    return build_selector(EMERGENCY_TOOLS, EMERGENCY_SYSTEM_PROMPT)


def format_reply(protocol: dict, reply_text: str = "") -> dict:
    """Shape an agent answer into the /ai/emergency response contract.

    Implemented now because it is pure formatting, and because it is what
    guarantees the UI gets renderable step cards no matter what the model says:
    the steps come from the approved protocol, not from the generated prose.
    """
    steps = list(protocol.get("steps") or [])[:MAX_STEPS]
    actions = [{"type": "call", "label": "Call 112 now", "value": "tel:112"}]
    if protocol.get("scenario_id"):
        actions.append(
            {
                "type": "open_protocol",
                "label": f"Full steps: {protocol.get('title', 'protocol')}",
                "value": protocol["scenario_id"],
            }
        )

    return {
        "reply": reply_text.strip(),
        "steps": steps,
        "do_not": list(protocol.get("do_not") or []),
        "protocol_id": protocol.get("scenario_id"),
        "severity": protocol.get("severity"),
        "actions": actions,
        "disclaimer": EMERGENCY_DISCLAIMER,
    }


__all__ = [
    "MODEL_ID",
    "TEMPERATURE",
    "MAX_STEPS",
    "EMERGENCY_SYSTEM_PROMPT",
    "EMERGENCY_TOOLS",
    "build_agent",
    "format_reply",
]
