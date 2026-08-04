"""Tests for scripts/phase5_factorial_control.py
(reports/phase5_factorial_control_protocol.md, PRE-REGISTERED 2026-08-04).

The invariant worth the most here is **C1: segmentation must be inert for
bag-of-token channels**. The protocol defines a rendering as the segment
inside which a feature may form, so BM25 and unigram TF-IDF -- which are bags
of tokens -- must be bit-identical between LEGACY and BOUNDARY. The first
implementation failed this by up to 0.136 cosine, because vectorizing per
segment silently moved document frequency from a per-fragment to a per-line
estimate. That would have made the rendering factor measure two things at
once and no result would have been attributable to either. The fix (count per
segment, weight per fragment) is what these tests pin.

Importing the script pulls in torch via phase5_bm25_combiner, which
requirements-ci.txt deliberately omits; skipped when unavailable, like the
P4-F, combiner and statistics-universe tests.
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
    import eval_harness as eh
    import phase5_bm25_combiner as comb
    import phase5_factorial_control as fc


def _row(fid, cth, lines, split="dev"):
    """A fragment whose three renderings are stated explicitly. SCOPED here
    drops the last line, standing in for a language refusal."""
    flat = [t for line in lines for t in line]
    return {
        "fragment_id": fid, "parent_doc": fid, "cth": cth,
        "main_split": split, "tokens": flat,
        "LEGACY": [flat] if flat else [],
        "BOUNDARY": [list(line) for line in lines],
        "SCOPED": [list(line) for line in lines[:-1]] if len(lines) > 1 else
                  [list(line) for line in lines],
    }


def _rows():
    return [
        _row("f1", 1, [["a", "b", "c"], ["d", "e", "f"]]),
        _row("f2", 1, [["a", "b", "x"], ["d", "e", "y"]]),
        _row("f3", 2, [["p", "q", "r"], ["s", "t", "u"]]),
        _row("f4", 2, [["p", "q", "z"], ["s", "t", "w"]]),
    ]


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestPreRegisteredConstants(unittest.TestCase):
    """Changing one of these invalidates the reported verdict."""

    def test_factors_match_protocol(self):
        self.assertEqual(fc.RENDERINGS, ["LEGACY", "BOUNDARY", "SCOPED"])
        self.assertEqual(fc.CHANNELS, [
            "unigram_tfidf", "bigram_only_tfidf", "unigram_plus_bigram_tfidf",
            "char_within_sign", "char_across_sign"])
        self.assertEqual(fc.CONDITIONAL_CHANNELS, [
            "bigram_only_tfidf", "char_within_sign", "char_across_sign"])
        self.assertEqual(fc.PRIMARY_RENDERING, "SCOPED")
        self.assertEqual(fc.BASE_CHANNEL, "unigram_tfidf")
        self.assertEqual(fc.DECISION_MARGIN, 0.010)

    def test_both_weight_grids_contain_zero(self):
        """Zero in both grids is what makes each arm's family strictly contain
        its own reference, so an increment is attributable to the added
        channel rather than to reparameterization."""
        self.assertIn(0.0, comb.ALPHA_GRID)
        self.assertIn(0.0, fc.SECOND_GRID)
        self.assertEqual(min(fc.SECOND_GRID), 0.0)

    def test_conditional_set_excludes_the_channel_containing_the_base(self):
        """unigram_plus_bigram contains the base channel, so its 'increment
        over unigram' would not isolate anything."""
        self.assertNotIn("unigram_plus_bigram_tfidf", fc.CONDITIONAL_CHANNELS)


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestC1SegmentationInertForBags(unittest.TestCase):
    """The check that caught the document-frequency confound."""

    def test_bm25_identical_across_segmentation(self):
        rows = _rows()
        a = fc.bm25_similarity(rows, rows, "LEGACY")
        b = fc.bm25_similarity(rows, rows, "BOUNDARY")
        np.testing.assert_allclose(a, b)

    def test_unigram_identical_across_segmentation(self):
        rows = _rows()
        a = fc.channel_similarity(rows, rows, "LEGACY", "unigram_tfidf")
        b = fc.channel_similarity(rows, rows, "BOUNDARY", "unigram_tfidf")
        np.testing.assert_allclose(a, b, atol=1e-12)

    def test_bigram_channel_is_not_segmentation_invariant(self):
        """The converse: if bigrams did NOT change, segmentation would not be
        doing the one job it exists to do."""
        rows = _rows()
        a = fc.channel_similarity(rows, rows, "LEGACY", "bigram_only_tfidf")
        b = fc.channel_similarity(rows, rows, "BOUNDARY", "bigram_only_tfidf")
        self.assertFalse(np.allclose(a, b))


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestSegmentFeatures(unittest.TestCase):

    def test_no_bigram_spans_a_segment_boundary(self):
        """C4, stated directly: the cross-line pair must be absent."""
        rows = _rows()
        docs, _owner = fc._segment_docs(rows[:1], "BOUNDARY", "bigram_only_tfidf")
        produced = {t for doc in docs for t in doc}
        self.assertIn("a␟b", produced)
        self.assertNotIn("c␟d", produced,
                         "a bigram joined the end of line 1 to the start of "
                         "line 2, which boundary-preserving rendering forbids")

    def test_flat_rendering_does_span_the_boundary(self):
        rows = _rows()
        docs, _owner = fc._segment_docs(rows[:1], "LEGACY", "bigram_only_tfidf")
        produced = {t for doc in docs for t in doc}
        self.assertIn("c␟d", produced,
                      "LEGACY is the rendering whose cross-line bigrams the "
                      "protocol exists to measure")

    def test_bigram_only_channel_carries_no_unigrams(self):
        rows = _rows()
        docs, _owner = fc._segment_docs(rows[:1], "BOUNDARY", "bigram_only_tfidf")
        produced = {t for doc in docs for t in doc}
        self.assertTrue(all("␟" in t for t in produced))

    def test_unigram_plus_bigram_carries_both(self):
        rows = _rows()
        docs, _owner = fc._segment_docs(
            rows[:1], "BOUNDARY", "unigram_plus_bigram_tfidf")
        produced = {t for doc in docs for t in doc}
        self.assertIn("a", produced)
        self.assertIn("a␟b", produced)

    def test_add_bigrams_split_point_is_correct(self):
        """bigram_only slices add_bigrams()'s output; if the harness ever
        changed its ordering, the channel would silently become unigrams."""
        seg = ["a", "b", "c"]
        self.assertEqual(eh.add_bigrams(seg)[len(seg):],
                         ["a␟b", "b␟c"])


@unittest.skipUnless(TORCH_AVAILABLE, "torch not installed (not in requirements-ci.txt)")
class TestCharacterChannels(unittest.TestCase):

    def test_within_sign_cannot_see_across_a_sign_boundary(self):
        """The partial-sign hypothesis needs the two channels to actually
        differ in what they can match. Two fragments sharing a cross-sign
        string but no within-sign 4-gram must look more similar to the
        across-sign channel."""
        rows = [
            _row("g1", 1, [["abcd", "efgh"]]),
            _row("g2", 1, [["abcd", "efgh"]]),
            _row("g3", 2, [["zzcd", "efzz"]]),
            _row("g4", 2, [["zzcd", "efzz"]]),
        ]
        across = fc.channel_similarity(rows, rows, "LEGACY", "char_across_sign")
        within = fc.channel_similarity(rows, rows, "LEGACY", "char_within_sign")
        # "d ef" spans the space between two signs; only char_across can hold it.
        self.assertGreater(across[0, 2], within[0, 2])


if __name__ == "__main__":
    unittest.main()
