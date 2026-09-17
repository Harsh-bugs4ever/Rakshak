"""GET /aftermath/* - stage checklists and FAQ search."""

import pytest

from src.handlers.aftermath import handler, rank, score, tokenize
from tests.conftest import body_of, data_of, error_of, make_event

STEPS = "/aftermath/steps"
FAQS = "/aftermath/faqs"


def call(path=STEPS, **kwargs):
    return handler(make_event(path=path, **kwargs), None)


class TestStages:
    @pytest.mark.parametrize("stage", ["hospital", "police", "insurance", "legal"])
    def test_each_stage_is_reachable(self, dynamodb, stage):
        data = data_of(call(query={"stage": stage}))
        assert data["stage_id"] == stage
        assert data["checklist"]

    def test_hospital_stage_mentions_mlc(self, dynamodb):
        # The single most important thing a family must do - guard it with a test.
        text = " ".join(data_of(call(query={"stage": "hospital"}))["checklist"]).lower()
        assert "mlc" in text

    def test_police_stage_mentions_fir_copy(self, dynamodb):
        text = " ".join(data_of(call(query={"stage": "police"}))["checklist"]).lower()
        assert "fir" in text

    def test_list_returns_all_four_in_order(self, dynamodb):
        data = data_of(call())
        assert data["count"] == 4
        assert [i["stage_id"] for i in data["items"]] == [
            "hospital", "police", "insurance", "legal",
        ]

    def test_stage_is_case_insensitive(self, dynamodb):
        assert data_of(call(query={"stage": "HOSPITAL"}))["stage_id"] == "hospital"

    def test_unknown_stage_is_400_with_the_valid_options(self, dynamodb):
        response = call(query={"stage": "morgue"})
        assert response["statusCode"] == 400
        assert "hospital" in error_of(response)["message"]

    def test_empty_table_returns_empty_list(self, empty_dynamodb):
        assert data_of(call())["count"] == 0

    def test_null_query_string(self, dynamodb):
        assert call(query=None)["statusCode"] == 200


class TestFaqTopicFilter:
    def test_topic_uses_the_gsi(self, dynamodb):
        body = body_of(call(path=FAQS, query={"topic": "fir"}))
        assert body["meta"]["index"] == "topic-index"
        assert all(i["topic"] == "fir" for i in body["data"]["items"])

    def test_topic_returns_something(self, dynamodb):
        assert data_of(call(path=FAQS, query={"topic": "insurance"}))["count"] >= 2

    def test_unknown_topic_is_400(self, dynamodb):
        assert call(path=FAQS, query={"topic": "aliens"})["statusCode"] == 400

    def test_no_filters_lists_faqs_up_to_the_default_limit(self, dynamodb):
        data = data_of(call(path=FAQS))
        assert data["count"] == 10  # default limit for FAQs
        assert data["query"] is None

    def test_limit_is_respected(self, dynamodb):
        assert data_of(call(path=FAQS, query={"limit": "3"}))["count"] == 3

    def test_limit_clamps_rather_than_erroring(self, dynamodb):
        assert data_of(call(path=FAQS, query={"limit": "9999"}))["count"] <= 50

    def test_invalid_limit_is_400(self, dynamodb):
        assert call(path=FAQS, query={"limit": "many"})["statusCode"] == 400


class TestFaqSearch:
    def test_finds_the_fir_delay_answer(self, dynamodb):
        items = data_of(call(path=FAQS, query={"q": "police refusing fir"}))["items"]
        assert items[0]["faq_id"] == "faq_fir_delay"

    def test_results_carry_a_score(self, dynamodb):
        items = data_of(call(path=FAQS, query={"q": "fir"}))["items"]
        assert all(i["score"] > 0 for i in items)

    def test_results_are_sorted_by_descending_score(self, dynamodb):
        scores = [i["score"] for i in data_of(call(path=FAQS, query={"q": "insurance claim"}))["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_reports_its_engine(self, dynamodb):
        # Day 2 swaps this to "opensearch"; the field is how the UI can tell.
        assert body_of(call(path=FAQS, query={"q": "fir"}))["meta"]["source"] == "scan+score"

    def test_hospital_money_question_finds_the_refusal_answer(self, dynamodb):
        items = data_of(call(path=FAQS, query={"q": "hospital deposit money treatment"}))["items"]
        assert items[0]["faq_id"] == "faq_hospital_refuse"

    def test_free_legal_aid_query(self, dynamodb):
        items = data_of(call(path=FAQS, query={"q": "free legal aid"}))["items"]
        assert items[0]["topic"] == "legal_aid"

    def test_nonsense_query_returns_empty_not_everything(self, dynamodb):
        # Returning the whole corpus for a typo would look like a broken search.
        assert data_of(call(path=FAQS, query={"q": "zzzzqqqq"}))["count"] == 0

    def test_stopword_only_query_returns_nothing(self, dynamodb):
        assert data_of(call(path=FAQS, query={"q": "what is the of and"}))["count"] == 0

    def test_topic_and_text_combine(self, dynamodb):
        items = data_of(call(path=FAQS, query={"topic": "fir", "q": "insurance"}))["items"]
        assert all(i["topic"] == "fir" for i in items)

    def test_search_limit_is_respected(self, dynamodb):
        assert data_of(call(path=FAQS, query={"q": "accident", "limit": "2"}))["count"] <= 2

    def test_query_is_echoed_back(self, dynamodb):
        assert data_of(call(path=FAQS, query={"q": "fir"}))["query"] == "fir"

    def test_punctuation_does_not_break_search(self, dynamodb):
        assert data_of(call(path=FAQS, query={"q": "F.I.R.?!"}))["count"] > 0

    def test_over_long_query_is_400(self, dynamodb):
        assert call(path=FAQS, query={"q": "x" * 300})["statusCode"] == 400

    def test_unicode_query_does_not_crash(self, dynamodb):
        assert call(path=FAQS, query={"q": "एफआईआर"})["statusCode"] == 200

    def test_sql_ish_query_is_harmless(self, dynamodb):
        # Free text is never interpolated anywhere; this is just a bad search.
        assert call(path=FAQS, query={"q": "'; DROP TABLE FAQs; --"})["statusCode"] == 200


class TestTokenizer:
    def test_lowercases_and_splits(self):
        assert tokenize("FIR Copy") == ["fir", "copy"]

    def test_strips_punctuation(self):
        assert tokenize("Hello, please!") == ["hello", "please"]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("F.I.R.", "fir"), ("M.L.C.", "mlc"), ("m.a.c.t", "mact")],
    )
    def test_dotted_acronyms_are_collapsed(self, text, expected):
        # Users type these with periods more often than without; the
        # single-character filter would otherwise shred them into nothing.
        assert tokenize(text) == [expected]

    def test_acronym_collapsing_leaves_normal_sentences_alone(self):
        assert tokenize("the hospital refused") == ["hospital", "refused"]

    def test_removes_stopwords(self):
        assert tokenize("what is the insurance") == ["insurance"]

    def test_drops_single_characters(self):
        # A stray "s" from a possessive matches nothing and inflates scores.
        assert "s" not in tokenize("police's report")

    def test_empty_string(self):
        assert tokenize("") == []

    def test_handles_non_string_input(self):
        assert tokenize(12345) == ["12345"]


class TestScoring:
    FAQ = {
        "faq_id": "x",
        "question": "Do we need FIR for the insurance claim?",
        "answer": "Yes, the FIR is essential for injury claims.",
        "topic": "fir",
        "tags": ["insurance", "fir"],
    }

    def test_question_match_outweighs_answer_match(self):
        question_only = {**self.FAQ, "answer": "", "tags": [], "topic": ""}
        answer_only = {**self.FAQ, "question": "", "tags": [], "topic": ""}
        assert score(question_only, ["fir"]) > score(answer_only, ["fir"])

    def test_tag_match_counts(self):
        assert score({**self.FAQ, "question": "", "answer": ""}, ["insurance"]) > 0

    def test_no_tokens_scores_zero(self):
        assert score(self.FAQ, []) == 0.0

    def test_unmatched_token_scores_zero(self):
        assert score(self.FAQ, ["helicopter"]) == 0.0

    def test_covering_more_of_the_query_scores_higher(self):
        both = score(self.FAQ, ["fir", "insurance"])
        one = score(self.FAQ, ["fir", "helicopter"])
        assert both > one

    def test_missing_fields_do_not_raise(self):
        assert score({"faq_id": "y"}, ["fir"]) == 0.0

    def test_none_tags_do_not_raise(self):
        assert score({**self.FAQ, "tags": None}, ["fir"]) > 0


class TestRank:
    ITEMS = [
        {"faq_id": "a", "question": "fir copy", "answer": "", "tags": [], "topic": ""},
        {"faq_id": "b", "question": "insurance", "answer": "", "tags": [], "topic": ""},
        {"faq_id": "c", "question": "fir copy free", "answer": "", "tags": [], "topic": ""},
    ]

    def test_drops_non_matches(self):
        assert [i["faq_id"] for i in rank(self.ITEMS, "fir")] == ["a", "c"]

    def test_ties_break_on_id_for_a_stable_order(self):
        results = rank(self.ITEMS, "fir copy")
        assert [i["faq_id"] for i in results] == ["a", "c"]

    def test_does_not_mutate_the_input(self):
        rank(self.ITEMS, "fir")
        assert "score" not in self.ITEMS[0]

    def test_empty_corpus(self):
        assert rank([], "fir") == []


class TestRouting:
    def test_faqs_path_reaches_the_faq_branch(self, dynamodb):
        assert "items" in data_of(call(path=FAQS))

    def test_stage_prefixed_faq_path(self, dynamodb):
        assert call(path="/Prod/aftermath/faqs")["statusCode"] == 200

    def test_trailing_slash_on_steps(self, dynamodb):
        assert call(path="/aftermath/steps/")["statusCode"] == 200

    def test_preflight(self, no_tables):
        assert call(method="OPTIONS")["statusCode"] == 204

    def test_missing_tables_are_502(self, no_tables):
        assert call()["statusCode"] == 502
