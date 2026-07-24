"""Regression tests for the P2-D source classification and exact test."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2d_reliability_audit as p2d


class TestP2DReliabilityAudit(unittest.TestCase):
    def test_relation_classification_is_fail_closed(self):
        self.assertEqual(
            p2d.classify_relation({
                "join_type": "direct", "declared_adjacent": True}),
            p2d.DIRECT,
        )
        self.assertEqual(
            p2d.classify_relation({
                "join_type": "indirect", "declared_adjacent": True}),
            p2d.INDIRECT,
        )
        self.assertEqual(
            p2d.classify_relation({
                "join_type": "inferred_from_shared_lines",
                "declared_adjacent": False,
            }),
            p2d.INFERRED,
        )
        self.assertEqual(
            p2d.classify_relation({
                "join_type": "direct", "declared_adjacent": False}),
            p2d.UNKNOWN,
        )

    def test_fisher_exact_matches_known_probe_table(self):
        result = p2d.fisher_exact_2x2([[17, 29], [76, 60]])
        self.assertAlmostEqual(result["odds_ratio"], 0.4627949183)
        self.assertAlmostEqual(result["p_two_sided"], 0.0281429852)
        self.assertAlmostEqual(result["p_enrichment_greater"], 0.9917895753)
        self.assertAlmostEqual(result["p_depletion_less"], 0.0199851163)

    def test_fisher_zero_denominator_is_explicit(self):
        result = p2d.fisher_exact_2x2([[1, 0], [0, 1]])
        self.assertTrue(math.isinf(result["odds_ratio"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
