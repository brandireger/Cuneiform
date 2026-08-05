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
class TestC5CrossFitting(unittest.TestCase):
    """The corrected C5.

    The first run searched weights out of fold, discarded the held-out
    predictions, took the MODAL weights over all five folds and re-scored all
    of dev -- so every query was scored under weights partly chosen using its
    own fold. C5 now asserts the fold-local invariant instead: within a fold,
    one weight pair serves every cell; across folds they may differ, and
    demanding a single global weight is exactly the defect."""

    def test_constant_within_fold_passes(self):
        per_fold = [
            {"fold": 0, "alpha_unigram_only": 0.5, "alpha_pair": [0.1, 1.0],
             "weights_by_cell": {
                 "joins": {"alpha_unigram_only": 0.5, "alpha_pair": [0.1, 1.0]},
                 "duplicates": {"alpha_unigram_only": 0.5, "alpha_pair": [0.1, 1.0]}}},
            {"fold": 1, "alpha_unigram_only": 0.75, "alpha_pair": [0.4, 0.4],
             "weights_by_cell": {
                 "joins": {"alpha_unigram_only": 0.75, "alpha_pair": [0.4, 0.4]},
                 "duplicates": {"alpha_unigram_only": 0.75, "alpha_pair": [0.4, 0.4]}}},
        ]
        res = tb.check_c5_weights_constant_within_fold(per_fold)
        self.assertTrue(res["passed"],
                        "weights differing ACROSS folds is what cross-fitting "
                        "looks like and must not fail C5")

    def test_differing_weights_within_one_fold_fails(self):
        per_fold = [
            {"fold": 0, "alpha_unigram_only": 0.5, "alpha_pair": [0.1, 1.0],
             "weights_by_cell": {
                 "joins": {"alpha_unigram_only": 0.5, "alpha_pair": [0.1, 1.0]},
                 "duplicates": {"alpha_unigram_only": 0.9, "alpha_pair": [0.9, 0.2]}}},
        ]
        res = tb.check_c5_weights_constant_within_fold(per_fold)
        self.assertFalse(res["passed"])
        self.assertEqual(res["offenders"][0]["fold"], 0)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestTierCPairInstances(unittest.TestCase):
    """A fragment with two Tier C partners must yield two instances with
    DIFFERENT exclusive renderings, not one that overwrites the other."""

    def _fixture(self):
        rows_by_id = {}
        for fid in ("P::1", "P::2", "P::3"):
            rows_by_id[fid] = {
                "fragment_id": fid, "language": "Hit",
                "by_line": {0: ["a"], 1: ["b"], 2: ["c"]},
                "HITTITE_ONLY::lines": [0, 1, 2],
                "HITTITE_ONLY": [["a"], ["b"], ["c"]],
            }
        meta = {
            frozenset(("P::1", "P::2")): {
                "tier": "C", "fragment_id_a": "P::1", "fragment_id_b": "P::2",
                "exclusive_untestable": False},
            frozenset(("P::1", "P::3")): {
                "tier": "C", "fragment_id_a": "P::1", "fragment_id_b": "P::3",
                "exclusive_untestable": False},
        }
        reconstructed = {"P": {"member_lines": {
            "1": [{"line_idx": 0, "shared_with": ["2"]},
                  {"line_idx": 1, "shared_with": ["3"]},
                  {"line_idx": 2, "shared_with": []}],
            "2": [{"line_idx": 0, "shared_with": ["1"]},
                  {"line_idx": 2, "shared_with": []}],
            "3": [{"line_idx": 1, "shared_with": ["1"]},
                  {"line_idx": 2, "shared_with": []}],
        }}}
        return rows_by_id, meta, reconstructed

    def test_a_shared_fragment_gets_partner_specific_renderings(self):
        rows_by_id, meta, rec = self._fixture()
        instances, counts = tb.tier_c_pair_instances(
            rows_by_id, meta, rec, "HITTITE_ONLY")
        self.assertEqual(counts["usable"], 2)
        by_partner = {(i["a"], i["b"]): i for i in instances}
        # vs P::2 the shared line is 0, so line 0 must be excluded but 1 kept;
        # vs P::3 the shared line is 1, so the opposite.
        segs_vs2 = by_partner[("P::1", "P::2")]["segs_a"]
        segs_vs3 = by_partner[("P::1", "P::3")]["segs_a"]
        self.assertNotEqual(segs_vs2, segs_vs3,
                            "P::1's exclusive rendering must depend on WHICH "
                            "partner it is being scored against")
        self.assertIn(["b"], segs_vs2)
        self.assertNotIn(["a"], segs_vs2)
        self.assertIn(["a"], segs_vs3)
        self.assertNotIn(["b"], segs_vs3)

    def test_single_partner_instances_are_counted_separately(self):
        rows_by_id, meta, rec = self._fixture()
        instances, counts = tb.tier_c_pair_instances(
            rows_by_id, meta, rec, "HITTITE_ONLY")
        # P::1 has two partners, so neither instance is single-partner.
        self.assertEqual(counts["usable_single_partner_only"], 0)
        self.assertFalse(any(i["single_partner"] for i in instances))


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestQueryRelativePopulation(unittest.TestCase):
    """The third amendment.

    Both query-relative scopes originally selected queries AND candidates under
    each fragment's OWN resolved language. For CROSS_LANGUAGE_PARALLEL that
    tested a monolingual query for content in a language it does not contain,
    which reported zero evaluable queries while the ceiling code simultaneously
    found thousands of reachable targets. Given how many population-construction
    defects this line has produced, each rule is pinned separately."""

    def _rows(self):
        def frag(fid, lang, hit_lines, akk_lines, split="dev"):
            r = {"fragment_id": fid, "parent_doc": fid, "cth": 1,
                 "main_split": split, "language": lang,
                 "SAME_LANGUAGE_AS_QUERY::Hit": hit_lines,
                 "SAME_LANGUAGE_AS_QUERY::Akk": akk_lines,
                 "CROSS_LANGUAGE_PARALLEL::Hit": akk_lines,
                 "CROSS_LANGUAGE_PARALLEL::Akk": hit_lines}
            return r
        four = [["a", "b", "c", "d"]]
        return {
            # monolingual Hittite query: plenty of Hit, no Akk
            "qh": frag("qh", "Hit", four, []),
            # fragment-level UNRESOLVED candidate that still has ample Hittite
            "cmix": frag("cmix", tb.UNRESOLVED, four, four, split="train"),
            # pure Akkadian candidate
            "cakk": frag("cakk", "Akk", [], four, split="train"),
            # unresolved QUERY -- must be refused outright
            "qmix": frag("qmix", tb.UNRESOLVED, four, four),
        }

    def test_query_is_rendered_in_its_own_language(self):
        rows = self._rows()
        self.assertEqual(tb.query_rendering_key(rows["qh"]),
                         "SAME_LANGUAGE_AS_QUERY::Hit")

    def test_unresolved_query_is_refused(self):
        rows = self._rows()
        self.assertIsNone(tb.query_rendering_key(rows["qmix"]))

    def test_candidate_key_follows_the_query_language(self):
        self.assertEqual(
            tb.candidate_rendering_key("CROSS_LANGUAGE_PARALLEL", "Hit"),
            "CROSS_LANGUAGE_PARALLEL::Hit")
        self.assertEqual(
            tb.candidate_rendering_key("SAME_LANGUAGE_AS_QUERY", "Akk"),
            "SAME_LANGUAGE_AS_QUERY::Akk")
        # fixed scopes ignore the query language entirely
        self.assertEqual(
            tb.candidate_rendering_key("HITTITE_ONLY", "Akk"), "HITTITE_ONLY")

    def test_unresolved_candidate_with_enough_query_language_content_is_eligible(self):
        """The point of amendment (b): a fragment that resolves to no single
        language may still answer a Hittite query with its Hittite lines."""
        rows = self._rows()
        dev = [rows["qh"]]
        labeled = [rows["cmix"], rows["cakk"]]
        base_pos = {"joins": {}, "duplicates": {"qh": {"cmix"}},
                    "pooled": {"qh": {"cmix"}}}
        groups = tb.build_language_groups(dev, labeled,
                                          "SAME_LANGUAGE_AS_QUERY", base_pos)
        hit = [g for g in groups if g["language"] == "Hit"][0]
        cand_ids = {r["fragment_id"] for r in hit["c_rows"]}
        self.assertIn("cmix", cand_ids,
                      "an unresolved candidate with ample Hittite content must "
                      "remain eligible for a Hittite query")
        self.assertNotIn("cakk", cand_ids)

    def test_cross_language_flips_which_candidates_are_eligible(self):
        rows = self._rows()
        dev = [rows["qh"]]
        labeled = [rows["cmix"], rows["cakk"]]
        base_pos = {"joins": {}, "duplicates": {"qh": {"cakk"}},
                    "pooled": {"qh": {"cakk"}}}
        groups = tb.build_language_groups(dev, labeled,
                                          "CROSS_LANGUAGE_PARALLEL", base_pos)
        hit = [g for g in groups if g["language"] == "Hit"][0]
        cand_ids = {r["fragment_id"] for r in hit["c_rows"]}
        self.assertIn("cakk", cand_ids)
        # the query itself is still selected by its OWN-language rendering
        self.assertEqual(hit["qkey"], "SAME_LANGUAGE_AS_QUERY::Hit")
        self.assertEqual(hit["ckey"], "CROSS_LANGUAGE_PARALLEL::Hit")
        self.assertEqual([r["fragment_id"] for r in hit["q_rows"]], ["qh"])

    def test_query_without_a_reachable_positive_is_dropped(self):
        rows = self._rows()
        dev = [rows["qh"]]
        labeled = [rows["cakk"]]          # only an Akkadian candidate
        base_pos = {"joins": {}, "duplicates": {"qh": {"cmix"}},
                    "pooled": {"qh": {"cmix"}}}   # target not in the universe
        groups = tb.build_language_groups(dev, labeled,
                                          "SAME_LANGUAGE_AS_QUERY", base_pos)
        hit = [g for g in groups if g["language"] == "Hit"][0]
        self.assertEqual(hit["q_rows"], [])
        self.assertEqual(hit["n_eligible_queries"], 1,
                         "eligibility and reachability are reported separately")


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestTaskAScopeMatching(unittest.TestCase):

    def test_matching_step2_rendering_per_scope(self):
        self.assertEqual(tb.TASK_A_RENDERING_FOR["HITTITE_ONLY"], "SCOPED")
        self.assertEqual(
            tb.TASK_A_RENDERING_FOR["ALL_LANGUAGES_UNCONDITIONED"], "BOUNDARY")

    def test_query_relative_scopes_get_no_arm(self):
        """No matching Step 2 arm exists, so transporting a Hittite-scoped
        configuration there would be a different claim."""
        for s in tb.QUERY_RELATIVE_SCOPES:
            self.assertIsNone(tb.TASK_A_RENDERING_FOR[s])
            self.assertIsNone(tb.load_task_a_frozen(tb.TASK_A_RENDERING_FOR[s]))


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestCommonPopulationAndFinalSystem(unittest.TestCase):

    def test_cross_language_is_outside_the_common_comparison(self):
        """§3.2. Letting the assistance channel in would collapse the per-cell
        intersection onto its small asymmetric population."""
        self.assertNotIn("CROSS_LANGUAGE_PARALLEL", tb.COMMON_POPULATION_SCOPES)
        self.assertEqual(tb.COMMON_POPULATION_SCOPES,
                         ["HITTITE_ONLY", "ALL_LANGUAGES_UNCONDITIONED",
                          "SAME_LANGUAGE_AS_QUERY"])

    def test_final_system_comparison_uses_identical_query_ids(self):
        frozen = {"a": {"recall@1": 1}, "b": {"recall@1": 0},
                  "only_in_frozen": {"recall@1": 1}}
        fitted = {"a": {"recall@1": 0}, "b": {"recall@1": 0},
                  "only_in_fitted": {"recall@1": 1}}
        clusters = {"a": "c1", "b": "c2"}
        res = tb.paired_final_system(frozen, fitted, clusters)
        self.assertEqual(res["n_paired"], 2,
                         "queries present in only one arm must be dropped")
        self.assertAlmostEqual(res["delta_frozen_minus_fitted"], 0.5)
        self.assertIn("NOT a comparison of within-arm increments",
                      res["estimand"])

    def test_final_system_comparison_returns_none_without_overlap(self):
        self.assertIsNone(tb.paired_final_system(
            {"a": {"recall@1": 1}}, {"b": {"recall@1": 1}}, {}))


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
