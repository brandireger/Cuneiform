"""Tests for the locked surrogate-review reveal analysis."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import phase6_surrogate_review_analyze as sa  # noqa: E402


def annotation(case_id, preference, support=None, physical=None):
    return {
        "case_id": case_id,
        "preferred_candidate": preference,
        "textual_relation_support": support or {"A": "STRONG", "B": "WEAK"},
        "formulaicity_ambiguity": "LOW",
        "physical_join_judgment": physical,
        "specialist_priority": "MEDIUM",
    }


def revealed(case_id, outcome="gained"):
    return {
        "case_id": case_id,
        "task_cell": "duplicates",
        "sampling_outcome": outcome,
        "candidate_A": {
            "method": "expanded_bigram",
            "benchmark_positive": True,
        },
        "candidate_B": {
            "method": "unigram",
            "benchmark_positive": False,
        },
    }


class TestSurrogateReviewAnalyze(unittest.TestCase):

    def test_requires_pre_reveal_lock(self):
        annotations = {
            "status": "DRAFT",
            "reveal_content_inspected_before_lock": False,
            "annotations": [annotation("SR001", "A")],
        }
        with self.assertRaises(RuntimeError):
            sa.analyze(annotations, {"cases": [revealed("SR001")]})

    def test_counts_method_preference_and_benchmark_agreement(self):
        annotations = {
            "status": "LOCKED_BEFORE_REVEAL_CONTENT_INSPECTION",
            "reveal_content_inspected_before_lock": False,
            "reviewer_role": "surrogate",
            "annotations": [
                annotation("SR001", "A"),
                annotation("SR002", "BOTH"),
                annotation("SR003", "NEITHER"),
            ],
        }
        reveal = {"cases": [
            revealed("SR001"),
            revealed("SR002"),
            revealed("SR003"),
        ]}
        result = sa.analyze(annotations, reveal)
        self.assertEqual(
            result["preference_by_stratum"]["duplicates::gained"],
            {"both": 1, "expanded": 1, "neither": 1},
        )
        agreement = result["benchmark_label_agreement"]
        self.assertEqual(agreement["single_candidate_choices"], 1)
        self.assertEqual(agreement["single_candidate_choice_is_benchmark_positive"], 1)
        self.assertEqual(agreement["all_nonabstaining_choices"], 2)
        self.assertEqual(agreement["selected_set_contains_benchmark_positive"], 2)

    def test_locked_legacy_reveal_field_is_interpreted_as_benchmark_only(self):
        self.assertTrue(sa.benchmark_positive({"editorial_relation_positive": True}))

    def test_rejects_case_id_mismatch(self):
        annotations = {
            "status": "LOCKED_BEFORE_REVEAL_CONTENT_INSPECTION",
            "reveal_content_inspected_before_lock": False,
            "reviewer_role": "surrogate",
            "annotations": [annotation("SR001", "A")],
        }
        with self.assertRaises(RuntimeError):
            sa.analyze(annotations, {"cases": [revealed("SR999")]})


if __name__ == "__main__":
    unittest.main()
