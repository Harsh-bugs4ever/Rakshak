"""Environment-driven configuration.

Values are read lazily (not at import time) so tests can set environment
variables in fixtures after the module has already been imported.
"""

import os

DEFAULT_REGION = "ap-south-1"

# Logical name -> environment variable that can override the physical table name.
TABLE_ENV_VARS = {
    "emergency_protocols": "TABLE_EMERGENCY_PROTOCOLS",
    "aftermath_steps": "TABLE_AFTERMATH_STEPS",
    "faqs": "TABLE_FAQS",
    "resources": "TABLE_RESOURCES",
}

DEFAULT_TABLE_NAMES = {
    "emergency_protocols": "EmergencyProtocols",
    "aftermath_steps": "AftermathSteps",
    "faqs": "FAQs",
    "resources": "Resources",
}


def region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_REGION


def dynamodb_endpoint():
    """LocalStack endpoint, or None to use the real AWS endpoint.

    Returns None for an empty string so that `AWS_ENDPOINT_URL=""` behaves the
    same as the variable being unset.
    """
    return os.environ.get("AWS_ENDPOINT_URL") or None


def table_name(logical: str) -> str:
    """Physical DynamoDB table name for a logical table key."""
    if logical not in DEFAULT_TABLE_NAMES:
        raise KeyError(f"Unknown logical table: {logical!r}")
    return os.environ.get(TABLE_ENV_VARS[logical], DEFAULT_TABLE_NAMES[logical])


def max_limit() -> int:
    """Upper bound on the `limit` query parameter."""
    try:
        return max(1, int(os.environ.get("MAX_PAGE_SIZE", "50")))
    except ValueError:
        return 50


def default_limit() -> int:
    try:
        return max(1, int(os.environ.get("DEFAULT_PAGE_SIZE", "20")))
    except ValueError:
        return 20
