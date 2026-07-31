"""Regression tests for the P2-E7 expert decision boundary."""

import copy
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import expert_decision_contract as edc


def provenance():
    return {
        "source_probe": "synthetic_test_fixture",
        "source_artifact": "none",
        "source_artifact_sha256": "0" * 64,
        "source_manifest": "none",
        "source_manifest_sha256": "0" * 64,
        "dev_example_only": True,
    }


def base_source(decision="PRESENT_CANDIDATE_SET"):
    return {
        "decision": decision,
        "evidence_policy": "catalog_assisted",
        "query": {
            "fragment_id": "fixture",
            "cth": 1,
            "span_ordinal": 0,
            "line_index_in_doc": 2,
            "sign_offset_in_line": 3,
            "left_anchor": ["a"],
            "right_anchor": ["b"],
        },
        "enabled_assistance_layers": [
            "OBSERVED_DOCUMENT_STRUCTURE",
            "EDITORIAL_TRANSCRIPTION",
            "CATALOG_METADATA",
        ],
        "editorial_features_used": ["token"],
        "model_features_used": [],
        "abstention_reason": (
            None if decision == "PRESENT_CANDIDATE_SET"
            else "No independent witness support."),
        "dev_evaluation_only": {
            "intentionally_hidden_attested_middle": ["SECRET"],
        },
    }


def p2e4_source():
    source = base_source()
    source["candidate_set"] = {
        "alternatives": [
            {
                "rank": 1,
                "middle": ["x"],
                "independent_witness_family_count": 2,
                "supporting_witness_families": ["A", "B"],
                "evidence_class": "EDITORIAL_TRANSCRIPTION",
                "calibration": {
                    "estimand": "rank group agreement",
                    "calibration_contexts_with_rank_available": 100,
                    "calibrated_empirical_agreement": 0.8,
                    "wilson_95": [0.71, 0.87],
                },
            }
        ],
        "total_alternatives": 1,
        "probability_warning": "Group rate only.",
    }
    return source


def p2e6_source(decision="PRESENT_CANDIDATE_SET", total=1):
    source = base_source(decision)
    source["query"]["mask_length"] = 2
    alternatives = []
    calibration = None
    if decision == "PRESENT_CANDIDATE_SET":
        alternatives = [
            {
                "rank": 1,
                "middle": ["x", "y"],
                "independent_witness_family_count": 2,
                "supporting_witness_families": ["A", "B"],
                "witness_support_share": 0.5,
                "evidence_class": "EDITORIAL_TRANSCRIPTION",
            }
        ]
        calibration = {
            "estimand": "set inclusion",
            "calibration_presented_contexts": 100,
            "candidate_set_calibration_rate": 0.4,
            "wilson_95": [0.31, 0.50],
        }
    source["candidate_set"] = {
        "tie_complete_alternatives": alternatives,
        "total_tie_complete_alternatives": (
            total if alternatives else 0),
        "set_level_calibration": calibration,
        "probability_warning": "Set group rate only.",
    }
    return source


def decision_for(packet, action="SELECT_OPTION"):
    return {
        "record_type": edc.DECISION_RECORD_TYPE,
        "contract_version": edc.CONTRACT_VERSION,
        "decision_id": "decision-1",
        "packet_id": packet["packet_id"],
        "packet_sha256": edc.canonical_sha256(packet),
        "action": action,
        "selected_option_id": (
            packet["candidate_set"]["options"][0]["option_id"]
            if action == "SELECT_OPTION" else None),
        "proposed_other_signs": None,
        "reviewer": {
            "reviewer_id": "expert-opaque-id",
            "declared_role": "Hittitologist",
        },
        "rationale": None,
        "created_utc": "2026-07-23T00:00:00Z",
        "assistance_acknowledged": True,
        "ground_truth_status": "QUARANTINED_EXPERT_JUDGMENT",
        "requires_adjudication": True,
    }


def language_context(**overrides):
    """A resolved Hittite language block unless a test overrides it."""
    kwargs = {
        "language_scope": "HITTITE_ONLY",
        "query_language": "Hit",
        "query_language_status": "RESOLVED",
        "language_rule_id": "word_override_else_line_v2",
    }
    kwargs.update(overrides)
    return edc.build_language_context(**kwargs)


def p2e4_empty_middle_source():
    """A P2-E4 source whose rank-1 witness proposal is the empty middle."""
    source = p2e4_source()
    source["candidate_set"]["alternatives"][0]["middle"] = []
    return source


class TestEmptyMiddleDisplay(unittest.TestCase):
    """The empty middle is contradictory evidence, not a candidate reading.

    Measured at 109 of 577 accepted cross-line real gaps and 10 of the 28
    exported demo packets, so this is a live display path, not a hypothetical.
    The remedy is display-only ON PURPOSE: the option keeps its rank and its
    witness support because that is the ranking P2-E4/P2-E9 were fit over, and
    removing it would decouple the calibrated rate from the thing it rates.
    """

    def build(self):
        return edc.adapt_p2e4_packet(
            p2e4_empty_middle_source(), "packet-em", provenance(),
            language_context())

    def test_the_option_is_not_dropped_or_reordered(self):
        """Filtering it would change the applied ranking. It must not."""
        packet = self.build()
        options = packet["candidate_set"]["options"]
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]["rank"], 1)
        self.assertEqual(options[0]["signs"], [])
        self.assertEqual(
            options[0]["support"]["independent_witness_family_count"], 2)

    def test_it_is_labelled_as_not_a_reading(self):
        display = self.build()["candidate_set"]["options"][0]["display"]
        self.assertEqual(display["kind"], "EMPTY_MIDDLE")
        self.assertFalse(display["is_a_reading"])
        self.assertTrue(display["render_signs_as"])
        self.assertTrue(display["headline"])

    def test_the_rank_group_rate_is_withheld(self):
        """The rank rate's estimand is agreement with the true attested
        middle; an option proposing no signs cannot be that middle."""
        option = self.build()["candidate_set"]["options"][0]
        self.assertEqual(option["option_audit"]["kind"], "UNAVAILABLE")
        self.assertIsNone(option["option_audit"]["estimate"])
        self.assertIsNone(option["option_audit"]["sample_size"])

    def test_it_produces_typed_contradictory_evidence(self):
        packet = self.build()
        contra = packet["contradictory_evidence"]
        self.assertEqual(len(contra), 1)
        self.assertEqual(contra[0]["type"], "WITNESS_ANCHORS_ADJACENT")
        self.assertEqual(contra[0]["polarity"], "CONTRADICTS_QUERY_STRUCTURE")
        self.assertEqual(contra[0]["source_refs"], ["A", "B"])

    def test_it_carries_the_limitation_code(self):
        codes = [item["code"] for item in self.build()["limitations"]]
        self.assertIn(edc.EMPTY_MIDDLE_LIMITATION_CODE, codes)

    def test_an_ordinary_option_is_untouched(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_source(), "packet-ok", provenance(), language_context())
        option = packet["candidate_set"]["options"][0]
        self.assertNotIn("display", option)
        self.assertEqual(option["option_audit"]["kind"], "GROUP_AUDIT_RATE")
        self.assertEqual(packet["contradictory_evidence"], [])

    def test_p2e6_multisign_is_covered_too(self):
        """5 of the 12 exported P2-E6 packets carry one, one at rank 1 on 19
        families. The set-inclusion rate is withheld on the same grounds."""
        source = p2e6_source()
        source["candidate_set"]["tie_complete_alternatives"][0]["middle"] = []
        packet = edc.adapt_p2e6_packet(
            source, "packet-em6", provenance(), language_context())
        option = packet["candidate_set"]["options"][0]
        self.assertEqual(option["display"]["kind"], "EMPTY_MIDDLE")
        self.assertEqual(option["option_audit"]["kind"], "UNAVAILABLE")


class TestEmptyMiddleFailsClosed(unittest.TestCase):
    def test_an_unknown_query_kind_is_refused(self):
        """No default: 'witnesses show nothing' means something different for
        an illegible trace, a restoration, a lacuna, and a hidden sign."""
        with self.assertRaises(edc.ContractError):
            edc.classify_empty_middle("SOMETHING_ELSE")

    def test_every_declared_kind_has_copy(self):
        for kind in edc.EMPTY_MIDDLE_QUERY_KINDS:
            with self.subTest(kind=kind):
                classification = edc.classify_empty_middle(kind)
                self.assertTrue(classification["headline"])
                self.assertTrue(classification["detail"])
                self.assertEqual(classification["query_kind"], kind)

    def test_the_four_real_situations_are_all_covered(self):
        self.assertEqual(
            set(edc.EMPTY_MIDDLE_QUERY_KINDS),
            {"ILLEGIBLE_TRACE", "EDITORIAL_RESTORATION",
             "INDETERMINATE_LACUNA", "HIDDEN_ATTESTED_SIGN"})

    def test_damage_state_maps_to_the_right_branch(self):
        self.assertEqual(
            edc.empty_middle_query_kind_for_damage("illegible_x"),
            "ILLEGIBLE_TRACE")
        self.assertEqual(
            edc.empty_middle_query_kind_for_damage("restored"),
            "EDITORIAL_RESTORATION")
        self.assertEqual(
            edc.empty_middle_query_kind_for_damage("laes"),
            "EDITORIAL_RESTORATION")

    def test_the_ellipsis_token_wins_over_its_damage_state(self):
        """An indeterminate lacuna is tagged `restored`, but the editor
        proposed no sign -- describing it as a restoration would misreport
        what they actually wrote."""
        self.assertEqual(
            edc.empty_middle_query_kind_for_damage(
                "restored", token=edc.INDETERMINATE_LACUNA_TOKEN),
            "INDETERMINATE_LACUNA")

    def test_an_attested_run_is_refused(self):
        """An attested run is not a gap; inferring a branch would hide a bug."""
        with self.assertRaises(edc.ContractError):
            edc.empty_middle_query_kind_for_damage("attested")

    def test_an_unknown_damage_state_is_refused(self):
        with self.assertRaises(edc.ContractError):
            edc.empty_middle_query_kind_for_damage(None)

    def test_the_mapping_only_returns_declared_kinds(self):
        for damage in ("illegible_x", "restored", "laes"):
            with self.subTest(damage=damage):
                self.assertIn(
                    edc.empty_middle_query_kind_for_damage(damage),
                    edc.EMPTY_MIDDLE_QUERY_KINDS)

    def test_an_unannotated_empty_option_is_rejected(self):
        """The defect this replaces fails silently -- a renderer just draws an
        empty candidate -- so the schema has to catch it."""
        packet = edc.adapt_p2e4_packet(
            p2e4_empty_middle_source(), "packet-em", provenance(),
            language_context())
        del packet["candidate_set"]["options"][0]["display"]
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(packet)

    def test_an_empty_option_may_not_carry_a_rank_rate(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_empty_middle_source(), "packet-em", provenance(),
            language_context())
        packet["candidate_set"]["options"][0]["option_audit"] = {
            "kind": "GROUP_AUDIT_RATE", "scope": "OPTION_RANK",
            "estimand": "rank group agreement",
            "estimate": 0.8,
            "interval": {"method": "WILSON_SCORE", "level": 0.95,
                         "lower": 0.71, "upper": 0.87},
            "sample_size": 100, "instance_truth_probability": False,
            "ui_label": "x",
        }
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(packet)

    def test_a_display_block_on_a_real_reading_is_rejected(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_source(), "packet-ok", provenance(), language_context())
        packet["candidate_set"]["options"][0]["display"] = {
            "kind": "EMPTY_MIDDLE", "query_kind": "ILLEGIBLE_TRACE",
            "is_a_reading": False, "render_signs_as": "(no sign)",
            "headline": "h", "detail": "d",
        }
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(packet)

    def test_a_display_block_claiming_to_be_a_reading_is_rejected(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_empty_middle_source(), "packet-em", provenance(),
            language_context())
        packet["candidate_set"]["options"][0]["display"]["is_a_reading"] = True
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(packet)


class TestExpertDecisionContract(unittest.TestCase):
    def test_single_sign_adapter_strips_hidden_gold(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_source(), "packet-1", provenance(), language_context())
        self.assertNotIn("dev_evaluation_only", packet)
        self.assertNotIn(
            "SECRET",
            str(packet),
        )
        audit = packet["candidate_set"]["options"][0]["option_audit"]
        self.assertEqual(audit["scope"], "OPTION_RANK")
        self.assertFalse(audit["instance_truth_probability"])

    def test_multisign_adapter_preserves_collapsed_tail(self):
        packet = edc.adapt_p2e6_packet(
            p2e6_source(total=48), "packet-2", provenance(), language_context())
        self.assertTrue(packet["candidate_set"]["tail_collapsed"])
        self.assertEqual(packet["candidate_set"]["collapsed_tail_count"], 47)
        self.assertEqual(
            packet["candidate_set"]["ranking_boundary_policy"],
            "TIE_COMPLETE",
        )

    def test_abstention_has_no_select_action_or_probability(self):
        packet = edc.adapt_p2e6_packet(
            p2e6_source("ABSTAIN"), "packet-3", provenance(), language_context())
        self.assertEqual(packet["candidate_set"]["options"], [])
        self.assertEqual(
            packet["workflow"]["allowed_actions"],
            ["OTHER_OR_UNSUPPORTED", "WITHHOLD_JUDGMENT"],
        )
        self.assertEqual(
            packet["candidate_set"]["set_audit"]["kind"],
            "UNAVAILABLE",
        )

    def test_validator_rejects_instance_probability(self):
        packet = edc.adapt_p2e6_packet(
            p2e6_source(), "packet-4", provenance(), language_context())
        unsafe = copy.deepcopy(packet)
        unsafe["candidate_set"]["set_audit"][
            "instance_truth_probability"] = True
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(unsafe)

    def test_selection_is_hash_bound_and_quarantined(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_source(), "packet-5", provenance(), language_context())
        decision = decision_for(packet)
        self.assertIs(edc.validate_expert_decision(decision, packet), decision)
        stale = copy.deepcopy(decision)
        stale["packet_sha256"] = "f" * 64
        with self.assertRaises(edc.ContractError):
            edc.validate_expert_decision(stale, packet)
        unsafe = copy.deepcopy(decision)
        unsafe["ground_truth_status"] = "GROUND_TRUTH"
        with self.assertRaises(edc.ContractError):
            edc.validate_expert_decision(unsafe, packet)

    def test_packet_must_state_its_language_context(self):
        # Contract 1.1.0: a packet may not be emitted without saying what
        # language it believed it was working in.
        with self.assertRaises(edc.ContractError):
            edc.adapt_p2e4_packet(
                p2e4_source(), "packet-7", provenance(), None)

    def test_unresolved_language_forces_an_explicit_limitation(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_source(), "packet-8", provenance(),
            language_context(
                query_language=None,
                query_language_status="UNRESOLVED_IN_SOURCE_RUN"))
        codes = [item["code"] for item in packet["limitations"]]
        self.assertIn("LANGUAGE_UNRESOLVED_IN_SOURCE_RUN", codes)
        # Stripping the disclosure must not leave a silently language-free
        # packet that still validates.
        unsafe = copy.deepcopy(packet)
        unsafe["limitations"] = [
            item for item in unsafe["limitations"]
            if not item["code"].startswith("LANGUAGE_")]
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(unsafe)

    def test_unresolved_status_cannot_also_name_a_language(self):
        with self.assertRaises(edc.ContractError):
            edc.adapt_p2e4_packet(
                p2e4_source(), "packet-9", provenance(),
                language_context(
                    query_language="Hit",
                    query_language_status="UNRESOLVED_IN_SOURCE_RUN"))

    def test_cross_language_evidence_requires_an_enabled_channel(self):
        with self.assertRaises(edc.ContractError):
            edc.adapt_p2e4_packet(
                p2e4_source(), "packet-10", provenance(),
                language_context(
                    cross_language_source_languages=["Hur"],
                    cross_language_assistance_enabled=False))

    def test_query_language_cannot_appear_in_the_cross_language_channel(self):
        # The two channels must stay separable, per PHASE4_CHARTER.md P4-D.
        with self.assertRaises(edc.ContractError):
            edc.adapt_p2e4_packet(
                p2e4_source(), "packet-11", provenance(),
                language_context(
                    cross_language_source_languages=["Hit"],
                    cross_language_assistance_enabled=True))

    def test_language_fields_stay_editorial_transcription(self):
        packet = edc.adapt_p2e4_packet(
            p2e4_source(), "packet-12", provenance(), language_context())
        self.assertEqual(
            packet["language"]["language_evidence_class"],
            "EDITORIAL_TRANSCRIPTION")
        unsafe = copy.deepcopy(packet)
        unsafe["language"]["language_evidence_class"] = "OBSERVED_ARTIFACT"
        with self.assertRaises(edc.ContractError):
            edc.validate_suggestion_packet(unsafe)

    def test_abstention_rejects_selection(self):
        packet = edc.adapt_p2e6_packet(
            p2e6_source("ABSTAIN"), "packet-6", provenance(), language_context())
        decision = decision_for(packet, "WITHHOLD_JUDGMENT")
        self.assertIs(edc.validate_expert_decision(decision, packet), decision)
        decision["action"] = "SELECT_OPTION"
        decision["selected_option_id"] = "option-001"
        with self.assertRaises(edc.ContractError):
            edc.validate_expert_decision(decision, packet)


if __name__ == "__main__":
    unittest.main(verbosity=2)
