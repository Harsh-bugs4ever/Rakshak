"""Tools the agents may call. Retrieval only - no reasoning lives here."""

from .aftermath_tools import (
    get_aftermath_steps,
    search_faqs,
    search_resources,
)
from .emergency_tools import (
    get_emergency_protocol,
    get_good_samaritan_info,
    get_state_emergency_numbers,
    list_emergency_scenarios,
)

EMERGENCY_TOOLS = [
    get_emergency_protocol,
    list_emergency_scenarios,
    get_state_emergency_numbers,
    get_good_samaritan_info,
]

AFTERMATH_TOOLS = [
    get_aftermath_steps,
    search_faqs,
    search_resources,
]

__all__ = [
    "EMERGENCY_TOOLS",
    "AFTERMATH_TOOLS",
    "get_emergency_protocol",
    "list_emergency_scenarios",
    "get_state_emergency_numbers",
    "get_good_samaritan_info",
    "get_aftermath_steps",
    "search_faqs",
    "search_resources",
]
