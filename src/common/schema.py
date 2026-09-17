"""Seed-data validation.

Content is the product here: a missing `steps` array means a bystander sees an
empty card at a crash scene. The seeder validates every record before writing,
so bad content fails loudly at build time instead of silently at 2am.
"""

TABLE_SPECS = {
    "emergency_protocols": {
        "file": "emergency_protocols.json",
        "table": "EmergencyProtocols",
        "key": "scenario_id",
        "required": ("scenario_id", "title", "steps"),
        "lists": ("steps", "do_not", "tags"),
        "non_empty_lists": ("steps",),
        "enums": {"severity": ("critical", "high", "moderate")},
    },
    "aftermath_steps": {
        "file": "aftermath_steps.json",
        "table": "AftermathSteps",
        "key": "stage_id",
        "required": ("stage_id", "title", "checklist"),
        "lists": ("checklist", "details", "tags"),
        "non_empty_lists": ("checklist",),
        "enums": {"stage_id": ("hospital", "police", "insurance", "legal")},
    },
    "faqs": {
        "file": "faqs.json",
        "table": "FAQs",
        "key": "faq_id",
        "required": ("faq_id", "question", "answer", "topic"),
        "lists": ("tags",),
        "non_empty_lists": (),
        "enums": {
            "topic": (
                "good_samaritan",
                "hospital",
                "fir",
                "insurance",
                "legal_aid",
                "compensation",
            )
        },
    },
    "resources": {
        "file": "resources.json",
        "table": "Resources",
        "key": "resource_id",
        "required": ("resource_id", "name", "type", "state"),
        "lists": ("tags",),
        "non_empty_lists": (),
        "enums": {"type": ("hospital", "legal_aid", "ngo", "scheme")},
    },
}


def validate_records(logical: str, records) -> list:
    """Return a list of human-readable problems. Empty means the data is good."""
    spec = TABLE_SPECS[logical]
    problems = []

    if not isinstance(records, list):
        return [f"{spec['file']}: top level must be a JSON array."]
    if not records:
        return [f"{spec['file']}: contains no records."]

    seen = {}
    for index, record in enumerate(records):
        where = f"{spec['file']}[{index}]"

        if not isinstance(record, dict):
            problems.append(f"{where}: expected an object, got {type(record).__name__}.")
            continue

        for field in spec["required"]:
            value = record.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                problems.append(f"{where}: missing required field {field!r}.")

        key_value = record.get(spec["key"])
        if isinstance(key_value, str) and key_value:
            if key_value in seen:
                problems.append(
                    f"{where}: duplicate {spec['key']} {key_value!r} "
                    f"(first seen at index {seen[key_value]})."
                )
            else:
                seen[key_value] = index

        for field in spec["lists"]:
            if field in record and not isinstance(record[field], list):
                problems.append(f"{where}: field {field!r} must be a list.")

        for field in spec["non_empty_lists"]:
            value = record.get(field)
            if isinstance(value, list) and not value:
                problems.append(f"{where}: field {field!r} must not be empty.")

        for field, allowed in spec["enums"].items():
            value = record.get(field)
            if value is not None and str(value).lower() not in allowed:
                problems.append(
                    f"{where}: {field}={value!r} is not one of {', '.join(allowed)}."
                )

        problems.extend(_check_geo(record, where))

    return problems


def _check_geo(record, where) -> list:
    geo = record.get("geo")
    if geo is None:
        return []
    if not isinstance(geo, dict):
        return [f"{where}: 'geo' must be an object with lat and lon."]

    problems = []
    for axis, bound in (("lat", 90), ("lon", 180)):
        value = geo.get(axis)
        if value is None:
            problems.append(f"{where}: 'geo' is missing {axis!r}.")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            problems.append(f"{where}: geo.{axis} must be a number.")
            continue
        if not -bound <= value <= bound:
            problems.append(f"{where}: geo.{axis}={value} is outside +/-{bound}.")
    return problems
