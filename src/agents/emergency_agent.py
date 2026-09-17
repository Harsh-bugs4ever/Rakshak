"""EmergencyGuideAgent - Day 2.

The tools and the system prompt are ready; only the Strands wiring is missing.
`build_agent` raises rather than silently returning a mock, because a stub that
pretends to work would be discovered at a crash scene.

Day 2 implementation sketch:

    from strands import Agent
    from strands.models import BedrockModel

    def build_agent():
        return Agent(
            model=BedrockModel(model_id=MODEL_ID, temperature=0.2),
            system_prompt=EMERGENCY_SYSTEM_PROMPT,
            tools=EMERGENCY_TOOLS,
        )
"""

import os

from .prompts import EMERGENCY_DISCLAIMER, EMERGENCY_SYSTEM_PROMPT
from .tools import EMERGENCY_TOOLS

# Low temperature on purpose: this agent reads out an approved checklist. There
# is no upside to creative phrasing when someone is doing chest compressions.
MODEL_ID = os.environ.get("EMERGENCY_MODEL_ID", "claude-sonnet-5")
TEMPERATURE = 0.2
MAX_STEPS = 4


def build_agent():
    """Construct the Strands agent. Not implemented until Day 2."""
    raise NotImplementedError(
        "EmergencyGuideAgent is not wired up yet. "
        "POST /ai/emergency returns 501 until this lands."
    )


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
