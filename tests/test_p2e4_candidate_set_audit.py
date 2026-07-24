"""Regression tests for P2-E4 candidate-set audit utilities."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2e4_candidate_set_audit as p2e4


def ranking(*proposals):
    alternatives = [
        {
            "proposal": (proposal,),
            "support_count": len(proposals) - index,
            "supporting_families": (f"f{index}",),
        }
        for index, proposal in enumerate(proposals)
    ]
    return {
        "alternatives": alternatives,
        "alternative_count": len(alternatives),
        "unique_top": True,
        "top_support": len(proposals),
        "runner_up_support": max(0, len(proposals) - 1),
        "support_margin": 1,
        "dominance": 0.6,
    }


class TestP2E4CandidateSetAudit(unittest.TestCase):
    def test_candidate_depth_recovers_lower_ranked_attested_reading(self):
        record = {
            "cth": 1,
            "gold": ("gold",),
            "ranking": ranking("variant", "gold"),
        }
        metrics = p2e4.candidate_set_metrics([record], [1, 2])
        self.assertEqual(
            metrics["prefix_sets"]["1"]["attested_inclusion_contexts"], 0)
        self.assertEqual(
            metrics["prefix_sets"]["2"]["attested_inclusion_contexts"], 1)
        self.assertEqual(metrics["attested_lower_ranked_contexts"], 1)

    def test_absent_attested_reading_is_not_relabeled_variant(self):
        record = {
            "gold": ("gold",),
            "ranking": ranking("other"),
        }
        self.assertEqual(
            p2e4.disagreement_category(record),
            "ATTESTED_READING_ABSENT_TOP_EQUAL_LENGTH_DIFFERENT",
        )

    def test_rank_calibration_names_group_estimand(self):
        rule = {
            "minimum_top_support_families": 1,
            "minimum_support_margin": 1,
            "minimum_dominance": 0.0,
            "maximum_alternatives": None,
        }
        records = [
            {"gold": ("a",), "ranking": ranking("a", "b")},
            {"gold": ("b",), "ranking": ranking("a", "b")},
        ]
        result = p2e4.rank_calibration(
            records, rule, 2, "named estimand")
        self.assertEqual(
            result["1"]["calibration_contexts_with_rank_available"], 2)
        self.assertEqual(
            result["1"]["calibrated_empirical_agreement"], 0.5)
        self.assertTrue(result["1"]["not_an_instance_truth_probability"])

    def test_anchor_repeat_count_is_query_local(self):
        records = [
            {
                "fragment_id": "a",
                "left_anchor": ("L",),
                "right_anchor": ("R",),
            },
            {
                "fragment_id": "a",
                "left_anchor": ("L",),
                "right_anchor": ("R",),
            },
            {
                "fragment_id": "b",
                "left_anchor": ("L",),
                "right_anchor": ("R",),
            },
        ]
        p2e4.add_anchor_repeat_counts(records)
        self.assertEqual(records[0]["query_anchor_occurrence_count"], 2)
        self.assertEqual(records[2]["query_anchor_occurrence_count"], 1)

    def test_candidate_set_tracer_passes(self):
        self.assertEqual(
            p2e4.candidate_set_tracer()["blocking_failures"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
