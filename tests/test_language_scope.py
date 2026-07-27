"""P4-D: the language-scope calling convention must fail closed.

These tests exist because the pre-Phase-4 convention did NOT fail closed --
`line_lang_lookup=None` silently restored language-blind behavior for any
caller that forgot the argument. Each test below pins one way that defect
could come back.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import language_layers_v2 as llv2  # noqa: E402
import language_lookup_v2 as llookup  # noqa: E402
import language_scope as ls  # noqa: E402

CONTRACT = llv2.load_language_contract(ROOT / "configs" / "language_layers_v2.json")


def scope(name, **kwargs):
    return ls.build_language_scope(name, contract=CONTRACT, **kwargs)


class TestLanguageScopeConstruction(unittest.TestCase):
    def test_permissive_scope_names_are_refused(self):
        for name in (None, "auto", "default", "language_blind"):
            with self.assertRaises(ls.LanguageScopeError):
                scope(name)

    def test_unknown_scope_name_is_refused(self):
        with self.assertRaises(ls.LanguageScopeError):
            scope("HITTITE")

    def test_query_relative_scopes_require_a_resolved_query_language(self):
        for name in ("SAME_LANGUAGE_AS_QUERY", "CROSS_LANGUAGE_PARALLEL"):
            with self.assertRaises(ls.LanguageScopeError):
                scope(name)
            with self.assertRaises(ls.LanguageScopeError):
                scope(name, query_language="Klingon")
            self.assertTrue(scope(name, query_language="Hit").is_query_relative)

    def test_non_query_scopes_refuse_a_query_language(self):
        with self.assertRaises(ls.LanguageScopeError):
            scope("HITTITE_ONLY", query_language="Hit")

    def test_unknown_mixed_line_policy_is_refused(self):
        with self.assertRaises(ls.LanguageScopeError):
            scope("HITTITE_ONLY", mixed_line_policy="SPLICE_TOKENS")

    def test_manifest_entry_names_the_rule_and_ablation_status(self):
        entry = scope("HITTITE_ONLY").manifest_entry()
        self.assertEqual(entry["language_scope"], "HITTITE_ONLY")
        self.assertEqual(entry["language_rule_id"], "word_override_else_line_v2")
        self.assertFalse(entry["ablation_only"])
        self.assertTrue(
            scope("ALL_LANGUAGES_UNCONDITIONED").manifest_entry()["ablation_only"])


class TestRequireLanguageScope(unittest.TestCase):
    def test_none_is_refused_with_actionable_guidance(self):
        with self.assertRaises(ls.LanguageScopeError) as caught:
            ls.require_language_scope(None, label="unit")
        self.assertIn("build_language_scope", str(caught.exception))

    def test_a_bare_scope_name_is_refused(self):
        # The whole point of the value object: a string looks valid but has
        # never been validated against the contract.
        with self.assertRaises(ls.LanguageScopeError):
            ls.require_language_scope("HITTITE_ONLY", label="unit")

    def test_a_validated_scope_passes_through_unchanged(self):
        built = scope("HITTITE_ONLY")
        self.assertIs(ls.require_language_scope(built, label="unit"), built)


def index(lines):
    return llookup.EffectiveLanguageIndex(
        lines, source_path="test", source_sha256="0" * 64,
        n_rows=sum(len(v[0]) for v in lines.values()), n_docs=1)


class TestEffectiveLanguageIndexDecisions(unittest.TestCase):
    """Line-admission decisions under each scope."""

    def decide(self, langs, structural, scope_obj, n_source_tokens=None):
        idx = index({("d", 0): (tuple(langs), tuple(structural))})
        return idx.line_decision(
            scope_obj, "d", 0,
            n_source_tokens=(
                len(langs) if n_source_tokens is None else n_source_tokens))

    def test_pure_hittite_line_is_admitted(self):
        decision = self.decide(
            ["Hit", "Hit"], [False, False], scope("HITTITE_ONLY"))
        self.assertTrue(decision.in_scope)
        self.assertEqual(decision.sole_language, "Hit")

    def test_word_level_override_excludes_a_hittite_tagged_line(self):
        # The 5,670-case Gate 0 finding: a `Hit` LINE carrying explicit `Hur`
        # WORDS. The v1 line-granularity filter admitted this whole line.
        decision = self.decide(
            ["Hit", "Hur", "Hit"], [False, False, False],
            scope("HITTITE_ONLY"))
        self.assertFalse(decision.in_scope)
        self.assertEqual(decision.reason, llookup.REASON_MIXED)
        self.assertEqual(decision.languages, frozenset({"Hit", "Hur"}))

    def test_unresolved_language_is_never_guessed_into_scope(self):
        decision = self.decide(
            ["Hit", None], [False, False], scope("HITTITE_ONLY"))
        self.assertFalse(decision.in_scope)
        self.assertEqual(decision.reason, llookup.REASON_UNRESOLVED)

    def test_structural_tokens_are_not_lexical_language_evidence(self):
        # Gate 0 decision 6: structural specials inherit a language for
        # layout but must not make a line look multilingual.
        decision = self.decide(
            ["Hit", "Akk"], [False, True], scope("HITTITE_ONLY"))
        self.assertTrue(decision.in_scope)
        self.assertEqual(decision.n_lexical_tokens, 1)

    def test_token_count_mismatch_refuses_the_line(self):
        # The historical decomposed cache conflates archive stems under one
        # doc_id (9,940 duplicate-key rows / 28 docs). Positional language
        # lookup against a disagreeing token count must never proceed.
        decision = self.decide(
            ["Hit", "Hit"], [False, False], scope("HITTITE_ONLY"),
            n_source_tokens=5)
        self.assertFalse(decision.in_scope)
        self.assertEqual(decision.reason, llookup.REASON_TOKEN_COUNT_MISMATCH)

    def test_uncovered_line_is_refused_except_under_the_ablation(self):
        idx = index({("d", 0): (("Hit",), (False,))})
        self.assertFalse(
            idx.line_decision(
                scope("HITTITE_ONLY"), "d", 99, n_source_tokens=1).in_scope)
        self.assertTrue(
            idx.line_decision(
                scope("ALL_LANGUAGES_UNCONDITIONED"), "d", 99,
                n_source_tokens=1).in_scope)

    def test_same_language_as_query_follows_the_query_language(self):
        akkadian = scope("SAME_LANGUAGE_AS_QUERY", query_language="Akk")
        self.assertTrue(
            self.decide(["Akk"], [False], akkadian).in_scope)
        self.assertFalse(
            self.decide(["Hit"], [False], akkadian).in_scope)

    def test_cross_language_parallel_excludes_the_query_language(self):
        cross = scope("CROSS_LANGUAGE_PARALLEL", query_language="Hit")
        self.assertTrue(self.decide(["Hur"], [False], cross).in_scope)
        refused = self.decide(["Hit"], [False], cross)
        self.assertFalse(refused.in_scope)
        self.assertEqual(refused.reason, llookup.REASON_OTHER_LANGUAGE)

    def test_multilingual_conditioned_admits_any_resolved_language(self):
        conditioned = scope("MULTILINGUAL_CONDITIONED")
        self.assertTrue(
            self.decide(["Hit", "Hur"], [False, False], conditioned).in_scope)
        self.assertFalse(
            self.decide(["Hit", None], [False, False], conditioned).in_scope)

    def test_decisions_are_counted_by_reason_for_reporting(self):
        idx = index({
            ("d", 0): (("Hit",), (False,)),
            ("d", 1): (("Hur",), (False,)),
        })
        hittite = scope("HITTITE_ONLY")
        idx.line_decision(hittite, "d", 0, n_source_tokens=1)
        idx.line_decision(hittite, "d", 1, n_source_tokens=1)
        summary = idx.decision_summary()["HITTITE_ONLY"]
        self.assertEqual(summary[llookup.REASON_IN_SCOPE], 1)
        self.assertEqual(summary[llookup.REASON_OTHER_LANGUAGE], 1)


if __name__ == "__main__":
    unittest.main()
