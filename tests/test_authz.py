"""Cedar-style authorization: default deny, forbid beats permit."""

import pytest

from src.common.authz import (
    PUBLIC_CONTENT,
    Principal,
    is_authorized,
    principal_from_event,
    require,
)
from src.common.errors import Forbidden
from tests.conftest import make_event

ANON = Principal()
ADMIN = Principal(role="admin", user_id="u-1")


class TestPrincipalFromEvent:
    def test_no_headers_is_anonymous(self):
        assert principal_from_event(make_event()).role == "anonymous"

    def test_none_event_is_anonymous(self):
        assert principal_from_event(None).role == "anonymous"

    def test_null_headers_is_anonymous(self):
        assert principal_from_event({"headers": None}).role == "anonymous"

    def test_admin_header_is_honoured(self):
        event = make_event(headers={"X-User-Role": "admin", "X-User-Id": "u-1"})
        principal = principal_from_event(event)
        assert principal.is_admin and principal.user_id == "u-1"

    @pytest.mark.parametrize("header", ["x-user-role", "X-USER-ROLE", "X-User-Role", "x-User-role"])
    def test_header_lookup_is_case_insensitive(self, header):
        # v1 preserves client casing, v2 lower-cases, curl users do as they please.
        assert principal_from_event(make_event(headers={header: "admin"})).is_admin

    @pytest.mark.parametrize("value", ["ADMIN", " admin ", "Admin"])
    def test_role_value_is_normalised(self, value):
        assert principal_from_event(make_event(headers={"X-User-Role": value})).is_admin

    @pytest.mark.parametrize("value", ["superuser", "root", "", "   ", "admin'; --"])
    def test_unknown_role_degrades_to_anonymous(self, value):
        # Failing closed: an unrecognised role must never gain privileges.
        assert principal_from_event(make_event(headers={"X-User-Role": value})).role == "anonymous"

    def test_none_role_value(self):
        assert principal_from_event({"headers": {"X-User-Role": None}}).role == "anonymous"

    def test_missing_user_id_defaults(self):
        assert principal_from_event(make_event(headers={"X-User-Role": "admin"})).user_id == "anonymous"

    def test_none_header_key_is_skipped(self):
        assert principal_from_event({"headers": {None: "x"}}).role == "anonymous"


class TestReads:
    @pytest.mark.parametrize("resource", sorted(PUBLIC_CONTENT))
    @pytest.mark.parametrize("action", ["read", "search"])
    def test_anonymous_may_read_everything(self, action, resource):
        decision = is_authorized(ANON, action, resource)
        assert decision.allowed
        assert decision.reasons == ["permit_public_read"]

    def test_admin_may_also_read(self):
        assert is_authorized(ADMIN, "read", "FAQs").allowed

    def test_action_is_case_insensitive(self):
        assert is_authorized(ANON, "READ", "FAQs").allowed


class TestWrites:
    @pytest.mark.parametrize("action", ["write", "delete"])
    def test_admin_may_write(self, action):
        decision = is_authorized(ADMIN, action, "EmergencyProtocols")
        assert decision.allowed
        assert decision.reasons == ["permit_admin_write"]

    @pytest.mark.parametrize("action", ["write", "delete"])
    def test_anonymous_may_not_write(self, action):
        decision = is_authorized(ANON, action, "EmergencyProtocols")
        assert not decision.allowed
        assert decision.decision == "Deny"
        # A named reason, not an empty one: the forbid policy matched.
        assert decision.reasons == ["forbid_non_admin_writes"]


class TestDefaultDeny:
    def test_unknown_action_is_denied_with_no_reasons(self):
        decision = is_authorized(ADMIN, "detonate", "FAQs")
        assert not decision.allowed
        # Empty reasons means "no policy matched" - the correct default.
        assert decision.reasons == []

    def test_unknown_resource_is_denied_even_for_admin(self):
        assert not is_authorized(ADMIN, "read", "UserSecrets").allowed

    @pytest.mark.parametrize("action", [None, "", "   "])
    def test_empty_action_is_denied(self, action):
        assert not is_authorized(ANON, action, "FAQs").allowed

    def test_decision_serialises_for_the_error_body(self):
        assert is_authorized(ANON, "write", "FAQs").to_dict() == {
            "decision": "Deny",
            "reasons": ["forbid_non_admin_writes"],
        }


class TestRequire:
    def test_allows_silently(self):
        assert require(ANON, "read", "FAQs").allowed

    def test_raises_forbidden_with_cedar_details(self):
        with pytest.raises(Forbidden) as exc:
            require(ANON, "write", "FAQs")
        assert exc.value.status == 403
        assert exc.value.details["cedar"]["decision"] == "Deny"

    def test_write_denial_says_admins_only(self):
        with pytest.raises(Forbidden, match="Only admins"):
            require(ANON, "write", "FAQs")

    def test_non_write_denial_uses_the_generic_message(self):
        with pytest.raises(Forbidden, match="not allowed"):
            require(ANON, "read", "UnknownTable")
