"""Tests for scripts/phase5_bm25_combiner.py
(reports/phase5_bm25_combiner_protocol.md, PRE-REGISTERED 2026-08-04).

Two kinds of invariant are pinned here.

1. **The pre-registered decision rule.** The protocol was committed before the
   run so that the rule provably preceded the data. Pinning its constants in
   a test is what stops a later edit from silently moving the bar the reported
   verdict was measured against -- the same reason the ratified queue-policy
   character set is pinned by codepoint.
2. **The two numerical claims the results rest on**: that row normalization
   cannot reorder a query's own ranking (so alpha=0 really is BM25), and that
   RRF ranks are taken within each query's eligible pool (so the reported RRF
   failure is the method's, not an artifact of ranking before masking).

Importing the script requires torch, which requirements-ci.txt deliberately
omits; skipped when it is unavailable, like the P4-F tests.
"""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import torch  # noqa: F401
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    import phase5_bm25_combiner as c


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestPreRegisteredRule(unittest.TestCase):
    """These constants are the ratified rule. Changing one invalidates the
    reported REALIZABLE verdict; the test exists to make that visible."""

    def test_margin_and_folds_match_protocol(self):
        self.assertEqual(c.DECISION_MARGIN, 0.010)
        self.assertEqual(c.N_FOLDS, 5)
        self.assertEqual(c.RRF_K, 60)
        self.assertEqual(c.PRIMARY, "google/canine-s")

    def test_alpha_grid_contains_zero(self):
        """alpha=0 must be in the grid: it is what makes the combiner family
        strictly contain the BM25 baseline, so a held-out gain is
        attributable to the added signal rather than to reparameterization."""
        self.assertIn(0.0, c.ALPHA_GRID)
        self.assertEqual(min(c.ALPHA_GRID), 0.0,
                         "negative alpha would let the combiner invert the "
                         "candidate signal, which the protocol does not declare")


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestNormalizationIsRankPreserving(unittest.TestCase):

    def test_znorm_preserves_within_row_order(self):
        rng = np.random.default_rng(0)
        M = rng.normal(size=(20, 50)) * rng.uniform(0.1, 100, size=(20, 1))
        Z = c.znorm_rows(M)
        for i in range(M.shape[0]):
            self.assertTrue(
                np.array_equal(np.argsort(-M[i], kind="stable"),
                               np.argsort(-Z[i], kind="stable")),
                "row z-normalization reordered a query's candidates; alpha=0 "
                "would then not reproduce BM25 and every delta would be void")

    def test_constant_row_does_not_divide_by_zero(self):
        Z = c.znorm_rows(np.ones((2, 5)))
        self.assertTrue(np.isfinite(Z).all())


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestRRFRanksWithinEligiblePool(unittest.TestCase):

    def test_same_parent_candidates_are_marked_ineligible(self):
        bm25 = np.array([[5.0, 4.0, 3.0, 2.0]])
        cos = np.array([[0.1, 0.9, 0.5, 0.2]])
        out = c.rrf_matrix(bm25, cos, ["A", "A", "B", "C"])
        self.assertEqual(out[0, 0], c.INELIGIBLE)
        self.assertEqual(out[0, 1], c.INELIGIBLE)
        self.assertTrue(np.isfinite(out[0, 2]) and np.isfinite(out[0, 3]))

    def test_ranks_exclude_ineligible_candidates(self):
        """The eligible candidates must be ranked 1..n among THEMSELVES. If
        ranks were taken over the full pool and masked afterwards, the
        excluded rows would shift each list by a different amount and the
        fused score would differ -- RRF's sum of reciprocals is not invariant
        to that."""
        bm25 = np.array([[9.0, 1.0, 0.5]])
        cos = np.array([[9.0, 0.2, 0.1]])
        out = c.rrf_matrix(bm25, cos, ["A", "B", "C"])
        # candidate 1 is top of both eligible lists -> rank 1 in each
        self.assertAlmostEqual(out[0, 1], 2.0 / (c.RRF_K + 1))
        self.assertAlmostEqual(out[0, 2], 2.0 / (c.RRF_K + 2))

    def test_query_with_no_eligible_candidates_is_left_ineligible(self):
        out = c.rrf_matrix(np.array([[1.0, 2.0]]), np.array([[1.0, 2.0]]),
                           ["A", "A"])
        self.assertTrue((out == c.INELIGIBLE).all())


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestFoldAssignment(unittest.TestCase):

    def _rows(self, spec):
        return [{"cth": k} for k, n in spec.items() for _ in range(n)]

    def test_every_composition_gets_exactly_one_fold(self):
        rows = self._rows({"a": 30, "b": 20, "c": 10, "d": 5, "e": 5, "f": 1})
        fold_of, load = c.assign_folds(rows)
        self.assertEqual(set(fold_of), {"a", "b", "c", "d", "e", "f"})
        self.assertTrue(all(0 <= f < c.N_FOLDS for f in fold_of.values()))
        self.assertEqual(sum(load), len(rows))

    def test_deterministic(self):
        rows = self._rows({"a": 7, "b": 7, "c": 3, "d": 3, "e": 1})
        self.assertEqual(c.assign_folds(rows)[0], c.assign_folds(rows)[0])

    def test_balances_by_query_count_not_composition_count(self):
        """One composition with 100 fragments must not sit in the same fold as
        the next-largest just because folds were balanced by composition."""
        rows = self._rows({"big": 100, "b": 20, "c": 20, "d": 20, "e": 20,
                           "f": 20})
        fold_of, load = c.assign_folds(rows)
        self.assertEqual(max(load) - min(load), 100 - 20)
        self.assertNotEqual(fold_of["big"], fold_of["b"])


if __name__ == "__main__":
    unittest.main()
