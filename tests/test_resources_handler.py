"""GET /resources - hospitals, legal aid, NGOs and schemes."""

import pytest

from src.handlers.resources import handler
from tests.conftest import body_of, data_of, error_of, make_event

BENGALURU = {"lat": "12.9716", "lon": "77.5946"}


def call(**kwargs):
    return handler(make_event(path="/resources", **kwargs), None)


def ids(response):
    return [i["resource_id"] for i in data_of(response)["items"]]


class TestListing:
    def test_no_filters_returns_everything(self, dynamodb):
        assert data_of(call())["count"] == 10

    def test_null_query_string(self, dynamodb):
        assert call(query=None)["statusCode"] == 200

    def test_default_sort_is_alphabetical(self, dynamodb):
        names = [i["name"] for i in data_of(call())["items"]]
        assert names == sorted(names, key=str.lower)

    def test_total_reports_matches_before_the_limit(self, dynamodb):
        data = data_of(call(query={"limit": "2"}))
        assert data["count"] == 2
        assert data["total"] == 10

    def test_empty_table(self, empty_dynamodb):
        assert data_of(call())["count"] == 0


class TestTypeFilter:
    @pytest.mark.parametrize("type_", ["hospital", "legal_aid", "ngo", "scheme"])
    def test_each_type_returns_only_that_type(self, dynamodb, type_):
        items = data_of(call(query={"type": type_}))["items"]
        assert items and all(i["type"] == type_ for i in items)

    def test_type_is_case_insensitive(self, dynamodb):
        assert data_of(call(query={"type": "HOSPITAL"}))["count"] == 4

    def test_unknown_type_is_400(self, dynamodb):
        response = call(query={"type": "morgue"})
        assert response["statusCode"] == 400
        assert "hospital" in error_of(response)["message"]


class TestStateFilter:
    def test_state_filter_matches(self, dynamodb):
        assert "res_nimhans_trauma_blr" in ids(call(query={"state": "Karnataka"}))

    def test_state_filter_is_case_insensitive(self, dynamodb):
        assert ids(call(query={"state": "karnataka"})) == ids(call(query={"state": "Karnataka"}))

    def test_nationwide_entries_survive_a_state_filter(self, dynamodb):
        # NALSA and the Solatium scheme are valid answers in every state.
        assert "res_nalsa" in ids(call(query={"state": "Karnataka"}))

    def test_other_states_are_excluded(self, dynamodb):
        assert "res_aiims_trauma_del" not in ids(call(query={"state": "Karnataka"}))

    def test_unknown_state_still_returns_nationwide_entries(self, dynamodb):
        # Better to show NALSA than an empty screen to a family in Tripura.
        assert "res_nalsa" in ids(call(query={"state": "Tripura"}))


class TestCityFilter:
    def test_city_filter_matches(self, dynamodb):
        assert "res_kem_mum" in ids(call(query={"city": "Mumbai"}))

    def test_records_without_a_city_are_kept(self, dynamodb):
        # A state legal authority is not city-specific but is still relevant.
        assert "res_nalsa" in ids(call(query={"city": "Bengaluru"}))

    def test_city_and_state_combine(self, dynamodb):
        result = ids(call(query={"state": "Karnataka", "city": "Bengaluru"}))
        assert "res_nimhans_trauma_blr" in result
        assert "res_kem_mum" not in result


class TestTextSearch:
    def test_matches_a_tag(self, dynamodb):
        assert data_of(call(query={"q": "trauma"}))["count"] >= 3

    def test_matches_the_name(self, dynamodb):
        assert "res_nimhans_trauma_blr" in ids(call(query={"q": "NIMHANS"}))

    def test_matches_the_description(self, dynamodb):
        assert data_of(call(query={"q": "neurotrauma"}))["count"] == 1

    def test_all_words_must_match(self, dynamodb):
        # "24x7 trauma" must not match a record that is merely 24x7.
        both = data_of(call(query={"q": "trauma government"}))["count"]
        one = data_of(call(query={"q": "trauma"}))["count"]
        assert both < one

    def test_no_match_returns_empty(self, dynamodb):
        assert data_of(call(query={"q": "helicopter rescue"}))["count"] == 0

    def test_search_combines_with_type(self, dynamodb):
        items = data_of(call(query={"type": "legal_aid", "q": "free"}))["items"]
        assert all(i["type"] == "legal_aid" for i in items)


class TestDistanceSort:
    def test_nearest_first(self, dynamodb):
        result = ids(call(query={**BENGALURU, "type": "hospital"}))
        assert result[0] in ("res_victoria_blr", "res_nimhans_trauma_blr")
        assert result[-1] in ("res_aiims_trauma_del", "res_kem_mum")

    def test_distance_is_annotated(self, dynamodb):
        items = data_of(call(query={**BENGALURU, "type": "hospital"}))["items"]
        assert items[0]["distance_km"] < 10

    def test_distances_ascend(self, dynamodb):
        items = data_of(call(query={**BENGALURU, "type": "hospital"}))["items"]
        distances = [i["distance_km"] for i in items]
        assert distances == sorted(distances)

    def test_records_without_coordinates_go_last_not_missing(self, dynamodb):
        # An NGO with no lat/lon is still the right answer sometimes.
        items = data_of(call(query=BENGALURU))["items"]
        located = [i for i in items if i["distance_km"] is not None]
        unlocated = [i for i in items if i["distance_km"] is None]
        assert unlocated
        assert items[: len(located)] == located

    def test_no_distance_field_when_coords_absent(self, dynamodb):
        assert "distance_km" not in data_of(call())["items"][0]

    @pytest.mark.parametrize("partial", [{"lat": "12.97"}, {"lon": "77.59"}])
    def test_half_a_coordinate_is_400(self, dynamodb, partial):
        response = call(query=partial)
        assert response["statusCode"] == 400
        assert "lat" in error_of(response)["message"]

    @pytest.mark.parametrize(
        "bad", [{"lat": "91", "lon": "0"}, {"lat": "0", "lon": "181"}, {"lat": "x", "lon": "0"}]
    )
    def test_out_of_range_coordinates_are_400(self, dynamodb, bad):
        assert call(query=bad)["statusCode"] == 400

    def test_limit_applies_after_distance_sort(self, dynamodb):
        data = data_of(call(query={**BENGALURU, "type": "hospital", "limit": "1"}))
        assert data["count"] == 1
        assert data["total"] == 4
        assert data["items"][0]["resource_id"] in ("res_victoria_blr", "res_nimhans_trauma_blr")


class TestEnvelope:
    def test_decimal_coordinates_serialise(self, dynamodb):
        # DynamoDB stores lat/lon as Decimal; unhandled this is a 500.
        geo = data_of(call(query={"q": "NIMHANS"}))["items"][0]["geo"]
        assert geo["lat"] == pytest.approx(12.9433)

    def test_meta_source(self, dynamodb):
        assert body_of(call())["meta"]["source"] == "dynamodb"

    def test_preflight(self, no_tables):
        assert call(method="OPTIONS")["statusCode"] == 204

    def test_missing_table_is_502(self, no_tables):
        assert call()["statusCode"] == 502
