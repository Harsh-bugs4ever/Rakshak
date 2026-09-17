"""Content that never changes and must never depend on a database call.

Emergency numbers and Good Samaritan rights are served from memory. If DynamoDB
is down at 2am, the bystander still gets the number to dial.
"""

NATIONAL_NUMBERS = {
    "ambulance": "108",
    "police": "112",
    "fire": "101",
    "unified": "112",
    "women_helpline": "1091",
    "highway_patrol": "1033",
}

# States where the ambulance number differs from the national 108.
STATE_OVERRIDES = {
    "tamil nadu": {"ambulance": "108"},
    "kerala": {"ambulance": "108"},
    "west bengal": {"ambulance": "102"},
    "odisha": {"ambulance": "108"},
    "delhi": {"ambulance": "102"},
    "maharashtra": {"ambulance": "108"},
    "karnataka": {"ambulance": "108"},
}

NOTE = "112 works everywhere in India and connects to police, fire and ambulance."

GOOD_SAMARITAN = {
    "title": "You are protected when you help",
    "points": [
        "You cannot be forced to reveal your name or address.",
        "You cannot be detained or made to pay for the victim's treatment.",
        "Hospitals must start emergency treatment without waiting for police formalities.",
        "If you choose to be a witness, you can be examined only once, at a time and place you pick.",
        "No civil or criminal liability follows from helping in good faith.",
    ],
    "source": "Good Samaritan guidelines, Motor Vehicles Act s.134A",
    "disclaimer": "General information, not legal advice.",
}


def emergency_numbers(state=None) -> dict:
    """Numbers for a state, falling back to the national set.

    An unknown state is not an error - it returns the national numbers, because
    refusing to show 112 over a spelling mismatch would be indefensible.
    """
    numbers = dict(NATIONAL_NUMBERS)
    resolved_state = None
    if state:
        key = state.strip().lower()
        if key in STATE_OVERRIDES:
            numbers.update(STATE_OVERRIDES[key])
            resolved_state = state.strip()
    return {
        "state": resolved_state,
        "matched": resolved_state is not None,
        **numbers,
        "note": NOTE,
    }


def good_samaritan() -> dict:
    return dict(GOOD_SAMARITAN)
