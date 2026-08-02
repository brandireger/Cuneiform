"""Tests for the second workbench queue (reports/phase5_second_queue.md).

Two channels, two independent things that must hold: RARE_BY_RARITY must not
reintroduce the alphabetical-sort bias
reports/phase5_p4e2_queue_policy_ratification.md already found and named once
("your trace is off-formula" is a different bug; this is the "I was reading
an alphabetically sorted sample" one), and LOCAL_CONTEXT_PARALLEL's
contentless test must operate on the flanking context, not the member's own
(inherently damaged) content.
"""
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lib"))

import phase4_workbench_second_queue_export as second  # noqa: E402


def sequence_proposal(sequence, *, member_count=2, documents=1,
                       cluster_id="seq-s-00001"):
    return {
        "cluster_id": cluster_id,
        "member_occurrence_ids": [f"occ-{i}" for i in range(member_count)],
        "supporting_evidence": [{
            "type": "EXACT_NORMALIZED_SIGN_SEQUENCE",
            "sequence": sequence,
            "member_count": member_count,
            "distinct_document_count": documents,
            "languages": ["Hit"],
            "value_is_a_count_not_a_score": True,
        }],
    }


def context_proposal(left, right, *, member_count=2, documents=1,
                      cluster_id="ctx-s-00001"):
    return {
        "cluster_id": cluster_id,
        "member_occurrence_ids": [f"occ-{i}" for i in range(member_count)],
        "supporting_evidence": [{
            "type": "LOCAL_LEFT_RIGHT_CONTEXT",
            "left": left,
            "right": right,
            "context_window": 1,
            "member_count": member_count,
            "distinct_document_count": documents,
            "languages": ["Hit"],
            "value_is_a_count_not_a_score": True,
        }],
    }


class TestTiebreakIsNotAlphabetical(unittest.TestCase):
    """The regression this whole channel exists to avoid repeating."""

    def test_a_run_of_alphabetically_early_cluster_ids_is_not_all_first(self):
        """The concrete failure mode measured in practice: before this fix,
        the entire visible top of RARE_BY_RARITY was punctuation-leading
        sequences, because build_clusters() assigns cluster_id in sorted-
        bucket-key order and the old tiebreak was cluster_id itself. Give
        50 equally-ranked proposals cluster_ids in that same ascending
        order and require the ranked output to NOT reproduce it."""
        tied = [
            sequence_proposal(f"seq-{i}", documents=1, member_count=2,
                               cluster_id=f"seq-s-{i:05d}")
            for i in range(50)
        ]
        ranked_ids = [c["cluster_id"]
                      for c in sorted(tied, key=second.rarity_rank_key)]
        original_order = [c["cluster_id"] for c in tied]
        self.assertNotEqual(ranked_ids, original_order)

    def test_tiebreak_is_deterministic_across_runs(self):
        self.assertEqual(
            second.tiebreak("seq-s-00001"), second.tiebreak("seq-s-00001"))

    def test_tiebreak_does_not_correlate_with_string_order(self):
        """A regression guard with teeth: if tiebreak() is ever changed back
        to something string-order-correlated, this catches it directly
        rather than relying on a probabilistic sample."""
        ids = [f"seq-s-{i:05d}" for i in range(50)]
        by_id_order = ids
        by_tiebreak_order = sorted(ids, key=second.tiebreak)
        self.assertNotEqual(by_id_order, by_tiebreak_order)


class TestRarityRanking(unittest.TestCase):
    def test_fewer_documents_ranks_first(self):
        rare = sequence_proposal("numun", documents=1, cluster_id="c-rare")
        common = sequence_proposal("a", documents=3542, cluster_id="c-common")
        ordered = sorted([common, rare], key=second.rarity_rank_key)
        self.assertEqual(ordered[0]["cluster_id"], "c-rare")

    def test_fewer_members_breaks_a_document_count_tie(self):
        sparse = sequence_proposal(
            "numun", documents=1, member_count=2, cluster_id="c-sparse")
        repeated = sequence_proposal(
            "kalam", documents=1, member_count=8, cluster_id="c-repeated")
        ordered = sorted([repeated, sparse], key=second.rarity_rank_key)
        self.assertEqual(ordered[0]["cluster_id"], "c-sparse")


class TestContextRanking(unittest.TestCase):
    def test_more_documents_ranks_first_opposite_of_rarity(self):
        """LOCAL_CONTEXT_PARALLEL's whole point is a well-supported slot, so
        its bias is the OPPOSITE of RARE_BY_RARITY's -- this pins that the
        two were not accidentally given the same direction."""
        well_supported = context_proposal(
            "an", "an", documents=17, cluster_id="c-well-supported")
        sparse = context_proposal(
            "x", "y", documents=2, cluster_id="c-sparse")
        ordered = sorted([sparse, well_supported], key=second.context_rank_key)
        self.assertEqual(ordered[0]["cluster_id"], "c-well-supported")


class TestContextContentlessDetection(unittest.TestCase):
    """Applies the ratified character set to the CONTEXT KEY, not the
    member's own content -- unlike the first queue's contentless test, an
    unresolved occurrence's own content is inherently damaged by
    definition, so testing IT for contentlessness would exclude the entire
    channel."""

    def test_illegible_flanked_by_illegible_is_contentless(self):
        self.assertTrue(second.context_is_contentless(context_proposal("x", "x")))

    def test_real_word_on_both_sides_is_not_contentless(self):
        self.assertFalse(
            second.context_is_contentless(context_proposal("an", "zi")))

    def test_contentless_on_one_side_only_is_still_contentless(self):
        """A cluster keyed on 'flanked by a real word on the left, nothing
        legible on the right' still tells an expert only half of what the
        environment was -- excluded on either side alone, matching the
        first queue's 'nothing between them' standard for a similar
        both-sides-matter judgment."""
        self.assertTrue(
            second.context_is_contentless(context_proposal("an", "x")))
        self.assertTrue(
            second.context_is_contentless(context_proposal("x", "an")))

    def test_empty_context_is_contentless(self):
        self.assertTrue(second.context_is_contentless(context_proposal("", "an")))


class TestSourceEvidenceAccessors(unittest.TestCase):
    def test_context_accessors_read_the_right_evidence_type(self):
        proposal = context_proposal("an", "zi", documents=5, member_count=9)
        self.assertEqual(second.context_left(proposal), "an")
        self.assertEqual(second.context_right(proposal), "zi")
        self.assertEqual(second.context_distinct_document_count(proposal), 5)
        self.assertEqual(second.context_languages(proposal), ["Hit"])

    def test_context_accessors_ignore_a_sequence_evidence_proposal(self):
        """The two channels' proposals must never be silently cross-read --
        a sequence-typed proposal handed to a context accessor should read
        as empty, not raise or return the wrong field."""
        proposal = sequence_proposal("numun")
        self.assertEqual(second.context_left(proposal), "")
        self.assertEqual(second.context_right(proposal), "")


if __name__ == "__main__":
    unittest.main()
