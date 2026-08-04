"""Tests for scripts/phase5_taskb_transfer.py
(reports/phase5_taskb_transfer_protocol.md, PRE-REGISTERED and amended
2026-08-04).

The load-bearing test here is **C1**. The protocol's first draft asserted that
no positive relation's endpoints share a family. That is wrong, and wrong in a
way this repository has already paid for: composite join members share a
`parent_doc` and therefore a family by construction, because
`fragment_family()` strips the `::N` suffix. The real exclusion predicate in
`top_k_ranking` is **same family AND different parent_doc**, and the
2026-07-22 bugfix in that function records what happens when the `parent_doc`
clause is missing -- joins tier-A/B recall@1 read 0.0 against a real
0.059/0.5. `TestC1` pins both directions: a same-family/same-parent positive
must pass, and a same-family/different-parent one must fail.

Also pinned: the bin exception's three prohibitions (C6), the joins/duplicates
partition (C4), Holm-Bonferroni's step-down behaviour, and that the cluster
bootstrap resamples clusters rather than rows.

Importing the script pulls in torch via phase5_bm25_combiner, which
requirements-ci.txt deliberately omits; skipped when unavailable.
"""
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
    import phase5_taskb_transfer as tb


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestPreRegisteredConstants(unittest.TestCase):

    def test_primary_family_and_alpha(self):
        self.assertEqual(tb.PRIMARY_CELLS, ["joins", "duplicates", "pooled"])
        self.assertEqual(tb.PRIMARY_SCOPE, "HITTITE_ONLY")
        self.assertEqual(tb.FAMILY_ALPHA, 0.05)

    def test_base_scope_is_the_most_permissive(self):
        """§4's base population must come from the widest scope, or the
        coverage loss of every other scope is measured against a floor that
        already removed material."""
        self.assertEqual(tb.BASE_SCOPE, "ALL_LANGUAGES_UNCONDITIONED")

    def test_metrics_include_the_required_depths(self):
        for k in (1, 5, 10, 100):
            self.assertIn(k, tb.KS)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestC1FamilyPredicate(unittest.TestCase):
    """The amendment. Both directions are pinned."""

    def test_same_family_same_parent_positive_is_kept(self):
        """A composite join pair. These share a family by construction and
        MUST NOT be reported as excluded -- asserting otherwise would flag
        every valid join."""
        positives = {"KBo 64.15+::1": {"KBo 64.15+::2"}}
        res = tb.check_c1_family(positives, family_map={})
        self.assertTrue(res["passed"])
        self.assertEqual(res["n_positives_excluded_by_predicate"], 0)
        self.assertEqual(res["n_same_family_same_parent_kept"], 1)

    def test_same_family_different_parent_positive_is_flagged(self):
        """This one really would be excluded by top_k_ranking, so it must
        fail the check."""
        family_map = {"KUB 7.58": "KUB 7.58", "KUB 7.58 Vs. I": "KUB 7.58"}
        positives = {"KUB 7.58": {"KUB 7.58 Vs. I"}}
        res = tb.check_c1_family(positives, family_map)
        self.assertFalse(res["passed"])
        self.assertEqual(res["n_positives_excluded_by_predicate"], 1)

    def test_predicate_is_documented_in_the_payload(self):
        res = tb.check_c1_family({}, family_map={})
        self.assertEqual(res["predicate"], "same family AND different parent_doc")


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestC4AndC6(unittest.TestCase):

    def test_c4_detects_a_pair_in_both_relation_sets(self):
        positives = {"joins": {"a": {"b"}}, "duplicates": {"a": {"b"}},
                     "pooled": {"a": {"b"}}}
        self.assertFalse(tb.check_c4_partition(positives)["passed"])

    def test_c4_passes_on_a_real_partition(self):
        positives = {"joins": {"a": {"b"}}, "duplicates": {"a": {"c"}},
                     "pooled": {"a": {"b", "c"}}}
        self.assertTrue(tb.check_c4_partition(positives)["passed"])

    def test_c6_flags_a_bin_fragment_in_the_non_bin_index(self):
        """Prohibition 2: a bin-exception fragment in the ordinary index would
        become an ordinary negative for non-bin queries."""
        res = tb.check_c6_bin({"binfrag"},
                              {"duplicates": {}, "pooled": {}},
                              {"binfrag", "other"})
        self.assertFalse(res["passed"])
        self.assertFalse(
            res["prohibition_2_never_in_non_bin_candidate_index"]["passed"])

    def test_c6_flags_a_bin_fragment_as_a_duplicate_target(self):
        res = tb.check_c6_bin({"binfrag"},
                              {"duplicates": {"q": {"binfrag"}}, "pooled": {}},
                              {"other"})
        self.assertFalse(res["passed"])

    def test_c6_passes_when_the_exception_stays_in_its_lane(self):
        res = tb.check_c6_bin({"binfrag"},
                              {"duplicates": {"q": {"r"}}, "pooled": {"q": {"r"}}},
                              {"q", "r"})
        self.assertTrue(res["passed"])


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestInference(unittest.TestCase):

    def test_holm_bonferroni_steps_down_and_stops(self):
        out = tb.holm_bonferroni({"a": 0.001, "b": 0.04, "c": 0.9}, alpha=0.05)
        self.assertTrue(out["a"]["reject"])
        self.assertFalse(out["c"]["reject"])
        # smallest p is compared against alpha/m, not alpha
        self.assertAlmostEqual(out["a"]["adjusted_threshold"], 0.05 / 3)

    def test_holm_bonferroni_is_stricter_than_uncorrected(self):
        """p=0.03 clears an uncorrected 0.05 but must not clear alpha/3."""
        out = tb.holm_bonferroni({"a": 0.03, "b": 0.5, "c": 0.6}, alpha=0.05)
        self.assertFalse(out["a"]["reject"])

    def test_cluster_bootstrap_resamples_clusters_not_rows(self):
        """One cluster holding many identical rows must not narrow the
        interval the way many independent rows would -- that is the whole
        point of correction 5."""
        many_rows_one_cluster = {"c1": [1.0] * 50 + [0.0] * 50}
        many_clusters = {f"c{i}": [1.0] if i % 2 else [0.0] for i in range(100)}
        _d1, ci1 = tb.cluster_bootstrap(many_rows_one_cluster, reps=200)
        _d2, ci2 = tb.cluster_bootstrap(many_clusters, reps=200)
        self.assertEqual(ci1[0], ci1[1], "a single cluster cannot vary")
        self.assertGreater(ci2[1] - ci2[0], 0.0)

    def test_join_components_are_transitive(self):
        """A+B and B+C are one physical object, so they must be one cluster."""
        meta = {frozenset(("a", "b")): {}, frozenset(("b", "c")): {}}
        comps = tb.join_components(meta)
        self.assertEqual(comps["a"], comps["c"])

    def test_join_components_separate_unrelated_objects(self):
        meta = {frozenset(("a", "b")): {}, frozenset(("x", "y")): {}}
        comps = tb.join_components(meta)
        self.assertNotEqual(comps["a"], comps["x"])

    def test_join_components_survive_a_degenerate_pair(self):
        """Two corpus rows give both members the same siglum, so the pair
        frozenset collapses to one element. That crashed the first run. The
        real fix drops such pairs upstream, but the graph builder must not be
        the thing that explodes if one ever reaches it."""
        meta = {frozenset(("a", "b")): {}, frozenset(("solo",)): {}}
        comps = tb.join_components(meta)
        self.assertEqual(comps["a"], comps["b"])


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestScopeSelection(unittest.TestCase):

    def test_unresolved_query_language_has_no_query_relative_rendering(self):
        """§3.3 fails closed rather than assigning a majority language."""
        row = {"language": tb.UNRESOLVED}
        self.assertIsNone(tb.scope_key_for(row, "SAME_LANGUAGE_AS_QUERY"))

    def test_fixed_scope_key_ignores_query_language(self):
        row = {"language": tb.UNRESOLVED}
        self.assertEqual(tb.scope_key_for(row, "HITTITE_ONLY"), "HITTITE_ONLY")

    def test_scorable_excludes_rows_the_scope_empties(self):
        """A row the scope empties is refused, not scored as a failure."""
        rows = [{"language": "Hit", "HITTITE_ONLY": [["a", "b", "c", "d"]]},
                {"language": "Hit", "HITTITE_ONLY": [["a"]]},
                {"language": "Hit", "HITTITE_ONLY": []}]
        self.assertEqual(len(tb.scorable(rows, "HITTITE_ONLY")), 1)


if __name__ == "__main__":
    unittest.main()
