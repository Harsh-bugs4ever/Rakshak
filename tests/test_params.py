"""Query parameter parsing - where malformed client input gets stopped."""

import pytest

from src.common import params
from src.common.errors import BadRequest
from tests.conftest import make_event


class TestQueryParams:
    def test_none_query_string_becomes_empty_dict(self):
        # API Gateway sends null, not {}, when there is no query string.
        assert params.query_params(make_event(query=None)) == {}

    def test_missing_key_entirely(self):
        assert params.query_params({}) == {}

    def test_none_event(self):
        assert params.query_params(None) == {}

    def test_non_dict_query_string_is_ignored(self):
        assert params.query_params({"queryStringParameters": "scenario=x"}) == {}

    def test_none_keys_are_dropped(self):
        assert params.query_params({"queryStringParameters": {None: "x", "a": "1"}}) == {"a": "1"}


class TestGetStr:
    def test_returns_trimmed_value(self):
        assert params.get_str({"state": "  Karnataka  "}, "state") == "Karnataka"

    def test_absent_returns_default(self):
        assert params.get_str({}, "state", default="All India") == "All India"

    def test_blank_is_treated_as_absent(self):
        # `?state=` is a UI rendering an empty select, not a filter for "".
        assert params.get_str({"state": "   "}, "state") is None

    def test_none_value_is_absent(self):
        assert params.get_str({"state": None}, "state") is None

    def test_lower_flag_normalises(self):
        assert params.get_str({"t": "HOSPITAL"}, "t", lower=True) == "hospital"

    def test_non_string_is_coerced(self):
        assert params.get_str({"n": 5}, "n") == "5"

    def test_over_long_value_is_rejected(self):
        with pytest.raises(BadRequest, match="too long"):
            params.get_str({"q": "x" * 501}, "q")

    def test_exactly_at_limit_is_accepted(self):
        assert params.get_str({"q": "x" * 500}, "q") == "x" * 500


class TestGetSlug:
    @pytest.mark.parametrize("value", ["not_breathing", "res-kem-mum", "a", "faq_fir_delay", "a1"])
    def test_accepts_valid_slugs(self, value):
        assert params.get_slug({"id": value}, "id") == value

    def test_normalises_case_and_whitespace(self):
        assert params.get_slug({"id": "  NOT_BREATHING "}, "id") == "not_breathing"

    @pytest.mark.parametrize(
        "value",
        [
            "not breathing",        # space
            "not/breathing",        # path traversal attempt
            "../../etc/passwd",
            "drop table",
            "_leading",             # must start alphanumeric
            "-leading",
            "scenario;",
            "scen@rio",
            "x" * 65,               # too long
        ],
    )
    def test_rejects_malformed_slugs(self, value):
        with pytest.raises(BadRequest):
            params.get_slug({"id": value}, "id")

    def test_absent_returns_default(self):
        assert params.get_slug({}, "id", default="fallback") == "fallback"


class TestGetEnum:
    def test_accepts_known_value(self):
        assert params.get_enum({"stage": "hospital"}, "stage", ("hospital", "police")) == "hospital"

    def test_is_case_insensitive(self):
        assert params.get_enum({"stage": "HOSPITAL"}, "stage", ("hospital",)) == "hospital"

    def test_unknown_value_lists_the_options(self):
        with pytest.raises(BadRequest) as exc:
            params.get_enum({"stage": "morgue"}, "stage", ("hospital", "police"))
        assert "hospital" in str(exc.value) and "police" in str(exc.value)

    def test_absent_returns_default(self):
        assert params.get_enum({}, "stage", ("hospital",)) is None


class TestGetLimit:
    def test_default_when_absent(self):
        assert params.get_limit({}) == 20

    def test_explicit_default(self):
        assert params.get_limit({}, default=10) == 10

    def test_parses_a_number(self):
        assert params.get_limit({"limit": "5"}) == 5

    def test_tolerates_whitespace(self):
        assert params.get_limit({"limit": " 5 "}) == 5

    def test_blank_falls_back_to_default(self):
        assert params.get_limit({"limit": ""}) == 20

    def test_clamps_to_maximum_rather_than_erroring(self):
        # Asking for more than we hold is not a client bug worth a 400.
        assert params.get_limit({"limit": "9999"}) == 50

    @pytest.mark.parametrize("value", ["0", "-1", "-999"])
    def test_rejects_non_positive(self, value):
        with pytest.raises(BadRequest, match="at least 1"):
            params.get_limit({"limit": value})

    @pytest.mark.parametrize("value", ["abc", "1.5", "1e3", "null", "NaN"])
    def test_rejects_non_integers(self, value):
        with pytest.raises(BadRequest, match="whole number"):
            params.get_limit({"limit": value})

    def test_respects_env_maximum(self, monkeypatch):
        monkeypatch.setenv("MAX_PAGE_SIZE", "3")
        assert params.get_limit({"limit": "100"}) == 3

    def test_garbage_env_maximum_falls_back_to_50(self, monkeypatch):
        monkeypatch.setenv("MAX_PAGE_SIZE", "banana")
        assert params.get_limit({"limit": "100"}) == 50


class TestGetFloat:
    def test_parses(self):
        assert params.get_float({"lat": "12.97"}, "lat") == pytest.approx(12.97)

    def test_parses_negative(self):
        assert params.get_float({"lon": "-77.59"}, "lon") == pytest.approx(-77.59)

    def test_absent_returns_default(self):
        assert params.get_float({}, "lat", default=0.0) == 0.0

    def test_rejects_text(self):
        with pytest.raises(BadRequest, match="must be a number"):
            params.get_float({"lat": "north"}, "lat")

    def test_rejects_nan(self):
        # NaN fails every comparison, so a naive range check lets it through.
        with pytest.raises(BadRequest, match="must be a number"):
            params.get_float({"lat": "nan"}, "lat", minimum=-90, maximum=90)

    def test_rejects_infinity_via_range(self):
        with pytest.raises(BadRequest):
            params.get_float({"lat": "inf"}, "lat", minimum=-90, maximum=90)

    def test_enforces_minimum(self):
        with pytest.raises(BadRequest, match="at least"):
            params.get_float({"lat": "-91"}, "lat", minimum=-90, maximum=90)

    def test_enforces_maximum(self):
        with pytest.raises(BadRequest, match="at most"):
            params.get_float({"lat": "91"}, "lat", minimum=-90, maximum=90)

    def test_accepts_exact_bounds(self):
        assert params.get_float({"lat": "90"}, "lat", minimum=-90, maximum=90) == 90


class TestGetCoords:
    def test_both_present(self):
        assert params.get_coords({"lat": "12.97", "lon": "77.59"}) == pytest.approx((12.97, 77.59))

    def test_neither_present_returns_none(self):
        assert params.get_coords({}) is None

    @pytest.mark.parametrize("partial", [{"lat": "12.97"}, {"lon": "77.59"}])
    def test_one_without_the_other_is_an_error(self, partial):
        # Silently ignoring it would show an unsorted list that looks sorted.
        with pytest.raises(BadRequest, match="Both 'lat' and 'lon'"):
            params.get_coords(partial)

    def test_zero_zero_is_valid_not_falsy(self):
        assert params.get_coords({"lat": "0", "lon": "0"}) == (0.0, 0.0)


class TestHttpMethod:
    def test_v1_payload(self):
        assert params.http_method({"httpMethod": "post"}) == "POST"

    def test_v2_payload(self):
        assert params.http_method({"requestContext": {"http": {"method": "get"}}}) == "GET"

    def test_defaults_to_get(self):
        assert params.http_method({}) == "GET"

    def test_none_event(self):
        assert params.http_method(None) == "GET"

    def test_v2_wins_when_both_present(self):
        event = {"httpMethod": "GET", "requestContext": {"http": {"method": "OPTIONS"}}}
        assert params.http_method(event) == "OPTIONS"
