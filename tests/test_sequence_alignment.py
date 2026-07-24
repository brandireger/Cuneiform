"""Regression tests for bounded, inspectable sequence alignment."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import sequence_alignment as sa


class TestSequenceAlignment(unittest.TestCase):
    def test_exact_flanks_recover_bounded_middle(self):
        alignments = sa.bounded_two_flank_alignments(
            ("A", "B"),
            ("D", "E"),
            ("A", "B", "X", "D", "E"),
            maximum_middle_length=3,
        )
        self.assertEqual(alignments[0]["middle"], ("X",))
        self.assertEqual(alignments[0]["normalized_score"], 1.0)

    def test_flank_edit_is_visible_and_tolerated(self):
        alignments = sa.bounded_two_flank_alignments(
            ("A", "B", "C"),
            ("D", "E", "F"),
            ("A", "B", "Z", "C", "X", "D", "E", "F"),
            maximum_middle_length=3,
            minimum_normalized_score=0.5,
        )
        match = next(
            value for value in alignments if value["middle"] == ("X",))
        self.assertGreaterEqual(match["left"]["query_gaps"], 1)
        self.assertEqual(match["left_boundary"], 4)
        self.assertEqual(match["right_boundary"], 5)

    def test_middle_never_exceeds_bound(self):
        alignments = sa.bounded_two_flank_alignments(
            ("A", "B"),
            ("D", "E"),
            ("A", "B", "X", "Y", "Z", "D", "E"),
            maximum_middle_length=2,
        )
        self.assertTrue(
            all(len(value["middle"]) <= 2 for value in alignments))
        self.assertNotIn(
            ("X", "Y", "Z"),
            {value["middle"] for value in alignments},
        )

    def test_order_scramble_changes_alignment(self):
        original = sa.bounded_two_flank_alignments(
            ("A", "B", "C"),
            ("D", "E", "F"),
            ("A", "B", "C", "X", "D", "E", "F"),
            maximum_middle_length=3,
        )
        scrambled = sa.bounded_two_flank_alignments(
            ("C", "B", "A"),
            ("F", "E", "D"),
            ("A", "B", "C", "X", "D", "E", "F"),
            maximum_middle_length=3,
        )
        self.assertNotEqual(
            [(value["middle"], value["score"]) for value in original],
            [(value["middle"], value["score"]) for value in scrambled],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
