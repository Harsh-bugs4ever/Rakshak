"""Typed API errors.

Handlers raise these; the @api_handler decorator turns them into the standard
error envelope. Anything else that escapes becomes a generic 500 so that a bug
never leaks a stack trace to a bystander at a crash scene.
"""


class ApiError(Exception):
    """Base class for errors that map to a specific HTTP status and code."""

    status = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details=None, status=None, code=None):
        super().__init__(message)
        self.message = message
        self.details = details
        if status is not None:
            self.status = status
        if code is not None:
            self.code = code

    def to_error(self) -> dict:
        payload = {"code": self.code, "message": self.message}
        if self.details:
            payload.update(self.details)
        return payload


class BadRequest(ApiError):
    status = 400
    code = "BAD_REQUEST"


class Forbidden(ApiError):
    status = 403
    code = "FORBIDDEN"


class NotFound(ApiError):
    status = 404
    code = "NOT_FOUND"


class RateLimited(ApiError):
    status = 429
    code = "RATE_LIMITED"


class UpstreamError(ApiError):
    """DynamoDB / OpenSearch failed. 502: the failure is downstream of us."""

    status = 502
    code = "UPSTREAM_ERROR"
