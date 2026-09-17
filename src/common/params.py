"""Query-string parsing and validation.

API Gateway hands `queryStringParameters: null` when there are no parameters,
and individual values can be None. Every accessor here tolerates both rather
than making each handler remember to.
"""

import re

from . import config
from .errors import BadRequest

# Identifiers are our own slugs (`not_breathing`, `res_kem_mum`). Constraining
# them up front keeps malformed input out of the data layer entirely.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

MAX_QUERY_LEN = 200
MAX_TEXT_LEN = 500


def query_params(event) -> dict:
    raw = (event or {}).get("queryStringParameters") or {}
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k is not None}


def path_params(event) -> dict:
    raw = (event or {}).get("pathParameters") or {}
    return raw if isinstance(raw, dict) else {}


def get_str(params: dict, name: str, *, default=None, max_len=MAX_TEXT_LEN, lower=False):
    """Trimmed string, or `default` when absent or blank.

    An empty value (`?stage=`) is treated as absent, not as an empty-string
    filter - it is nearly always a UI that rendered a blank select.
    """
    value = params.get(name)
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return default
    if len(value) > max_len:
        raise BadRequest(f"Parameter {name!r} is too long (max {max_len} characters).")
    return value.lower() if lower else value


def get_slug(params: dict, name: str, *, default=None):
    """A validated identifier, normalised to lowercase."""
    value = get_str(params, name, default=None, max_len=64, lower=True)
    if value is None:
        return default
    if not SLUG_RE.match(value):
        raise BadRequest(
            f"Parameter {name!r} must contain only letters, numbers, hyphens and underscores."
        )
    return value


def get_enum(params: dict, name: str, allowed, *, default=None):
    """A value constrained to a known set, with the options listed on failure."""
    value = get_str(params, name, default=None, lower=True)
    if value is None:
        return default
    if value not in allowed:
        raise BadRequest(
            f"Unknown {name} {value!r}. Valid values: {', '.join(sorted(allowed))}."
        )
    return value


def get_limit(params: dict, *, default=None, maximum=None):
    """Parse `limit`, clamped to the configured maximum.

    Over-large values clamp rather than erroring - a client asking for more than
    we hold is not a mistake worth failing a request over. Non-numeric and
    non-positive values are a genuine client bug, so those do raise.
    """
    default = config.default_limit() if default is None else default
    maximum = config.max_limit() if maximum is None else maximum

    raw = params.get("limit")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise BadRequest("Parameter 'limit' must be a whole number.")
    if value < 1:
        raise BadRequest("Parameter 'limit' must be at least 1.")
    return min(value, maximum)


def get_float(params: dict, name: str, *, minimum=None, maximum=None, default=None):
    raw = params.get(name)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        raise BadRequest(f"Parameter {name!r} must be a number.")
    # NaN fails every comparison, so it slips past a naive range check.
    if value != value:
        raise BadRequest(f"Parameter {name!r} must be a number.")
    if minimum is not None and value < minimum:
        raise BadRequest(f"Parameter {name!r} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise BadRequest(f"Parameter {name!r} must be at most {maximum}.")
    return value


def get_coords(params: dict):
    """(lat, lon) when both are present and valid, else None.

    One coordinate without the other is a client bug worth surfacing - silently
    ignoring it would show an unsorted list that looks sorted by distance.
    """
    lat = get_float(params, "lat", minimum=-90, maximum=90)
    lon = get_float(params, "lon", minimum=-180, maximum=180)
    if lat is None and lon is None:
        return None
    if lat is None or lon is None:
        raise BadRequest("Both 'lat' and 'lon' are required to sort by distance.")
    return lat, lon


def get_query_text(params: dict, name: str = "q"):
    return get_str(params, name, max_len=MAX_QUERY_LEN)


def http_method(event) -> str:
    """Method for both API Gateway payload v1 and v2."""
    event = event or {}
    v2 = ((event.get("requestContext") or {}).get("http") or {}).get("method")
    return str(v2 or event.get("httpMethod") or "GET").upper()
