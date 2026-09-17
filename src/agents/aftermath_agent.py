"""AftermathGuideAgent - Day 2.

Same shape as the emergency agent: tools and prompt are ready, Strands wiring is
the remaining work.

Day 2 implementation sketch:

    from strands import Agent
    from strands.models import BedrockModel

    def build_agent():
        return Agent(
            model=BedrockModel(model_id=MODEL_ID, temperature=0.3),
            system_prompt=AFTERMATH_SYSTEM_PROMPT,
            tools=AFTERMATH_TOOLS,
        )
"""

import os

from .prompts import AFTERMATH_DISCLAIMER, AFTERMATH_SYSTEM_PROMPT
from .tools import AFTERMATH_TOOLS

MODEL_ID = os.environ.get("AFTERMATH_MODEL_ID", "claude-sonnet-5")
TEMPERATURE = 0.3
MAX_CITATIONS = 3


def build_agent():
    """Construct the Strands agent. Not implemented until Day 2."""
    raise NotImplementedError(
        "AftermathGuideAgent is not wired up yet. "
        "POST /ai/aftermath returns 501 until this lands."
    )


def format_reply(reply_text: str, faqs=None, stage=None, state=None) -> dict:
    """Shape an agent answer into the /ai/aftermath response contract.

    Citations are built from the retrieved records rather than parsed out of the
    model's prose, so a citation can never point at something that was not
    actually retrieved.
    """
    citations = [
        {"faq_id": f.get("faq_id"), "question": f.get("question")}
        for f in (faqs or [])[:MAX_CITATIONS]
        if f.get("faq_id")
    ]
    if stage and stage.get("found"):
        citations.append({"stage_id": stage.get("stage_id"), "title": stage.get("title")})

    suggested = []
    if stage and stage.get("stage_id"):
        suggested.append(
            {"type": "open_stage", "label": stage.get("title", "Checklist"),
             "value": stage["stage_id"]}
        )
    if state:
        suggested.append(
            {
                "type": "open_resources",
                "label": f"Legal aid in {state}",
                "value": f"type=legal_aid&state={state}",
            }
        )

    return {
        "reply": reply_text.strip(),
        "citations": citations,
        "suggested_next": suggested,
        "disclaimer": AFTERMATH_DISCLAIMER,
    }


__all__ = [
    "MODEL_ID",
    "TEMPERATURE",
    "MAX_CITATIONS",
    "AFTERMATH_SYSTEM_PROMPT",
    "AFTERMATH_TOOLS",
    "build_agent",
    "format_reply",
]
