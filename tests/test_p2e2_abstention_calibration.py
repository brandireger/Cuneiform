"""Regression tests for P2-E2 evidence ranking and abstention."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2e2_abstention_calibration as p2e2
import p2e_witness_recoverability as p2e


def synthetic_index(lines, families):
    key = (("L",), ("R",))
    cths = {fragment_id: 1 for fragment_id in lines}
    return key, p2e.build_anchor_index(
        lines, lines, families, 1, {1: {key}}, cths, max_middle=2)


class TestP2E2Calibration(unittest.TestCase):
    def test_rank_uses_independent_family_support(self):
        lines = {
            "w1": [["L", "gold", "R"]],
            "w2": [["L", "gold", "R"]],
            "w3": [["L", "variant", "R"]],
        }
        families = {"w1": "f1", "w2": "f2", "w3": "f3"}
        key, index = synthetic_index(lines, families)
        ranking = p2e2.proposal_ranking(index, 1, key, "query")
        self.assertEqual(ranking["alternatives"][0]["proposal"], ("gold",))
        self.assertEqual(ranking["top_support"], 2)
        self.assertTrue(ranking["unique_top"])

    def test_evidence_tie_abstains_without_lexical_tiebreak(self):
        lines = {
            "w1": [["L", "aaa", "R"]],
            "w2": [["L", "zzz", "R"]],
        }
        families = {"w1": "f1", "w2": "f2"}
        key, index = synthetic_index(lines, families)
        ranking = p2e2.proposal_ranking(index, 1, key, "query")
        permissive = {
            "minimum_top_support_families": 1,
            "minimum_support_margin": 0,
            "minimum_dominance": 0.0,
            "maximum_alternatives": None,
        }
        self.assertFalse(ranking["unique_top"])
        self.assertFalse(p2e2.rule_accepts(ranking, permissive))

    def test_query_family_does_not_vote_for_itself(self):
        lines = {"w": [["L", "gold", "R"]]}
        key, index = synthetic_index(lines, {"w": "query-family"})
        ranking = p2e2.proposal_ranking(
            index, 1, key, "query-family")
        self.assertEqual(ranking["alternatives"], [])

    def test_rule_metrics_preserve_gold_anywhere_separately(self):
        ranking = {
            "alternatives": [
                {
                    "proposal": ("variant",),
                    "supporting_families": ("f1", "f2"),
                    "support_count": 2,
                },
                {
                    "proposal": ("gold",),
                    "supporting_families": ("f3",),
                    "support_count": 1,
                },
            ],
            "unique_top": True,
            "top_support": 2,
            "runner_up_support": 1,
            "support_margin": 1,
            "dominance": 2 / 3,
            "alternative_count": 2,
        }
        record = {"gold": ("gold",), "ranking": ranking}
        rule = {
            "minimum_top_support_families": 1,
            "minimum_support_margin": 1,
            "minimum_dominance": 0.0,
            "maximum_alternatives": None,
        }
        result = p2e2.evaluate_rule([record], rule)
        self.assertEqual(result["accepted_spans"], 1)
        self.assertEqual(result["top1_exact_agreement_spans"], 0)
        self.assertEqual(
            result["gold_anywhere_in_preserved_alternatives"], 1)

    def test_composition_partition_is_disjoint(self):
        lines = {
            "a1": [["L", "x", "R"]],
            "a2": [["L", "y", "R"]],
            "b1": [["L", "x", "R"]],
            "b2": [["L", "y", "R"]],
        }
        cths = {"a1": 1, "a2": 1, "b1": 2, "b2": 2}
        families = {
            "a1": "a1", "a2": "a2", "b1": "b1", "b2": "b2"}
        by_cth = {1: ["a1", "a2"], 2: ["b1", "b2"]}
        calibration, evaluation, _, _ = p2e2.split_compositions(
            lines, cths, families, by_cth, 1, 1)
        self.assertTrue(calibration)
        self.assertTrue(evaluation)
        self.assertFalse(calibration & evaluation)
        self.assertEqual(calibration | evaluation, {1, 2})

    def test_wilson_interval_is_bounded(self):
        lower, upper = p2e2.wilson_interval(90, 100)
        self.assertLess(lower, 0.9)
        self.assertGreater(upper, 0.9)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)

    def test_vectorized_rule_evaluation_matches_scalar(self):
        ranking = {
            "alternatives": [
                {
                    "proposal": ("gold",),
                    "supporting_families": ("f1", "f2"),
                    "support_count": 2,
                },
            ],
            "unique_top": True,
            "top_support": 2,
            "runner_up_support": 0,
            "support_margin": 2,
            "dominance": 1.0,
            "alternative_count": 1,
        }
        records = [{"gold": ("gold",), "ranking": ranking}]
        rule = {
            "minimum_top_support_families": 1,
            "minimum_support_margin": 1,
            "minimum_dominance": 0.0,
            "maximum_alternatives": None,
        }
        scalar = p2e2.evaluate_rule(records, rule)
        vectorized = p2e2.evaluate_rules_vectorized(records, [rule])[0]
        self.assertEqual(scalar, vectorized)


if __name__ == "__main__":
    unittest.main(verbosity=2)
