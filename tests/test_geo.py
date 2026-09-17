"""Distance maths for the trauma-centre finder."""

from decimal import Decimal

import pytest

from src.common.geo import extract_point, haversine_km

# Real coordinates from data/resources.json.
NIMHANS = (12.9433, 77.5964)
VICTORIA = (12.9622, 77.5731)
AIIMS_TRAUMA = (28.5672, 77.2100)


class TestHaversine:
    def test_zero_distance_to_itself(self):
        assert haversine_km(*NIMHANS, *NIMHANS) == 0.0

    def test_two_bengaluru_hospitals_are_a_few_km_apart(self):
        assert 2.0 < haversine_km(*NIMHANS, *VICTORIA) < 4.5

    def test_bengaluru_to_delhi_is_roughly_1740km(self):
        assert haversine_km(*NIMHANS, *AIIMS_TRAUMA) == pytest.approx(1740, abs=40)

    def test_is_symmetric(self):
        assert haversine_km(*NIMHANS, *AIIMS_TRAUMA) == haversine_km(*AIIMS_TRAUMA, *NIMHANS)

    def test_accepts_decimals_from_dynamodb(self):
        assert haversine_km(Decimal("12.9433"), Decimal("77.5964"), *VICTORIA) > 0

    def test_accepts_strings(self):
        assert haversine_km("12.9433", "77.5964", *VICTORIA) > 0

    def test_antipodal_points_do_not_raise(self):
        # Floating point can push the haversine term just above 1; unclamped,
        # sqrt of the negative remainder would raise a ValueError.
        assert haversine_km(0, 0, 0, 180) == pytest.approx(20015, abs=50)

    def test_poles(self):
        assert haversine_km(90, 0, -90, 0) == pytest.approx(20015, abs=50)

    def test_crossing_the_antimeridian_is_short(self):
        assert haversine_km(0, 179.5, 0, -179.5) == pytest.approx(111, abs=5)

    def test_result_is_rounded_to_two_places(self):
        value = haversine_km(*NIMHANS, *VICTORIA)
        assert value == round(value, 2)


class TestExtractPoint:
    def test_reads_a_valid_geo_block(self):
        assert extract_point({"geo": {"lat": 12.9, "lon": 77.5}}) == (12.9, 77.5)

    def test_converts_decimals(self):
        point = extract_point({"geo": {"lat": Decimal("12.9"), "lon": Decimal("77.5")}})
        assert point == pytest.approx((12.9, 77.5))

    def test_zero_coordinates_are_valid(self):
        # Null Island is a real point; `if not lat` would wrongly reject it.
        assert extract_point({"geo": {"lat": 0, "lon": 0}}) == (0.0, 0.0)

    @pytest.mark.parametrize(
        "item",
        [
            {},                                      # no geo at all (NGOs, schemes)
            {"geo": None},
            {"geo": "12.9,77.5"},                    # wrong type
            {"geo": {}},
            {"geo": {"lat": 12.9}},                  # half a point
            {"geo": {"lon": 77.5}},
            {"geo": {"lat": None, "lon": 77.5}},
            {"geo": {"lat": "north", "lon": "east"}},
            {"geo": {"lat": 91, "lon": 0}},          # out of range
            {"geo": {"lat": -91, "lon": 0}},
            {"geo": {"lat": 0, "lon": 181}},
            {"geo": {"lat": float("nan"), "lon": 0}},
        ],
    )
    def test_unusable_geo_returns_none_rather_than_raising(self, item):
        # A legal aid office with no coordinates is still a valid answer.
        assert extract_point(item) is None
