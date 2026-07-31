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


class TestQueuePolicyRatification(unittest.TestCase):
    """The two selection rules do not have the same standing.

    Contentless exclusion was ratified 2026-07-31 after measurement; the
    minimum-length rule was deferred because it is a no-op at the current
    ranking and payload bound. Presenting them as equally settled would
    misrepresent what a specialist's judgments were made under.
    """

    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(
            (ROOT / "configs" / "p4e2_queue_policy.json").read_text(
                encoding="utf-8"))

    def test_contentless_exclusion_is_ratified(self):
        self.assertEqual(
            self.policy["contentless_sequence_exclusion"]["status"], "RATIFIED")

    def test_minimum_length_is_not_presented_as_ratified(self):
        self.assertEqual(
            self.policy["minimum_sequence_length"]["status"],
            "UNRATIFIED_DEFERRED")

    def test_the_policy_name_is_versioned_past_the_widening(self):
        """A changed selection rule must change the queue's name, so a reader
        of an expert's annotations can tell which queue produced them."""
        self.assertEqual(
            self.policy["queue_policy"], "contentful_sequence_length_v2")
        self.assertEqual(
            self.policy["supersedes"], "contentful_sequence_length_v1")

    def test_the_export_reads_its_rules_from_the_record(self):
        self.assertEqual(export.QUEUE_POLICY, self.policy["queue_policy"])
        self.assertEqual(
            export.CONTENTLESS_CHARS,
            frozenset(self.policy["contentless_sequence_exclusion"]["chars"]))
        self.assertEqual(
            export.MIN_SEQUENCE_LENGTH,
            self.policy["minimum_sequence_length"]["value_in_use"])

    def test_an_unknown_status_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            broken = json.loads(json.dumps(self.policy))
            broken["minimum_sequence_length"]["status"] = "PROBABLY_FINE"
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(SystemExit):
                export.load_queue_policy(path)

    def test_a_missing_record_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                export.load_queue_policy(Path(tmp) / "absent.json")


class TestContentlessSafetyInvariant(unittest.TestCase):
    """No sequence carrying a sign value may be excluded as contentless.

    A real reading always contains a letter, and the only letter in the set is
    the illegible placeholder `x`. This is the invariant that makes widening
    the character set safe, so it is asserted rather than inspected.
    """

    def test_no_letter_other_than_x_is_contentless(self):
        offenders = sorted(
            c for c in export.CONTENTLESS_CHARS if c.isalpha() and c != "x")
        self.assertEqual(offenders, [])

    def test_digits_are_never_contentless(self):
        """`10` alone is in 81 documents and `d 10` in 70 -- the Storm God with
        a damaged determinative. `30` is the Moon God. A numeral is content."""
        for digit in "0123456789":
            with self.subTest(digit=digit):
                self.assertNotIn(digit, export.CONTENTLESS_CHARS)
        for sequence in ("10", "30", "7", "d 10"):
            with self.subTest(sequence=sequence):
                self.assertFalse(
                    export.sequence_is_contentless(proposal_with(sequence)))

    def test_the_ratified_apparatus_marks_are_contentless(self):
        for sequence in ("…", "(…)", "? ? ?", "(?)", "!", "==", "}",
                         "〈〉", "(_ …)", "…..", "x x x",
                         "(_)"):
            with self.subTest(sequence=sequence):
                self.assertTrue(
                    export.sequence_is_contentless(proposal_with(sequence)))

    def test_the_character_set_is_pinned_by_codepoint(self):
        """Homoglyphs are the live risk here, and they fail silently.

        The corpus uses U+2329/U+232A angle brackets; U+3008/U+3009 are
        visually identical CJK characters that occur in it zero times. A
        future edit that pastes the wrong one would leave the rule looking
        correct while catching nothing, so the set is pinned by codepoint
        rather than by appearance. This test caught exactly that mistake in
        its own first draft.
        """
        self.assertEqual(
            sorted(f"U+{ord(c):04X}" for c in export.CONTENTLESS_CHARS),
            ["U+0020", "U+0021", "U+0028", "U+0029", "U+002E", "U+003D",
             "U+003F", "U+005F", "U+0078", "U+007D", "U+0323", "U+2026",
             "U+2329", "U+232A"])

    def test_cjk_angle_bracket_homoglyphs_are_not_in_the_set(self):
        for homoglyph in ("〈", "〉", "《", "》"):
            with self.subTest(homoglyph=homoglyph):
                self.assertNotIn(homoglyph, export.CONTENTLESS_CHARS)

    def test_apparatus_attached_to_a_reading_stays(self):
        """One uncertainty mark inside a real sequence is still evidence."""
        for sequence in ("an!", "al?", "at〉", "an da x zi", "ma a an"):
            with self.subTest(sequence=sequence):
                self.assertFalse(
                    export.sequence_is_contentless(proposal_with(sequence)))

    def test_marks_the_scribe_made_are_not_apparatus(self):
        """U+12471 is a cuneiform punctuation sign and `×` belongs to compound
        sign names like SI×SÁ. Both are on the tablet, not notes about it."""
        for sequence in ("\U00012471", "×"):
            with self.subTest(sequence=sequence):
                self.assertFalse(
                    export.sequence_is_contentless(proposal_with(sequence)))


class TestLanguageSelection(unittest.TestCase):
    """`--language` decides which language a specialist spends a session in.

    It fails closed on an unknown code for a specific reason: a silently empty
    queue is indistinguishable from "this language has no unresolved
    material", which is a different and far more interesting claim.
    """

    CODES = ["Hit", "Akk", "Sum", "Hat", "Hur", "Luw", "Pal"]

    def parse(self, values):
        return export.parse_language_selection(
            values, canonical_codes=self.CODES)

    def test_no_selection_means_no_restriction(self):
        for values in (None, [], [""], [" , "]):
            with self.subTest(values=values):
                self.assertIsNone(self.parse(values))

    def test_repeated_and_comma_separated_forms_agree(self):
        self.assertEqual(self.parse(["Akk", "Hur"]), frozenset({"Akk", "Hur"}))
        self.assertEqual(self.parse(["Akk,Hur"]), frozenset({"Akk", "Hur"}))
        self.assertEqual(self.parse(["Akk, Hur"]), frozenset({"Akk", "Hur"}))

    def test_unknown_code_is_refused_not_silently_empty(self):
        for bad in ("Akkadian", "akk", "AKK", "Hittite", "xx"):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    self.parse([bad])

    def test_unresolved_sentinel_must_be_requested_by_name(self):
        """It is not a canonical code and is never swept in with a real one."""
        self.assertEqual(
            self.parse([export.UNRESOLVED_LANGUAGE]),
            frozenset({export.UNRESOLVED_LANGUAGE}))
        selection = self.parse(["Hit"])
        self.assertNotIn(export.UNRESOLVED_LANGUAGE, selection)

    def test_cluster_languages_reads_the_declared_evidence(self):
        proposal = proposal_with("an da")
        self.assertEqual(export.cluster_languages(proposal), ["Hit"])

    def test_a_null_language_becomes_the_unresolved_sentinel(self):
        proposal = proposal_with("an da")
        proposal["supporting_evidence"][0]["languages"] = [None]
        self.assertEqual(
            export.cluster_languages(proposal), [export.UNRESOLVED_LANGUAGE])

    def test_selection_admits_only_matching_clusters(self):
        hittite = proposal_with("an da")
        akkadian = proposal_with("an da")
        akkadian["supporting_evidence"][0]["languages"] = ["Akk"]
        selection = frozenset({"Akk"})
        self.assertFalse(export.proposal_matches_language(hittite, selection))
        self.assertTrue(export.proposal_matches_language(akkadian, selection))

    def test_no_selection_admits_everything(self):
        proposal = proposal_with("an da")
        self.assertTrue(export.proposal_matches_language(proposal, None))

    def test_a_cross_language_cluster_matches_on_any_declared_language(self):
        """Cross-language clusters span languages BY DESIGN.

        Selecting `Luw` there means "clusters that involve Luwian", whose other
        members are in other languages. That is the channel working, not a leak.
        """
        cross = proposal_with("an da")
        cross["supporting_evidence"][0]["languages"] = ["Hit", "Luw"]
        self.assertTrue(
            export.proposal_matches_language(cross, frozenset({"Luw"})))
        self.assertTrue(
            export.proposal_matches_language(cross, frozenset({"Hit"})))
        self.assertFalse(
            export.proposal_matches_language(cross, frozenset({"Akk"})))


class TestBrowserDisclosureContract(unittest.TestCase):
    """The mandated disclosures moved behind progressive disclosure.

    They are still on the page in full. These tests exist so a later
    readability pass cannot quietly delete one: collapsing a required
    statement is a presentation change, deleting it is a contract breach, and
    the two look identical in a diff of a 900-line HTML file.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = (
            ROOT / "demo" / "workbench_unresolved_prototype.html"
        ).read_text(encoding="utf-8")

    def test_counts_are_never_presented_as_probabilities(self):
        """Standing display rule 2."""
        self.assertIn(
            "counts of matching occurrences, not a probability or a "
            "confidence score", self.html)

    def test_absent_contradictory_evidence_is_not_read_as_agreement(self):
        """Standing display rule 3."""
        self.assertIn(
            "That is the absence of a recorded objection, not evidence of "
            "its soundness", self.html)

    def test_the_subset_statement_stays_outside_the_disclosure(self):
        """Standing display rule 5: the headline must not be collapsible."""
        headline = self.html.index("This is a subset, not the corpus.")
        disclosure = self.html.index("What was held out, and why")
        self.assertLess(headline, disclosure)

    def test_quarantine_statement_is_present_and_uncollapsed(self):
        self.assertIn("QUARANTINED_EXPERT_JUDGMENT", self.html)
        quarantine = self.html.index(
            "requires a separate adjudication gate")
        provenance = self.html.index("Provenance and queue parameters")
        self.assertLess(quarantine, provenance)

    def test_withhold_judgment_is_always_offered(self):
        """Standing display rule 4."""
        self.assertIn("WITHHOLD_JUDGMENT", self.html)
        self.assertIn("Assert nothing", self.html)

    def test_actions_are_grouped_by_what_the_click_records(self):
        for group_label in ("Record a claim about this occurrence",
                            "Correct this grouping",
                            "Assert nothing"):
            with self.subTest(group_label=group_label):
                self.assertIn(group_label, self.html)

    def test_every_action_carries_an_explanatory_title(self):
        """A specialist must know what a click records before clicking."""
        for action in ("PROPOSE_READING", "PROPOSE_PHRASE", "PROPOSE_LANGUAGE",
                       "PROPOSE_LEXICAL_IDENTITY", "REMOVE_FROM_CLUSTER",
                       "REJECT_HYPOTHESIS", "WITHHOLD_JUDGMENT"):
            with self.subTest(action=action):
                self.assertIn(f'["{action}"', self.html)

    def test_damage_overlay_is_display_only_and_has_a_legend(self):
        for piece in ('id="damage-mode"', "function applyDamageMode(",
                      "DAMAGE_LEGENDS", 'id="damage-legend"',
                      'body[data-damage="attested"]',
                      'body[data-damage="off"]'):
            with self.subTest(piece=piece):
                self.assertIn(piece, self.html)

    def test_rule_status_is_read_from_the_manifest_not_hardcoded(self):
        """The page must not claim a rule was ratified when the record says
        otherwise, so the status travels with the queue."""
        self.assertIn("function ruleStatusLabel(", self.html)
        self.assertIn("MANIFEST.selection_rule_status", self.html)
        for state in ("ratified", "awaiting ratification — deferred",
                      "status not recorded"):
            with self.subTest(state=state):
                self.assertIn(state, self.html)

    def test_the_old_both_unratified_claim_is_gone(self):
        """Contentless was ratified 2026-07-31; saying otherwise is false."""
        self.assertNotIn("display policies still awaiting ratification",
                         self.html)

    def test_single_language_queue_disclaims_calibration(self):
        """A review surface must never be mistaken for a prediction surface."""
        self.assertIn("review surface, not a prediction surface", self.html)
        self.assertIn("No per-language", self.html)


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

    def test_browser_export_is_an_explicit_local_json_download(self):
        for contract_piece in (
                "new Blob([JSON.stringify(payload, null, 2)]",
                '{ type: "application/json" }',
                "a.download = `workbench_events_",
                "a.click();",
                "URL.revokeObjectURL(url);"):
            with self.subTest(contract_piece=contract_piece):
                self.assertIn(contract_piece, self.html)

    def test_browser_has_no_direct_network_or_ingest_path(self):
        for prohibited_path in (
                "fetch(",
                "XMLHttpRequest",
                "phase4_workbench_ingest_events.py("):
            with self.subTest(prohibited_path=prohibited_path):
                self.assertNotIn(prohibited_path, self.html)


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
