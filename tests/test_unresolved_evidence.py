"""P4-E: the Unresolved Evidence Workbench contract invariants.

Each test pins one acceptance check from
`specs/UNRESOLVED_EVIDENCE_WORKBENCH.md`, or one defect found while
implementing the extraction.
"""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import unresolved_evidence as ue  # noqa: E402


def provenance():
    return ue.build_provenance(
        split_manifest_hash="a" * 64,
        language_layer_hash="b" * 64,
        config_hash="c" * 64,
        git_commit="deadbeef",
        seed=1,
        evidence_policy="transcription_assisted",
        created_utc="2026-07-26T00:00:00+00:00",
    )


def location(**overrides):
    kwargs = {
        "doc_id": "KBo 1.1",
        "fragment_id": "KBo 1.1",
        "line_index_in_doc": 3,
        "word_index_in_line": 2,
        "token_start": 4,
        "token_end": 6,
        "main_split": "train",
        "source_archive_member": "x/KBo 1.1.xml",
        "source_payload_sha256": "d" * 64,
    }
    kwargs.update(overrides)
    return ue.build_location(**kwargs)


def language(**overrides):
    kwargs = {
        "document": None, "line": "Hit", "word": None, "effective": "Hit",
        "effective_status": "RESOLVED", "effective_source": "LINE_INHERITED",
    }
    kwargs.update(overrides)
    return ue.build_language_assignment(**kwargs)


def occurrence(**overrides):
    kwargs = {
        "occurrence_id": "occ-1",
        "categories": ["ILLEGIBLE_SIGN"],
        "location": location(),
        "language": language(),
        "display": {"tokens": ["x", "x"]},
        "context": {"left": [], "right": [], "lexical_unknown_detector": None},
        "evidence_classes": ["EDITORIAL_TRANSCRIPTION"],
        "assistance_layers": [],
        "provenance": provenance(),
    }
    kwargs.update(overrides)
    return ue.build_occurrence(**kwargs)


class TestOccurrence(unittest.TestCase):
    def test_every_occurrence_is_checksum_anchored(self):
        # Acceptance check 1: stable source location and checksum.
        self.assertEqual(len(occurrence()["location"]["source_payload_sha256"]), 64)
        with self.assertRaises(ue.WorkbenchError):
            occurrence(location=location(source_payload_sha256="short"))

    def test_categories_are_non_empty_and_known(self):
        # Acceptance check 2.
        with self.assertRaises(ue.WorkbenchError):
            occurrence(categories=[])
        with self.assertRaises(ue.WorkbenchError):
            occurrence(categories=["NOT_A_CATEGORY"])

    def test_protected_test_material_cannot_be_extracted(self):
        # Acceptance check 3.
        with self.assertRaises(ue.WorkbenchError):
            location(main_split="test")

    def test_lexical_unknown_requires_a_named_detector(self):
        # The contract forbids inferring LEXICAL_UNKNOWN from a tokenizer OOV.
        with self.assertRaises(ue.WorkbenchError):
            occurrence(categories=["TOKENIZER_OOV", "LEXICAL_UNKNOWN"])
        allowed = occurrence(
            categories=["TOKENIZER_OOV", "LEXICAL_UNKNOWN"],
            context={"lexical_unknown_detector": "expert_adjudication:e-1"})
        self.assertIn("LEXICAL_UNKNOWN", allowed["categories"])

    def test_rare_form_requires_a_named_detector(self):
        # Ratified 2026-07-27: RARE_FORM is a claim about corpus frequency and
        # must name the detector that produced it. It is a separate category
        # from LEXICAL_UNKNOWN precisely so that "rare here" is never read as
        # "unknown to Hittitology".
        with self.assertRaises(ue.WorkbenchError):
            occurrence(categories=["RARE_FORM"])
        allowed = occurrence(
            categories=["RARE_FORM"],
            context={"rare_form_detector": "attested_frequency_at_most_1"})
        self.assertIn("RARE_FORM", allowed["categories"])

    def test_rare_form_and_lexical_unknown_are_separate_claims(self):
        self.assertIn("RARE_FORM", ue.CATEGORIES)
        self.assertIn("LEXICAL_UNKNOWN", ue.CATEGORIES)
        self.assertEqual(
            ue.DETECTOR_REQUIRED_CATEGORIES,
            {"RARE_FORM": "rare_form_detector",
             "LEXICAL_UNKNOWN": "lexical_unknown_detector"})

    def test_unresolved_language_must_carry_a_language_category(self):
        # Regression: the first extraction pass dropped 71 tokens whose line
        # carried no language attribute, because no category could name that.
        with self.assertRaises(ue.WorkbenchError):
            occurrence(
                categories=["ILLEGIBLE_SIGN"],
                language=language(
                    line=None, effective=None,
                    effective_status="UNRESOLVED_LINE_LANGUAGE",
                    effective_source="UNRESOLVED"))
        ok = occurrence(
            categories=["ILLEGIBLE_SIGN", "MISSING_LANGUAGE_TAG"],
            language=language(
                line=None, effective=None,
                effective_status="UNRESOLVED_LINE_LANGUAGE",
                effective_source="UNRESOLVED"))
        self.assertIn("MISSING_LANGUAGE_TAG", ok["categories"])

    def test_missing_is_distinct_from_empty_malformed_and_unrecognized(self):
        # Gate 0 drew these distinctions deliberately; collapsing them would
        # destroy information about the source.
        self.assertEqual(
            {ue.LANGUAGE_STATUS_CATEGORY[status] for status in
             ("missing", "explicit_empty", "malformed", "unrecognized")},
            {"MISSING_LANGUAGE_TAG", "EMPTY_LANGUAGE_TAG",
             "MALFORMED_LANGUAGE_TAG", "UNRECOGNIZED_LANGUAGE_TAG"})

    def test_text_external_anomalies_may_have_no_line_or_token_span(self):
        # Contract 1.1.0: a PARSER_ANOMALY outside the primary <text>.
        item = occurrence(
            categories=["PARSER_ANOMALY"],
            location=location(
                line_index_in_doc=None, token_start=None, token_end=None,
                word_index_in_line=None, fragment_id=None),
            language=language(
                line=None, effective=None, effective_status="MISSING",
                effective_source="UNRESOLVED"))
        self.assertIsNone(item["location"]["line_index_in_doc"])
        # A half-present span is still refused.
        with self.assertRaises(ue.WorkbenchError):
            occurrence(location=location(token_start=4, token_end=None))

    def test_occurrence_is_never_corpus_truth(self):
        item = occurrence()
        self.assertEqual(item["ground_truth_status"], "NOT_CORPUS_TRUTH")
        unsafe = copy.deepcopy(item)
        unsafe["ground_truth_status"] = "CORPUS_TRUTH"
        with self.assertRaises(ue.WorkbenchError):
            ue.validate_occurrence(unsafe)

    def test_cu_preview_must_be_labeled_restoration_bearing(self):
        with self.assertRaises(ue.WorkbenchError):
            occurrence(display={"cu": "▒▒"})
        self.assertIn("cu", occurrence(display={
            "cu": "▒▒",
            "cu_is_editorial_restoration_bearing": True})["display"])


class TestClusterProposal(unittest.TestCase):
    def cluster(self, **overrides):
        kwargs = {
            "cluster_id": "c-1",
            "member_occurrence_ids": ["occ-1", "occ-2"],
            "method_name": "exact_normalized_sign_sequence",
            "evidence_class": "EDITORIAL_TRANSCRIPTION",
            "model_derived": False,
            "language_scope": "SAME_LANGUAGE_AS_QUERY",
            "supporting_evidence": [],
            "contradictory_evidence": [],
            "provenance": provenance(),
        }
        kwargs.update(overrides)
        return ue.build_cluster_proposal(**kwargs)

    def test_similarity_values_are_never_probabilities(self):
        # Acceptance check 6.
        item = self.cluster()
        self.assertIs(item["scores_are_probabilities"], False)
        unsafe = copy.deepcopy(item)
        unsafe["scores_are_probabilities"] = True
        with self.assertRaises(ue.WorkbenchError):
            ue.validate_cluster_proposal(unsafe)

    def test_deterministic_channels_are_system_not_model_proposals(self):
        # Ratified 2026-07-27: a status of MODEL_PROPOSAL told an expert a
        # model was consulted when the channel was plain string matching.
        self.assertEqual(self.cluster()["status"], "SYSTEM_PROPOSAL")
        self.assertEqual(
            self.cluster(model_derived=True)["status"], "MODEL_PROPOSAL")

    def test_system_proposal_cannot_claim_model_derivation(self):
        with self.assertRaises(ue.WorkbenchError):
            self.cluster(status="SYSTEM_PROPOSAL", model_derived=True)

    def test_clusters_start_as_proposals_and_stay_non_truth(self):
        # Acceptance checks 5 and 9.
        self.assertIn(
            self.cluster()["status"], ue.SYSTEM_ASSIGNABLE_CLUSTER_STATUSES)
        unsafe = copy.deepcopy(self.cluster(status="EXPERT_CURATED"))
        unsafe["ground_truth_status"] = "CORPUS_TRUTH"
        with self.assertRaises(ue.WorkbenchError):
            ue.validate_cluster_proposal(unsafe)

    def test_language_scope_is_explicit(self):
        with self.assertRaises(ue.WorkbenchError):
            self.cluster(language_scope="auto")

    def test_duplicate_members_are_refused(self):
        with self.assertRaises(ue.WorkbenchError):
            self.cluster(member_occurrence_ids=["occ-1", "occ-1"])


class TestAnnotationEvents(unittest.TestCase):
    def log_with_one_event(self):
        log = ue.AnnotationEventLog()
        log.append(
            event_id="e-1", action="PROPOSE_READING", target_id="occ-1",
            reviewed_record=occurrence(), prior_event_sha256=None,
            reviewer_id="reviewer-a", declared_role="hittitologist",
            hypothesis={"signs": ["ta", "ak"]},
            created_utc="2026-07-26T00:00:00+00:00")
        return log

    def test_events_are_quarantined_and_require_adjudication(self):
        # Acceptance checks 9 and 12.
        event = self.log_with_one_event().events[0]
        self.assertEqual(
            event["ground_truth_status"], "QUARANTINED_EXPERT_JUDGMENT")
        self.assertIs(event["requires_adjudication"], True)
        unsafe = copy.deepcopy(event)
        unsafe["requires_adjudication"] = False
        with self.assertRaises(ue.WorkbenchError):
            ue.validate_annotation_event(unsafe)

    def test_log_is_append_only_and_hash_chained(self):
        # Acceptance check 7.
        log = self.log_with_one_event()
        head = log.head_sha256()
        log.append(
            event_id="e-2", action="WITHHOLD_JUDGMENT", target_id="occ-1",
            reviewed_record=occurrence(), reviewer_id="reviewer-a",
            declared_role="hittitologist",
            created_utc="2026-07-26T00:01:00+00:00")
        self.assertEqual(log.events[1]["prior_event_sha256"], head)
        self.assertTrue(log.verify_chain())

        # An event that does not chain onto the head is refused outright.
        with self.assertRaises(ue.WorkbenchError):
            log.append(
                event_id="e-3", action="WITHHOLD_JUDGMENT", target_id="occ-1",
                reviewed_record=occurrence(), prior_event_sha256="f" * 64,
                reviewer_id="reviewer-a", declared_role="hittitologist",
                created_utc="2026-07-26T00:02:00+00:00")

    def test_rewriting_history_breaks_the_chain(self):
        log = self.log_with_one_event()
        log.append(
            event_id="e-2", action="REJECT_HYPOTHESIS", target_id="occ-1",
            reviewed_record=occurrence(), reviewer_id="reviewer-b",
            declared_role="hittitologist",
            created_utc="2026-07-26T00:01:00+00:00")
        tampered = log.events
        tampered[0]["rationale"] = "silently edited after the fact"
        with self.assertRaises(ue.WorkbenchError):
            ue.AnnotationEventLog(tampered)

    def test_withholding_judgment_cannot_carry_a_hypothesis(self):
        # Acceptance check 11: withhold is always available, and it means
        # withheld -- not a hypothesis wearing a withdrawal's label.
        with self.assertRaises(ue.WorkbenchError):
            ue.build_annotation_event(
                event_id="e-x", action="WITHHOLD_JUDGMENT", target_id="occ-1",
                reviewed_record=occurrence(), prior_event_sha256=None,
                reviewer_id="r", declared_role="hittitologist",
                hypothesis={"signs": ["ta"]})

    def test_proposals_require_a_hypothesis(self):
        for action in sorted(ue.HYPOTHESIS_ACTIONS):
            with self.assertRaises(ue.WorkbenchError):
                ue.build_annotation_event(
                    event_id="e-x", action=action, target_id="occ-1",
                    reviewed_record=occurrence(), prior_event_sha256=None,
                    reviewer_id="r", declared_role="hittitologist")

    def test_cluster_actions_must_name_their_cluster(self):
        with self.assertRaises(ue.WorkbenchError):
            ue.build_annotation_event(
                event_id="e-x", action="ADD_TO_CLUSTER", target_id="occ-1",
                reviewed_record=occurrence(), prior_event_sha256=None,
                reviewer_id="r", declared_role="hittitologist",
                hypothesis={"note": "no cluster_id"})

    def test_reviewed_record_hash_detects_a_changed_record(self):
        item = occurrence()
        event = ue.build_annotation_event(
            event_id="e-1", action="REJECT_HYPOTHESIS", target_id="occ-1",
            reviewed_record=item, prior_event_sha256=None,
            reviewer_id="r", declared_role="hittitologist")
        changed = copy.deepcopy(item)
        changed["display"]["tokens"] = ["different"]
        self.assertNotEqual(
            event["reviewed_record_sha256"], ue.canonical_sha256(changed))


class TestSnapshotProjection(unittest.TestCase):
    """Acceptance check 8: snapshots reproduce deterministically."""

    def build_log(self):
        log = ue.AnnotationEventLog()
        log.append(
            event_id="e-1", action="ADD_TO_CLUSTER", target_id="occ-1",
            reviewed_record={"id": "occ-1"}, reviewer_id="r",
            declared_role="hittitologist", hypothesis={"cluster_id": "c-1"},
            created_utc="2026-07-26T00:00:00+00:00")
        log.append(
            event_id="e-2", action="ADD_TO_CLUSTER", target_id="occ-2",
            reviewed_record={"id": "occ-2"}, reviewer_id="r",
            declared_role="hittitologist", hypothesis={"cluster_id": "c-2"},
            created_utc="2026-07-26T00:01:00+00:00")
        return log

    def test_projection_is_deterministic(self):
        events = self.build_log().events
        self.assertEqual(
            ue.project_snapshot(events), ue.project_snapshot(events))

    def test_grouping_moves_status_and_membership_together(self):
        snapshot = ue.project_snapshot(self.build_log().events)
        self.assertEqual(
            snapshot["occurrences"]["occ-1"]["status"], "GROUPED")
        self.assertEqual(
            snapshot["clusters"]["c-1"]["members"], ["occ-1"])

    def test_merge_moves_members_and_retains_the_emptied_cluster(self):
        log = self.build_log()
        log.append(
            event_id="e-3", action="MERGE_CLUSTERS", target_id="c-1",
            reviewed_record={"id": "c-1"}, reviewer_id="r",
            declared_role="hittitologist",
            hypothesis={"merged_cluster_ids": ["c-2"]},
            created_utc="2026-07-26T00:02:00+00:00")
        snapshot = ue.project_snapshot(log.events)
        self.assertEqual(
            sorted(snapshot["clusters"]["c-1"]["members"]), ["occ-1", "occ-2"])
        self.assertEqual(snapshot["clusters"]["c-2"]["members"], [])
        # The emptied cluster is retained, not deleted: the log's history
        # stays inspectable.
        self.assertIn("c-2", snapshot["clusters"])

    def test_split_redistributes_members(self):
        log = self.build_log()
        log.append(
            event_id="e-3", action="MERGE_CLUSTERS", target_id="c-1",
            reviewed_record={"id": "c-1"}, reviewer_id="r",
            declared_role="hittitologist",
            hypothesis={"merged_cluster_ids": ["c-2"]},
            created_utc="2026-07-26T00:02:00+00:00")
        log.append(
            event_id="e-4", action="SPLIT_CLUSTER", target_id="c-1",
            reviewed_record={"id": "c-1"}, reviewer_id="r",
            declared_role="hittitologist",
            hypothesis={"split_into": {"c-3": ["occ-2"]}},
            created_utc="2026-07-26T00:03:00+00:00")
        snapshot = ue.project_snapshot(log.events)
        self.assertEqual(snapshot["clusters"]["c-1"]["members"], ["occ-1"])
        self.assertEqual(snapshot["clusters"]["c-3"]["members"], ["occ-2"])

    def test_nothing_is_promoted_to_expert_supported_automatically(self):
        log = self.build_log()
        log.append(
            event_id="e-3", action="PROPOSE_READING", target_id="occ-1",
            reviewed_record={"id": "occ-1"}, reviewer_id="r",
            declared_role="hittitologist", hypothesis={"signs": ["ta"]},
            created_utc="2026-07-26T00:02:00+00:00")
        snapshot = ue.project_snapshot(log.events)
        self.assertEqual(
            snapshot["occurrences"]["occ-1"]["status"], "HYPOTHESIS")
        statuses = {
            state["status"] for state in snapshot["occurrences"].values()}
        self.assertNotIn("EXPERT_SUPPORTED", statuses)

    def test_unreviewed_occurrences_are_reported_not_omitted(self):
        snapshot = ue.project_snapshot(
            self.build_log().events, occurrence_ids=["occ-1", "occ-9"])
        self.assertEqual(
            snapshot["occurrences"]["occ-9"]["status"], "UNREVIEWED")


if __name__ == "__main__":
    unittest.main()
