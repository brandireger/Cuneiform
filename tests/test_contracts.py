#!/usr/bin/env python3
"""Fail-closed regression tests for lightweight ingress contracts."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import contracts


class TestCleanroomSplitContract(unittest.TestCase):
    def test_rejects_test_id(self):
        with self.assertRaises(AssertionError):
            contracts.assert_no_test(
                ["frag-test"], {"frag-test": "test"}, label="unit")

    def test_rejects_unknown_id(self):
        with self.assertRaises(AssertionError):
            contracts.assert_no_test(
                ["missing"], {"known": "train"}, label="unit")

    def test_rejects_unknown_split_value(self):
        with self.assertRaises(AssertionError):
            contracts.assert_no_test(
                ["frag"], {"frag": "holdout"}, label="unit")

    def test_accepts_non_test_splits(self):
        contracts.assert_no_test(
            ["train", "dev", "discovery"],
            {"train": "train", "dev": "dev", "discovery": "discovery"},
            label="unit",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
