"""Regression tests for P2-E3 cross-calibration utilities."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2e3_cross_calibration as p2e3


class TestP2E3CrossCalibration(unittest.TestCase):
    def test_anchor_pair_frequency_counts_compositions_not_occurrences(self):
        sequences = {
            1: [["L", "x", "R"], ["L", "x", "R"]],
            2: [["L", "y", "R"]],
            3: [["X", "z", "Y"]],
        }
        key = (("L",), ("R",))
        frequency = p2e3.anchored_key_document_frequency(
            sequences, {1: {key}}, max_middle=2)[1]
        self.assertEqual(frequency[key], 2)

    def test_formulaicity_tracer_passes(self):
        self.assertEqual(p2e3.formulaicity_tracer()["blocking_failures"], 0)

    def test_bin_value_fails_closed(self):
        bins = [
            {"name": "one", "minimum": 1, "maximum": 1},
            {"name": "many", "minimum": 2, "maximum": None},
        ]
        self.assertEqual(p2e3.bin_value(1, bins), "one")
        self.assertEqual(p2e3.bin_value(5, bins), "many")
        with self.assertRaises(AssertionError):
            p2e3.bin_value(0, bins)

    def test_fold_assignment_is_disjoint_and_complete(self):
        weights = {1: 100, 2: 80, 3: 40, 4: 20, 5: 10, 6: 0}
        folds = p2e3.assign_composition_folds(
            weights, set(weights), n_folds=3)
        covered = set().union(*(fold["cth"] for fold in folds))
        self.assertEqual(covered, set(weights))
        self.assertEqual(
            sum(len(fold["cth"]) for fold in folds), len(weights))
        for left in folds:
            for right in folds:
                if left["fold"] < right["fold"]:
                    self.assertFalse(left["cth"] & right["cth"])

    def test_unavailable_rule_means_full_abstention(self):
        ranking = {
            "alternatives": [{
                "proposal": ("gold",),
                "supporting_families": ("w",),
                "support_count": 1,
            }],
            "unique_top": True,
            "top_support": 1,
            "runner_up_support": 0,
            "support_margin": 1,
            "dominance": 1.0,
            "alternative_count": 1,
        }
        counts = p2e3.empty_counts()
        p2e3.update_counts(
            counts, [{"gold": ("gold",), "ranking": ranking}], rule=None)
        result = p2e3.finalize_counts(counts)
        self.assertEqual(result["eligible_spans"], 1)
        self.assertEqual(result["accepted_spans"], 0)
        self.assertEqual(result["coverage_percent_of_eligible"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
