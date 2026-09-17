"""The handler decorator: timing, CORS preflight, and error translation.

Every Lambda entry point wears @api_handler so that no handler has to remember
try/except, and so an unexpected exception becomes a well-formed envelope
instead of API Gateway's bare "Internal server error".
"""

import functools
import logging
import os

from .errors import ApiError
from .params import http_method
from .response import Timer, fail, no_content

logger = logging.getLogger("rakshak")
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def api_handler(func):
    @functools.wraps(func)
    def wrapper(event, context=None):
        timer = Timer()

        # Preflight never reaches business logic.
        if http_method(event) == "OPTIONS":
            return no_content()

        try:
            return func(event, context, timer)
        except ApiError as exc:
            # Expected failures: a 404 for an unknown scenario is not an
            # incident, so log at info and keep the message user-facing.
            logger.info("api_error code=%s message=%s", exc.code, exc.message)
            return fail(
                exc.code,
                exc.message,
                status=exc.status,
                details=exc.details,
                meta={"source": "api", "took_ms": timer.ms},
            )
        except Exception:
            # Unexpected: log the traceback for us, tell the caller nothing.
            logger.exception("unhandled_error path=%s", (event or {}).get("path"))
            return fail(
                "INTERNAL_ERROR",
                "Something went wrong. Emergency numbers still work: call 112.",
                status=500,
                meta={"source": "api", "took_ms": timer.ms},
            )

    return wrapper
