import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
PREP_PATH = ROOT / "configs" / "phase4_preparation.json"
LANGUAGE_CONFIG_PATH = ROOT / "configs" / "language_layers_v2.json"
SCHEMA_PATH = ROOT / "configs" / "unresolved_evidence_contract.schema.json"
REGISTRY_PATH = ROOT / "configs" / "evidence_registry.yaml"
GATE2_ACCEPTANCE_PATH = (
    ROOT / "Phase4" / "phase4_out" / "gate2_acceptance.json")
PROJECTION_PATH = (
    ROOT / "Phase4" / "phase4_out" / "language_projection_manifest.json")


class TestPhase4Preparation(unittest.TestCase):
    def test_gate0_authorizes_only_gate1_migration(self):
        config = json.loads(PREP_PATH.read_text(encoding="utf-8"))
        self.assertEqual(config["status"], "GATE2_PASSED_P4D_P4E_AUTHORIZED")
        self.assertFalse(config["test_access_authorized"])
        self.assertFalse(config["training_authorized"])
        self.assertEqual(
            config["active_effective_language_rule"],
            "word_override_else_line_v2",
        )
        self.assertFalse(
            config["historical_checkpoint_disposition"]["overwrite_allowed"])

    def test_language_scopes_are_explicit_and_have_no_auto_default(self):
        config = json.loads(PREP_PATH.read_text(encoding="utf-8"))
        scopes = set(config["ratified_language_scopes"])
        self.assertEqual(
            scopes,
            {
                "HITTITE_ONLY",
                "SAME_LANGUAGE_AS_QUERY",
                "MULTILINGUAL_CONDITIONED",
                "CROSS_LANGUAGE_PARALLEL",
                "ALL_LANGUAGES_UNCONDITIONED",
            },
        )
        self.assertIn(None, config["prohibited_scope_values"])
        self.assertIn("auto", config["prohibited_scope_values"])

    def test_ratified_effective_language_rule_fails_closed(self):
        config = json.loads(LANGUAGE_CONFIG_PATH.read_text(encoding="utf-8"))
        rule = config["effective_rule"]
        auth = config["authorization"]

        self.assertEqual(rule["rule_id"], "word_override_else_line_v2")
        self.assertEqual(
            rule["explicit_empty_word_tag"]["effective_status"],
            "RESOLVED_WITH_SOURCE_ANOMALY",
        )
        self.assertEqual(
            rule["malformed_or_unrecognized_word_tag"]["action"],
            "UNRESOLVED_NO_FALLBACK",
        )
        self.assertEqual(
            rule["document_language_fallback"]["action"], "PROHIBITED")
        self.assertTrue(auth["gate_1_migration_implementation"])
        self.assertTrue(auth["gate_2_token_dataset_implementation"])
        self.assertTrue(
            auth["language_aware_api_and_workbench_implementation"])
        self.assertFalse(auth["test_access"])
        self.assertFalse(auth["gpu_training"])
        self.assertFalse(auth["training_dataset_export"])

    def test_gate2_acceptance_and_all_scope_contracts_are_recorded(self):
        acceptance = json.loads(
            GATE2_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        projections = json.loads(
            PROJECTION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(acceptance["status"], "PASS")
        self.assertFalse(
            acceptance["authorization_after_gate"]["training_authorized"])
        self.assertEqual(
            set(projections["projections"]),
            {
                "HITTITE_ONLY",
                "SAME_LANGUAGE_AS_QUERY",
                "MULTILINGUAL_CONDITIONED",
                "CROSS_LANGUAGE_PARALLEL",
                "ALL_LANGUAGES_UNCONDITIONED",
            },
        )
        self.assertTrue(
            projections["projections"][
                "ALL_LANGUAGES_UNCONDITIONED"]["ablation_only"])

    def test_unresolved_schema_preserves_quarantine_invariants(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        defs = schema["$defs"]
        occurrence = defs["occurrence"]["properties"]
        cluster = defs["cluster_proposal"]["properties"]
        event = defs["annotation_event"]["properties"]

        self.assertEqual(
            occurrence["ground_truth_status"]["const"], "NOT_CORPUS_TRUTH")
        self.assertFalse(cluster["scores_are_probabilities"]["const"])
        self.assertEqual(
            event["ground_truth_status"]["const"],
            "QUARANTINED_EXPERT_JUDGMENT",
        )
        self.assertTrue(event["requires_adjudication"]["const"])
        self.assertNotIn(
            "test",
            defs["source_location"]["properties"]["main_split"]["enum"],
        )
        categories = set(occurrence["categories"]["items"]["enum"])
        self.assertIn("EMPTY_LANGUAGE_TAG", categories)
        self.assertIn("MALFORMED_LANGUAGE_TAG", categories)
        sources = set(
            defs["language_assignment"]["properties"]["effective_source"][
                "enum"
            ]
        )
        self.assertIn("LINE_INHERITED_AFTER_EMPTY_WORD_TAG", sources)
        self.assertNotIn("DOCUMENT_INHERITED", sources)

    def test_existing_canonical_line_language_is_registered(self):
        raw = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        fields = raw["fields"]
        self.assertIn("line_lang_raw", fields)
        self.assertIn("line_lang_canonical", fields)
        self.assertEqual(
            fields["line_lang_canonical"]["depends_on"], ["line_lang_raw"])
        self.assertEqual(
            fields["line_lang_canonical"]["class"],
            "EDITORIAL_TRANSCRIPTION",
        )
        self.assertEqual(
            fields["effective_lang_canonical"]["class"],
            "EDITORIAL_TRANSCRIPTION",
        )


if __name__ == "__main__":
    unittest.main()
