#!/usr/bin/env python3
"""
scripts/evidence_policy_smoke.py -- standalone smoke script for the
evidence-policy infrastructure (lib/evidence_policy.py), per
specs/EVIDENCE_POLICY.md. NOT a Phase 2 probe: makes no research
claim, computes no scores, reports nothing citable. Its only job is to
exercise the policy system end-to-end against real fragment data and
produce one real sample manifest, per IMPLEMENTATION_REQUEST_FOR_CLAUDE.md
item 7 ("Integrate the policy and manifest into exactly one new Phase 2
probe or a tiny standalone smoke script").

Usage:
    python scripts/evidence_policy_smoke.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import eval_harness as eh
import evidence_policy as ep

REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"
OUT_MANIFEST = Path("p4_out") / "evidence_policy_smoke_manifest.json"


def main():
    print("Loading registry + policies...")
    registry = ep.load_registry(REGISTRY_PATH)
    strict = ep.load_policy("artifact_strict", POLICIES_PATH)
    transcription = ep.load_policy("transcription_assisted", POLICIES_PATH)
    print(f"  registry: {len(registry)} fields")
    print(f"  policies loaded: {strict.name}, {transcription.name}")

    print("\nLoading a few real fragments (eval_harness.load_fragment_universe)...")
    frags, splits, doc_table = eh.load_fragment_universe()
    sample = frags[frags["main_split"] == "dev"].head(3)
    sample_ids = sample["fragment_id"].tolist()
    print(f"  sample fragment_ids: {sample_ids}")

    # ---- demonstrate a permitted request under transcription_assisted ----
    print("\n[1] validate_fields(['sign_attested'], transcription_assisted) -- expect PASS")
    result = ep.validate_fields(["sign_attested"], registry, transcription)
    for fe in result:
        print(f"    {fe.field}: {fe.evidence_class.value} -- {fe.rationale[:70]}...")

    # ---- demonstrate the SAME field correctly rejected under artifact_strict ----
    print("\n[2] validate_fields(['sign_attested'], artifact_strict) -- expect FAIL (EDITORIAL_TRANSCRIPTION not permitted)")
    try:
        ep.validate_fields(["sign_attested"], registry, strict)
        print("    UNEXPECTED: did not raise")
    except ep.EvidencePolicyError as e:
        print(f"    raised as expected: {e}")

    # ---- demonstrate cu is denied even under the most permissive standard policy ----
    print("\n[3] validate_fields(['cu'], discovery_assisted) -- expect FAIL (explicitly denied everywhere)")
    discovery = ep.load_policy("discovery_assisted", POLICIES_PATH)
    try:
        ep.validate_fields(["cu"], registry, discovery)
        print("    UNEXPECTED: did not raise")
    except ep.EvidencePolicyError as e:
        print(f"    raised as expected: {e}")

    # ---- demonstrate a technical ID rejected as a semantic feature ----
    print("\n[4] validate_semantic_features(['doc_id', 'sign_attested'], transcription_assisted) -- expect FAIL (doc_id is SYSTEM_TECHNICAL)")
    try:
        ep.validate_semantic_features(["doc_id", "sign_attested"], registry, transcription)
        print("    UNEXPECTED: did not raise")
    except ep.EvidencePolicyError as e:
        print(f"    raised as expected: {e}")

    # ---- build and write one real sample manifest ----
    print("\n[5] Building a sample manifest for a hypothetical textual-affinity smoke run...")
    manifest = ep.build_manifest(
        task="textual_affinity",
        evidence_policy="transcription_assisted",
        features_requested=["sign_attested"],
        registry=registry,
        policy=transcription,
        dataset_manifest_path="p2_out/corpus.parquet",
        split_manifest_path="p2_out/splits.parquet",
        config_path=POLICIES_PATH,
        seed=20260722,
        declared_statistics_universe="full_non_test (per CLAUDE.md's corpus-statistics convention)",
    )
    manifest["_smoke_note"] = ("This is a smoke-test manifest, not a probe result. "
                                f"Sample fragment_ids used for demonstration: {sample_ids}")
    ep.write_manifest(manifest, OUT_MANIFEST)
    print(f"    wrote {OUT_MANIFEST}")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))

    print("\nSmoke script complete. All 4 fail-closed demonstrations behaved as expected.")


if __name__ == "__main__":
    main()
