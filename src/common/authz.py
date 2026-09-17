"""Cedar-style authorization, evaluated in-process.

The real Cedar policies live in `policies/rakshak.cedar`. This module mirrors
them with the same evaluation semantics so the Lambdas can enforce them without
a Cedar runtime in the hackathon build:

  * default is Deny - an unmatched request is denied, not allowed;
  * an explicit `forbid` beats any `permit`;
  * `reasons` lists the ids of the policies that produced the decision, so a
    denial with an empty `reasons` means "no policy matched".

Swapping this for the real engine later means replacing `is_authorized` only.
"""

from dataclasses import dataclass, field

# Every content table sits in one namespace: public to read, admin to change.
PUBLIC_CONTENT = {"EmergencyProtocols", "AftermathSteps", "FAQs", "Resources"}

READ_ACTIONS = {"read", "search"}
WRITE_ACTIONS = {"write", "delete"}
KNOWN_ACTIONS = READ_ACTIONS | WRITE_ACTIONS

VALID_ROLES = {"anonymous", "admin"}


@dataclass(frozen=True)
class Principal:
    role: str = "anonymous"
    user_id: str = "anonymous"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    decision: str
    reasons: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"decision": self.decision, "reasons": list(self.reasons)}


def principal_from_event(event) -> Principal:
    """Build the principal from request headers.

    Header lookup is case-insensitive: API Gateway v1 preserves the client's
    casing, v2 lower-cases everything, and curl users type whatever they like.
    An unrecognised role degrades to `anonymous` rather than erroring - failing
    closed is the safe direction for an authz default.
    """
    headers = (event or {}).get("headers") or {}
    lowered = {str(k).lower(): v for k, v in headers.items() if k is not None}

    raw_role = (lowered.get("x-user-role") or "").strip().lower()
    role = raw_role if raw_role in VALID_ROLES else "anonymous"

    user_id = (lowered.get("x-user-id") or "").strip() or "anonymous"
    return Principal(role=role, user_id=user_id)


def is_authorized(principal: Principal, action: str, resource: str) -> Decision:
    """Evaluate the policy set. Mirrors policies/rakshak.cedar."""
    action = (action or "").strip().lower()

    # Unknown action or resource: nothing can match, so Deny with no reasons.
    if action not in KNOWN_ACTIONS or resource not in PUBLIC_CONTENT:
        return Decision(False, "Deny", [])

    # forbid: a principal that is not an admin may never write. Listed first
    # because forbid overrides permit in Cedar regardless of ordering.
    if action in WRITE_ACTIONS and not principal.is_admin:
        return Decision(False, "Deny", ["forbid_non_admin_writes"])

    if action in READ_ACTIONS:
        return Decision(True, "Allow", ["permit_public_read"])

    if action in WRITE_ACTIONS and principal.is_admin:
        return Decision(True, "Allow", ["permit_admin_write"])

    return Decision(False, "Deny", [])


def require(principal: Principal, action: str, resource: str) -> Decision:
    """Authorize or raise Forbidden with the Cedar decision attached."""
    from .errors import Forbidden

    decision = is_authorized(principal, action, resource)
    if not decision.allowed:
        message = (
            "Only admins can edit safety content."
            if action in WRITE_ACTIONS
            else "You are not allowed to perform this action."
        )
        raise Forbidden(message, details={"cedar": decision.to_dict()})
    return decision
