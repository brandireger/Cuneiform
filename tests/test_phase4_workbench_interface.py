"""Tests for the P4-E2 review-queue export and expert-session ingest.

The queue's selection policy decides what a specialist is shown, so its edges
are pinned here rather than left to whatever the data happened to contain on
the day it was written. The ingest tests pin the refusals -- an ingest that
accepts a judgment about a record that has since changed would quietly
corrupt the one artifact in Phase 4 that cannot be rebuilt from the corpus.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lib"))

import phase4_workbench_ingest_events as ingest  # noqa: E402
import phase4_workbench_review_export as export  # noqa: E402
import unresolved_evidence as ue  # noqa: E402


def proposal_with(sequence, *, member_count=2, documents=2, cluster_id="c-1"):
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


class TestContentlessDetection(unittest.TestCase):
    """The placeholder families that actually occur in TLHdig 0.2."""

    def test_bare_illegible_placeholder_is_contentless(self):
        self.assertTrue(export.sequence_is_contentless(proposal_with("x")))

    def test_placeholder_runs_are_contentless(self):
        for sequence in ("x x", "x x x", "x x x x x( )x", "xx"):
            with self.subTest(sequence=sequence):
                self.assertTrue(
                    export.sequence_is_contentless(proposal_with(sequence)))

    def test_indeterminate_filler_is_contentless(self):
        for sequence in ("_", "_ _ _ _ _ _ _ _ _", "(_)", "(_)x"):
            with self.subTest(sequence=sequence):
                self.assertTrue(
                    export.sequence_is_contentless(proposal_with(sequence)))

    def test_a_real_reading_is_not_contentless(self):
        for sequence in ("ma a an", "ninda gur₄ ra em ṣa", "a", "ú"):
            with self.subTest(sequence=sequence):
                self.assertFalse(
                    export.sequence_is_contentless(proposal_with(sequence)))

    def test_a_reading_containing_a_placeholder_is_not_contentless(self):
        """One illegible sign inside a real sequence is still evidence."""
        self.assertFalse(
            export.sequence_is_contentless(proposal_with("an da x zi")))


class TestQueueRanking(unittest.TestCase):
    def test_sequence_length_outranks_document_count(self):
        """The bug this ordering fixes: `a` in 3,542 documents is not evidence.

        Ranking by document count alone put single damaged signs at the top of
        the queue -- the same Zipfian floor as `x`, one level up.
        """
        common_single = proposal_with("a", member_count=5446, documents=3542,
                                      cluster_id="c-common")
        rare_phrase = proposal_with("me na aḫ ḫa an da", member_count=3,
                                    documents=3, cluster_id="c-phrase")
        ordered = sorted([common_single, rare_phrase], key=export.rank_key)
        self.assertEqual(ordered[0]["cluster_id"], "c-phrase")

    def test_document_count_breaks_ties_within_a_length(self):
        few = proposal_with("an da", documents=2, cluster_id="c-few")
        many = proposal_with("ku it", documents=9, cluster_id="c-many")
        ordered = sorted([few, many], key=export.rank_key)
        self.assertEqual(ordered[0]["cluster_id"], "c-many")

    def test_ranking_is_reproducible_for_identical_clusters(self):
        a = proposal_with("an da", cluster_id="c-a")
        b = proposal_with("an da", cluster_id="c-b")
        self.assertEqual(
            [c["cluster_id"] for c in sorted([b, a], key=export.rank_key)],
            ["c-a", "c-b"])

    def test_sequence_length_counts_signs_not_characters(self):
        self.assertEqual(export.sequence_length(proposal_with("me na aḫ")), 3)
        self.assertEqual(export.sequence_length(proposal_with("")), 0)


class TestBrowserDialogContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (
            ROOT / "demo" / "workbench_unresolved_prototype.html"
        ).read_text(encoding="utf-8")

    def test_browser_unsupported_native_dialogs_are_absent(self):
        for native_call in ("window.prompt(", "window.alert(", "window.confirm("):
            with self.subTest(native_call=native_call):
                self.assertNotIn(native_call, self.html)

    def test_in_page_dialog_is_the_review_input_surface(self):
        for contract_piece in (
                'id="review-dialog"',
                'id="review-dialog-input" aria-labelledby="review-dialog-label"',
                'id="review-dialog-textarea" aria-labelledby="review-dialog-label"',
                "function uiPrompt(",
                "function uiConfirm(",
                "function uiAlert("):
            with self.subTest(contract_piece=contract_piece):
                self.assertIn(contract_piece, self.html)


class TestBackupGuard(unittest.TestCase):
    def test_empty_log_needs_no_backup(self):
        self.assertTrue(ingest.backup_is_current([]))

    def test_unbacked_log_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(ingest, "LEDGER_PATH", Path(tmp) / "none.jsonl"):
                self.assertFalse(ingest.backup_is_current([make_event()]))

    def test_log_whose_head_is_in_the_ledger_passes(self):
        event = make_event()
        head = ue.AnnotationEventLog([event]).head_sha256()
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "backup_ledger.jsonl"
            ledger.write_text(
                json.dumps({"chain_head_sha256": head}) + "\n", encoding="utf-8")
            with mock.patch.object(ingest, "LEDGER_PATH", ledger):
                self.assertTrue(ingest.backup_is_current([event]))

    def test_a_stale_ledger_entry_does_not_pass_a_newer_log(self):
        """Backing up once does not license appending forever."""
        first = make_event()
        log = ue.AnnotationEventLog([first])
        stale_head = log.head_sha256()
        log.append(
            event_id="evt-2", action="WITHHOLD_JUDGMENT", target_id="occ-1",
            reviewed_record={"occurrence_id": "occ-1"},
            reviewer_id="R", declared_role="Hittitologist")
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "backup_ledger.jsonl"
            ledger.write_text(
                json.dumps({"chain_head_sha256": stale_head}) + "\n",
                encoding="utf-8")
            with mock.patch.object(ingest, "LEDGER_PATH", ledger):
                self.assertFalse(ingest.backup_is_current(log.events))


def make_event(target_id="occ-1"):
    return ue.build_annotation_event(
        event_id="evt-1",
        action="WITHHOLD_JUDGMENT",
        target_id=target_id,
        reviewed_record={"occurrence_id": target_id},
        prior_event_sha256=None,
        reviewer_id="R",
        declared_role="Hittitologist",
    )


class TestSessionRechaining(unittest.TestCase):
    """A browser session chains from the head it assumed; disk decides."""

    def test_rechaining_preserves_the_reviewed_record_binding(self):
        record = {"occurrence_id": "occ-1", "categories": ["ILLEGIBLE_SIGN"]}
        expected = ue.canonical_sha256(record)

        existing = ue.AnnotationEventLog([make_event(target_id="occ-0")])
        rebuilt = existing.append(
            event_id="evt-session",
            action="PROPOSE_READING",
            target_id="occ-1",
            reviewed_record=record,
            reviewer_id="R",
            declared_role="Hittitologist",
            hypothesis={"proposed_reading": "ma a an"},
        )

        # The chain moved off the browser's assumed null head...
        self.assertIsNotNone(rebuilt["prior_event_sha256"])
        # ...but what the expert reviewed is untouched, which is the binding
        # that makes the judgment meaningful.
        self.assertEqual(rebuilt["reviewed_record_sha256"], expected)
        existing.verify_chain()

    def test_a_rewritten_record_no_longer_matches_its_event(self):
        record = {"occurrence_id": "occ-1", "categories": ["ILLEGIBLE_SIGN"]}
        event = ue.build_annotation_event(
            event_id="evt-1", action="PROPOSE_READING", target_id="occ-1",
            reviewed_record=record, prior_event_sha256=None, reviewer_id="R",
            declared_role="Hittitologist",
            hypothesis={"proposed_reading": "ma a an"})
        changed = dict(record, categories=["ILLEGIBLE_SIGN", "RARE_FORM"])
        self.assertNotEqual(
            event["reviewed_record_sha256"], ue.canonical_sha256(changed))


if __name__ == "__main__":
    unittest.main()
