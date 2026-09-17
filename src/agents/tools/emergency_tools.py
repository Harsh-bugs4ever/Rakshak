"""Tools the EmergencyGuideAgent may call.

Thin, deterministic wrappers over the data layer. Keeping them free of any
reasoning means the agent can only surface content that an admin approved -
the model chooses *which* protocol to read out, never what it says.
"""

from ...common import static_content
from ...common.store import get_item, scan_all

KNOWN_SCENARIOS = (
    "not_breathing",
    "breathing_injured",
    "heavy_bleeding",
    "unconscious_breathing",
)


def get_emergency_protocol(scenario: str) -> dict:
    """Fetch the approved steps for one scenario.

    Returns a dict with `found: False` rather than raising, so a bad guess by
    the model becomes a retry prompt instead of a 500 at a crash scene.
    """
    key = str(scenario or "").strip().lower()
    if key not in KNOWN_SCENARIOS:
        return {
            "found": False,
            "scenario": key,
            "available": list(KNOWN_SCENARIOS),
        }

    item = get_item("emergency_protocols", {"scenario_id": key})
    if item is None:
        return {"found": False, "scenario": key, "available": list(KNOWN_SCENARIOS)}

    return {
        "found": True,
        "scenario_id": item.get("scenario_id"),
        "title": item.get("title"),
        "severity": item.get("severity"),
        "steps": list(item.get("steps") or []),
        "do_not": list(item.get("do_not") or []),
    }


def list_emergency_scenarios() -> list:
    """Titles of every scenario, so the agent can pick without guessing ids."""
    return [
        {"scenario_id": i.get("scenario_id"), "title": i.get("title")}
        for i in scan_all("emergency_protocols")
    ]


def get_state_emergency_numbers(state: str = None) -> dict:
    """Helpline numbers. Never touches the database - it must not be able to fail."""
    return static_content.emergency_numbers(state)


def get_good_samaritan_info() -> dict:
    """The bystander's legal protections, in plain language."""
    return static_content.good_samaritan()
