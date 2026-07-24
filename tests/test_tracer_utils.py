"""Regression tests for scorer-appropriate tracer perturbations."""

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import tracer_utils


class TestTracerPerturbations(unittest.TestCase):
    def setUp(self):
        self.lines = [
            (0, [("a", "attested"), ("b", "restored")]),
            (1, [("c", "laes"), ("d", "attested")]),
        ]

    def test_order_permutation_preserves_layout_states_and_token_bag(self):
        permuted = tracer_utils.permute_token_order(
            self.lines, random.Random(7))

        self.assertEqual(
            [len(tokens) for _, tokens in permuted],
            [len(tokens) for _, tokens in self.lines],
        )
        self.assertEqual(
            [state for _, tokens in permuted for _, state in tokens],
            [state for _, tokens in self.lines for _, state in tokens],
        )
        self.assertEqual(
            Counter(token for _, tokens in permuted for token, _ in tokens),
            Counter(token for _, tokens in self.lines for token, _ in tokens),
        )

    def test_identity_corruption_changes_bag_and_preserves_length(self):
        original = ["a", "b", "a", "c"]
        corrupted = tracer_utils.corrupt_token_identities(
            original, random.Random(7), ["a", "b", "c", "d"])

        self.assertEqual(len(corrupted), len(original))
        self.assertTrue(all(a != b for a, b in zip(original, corrupted)))
        self.assertNotEqual(Counter(corrupted), Counter(original))

    def test_identity_corruption_requires_real_choice(self):
        with self.assertRaises(ValueError):
            tracer_utils.corrupt_token_identities(
                ["a"], random.Random(7), ["a"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
