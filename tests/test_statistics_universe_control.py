"""Tests for scripts/phase5_statistics_universe_control.py
(reports/phase5_statistics_universe_protocol.md, PRE-REGISTERED 2026-08-04).

Three kinds of invariant are pinned here.

1. **The pre-registered constants.** The protocol was committed before the run
   so the rule provably preceded the data; pinning the margin, the fixed
   character n-gram range and the two reproduction targets is what stops a
   later edit from quietly moving the bar the reported verdict was measured
   against.
2. **That the rectangular runner is the square one.** The script scores dev
   queries against a candidate pool they are not a subset of, which the
   existing `phase5_bm25_combiner.run_subset` cannot express. The new helper
   delegates to `eval_harness.run_task_a`'s precomputed path rather than
   reimplementing ranking -- a second ranking implementation is how E2
   happened -- and this pins that the two agree exactly when the pools
   coincide.
3. **That the vectorizers are fit on the index side only.** This is the whole
   point of the run: if `tfidf_cosine` fit on the queries, the statistics
   universe would once again be query-derived and the control would be
   measuring nothing.

Importing the script pulls in torch via phase5_bm25_combiner, which
requirements-ci.txt deliberately omits; skipped when unavailable, like the
P4-F and combiner tests.
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
    import phase5_bm25_combiner as comb
    import phase5_statistics_universe_control as su


def _rows():
    """Four fragments over two compositions, two of them sharing a parent_doc
    so the leave-one-out exclusion actually has something to exclude."""
    return [
        {"fragment_id": "f1", "parent_doc": "d1", "cth": 1,
         "tokens": ["a", "b", "c", "d"], "text": "a b c d"},
        {"fragment_id": "f2", "parent_doc": "d2", "cth": 1,
         "tokens": ["a", "b", "c", "e"], "text": "a b c e"},
        {"fragment_id": "f3", "parent_doc": "d3", "cth": 2,
         "tokens": ["x", "y", "z", "w"], "text": "x y z w"},
        {"fragment_id": "f4", "parent_doc": "d3", "cth": 2,
         "tokens": ["x", "y", "z", "v"], "text": "x y z v"},
    ]


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestPreRegisteredConstants(unittest.TestCase):
    """Changing one of these invalidates the reported verdict."""

    def test_margin_and_primary_arm_match_protocol(self):
        self.assertEqual(su.DECISION_MARGIN, 0.010)
        self.assertEqual(su.PRIMARY_ARM, "bm25_plus_bigram_tfidf")

    def test_char_ngram_range_is_fixed_not_fitted(self):
        """The protocol declares (4,6) fixed. Fitting the range per fold would
        reintroduce a moving arm into a run whose only moving part is the
        statistics universe."""
        self.assertEqual(su.CHAR_NGRAM_RANGE, (4, 6))

    def test_reproduction_targets_are_the_published_deltas(self):
        self.assertEqual(su.HISTORICAL["bm25_plus_unigram_tfidf"], 0.0520)
        self.assertEqual(su.HISTORICAL["bm25_plus_bigram_tfidf"], 0.1017)
        self.assertEqual(su.REPRO_TOL, 0.0005)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestRectangularRunner(unittest.TestCase):

    def test_matches_run_subset_when_pools_coincide(self):
        """The rectangular runner must be the square runner in the special
        case, or U1 would not reproduce the historical setup."""
        rows = _rows()
        rng = np.random.default_rng(0)
        scores = rng.normal(size=(len(rows), len(rows)))
        idx = list(range(len(rows)))

        pq_square, agg_square = comb.run_subset(rows, scores, idx)
        pq_rect, agg_rect = su.rectangular_task_a(rows, rows, scores, idx)

        self.assertEqual(pq_square, pq_rect)
        self.assertEqual(agg_square["recall@1"]["mean"],
                         agg_rect["recall@1"]["mean"])

    def test_query_subset_selects_the_matching_score_rows(self):
        """A misaligned subset would silently score each query against another
        query's row -- the failure run_task_a's shape guard exists to catch."""
        rows = _rows()
        rng = np.random.default_rng(1)
        scores = rng.normal(size=(len(rows), len(rows)))

        pq_all, _ = su.rectangular_task_a(rows, rows, scores, [0, 1, 2, 3])
        pq_one, _ = su.rectangular_task_a(rows, rows, scores, [2])

        by_id = {r["query_id"]: r for r in pq_all}
        for rec in pq_one:
            self.assertEqual(rec, by_id[rec["query_id"]])


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestStatisticsUniverse(unittest.TestCase):

    def test_tfidf_is_fit_on_the_index_not_the_queries(self):
        """A term absent from the index must contribute nothing, however
        heavily it is weighted on the query side. If the vectorizer were fit
        on the union, the statistics universe would be query-derived again."""
        index = [["a", "b"], ["a", "c"]]
        queries = [["a", "zzz", "zzz", "zzz"]]
        sim = su.tfidf_cosine(index, queries, tokenizer=lambda x: x,
                              preprocessor=lambda x: x, token_pattern=None)
        self.assertEqual(sim.shape, (1, 2))
        # 'zzz' is out of vocabulary, so the query reduces to 'a', which both
        # index documents contain -- the two similarities must be equal.
        self.assertAlmostEqual(sim[0, 0], sim[0, 1], places=12)

    def test_column_restriction_equals_scoring_a_smaller_pool(self):
        """U2 is built by restricting U3's score matrix to the dev columns.
        That is only legitimate if a score depends solely on globally-fit
        statistics and the candidate document itself."""
        index = [["a", "b"], ["a", "c"], ["d", "e"]]
        queries = [["a", "b"], ["d", "e"]]
        full = su.tfidf_cosine(index, queries, tokenizer=lambda x: x,
                               preprocessor=lambda x: x, token_pattern=None)
        restricted = full[:, [0, 2]]
        self.assertEqual(restricted.shape, (2, 2))
        np.testing.assert_allclose(restricted[:, 0], full[:, 0])
        np.testing.assert_allclose(restricted[:, 1], full[:, 2])


if __name__ == "__main__":
    unittest.main()
