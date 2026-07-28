"""Tests for the P2-E8 cross-line recoverability census.

Two things here are easy to get subtly wrong and expensive to get wrong
quietly: which region of the anchored window a line break falls in, and the
refusal to concatenate across a line the language scope excluded. The second
is a correctness property, not a tuning choice -- crossing an empty slot
fabricates adjacency between lines that had out-of-scope material between
them, which is precisely what EXCLUDE_LINE exists to prevent.
"""
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

import p2e8_cross_line_recoverability as p2e8  # noqa: E402


class TestBoundaryRegion(unittest.TestCase):
    """Window layout: [left_start, mask_start) [mask) [mask_end, right_end)."""

    def region(self, boundary, *, left_start=0, mask_start=2, mask_end=4,
               right_end=6):
        return p2e8.boundary_region(
            left_start, mask_start, mask_end, right_end, boundary)

    def test_a_window_not_crossing_the_boundary_is_not_cross_line(self):
        """That span belongs to P2-E's same-line population, not this one."""
        self.assertIsNone(self.region(0))
        self.assertIsNone(self.region(6))
        self.assertIsNone(self.region(9))

    def test_break_splitting_the_left_anchor(self):
        self.assertEqual(self.region(1), "in_left_anchor")

    def test_break_flush_against_the_mask_leaves_anchors_intact(self):
        self.assertEqual(self.region(2), "at_mask_start")
        self.assertEqual(self.region(4), "at_mask_end")

    def test_break_strictly_inside_the_mask(self):
        self.assertEqual(self.region(3), "in_mask")

    def test_break_splitting_the_right_anchor(self):
        self.assertEqual(self.region(5), "in_right_anchor")

    def test_in_mask_is_unreachable_for_a_single_sign_mask(self):
        """A line break cannot fall strictly inside one sign.

        An empty `in_mask` row for mask length 1 is therefore correct, not a
        measurement that silently failed.
        """
        regions = {
            self.region(b, mask_start=2, mask_end=3, right_end=5)
            for b in range(0, 6)
        }
        self.assertNotIn("in_mask", regions)
        self.assertIn("at_mask_start", regions)
        self.assertIn("at_mask_end", regions)

    def test_every_region_is_reachable_for_a_two_sign_mask(self):
        regions = {self.region(b) for b in range(1, 6)}
        self.assertEqual(set(p2e8.BOUNDARY_REGIONS), regions)


class TestCrossLineSpans(unittest.TestCase):
    def test_spans_are_yielded_across_a_real_boundary(self):
        lines = [["a", "b", "c"], ["d", "e", "f"]]
        spans = list(p2e8.iter_cross_line_spans(lines, 1, 1))
        self.assertTrue(spans)
        for region, (left, right), gold in spans:
            self.assertIn(region, p2e8.BOUNDARY_REGIONS)
            self.assertEqual(len(left), 1)
            self.assertEqual(len(right), 1)
            self.assertEqual(len(gold), 1)

    def test_an_empty_slot_is_never_crossed(self):
        """The out-of-scope line's absence is not permission to join its
        neighbours; doing so would invent a token adjacency."""
        self.assertEqual(
            list(p2e8.iter_cross_line_spans(
                [["a", "b", "c"], [], ["d", "e", "f"]], 1, 1)),
            [])

    def test_spans_never_cross_more_than_one_boundary(self):
        """Adjacent pairs only: a token from line 1 and one from line 3 must
        never land in the same window."""
        lines = [["a", "b"], ["c", "d"], ["e", "f"]]
        for region, (left, right), gold in p2e8.iter_cross_line_spans(
                lines, 1, 1):
            tokens = set(left) | set(right) | set(gold)
            self.assertFalse(tokens & {"a", "b"} and tokens & {"e", "f"})

    def test_refused_boundary_counting_matches_the_skip_rule(self):
        sequences = {
            "frag-a": [["a"], [], ["b"]],          # 2 boundaries, both refused
            "frag-b": [["c"], ["d"]],              # 1 boundary, crossed
        }
        refused, total = p2e8.count_refused_boundaries(sequences)
        self.assertEqual((refused, total), (2, 3))

    def test_gold_and_anchors_are_contiguous_in_the_flattened_pair(self):
        lines = [["a", "b"], ["c", "d"]]
        for _, (left, right), gold in p2e8.iter_cross_line_spans(lines, 1, 1):
            flat = ["a", "b", "c", "d"]
            joined = list(left) + list(gold) + list(right)
            start = flat.index(joined[0])
            self.assertEqual(flat[start:start + len(joined)], joined)


if __name__ == "__main__":
    unittest.main()
