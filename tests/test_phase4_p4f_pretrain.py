"""Tests for the P4-F Stage 1 data path (lib/p4f_data.py) and the
aux-threading added to lib/hittite_model.py and lib/hittite_tokenizer.py.

The property these exist to defend is narrow and total: **the language
vector the model is conditioned on must be exactly parallel to the token
vector it describes, at every position, after every transform.** A silent
misalignment here would not crash and would not obviously degrade the loss
curve -- it would just train arm B on scrambled language labels and make
the falsifier's comparison meaningless. That is the same failure shape as
the E2 content-blind scoring bug (P5_CLOSEOUT.md Sec.2.4), which ran for an
entire phase undetected.

The no-op tests matter as much as the alignment ones: `apply_span_masking`
and `build_boundary_example` are on D14's own training path, so the added
`aux` parameter must be provably invisible when it is not used.

Skipped without torch, matching tests/test_hittite_model_p4f.py -- torch is
deliberately absent from requirements-ci.txt (Gate 3 territory).
"""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import hittite_tokenizer as ht  # noqa: E402
from decompose_corpus import RESTORED  # noqa: E402

try:
    import torch  # noqa: F401
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    import p4f_data as p4f
    from hittite_model import apply_span_masking, build_boundary_example


SPECIALS_FOR_TEST = {0, 1, 2, 3}  # pad/unk/mask/gap stand-ins
MASK_ID, GAP_ID = 2, 3


def _tokens(n, start=10):
    return list(range(start, start + n))


class TestStructuredSequenceRefactorIsANoOp(unittest.TestCase):
    """`build_structured_sequence_attested` now delegates to
    `iter_structured_attested`. The emitted token sequence feeds the frozen
    D14 vocabulary, so the refactor must be output-identical, not merely
    output-equivalent-looking."""

    def setUp(self):
        # Two lines, mixed damage states, with left/right physical edges --
        # exercises every emit branch in the traversal.
        self.line_index = {
            ("doc1", 0): [("a", "attested"), ("b", RESTORED), ("c", "attested")],
            ("doc1", 1): [("d", "attested"), ("e", "attested")],
        }
        self.args = ("doc1", [0, 1], self.line_index, False, False,
                     {0: "left", 1: "right"})

    def test_emits_expected_sequence(self):
        seq = ht.build_structured_sequence_attested(*self.args)
        self.assertEqual(
            seq,
            ["<EDGE_T>", "<EDGE_L>", "a", "c", "<LINE>", "d", "e", "<EDGE_R>",
             "<EDGE_B>"])

    def test_iterator_and_builder_agree(self):
        seq = ht.build_structured_sequence_attested(*self.args)
        from_iter = [t for t, _, _ in ht.iter_structured_attested(*self.args)]
        self.assertEqual(seq, from_iter)

    def test_word_pos_counts_restored_tokens(self):
        """`word_pos` must be the position in the FULL line, not the
        restored-filtered one -- the Gate 2 language dataset is keyed by the
        full sequence, so counting after the filter would shift every
        language lookup on any line containing a restoration."""
        emitted = [(t, li, wp) for t, li, wp in
                   ht.iter_structured_attested(*self.args) if li is not None]
        self.assertEqual(
            emitted,
            [("a", 0, 0), ("c", 0, 2), ("d", 1, 0), ("e", 1, 1)])

    def test_emptied_lines_preserve_separator_slots(self):
        seq = [t for t, _, _ in ht.iter_structured_attested(
            *self.args, emptied_lines={0})]
        self.assertEqual(
            seq, ["<EDGE_T>", "<EDGE_L>", "<LINE>", "d", "e", "<EDGE_R>",
                  "<EDGE_B>"])
        # The <LINE> separator survives: line-position numbering elsewhere
        # depends on every slot staying present.
        self.assertEqual(seq.count("<LINE>"), 1)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
class TestSpanMaskingAuxIsAligned(unittest.TestCase):

    def _run(self, seed, aux=None):
        rng = random.Random(seed)
        return apply_span_masking(
            _tokens(60), MASK_ID, GAP_ID, 100, SPECIALS_FOR_TEST,
            [1, 2, 3, 4], rng, 0.15, 0.3, 20, aux=aux)

    def test_without_aux_returns_unchanged_two_tuple(self):
        for seed in range(25):
            out = self._run(seed)
            self.assertEqual(len(out), 2)

    def test_aux_does_not_change_ids_or_labels(self):
        """The added parameter must not perturb the RNG draw sequence or the
        masking decisions -- otherwise arm A and arm B would diverge for a
        reason that has nothing to do with conditioning."""
        for seed in range(25):
            ids_a, labels_a = self._run(seed)
            ids_b, labels_b, _aux = self._run(seed, aux=_tokens(60, start=1000))
            self.assertEqual(ids_a, ids_b, f"seed {seed}")
            self.assertEqual(labels_a, labels_b, f"seed {seed}")

    def test_aux_is_filtered_by_the_same_predicate(self):
        """Gap-collapse deletes positions. The surviving aux entries must be
        exactly the ones whose tokens survived, in order."""
        for seed in range(50):
            aux = [1000 + i for i in range(60)]
            ids, labels, kept_aux = self._run(seed, aux=aux)
            self.assertEqual(len(ids), len(kept_aux), f"seed {seed}")
            # Reconstruct which original indices survived: an unmasked,
            # un-collapsed position keeps its original token id.
            for token_id, aux_value in zip(ids, kept_aux):
                if token_id not in (MASK_ID, GAP_ID):
                    self.assertEqual(
                        aux_value - 1000, token_id - 10,
                        f"seed {seed}: aux drifted from its token")

    def test_length_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            self._run(0, aux=[0, 1, 2])


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
class TestBoundaryExampleAuxIsAligned(unittest.TestCase):

    def _pool_item(self, cth, n=80, start=500):
        return {"cth": cth, "genre_band": "g", "ids": _tokens(n, start),
                "lang_ids": [start + 1000 + i for i in range(n)]}

    def _run(self, seed, with_aux):
        tokens = _tokens(200, 10)
        aux = [1000 + i for i in range(200)]
        rng = random.Random(seed)
        pools = {"cross_genre": ([self._pool_item("other")], "mine"),
                 "random": ([self._pool_item("other2", start=700)], "mine")}
        kwargs = {"aux": aux, "aux_key": "lang_ids"} if with_aux else {}
        return build_boundary_example(
            tokens, 100, [40, 100, 160], rng, pools, window=32, **kwargs)

    def test_without_aux_returns_unchanged_four_tuple(self):
        for seed in range(30):
            out = self._run(seed, with_aux=False)
            if out is not None:
                self.assertEqual(len(out), 4)

    def test_aux_does_not_change_the_token_result(self):
        for seed in range(30):
            plain = self._run(seed, with_aux=False)
            withaux = self._run(seed, with_aux=True)
            if plain is None:
                self.assertIsNone(withaux)
                continue
            self.assertEqual(plain, withaux[:4], f"seed {seed}")

    def test_aux_slices_match_their_token_slices(self):
        for seed in range(60):
            out = self._run(seed, with_aux=True)
            if out is None:
                continue
            ctx, cont, _label, tier, aux_ctx, aux_cont = out
            self.assertEqual(len(ctx), len(aux_ctx), f"seed {seed} ctx")
            self.assertEqual(len(cont), len(aux_cont), f"seed {seed} cont")
            # Source document: ids are 10+i and aux is 1000+i, so every
            # correctly-aligned pair sits at a constant offset of 990.
            for token, aux_value in zip(ctx, aux_ctx):
                self.assertEqual(aux_value - token, 990, f"seed {seed} ctx")
            # A continuation drawn from the SAME document keeps that offset;
            # a cross-document negative must carry the OTHER document's
            # languages (offset 1000 by construction of _pool_item), which
            # is the entire reason aux_key exists.
            expected = 990 if tier in ("true_continuation", "in_doc") else 1000
            for token, aux_value in zip(cont, aux_cont):
                self.assertEqual(aux_value - token, expected,
                                 f"seed {seed} cont tier={tier}")


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
class TestRenderExampleWithLanguages(unittest.TestCase):
    """The join between the rendering traversal and the Gate 2 language
    dataset, exercised against a stub index with the real interface."""

    class StubIndex:
        def __init__(self, langs, admit=True):
            self.langs = langs          # (doc, line) -> [(lang, is_struct)]
            self.admit = admit
            self.decisions = []

        def line_decision(self, scope, doc_id, line_idx, *, n_source_tokens):
            self.decisions.append((doc_id, line_idx, n_source_tokens))

            class D:
                in_scope = self.admit
            return D()

        def token_language(self, doc_id, line_idx, word_pos):
            return self.langs[(doc_id, line_idx)][word_pos]

    def setUp(self):
        self.line_index = {
            ("d", 0): [("a", "attested"), ("b", RESTORED), ("c", "attested")],
            ("d", 1): [("e", "attested")],
        }
        self.scope = p4f.build_data_admission_scope()

    def test_languages_are_parallel_and_specials_are_unresolved(self):
        index = self.StubIndex({
            ("d", 0): [("Hit", False), ("Hit", False), ("Akk", False)],
            ("d", 1): [("Hur", False)],
        })
        tokens, lang_ids = p4f.render_example_with_languages(
            "d", [0, 1], self.line_index, False, False, {},
            admission_scope=self.scope, language_index=index)
        self.assertEqual(tokens, ["<EDGE_T>", "a", "c", "<LINE>", "e", "<EDGE_B>"])
        self.assertEqual(len(tokens), len(lang_ids))
        from hittite_model_p4f import LANGUAGE_TO_ID as L
        self.assertEqual(lang_ids, [
            L["<UNRESOLVED>"],  # <EDGE_T>
            L["Hit"],           # a  (word_pos 0)
            L["Akk"],           # c  (word_pos 2 -- skipped the restored 'b')
            L["<UNRESOLVED>"],  # <LINE>
            L["Hur"],           # e
            L["<UNRESOLVED>"],  # <EDGE_B>
        ])

    def test_structural_tokens_in_the_dataset_are_unresolved(self):
        index = self.StubIndex({
            ("d", 0): [("Hit", True), ("Hit", False), ("Hit", True)],
            ("d", 1): [("Hit", False)],
        })
        _tokens_out, lang_ids = p4f.render_example_with_languages(
            "d", [0, 1], self.line_index, False, False, {},
            admission_scope=self.scope, language_index=index)
        from hittite_model_p4f import LANGUAGE_TO_ID as L
        self.assertEqual(lang_ids[1], L["<UNRESOLVED>"])  # is_structural
        self.assertEqual(lang_ids[2], L["<UNRESOLVED>"])  # is_structural

    def test_refused_line_contributes_no_tokens(self):
        index = self.StubIndex({}, admit=False)
        tokens, lang_ids = p4f.render_example_with_languages(
            "d", [0, 1], self.line_index, False, False, {},
            admission_scope=self.scope, language_index=index)
        self.assertEqual(tokens, ["<EDGE_T>", "<LINE>", "<EDGE_B>"])
        self.assertEqual(len(tokens), len(lang_ids))

    def test_admission_is_asked_with_the_full_source_token_count(self):
        """`line_decision` refuses a line whose token count disagrees with
        the language dataset (the archive-stem conflation guard). Passing a
        restored-filtered count would make that guard fire on every line
        containing a restoration."""
        index = self.StubIndex({
            ("d", 0): [("Hit", False)] * 3, ("d", 1): [("Hit", False)]})
        p4f.render_example_with_languages(
            "d", [0, 1], self.line_index, False, False, {},
            admission_scope=self.scope, language_index=index)
        self.assertIn(("d", 0, 3), index.decisions)  # 3, not 2
        self.assertIn(("d", 1, 1), index.decisions)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed")
class TestScopeSeparation(unittest.TestCase):
    def test_data_admission_scope_is_not_an_ablation_scope(self):
        """If data admission ever ran under ALL_LANGUAGES_UNCONDITIONED, the
        ablation short-circuit in language_lookup_v2._classify would admit
        the unresolved and conflated lines that the conditioned arm refuses,
        silently giving the two arms different training data."""
        scope = p4f.build_data_admission_scope()
        self.assertEqual(scope.scope, "MULTILINGUAL_CONDITIONED")
        self.assertFalse(scope.is_ablation)


if __name__ == "__main__":
    unittest.main()


class TestRunTaskAPrecomputedScores(unittest.TestCase):
    """The withdrawn-rung screen (reports/phase5_ladder_screen_protocol.md)
    scores frozen-embedding candidates through run_task_a's precomputed path
    so that the candidate and the BM25 reference go through ONE ranking
    implementation. If that path ever diverges from the BM25 path on the same
    scores, the screen stops comparing like with like."""

    def setUp(self):
        import eval_harness as eh
        self.eh = eh
        self.ids = ["a", "b", "c", "d"]
        self.toks = [["x", "y"], ["x", "z"], ["p", "q"], ["p", "r"]]
        self.parent = ["d1", "d2", "d3", "d4"]
        self.cth = ["C1", "C1", "C2", "C2"]

    def _args(self):
        return (self.ids, self.toks, self.parent, self.cth,
                self.ids, self.toks, self.parent, self.cth)

    def test_precomputed_bm25_matrix_reproduces_the_bm25_path(self):
        pq1, a1 = self.eh.run_task_a(*self._args(), method="bm25")
        matrix, _ = self.eh.bm25_score_matrix(self.toks, self.toks)
        pq2, a2 = self.eh.run_task_a(*self._args(),
                                     precomputed_scores=matrix.toarray())
        self.assertEqual(pq1, pq2)
        self.assertEqual(a1, a2)

    def test_wrong_shape_fails_closed(self):
        import numpy as np
        with self.assertRaises(ValueError):
            self.eh.run_task_a(*self._args(),
                               precomputed_scores=np.zeros((3, 4)))


class TestRunRetrievalPrecomputedScores(unittest.TestCase):
    """Same guarantee for Task B (reports/phase5_combiner_taskb_protocol.md).
    run_retrieval carries self-exclusion and the H1 same-family exclusion, so
    a combiner must reach those through the same code BM25 does rather than
    through a second ranking implementation."""

    def setUp(self):
        import eval_harness as eh
        self.eh = eh
        self.ids = ["a", "b", "c", "d"]
        self.toks = [["x", "y"], ["x", "z"], ["p", "q"], ["p", "r"]]
        self.pos = {"a": {"b"}, "b": {"a"}, "c": {"d"}, "d": {"c"}}

    def test_precomputed_bm25_matrix_reproduces_the_bm25_path(self):
        pq1, a1 = self.eh.run_retrieval(self.ids, self.toks, self.ids,
                                        self.toks, self.pos, method="bm25")
        matrix, _ = self.eh.bm25_score_matrix(self.toks, self.toks)
        pq2, a2 = self.eh.run_retrieval(self.ids, self.toks, self.ids,
                                        self.toks, self.pos,
                                        precomputed_scores=matrix.toarray())
        self.assertEqual(pq1, pq2)
        self.assertEqual(a1, a2)

    def test_wrong_shape_fails_closed(self):
        import numpy as np
        with self.assertRaises(ValueError):
            self.eh.run_retrieval(self.ids, self.toks, self.ids, self.toks,
                                  self.pos, precomputed_scores=np.zeros((3, 9)))
