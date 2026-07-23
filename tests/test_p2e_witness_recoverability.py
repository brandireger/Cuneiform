"""Unit tests for the P2-E anchored-witness recoverability probe."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import p2e_witness_recoverability as p2e


class TestP2EWitnessRecoverability(unittest.TestCase):
    def test_masked_spans_do_not_cross_lines(self):
        spans = list(p2e.iter_masked_spans(
            [["a", "b", "c"], ["d", "e", "f"]], 1, 1))
        self.assertEqual(
            spans,
            [
                ((("a",), ("c",)), ("b",)),
                ((("d",), ("f",)), ("e",)),
            ],
        )

    def test_anchor_index_allows_variable_middle(self):
        lines = {"w": [["L1", "L2", "x", "y", "R1", "R2"]]}
        families = {"w": "witness-family"}
        cths = {"w": 7}
        requested = {7: {(("L1", "L2"), ("R1", "R2"))}}
        index = p2e.build_anchor_index(
            ["w"], lines, families, 2, requested, cths, max_middle=4)
        proposals = p2e.independent_proposals(
            index, 7, (("L1", "L2"), ("R1", "R2")), "query-family")
        self.assertEqual(proposals, {("x", "y")})

    def test_same_family_evidence_is_excluded(self):
        lines = {"w": [["L", "gold", "R"]]}
        families = {"w": "same-family"}
        cths = {"w": 1}
        requested = {1: {(("L",), ("R",))}}
        index = p2e.build_anchor_index(
            ["w"], lines, families, 1, requested, cths, max_middle=2)
        self.assertEqual(
            p2e.independent_proposals(
                index, 1, (("L",), ("R",)), "same-family"),
            set(),
        )

    def test_exact_variant_and_ambiguity_are_separable(self):
        lines = {
            "w1": [["L", "gold", "R"]],
            "w2": [["L", "variant", "R"]],
        }
        families = {"w1": "f1", "w2": "f2"}
        cths = {"w1": 1, "w2": 1}
        requested = {1: {(("L",), ("R",))}}
        index = p2e.build_anchor_index(
            lines, lines, families, 1, requested, cths, max_middle=2)
        proposals = p2e.independent_proposals(
            index, 1, (("L",), ("R",)), "query-family")
        self.assertEqual(proposals, {("gold",), ("variant",)})
        self.assertIn(("gold",), proposals)
        self.assertGreater(len(proposals), 1)

    def test_two_sided_join_coverage_requires_distinct_occurrences(self):
        lines_a = [["a", "b"]]
        lines_b = [["c", "d"]]
        self.assertTrue(p2e.has_two_sided_witness_coverage(
            lines_a, lines_b, [["z", "a", "b", "c", "d"]], 2))
        self.assertFalse(p2e.has_two_sided_witness_coverage(
            [["a"]], [["a"]], [["a"]], 1))

    def test_order_scramble_changes_synthetic_anchor_evidence(self):
        original = [["L1", "L2", "gold", "R1", "R2"]]
        scrambled = p2e.scramble_lines(original, p2e.SEED)
        self.assertEqual(sorted(original[0]), sorted(scrambled[0]))
        self.assertNotEqual(original, scrambled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
