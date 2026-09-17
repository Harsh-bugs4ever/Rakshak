"""Content tests.

The content *is* the product. A protocol with an empty `steps` array is an empty
card at a crash scene, and a missing 112 is worse than a crashed app. These tests
guard the data files themselves, not the code that reads them.
"""

import json
from pathlib import Path

import pytest

from src.common.schema import TABLE_SPECS, validate_records

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load(logical):
    with (DATA_DIR / TABLE_SPECS[logical]["file"]).open(encoding="utf-8") as fh:
        return json.load(fh)


class TestFilesAreValid:
    @pytest.mark.parametrize("logical", sorted(TABLE_SPECS))
    def test_file_exists(self, logical):
        assert (DATA_DIR / TABLE_SPECS[logical]["file"]).exists()

    @pytest.mark.parametrize("logical", sorted(TABLE_SPECS))
    def test_passes_schema_validation(self, logical):
        assert validate_records(logical, load(logical)) == []

    @pytest.mark.parametrize("logical", sorted(TABLE_SPECS))
    def test_no_duplicate_ids(self, logical):
        key = TABLE_SPECS[logical]["key"]
        ids = [r[key] for r in load(logical)]
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("logical", sorted(TABLE_SPECS))
    def test_ids_are_lowercase_slugs(self, logical):
        # The API lowercases inbound ids; uppercase seed ids would be unreachable.
        key = TABLE_SPECS[logical]["key"]
        assert all(r[key] == r[key].lower() for r in load(logical))


class TestEmergencyContent:
    def test_all_four_scenarios_present(self):
        ids = {r["scenario_id"] for r in load("emergency_protocols")}
        assert ids == {
            "not_breathing", "breathing_injured", "heavy_bleeding", "unconscious_breathing",
        }

    def test_every_protocol_tells_the_user_to_call_for_help(self):
        # The single non-negotiable instruction.
        for record in load("emergency_protocols"):
            text = " ".join(record["steps"])
            assert "112" in text or "108" in text, record["scenario_id"]

    def test_every_protocol_has_at_least_three_steps(self):
        assert all(len(r["steps"]) >= 3 for r in load("emergency_protocols"))

    def test_no_protocol_has_more_than_five_steps(self):
        # More than five steps is unreadable to someone in a panic.
        assert all(len(r["steps"]) <= 5 for r in load("emergency_protocols"))

    def test_every_protocol_has_do_nots(self):
        assert all(r.get("do_not") for r in load("emergency_protocols"))

    def test_steps_are_short_enough_to_read_at_a_glance(self):
        for record in load("emergency_protocols"):
            for step in record["steps"]:
                assert len(step) <= 140, f"{record['scenario_id']}: {step}"

    def test_not_breathing_covers_cpr(self):
        record = next(r for r in load("emergency_protocols") if r["scenario_id"] == "not_breathing")
        assert "chest" in " ".join(record["steps"]).lower()

    def test_breathing_injured_warns_against_moving_the_victim(self):
        record = next(
            r for r in load("emergency_protocols") if r["scenario_id"] == "breathing_injured"
        )
        assert any("move" in d.lower() for d in record["do_not"])


class TestAftermathContent:
    def test_all_four_stages_present_and_ordered(self):
        records = sorted(load("aftermath_steps"), key=lambda r: r["order"])
        assert [r["stage_id"] for r in records] == [
            "hospital", "police", "insurance", "legal",
        ]

    def test_orders_are_unique(self):
        orders = [r["order"] for r in load("aftermath_steps")]
        assert len(orders) == len(set(orders))

    def test_every_stage_has_a_checklist_and_details(self):
        for record in load("aftermath_steps"):
            assert len(record["checklist"]) >= 3, record["stage_id"]
            assert record["details"], record["stage_id"]

    def test_hospital_stage_covers_mlc(self):
        record = next(r for r in load("aftermath_steps") if r["stage_id"] == "hospital")
        assert "MLC" in " ".join(record["checklist"])

    def test_police_stage_covers_the_fir_copy(self):
        record = next(r for r in load("aftermath_steps") if r["stage_id"] == "police")
        assert "FIR" in " ".join(record["checklist"])

    def test_legal_stage_covers_mact_and_free_aid(self):
        record = next(r for r in load("aftermath_steps") if r["stage_id"] == "legal")
        text = " ".join(record["checklist"] + record["details"])
        assert "MACT" in text and "free legal aid" in text.lower()


class TestFaqContent:
    def test_at_least_fifteen_faqs(self):
        assert len(load("faqs")) >= 15

    def test_every_topic_has_coverage(self):
        topics = {r["topic"] for r in load("faqs")}
        assert topics == set(TABLE_SPECS["faqs"]["enums"]["topic"])

    def test_questions_end_with_a_question_mark(self):
        assert all(r["question"].rstrip().endswith("?") for r in load("faqs"))

    def test_answers_are_substantial_but_not_essays(self):
        for record in load("faqs"):
            assert 40 <= len(record["answer"]) <= 400, record["faq_id"]

    def test_good_samaritan_answer_covers_anonymity(self):
        record = next(r for r in load("faqs") if r["faq_id"] == "faq_gs_identity")
        assert "identity" in record["answer"].lower()


class TestResourceContent:
    def test_every_type_is_represented(self):
        types = {r["type"] for r in load("resources")}
        assert types == set(TABLE_SPECS["resources"]["enums"]["type"])

    def test_hospitals_all_have_coordinates(self):
        # Without geo they cannot be sorted by distance, which is their whole job.
        hospitals = [r for r in load("resources") if r["type"] == "hospital"]
        assert hospitals and all(r.get("geo") for r in hospitals)

    def test_hospital_coordinates_are_inside_india(self):
        for record in load("resources"):
            geo = record.get("geo")
            if not geo:
                continue
            assert 6 <= geo["lat"] <= 37, record["resource_id"]
            assert 68 <= geo["lon"] <= 98, record["resource_id"]

    def test_every_resource_has_a_contact_block(self):
        assert all(isinstance(r.get("contact"), dict) for r in load("resources"))

    def test_nationwide_entries_exist(self):
        # These are the fallback when a user's state has no local entry.
        assert any(r["state"] == "All India" for r in load("resources"))

    def test_hospitals_carry_an_emergency_number(self):
        for record in load("resources"):
            if record["type"] != "hospital":
                continue
            contact = record["contact"]
            assert contact.get("phone") or contact.get("alt_phone"), record["resource_id"]


class TestValidatorCatchesBadData:
    """The validator is only worth having if it actually fails on bad input."""

    GOOD = {
        "scenario_id": "test_case",
        "title": "Test",
        "steps": ["Call 112."],
        "do_not": [],
        "tags": [],
        "severity": "critical",
    }

    def test_accepts_a_good_record(self):
        assert validate_records("emergency_protocols", [self.GOOD]) == []

    def test_rejects_a_non_list_top_level(self):
        assert validate_records("emergency_protocols", {"a": 1})

    def test_rejects_an_empty_file(self):
        assert validate_records("emergency_protocols", [])

    def test_rejects_a_non_object_record(self):
        assert validate_records("emergency_protocols", ["just a string"])

    def test_rejects_a_missing_required_field(self):
        problems = validate_records("emergency_protocols", [{**self.GOOD, "title": None}])
        assert any("title" in p for p in problems)

    def test_rejects_a_blank_required_field(self):
        problems = validate_records("emergency_protocols", [{**self.GOOD, "title": "   "}])
        assert any("title" in p for p in problems)

    def test_rejects_empty_steps(self):
        problems = validate_records("emergency_protocols", [{**self.GOOD, "steps": []}])
        assert any("must not be empty" in p for p in problems)

    def test_rejects_steps_that_are_not_a_list(self):
        problems = validate_records("emergency_protocols", [{**self.GOOD, "steps": "Call 112"}])
        assert any("must be a list" in p for p in problems)

    def test_rejects_duplicate_ids_and_names_both_positions(self):
        problems = validate_records("emergency_protocols", [self.GOOD, dict(self.GOOD)])
        assert any("duplicate" in p and "index 0" in p for p in problems)

    def test_rejects_an_unknown_enum_value(self):
        problems = validate_records("emergency_protocols", [{**self.GOOD, "severity": "spicy"}])
        assert any("severity" in p for p in problems)

    def test_rejects_out_of_range_coordinates(self):
        record = {
            "resource_id": "r", "name": "N", "type": "ngo", "state": "Delhi",
            "geo": {"lat": 200, "lon": 0},
        }
        assert any("outside" in p for p in validate_records("resources", [record]))

    def test_rejects_half_a_geo_block(self):
        record = {
            "resource_id": "r", "name": "N", "type": "ngo", "state": "Delhi",
            "geo": {"lat": 12.9},
        }
        assert any("missing 'lon'" in p for p in validate_records("resources", [record]))

    def test_rejects_geo_that_is_not_an_object(self):
        record = {
            "resource_id": "r", "name": "N", "type": "ngo", "state": "Delhi",
            "geo": "12.9,77.5",
        }
        assert any("must be an object" in p for p in validate_records("resources", [record]))

    def test_accepts_a_record_with_no_geo_at_all(self):
        # NGOs and nationwide schemes have no single location.
        record = {"resource_id": "r", "name": "N", "type": "ngo", "state": "All India"}
        assert validate_records("resources", [record]) == []

    def test_rejects_a_boolean_masquerading_as_a_coordinate(self):
        # bool is a subclass of int in Python, so a naive isinstance check passes.
        record = {
            "resource_id": "r", "name": "N", "type": "ngo", "state": "Delhi",
            "geo": {"lat": True, "lon": 0},
        }
        assert any("must be a number" in p for p in validate_records("resources", [record]))

    def test_problem_messages_name_the_file_and_index(self):
        problems = validate_records("emergency_protocols", [{**self.GOOD, "title": None}])
        assert "emergency_protocols.json[0]" in problems[0]
