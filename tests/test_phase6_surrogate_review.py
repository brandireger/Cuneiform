"""Regression tests for the blinded Phase 6 surrogate-review exporter."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import torch  # noqa: F401
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    import phase6_surrogate_review_export as sr


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestSurrogateReviewExport(unittest.TestCase):

    def test_requested_sample_is_fixed_and_balanced(self):
        self.assertEqual(sum(sr.REQUESTED.values()), 20)
        self.assertEqual(sr.REQUESTED[("duplicates", "gained")], 6)
        self.assertEqual(sr.REQUESTED[("duplicates", "lost")], 6)
        self.assertEqual(sr.REQUESTED[("joins", "gained")], 5)
        self.assertEqual(sr.REQUESTED[("joins", "lost")], 3)

    def test_visible_fragment_removes_corpus_identity(self):
        row = {
            "fragment_id": "SECRET", "parent_doc": "SECRET_PARENT", "cth": 1,
            "HITTITE_ONLY::lines": [4, 7],
            "HITTITE_ONLY": [["nu", "NINDA"], ["pa", "an", "zi"]],
        }
        visible = sr.visible_fragment(row, "A")
        self.assertEqual(visible["alias"], "A")
        self.assertEqual(visible["attested_token_count"], 5)
        self.assertEqual([x["line_index"] for x in visible["lines"]], [4, 7])
        self.assertNotIn("fragment_id", visible)
        self.assertNotIn("parent_doc", visible)
        self.assertNotIn("cth", visible)

    def test_blind_case_rejects_method_or_truth_leak(self):
        sr.assert_blind_case({"case_id": "SR001", "candidate_A": {"alias": "A"}})
        with self.assertRaises(RuntimeError):
            sr.assert_blind_case({"case_id": "SR001", "method": "expanded"})
        with self.assertRaises(RuntimeError):
            sr.assert_blind_case({"case_id": "SR001", "candidate_A": {"correct": True}})

    def test_only_authoritative_self_join_exclusions_are_accepted(self):
        expected = sorted(sr.EXPECTED_DEGENERATE_SELF_JOINS)
        sr.assert_expected_degenerate_self_joins(expected)
        with self.assertRaises(RuntimeError):
            sr.assert_expected_degenerate_self_joins([])
        with self.assertRaises(RuntimeError):
            sr.assert_expected_degenerate_self_joins(expected + ["NEW::1"])

    def test_selection_is_deterministic_and_prefers_distinct_cth(self):
        pool = [
            {"query_id": "q1", "cell": "duplicates", "outcome": "gained"},
            {"query_id": "q2", "cell": "duplicates", "outcome": "gained"},
            {"query_id": "q3", "cell": "duplicates", "outcome": "gained"},
        ]
        pools = {("duplicates", "gained"): pool}
        cth = {"q1": 1, "q2": 1, "q3": 2}
        requested = {("duplicates", "gained"): 2}
        first, accounting = sr.select_cases(pools, cth, requested=requested, seed=9)
        second, _ = sr.select_cases(pools, cth, requested=requested, seed=9)
        self.assertEqual(first, second)
        self.assertEqual({cth[x["query_id"]] for x in first}, {1, 2})
        self.assertEqual(accounting["duplicates::gained"]["shortfall"], 0)


if __name__ == "__main__":
    unittest.main()
