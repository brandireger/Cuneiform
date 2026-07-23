#!/usr/bin/env python3
"""tests/test_evidence_policy.py -- fail-closed contract tests for
lib/evidence_policy.py, per specs/EVIDENCE_POLICY.md's 12-case list
(the original 10 from cuneiform_expert_patch/EVIDENCE_POLICY_SPEC.md
plus 2 corpus-specific cases found while verifying the registry).

Usage:
    python tests/test_evidence_policy.py
    python -m unittest tests.test_evidence_policy   (from repo root)

Stdlib unittest only -- no pytest dependency, consistent with this
project's stdlib-or-common-deps preference (CLAUDE.md).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import evidence_policy as ep

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "configs" / "evidence_registry.yaml"
POLICIES_PATH = Path(__file__).resolve().parent.parent / "configs" / "evidence_policies.yaml"


class TestEvidencePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = ep.load_registry(REGISTRY_PATH)
        cls.strict = ep.load_policy("artifact_strict", POLICIES_PATH)
        cls.transcription = ep.load_policy("transcription_assisted", POLICIES_PATH)
        cls.catalog = ep.load_policy("catalog_assisted", POLICIES_PATH)
        cls.scholar = ep.load_policy("scholar_assisted", POLICIES_PATH)
        cls.discovery = ep.load_policy("discovery_assisted", POLICIES_PATH)
        cls.all_policies = [cls.strict, cls.transcription, cls.catalog,
                             cls.scholar, cls.discovery]

    # 1. unknown field raises
    def test_unknown_field_raises(self):
        with self.assertRaises(ep.EvidencePolicyError):
            ep.validate_fields(["totally_made_up_field_xyz"], self.registry, self.strict)

    # 2. `cu` raises in every standard policy
    def test_cu_denied_everywhere(self):
        for policy in self.all_policies:
            with self.subTest(policy=policy.name):
                with self.assertRaises(ep.EvidencePolicyError):
                    ep.validate_fields(["cu"], self.registry, policy)

    # 3. restoration field raises under strict and transcription-assisted
    def test_restoration_field_denied_under_strict_and_transcription(self):
        # sign_full depends on sign_damage_states + signs (EDITORIAL_TRANSCRIPTION
        # effective class) -- use cu as the clean EDITORIAL_RESTORATION example,
        # already covered by test 2. Also check a hypothetical direct restoration
        # class field is rejected under strict (no restoration-class field is
        # currently registered outside cu/EDITORIAL_RESTORATION denial, so this
        # doubles as confirmation that EDITORIAL_RESTORATION is absent from
        # both policies' allow lists).
        self.assertNotIn(ep.EvidenceClass.EDITORIAL_RESTORATION, self.strict.allowed)
        self.assertNotIn(ep.EvidenceClass.EDITORIAL_RESTORATION, self.transcription.allowed)
        self.assertIn(ep.EvidenceClass.EDITORIAL_RESTORATION, self.scholar.allowed)

    # 4. catalog field raises under strict/transcription-assisted
    def test_catalog_field_denied_under_strict_and_transcription(self):
        with self.assertRaises(ep.EvidencePolicyError):
            ep.validate_fields(["cth"], self.registry, self.strict)
        with self.assertRaises(ep.EvidencePolicyError):
            ep.validate_fields(["cth"], self.registry, self.transcription)
        # allowed under catalog_assisted
        result = ep.validate_fields(["cth"], self.registry, self.catalog)
        self.assertEqual(result[0].evidence_class, ep.EvidenceClass.CATALOG_METADATA)

    # 5. model-derived field raises outside discovery mode
    def test_model_derived_denied_outside_discovery(self):
        for policy in (self.strict, self.transcription, self.catalog, self.scholar):
            with self.subTest(policy=policy.name):
                with self.assertRaises(ep.EvidencePolicyError):
                    ep.validate_fields(["bm25_score"], self.registry, policy)
        result = ep.validate_fields(["bm25_score"], self.registry, self.discovery)
        self.assertEqual(result[0].evidence_class, ep.EvidenceClass.MODEL_DERIVED)

    # 6. derived feature inherits the strongest dependency class
    def test_derived_feature_inherits_strongest_dependency(self):
        # sign_attested depends_on [signs (EDITORIAL_TRANSCRIPTION),
        # sign_damage_states (OBSERVED_DOCUMENT_STRUCTURE)] -- effective
        # class must be the more interpretive of the two: EDITORIAL_TRANSCRIPTION.
        eff = ep.effective_class("sign_attested", self.registry)
        self.assertEqual(eff, ep.EvidenceClass.EDITORIAL_TRANSCRIPTION)
        # restored_sign_fraction depends_on two OBSERVED_DOCUMENT_STRUCTURE
        # fields -- effective class stays OBSERVED_DOCUMENT_STRUCTURE.
        eff2 = ep.effective_class("restored_sign_fraction", self.registry)
        self.assertEqual(eff2, ep.EvidenceClass.OBSERVED_DOCUMENT_STRUCTURE)

    # 7. manifest lists all consumed fields and classes
    def test_manifest_lists_all_consumed_fields_and_classes(self):
        manifest = ep.build_manifest(
            task="textual_affinity", evidence_policy="transcription_assisted",
            features_requested=["sign_attested"],
            registry=self.registry, policy=self.transcription, seed=20260722,
        )
        self.assertEqual(manifest["features_observed"], ["sign_attested"])
        self.assertEqual(manifest["evidence_classes_used"],
                          [ep.EvidenceClass.EDITORIAL_TRANSCRIPTION.value])
        self.assertIn("git_commit", manifest)
        self.assertIn("created_utc", manifest)

    # 8. policy behavior is deterministic
    def test_policy_behavior_deterministic(self):
        r1 = ep.validate_fields(["sign_attested", "cth"], self.registry, self.catalog)
        r2 = ep.validate_fields(["sign_attested", "cth"], self.registry, self.catalog)
        self.assertEqual([(fe.field, fe.evidence_class) for fe in r1],
                          [(fe.field, fe.evidence_class) for fe in r2])

    # 9. semantic fields cannot be accessed by an unregistered alias
    def test_unregistered_alias_raises(self):
        # e.g. someone tries "attested_signs" instead of the registered
        # "sign_attested" -- must NOT silently resolve or fuzzy-match.
        with self.assertRaises(ep.EvidencePolicyError):
            ep.validate_fields(["attested_signs"], self.registry, self.transcription)

    # 10. technical IDs permitted for control flow but rejected in a
    # semantic feature matrix
    def test_technical_ids_control_flow_vs_semantic(self):
        # allowed for control-flow validation (every standard policy
        # includes SYSTEM_TECHNICAL for join/bookkeeping purposes)
        result = ep.validate_fields(["doc_id"], self.registry, self.strict)
        self.assertEqual(result[0].evidence_class, ep.EvidenceClass.SYSTEM_TECHNICAL)
        # but rejected outright when requested as a semantic feature
        with self.assertRaises(ep.EvidencePolicyError):
            ep.validate_semantic_features(["doc_id"], self.registry, self.strict)

    # 11. mrp_lemma_candidates denied in every policy including discovery
    def test_mrp_denied_everywhere_including_discovery(self):
        for policy in self.all_policies:
            with self.subTest(policy=policy.name):
                with self.assertRaises(ep.EvidencePolicyError):
                    ep.validate_fields(["mrp_lemma_candidates"], self.registry, policy)
                with self.assertRaises(ep.EvidencePolicyError):
                    ep.validate_fields(["mrp_selected"], self.registry, policy)

    # 12. lemma_full/lemma_attested denied via mixed-dependency lineage
    def test_lemma_fields_denied_via_mixed_lineage(self):
        for field_name in ("lemma_full", "lemma_attested"):
            with self.subTest(field=field_name):
                for policy in self.all_policies:
                    with self.assertRaises(ep.EvidencePolicyError):
                        ep.validate_fields([field_name], self.registry, policy)

    # --- extra: registry load itself fails closed on a dangling dependency ---
    def test_registry_load_rejects_dangling_dependency(self):
        import tempfile
        import yaml
        bad = {"fields": {"a": {"class": "SYSTEM_TECHNICAL", "depends_on": ["nonexistent_b"]}}}
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.safe_dump(bad, f)
            path = f.name
        try:
            with self.assertRaises(ep.EvidencePolicyError):
                ep.load_registry(path)
        finally:
            Path(path).unlink()

    # --- extra: EDITORIAL_RELATION never in a standard policy's allow list ---
    def test_editorial_relation_never_in_standard_policies(self):
        for policy in self.all_policies:
            with self.subTest(policy=policy.name):
                self.assertNotIn(ep.EvidenceClass.EDITORIAL_RELATION, policy.allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
