#!/usr/bin/env python3
"""P2-E7: normalize governed packets into the expert decision contract.

This is an engineering transformation, not a scorer. It deterministically
adapts one P2-E4 packet and the three P2-E6 outcome kinds, validates them, and
emits compact integration examples plus a provenance manifest.

Usage:
    python scripts/p2e7_contract_check.py
"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import evidence_policy as ep
import expert_decision_contract as edc


P2E4_PATH = Path("phase2_out") / "p2e4_candidate_set_packets.jsonl"
P2E4_MANIFEST = (
    Path("phase2_out") / "p2e4_candidate_set_audit_manifest.json")
P2E6_PATH = Path("phase2_out") / "p2e6_multisign_packets.jsonl"
P2E6_MANIFEST = (
    Path("phase2_out") / "p2e6_multisign_horizon_manifest.json")
SCHEMA_PATH = Path("configs") / "expert_decision_contract.schema.json"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"
SPLITS_PATH = Path("p2_out") / "splits.parquet"
OUT_DIR = Path("phase2_out")
EXAMPLES_PATH = OUT_DIR / "p2e7_contract_examples.jsonl"
RESULT_PATH = OUT_DIR / "p2e7_contract_check.json"
MANIFEST_PATH = OUT_DIR / "p2e7_contract_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e7_contract.md"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path):
    with open(path, encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def provenance(probe, artifact, manifest):
    return {
        "source_probe": probe,
        "source_artifact": artifact.as_posix(),
        "source_artifact_sha256": sha256(artifact),
        "source_manifest": manifest.as_posix(),
        "source_manifest_sha256": sha256(manifest),
        "dev_example_only": True,
        "hidden_evaluation_payload_removed": True,
    }


def select_examples():
    p2e4 = load_jsonl(P2E4_PATH)
    p2e6 = load_jsonl(P2E6_PATH)
    if not p2e4:
        raise AssertionError("P2-E7: P2-E4 source packets are empty")
    by_outcome = {}
    for packet in p2e6:
        by_outcome.setdefault(packet["outcome"], packet)
    required = {
        "ABSTAIN_NO_INDEPENDENT_WITNESS_SET",
        "PRESENTED_SET_EXCLUDES_ATTESTED",
        "PRESENTED_SET_INCLUDES_ATTESTED",
    }
    if set(by_outcome) != required:
        raise AssertionError(
            "P2-E7: P2-E6 packet outcomes changed: "
            f"{sorted(by_outcome)}")

    p2e4_provenance = provenance("P2-E4", P2E4_PATH, P2E4_MANIFEST)
    p2e6_provenance = provenance("P2-E6", P2E6_PATH, P2E6_MANIFEST)
    examples = [
        edc.adapt_p2e4_packet(
            p2e4[0], "p2e7-example-single-sign", p2e4_provenance),
    ]
    for index, outcome in enumerate(sorted(required), 1):
        examples.append(edc.adapt_p2e6_packet(
            by_outcome[outcome],
            f"p2e7-example-multisign-{index}",
            p2e6_provenance,
        ))
    return examples


def validate_schema_identity(schema):
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise AssertionError("P2-E7: schema draft changed")
    suggestion = schema["$defs"]["suggestion_packet"]
    decision = schema["$defs"]["decision_record"]
    if (
            suggestion["properties"]["contract_version"].get("const")
            != edc.CONTRACT_VERSION
            or decision["properties"]["contract_version"].get("const")
            != edc.CONTRACT_VERSION):
        raise AssertionError("P2-E7: schema and validator versions disagree")


def write_report(summary):
    statuses = summary["example_status_counts"]
    lines = [
        "# Phase 2 P2-E7 expert decision contract",
        "",
        "**[ENGINEERING CONTRACT — underlying Phase 2 measurements remain "
        "PROBE, not for citation]**",
        "",
        "## Result",
        "",
        "Contract v1.0.0 now represents single- and multi-sign candidate sets, "
        "explicit abstention, typed evidence, assistance layers, collapsed "
        "equal-support tails, and hash-bound expert decisions. The executable "
        "validator forbids automatic completion, per-option truth-probability "
        "claims, silent truncation, hidden dev-evaluation payloads, and "
        "automatic ground-truth mutation.",
        "",
        f"Four governed dev integration examples validate: "
        f"{statuses.get('PRESENT_CANDIDATES', 0)} candidate packets and "
        f"{statuses.get('ABSTAIN_INSUFFICIENT_EVIDENCE', 0)} abstention "
        "packet. P2-E4 rates remain option-rank group audits; P2-E6 rates "
        "remain whole-set group audits.",
        "",
        "## Phase 2 closeout judgment",
        "",
        "Phase 2 has met its chartered definition of done: it maps encoded "
        "recoverability, evidence classes, horizon loss, uncertainty limits, "
        "and abstention boundaries. It did not establish automatic "
        "restoration or individual-option probabilities. The frozen test side "
        "remains untouched and no exploratory result is promoted to a citable "
        "claim.",
        "",
        "Next: implement a small expert UI prototype against this contract, "
        "starting with the stronger single-sign candidate path and treating "
        "multi-sign witness sets as optional, collapsible evidence. Do not "
        "train another scorer until expert interaction with these packets "
        "reveals a specific missing capability.",
        "",
        "No scoring pass occurred, so no content-sensitivity tracer was "
        "applicable. Input packet manifests and SHA-256 hashes are inherited "
        "and recorded; all hidden audit answers were removed.",
        "",
        "**Falsifier:** this contract is insufficient if an expert cannot "
        "record a justified select/reject/other/withhold decision without "
        "losing a material evidence type or being shown a misleading "
        "uncertainty claim.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_schema_identity(schema)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("catalog_assisted", POLICIES_PATH)
    semantic_fields = [
        "token",
        "cth",
        "candidate_rank_calibration_rate",
        "candidate_set_calibration_rate",
        "independent_witness_family_support_count",
        "independent_witness_family_support_share",
    ]
    ep.validate_semantic_features(semantic_fields, registry, policy)

    examples = select_examples()
    for packet in examples:
        edc.validate_suggestion_packet(packet)
        serialized = json.dumps(packet, ensure_ascii=False)
        if "dev_evaluation_only" in serialized:
            raise AssertionError("P2-E7: hidden evaluation payload leaked")

    counts = Counter(packet["status"] for packet in examples)
    summary = {
        "work_item": "P2-E7 expert decision contract and Phase 2 closeout",
        "contract_version": edc.CONTRACT_VERSION,
        "schema": SCHEMA_PATH.as_posix(),
        "validator": "lib/expert_decision_contract.py",
        "examples": EXAMPLES_PATH.as_posix(),
        "example_count": len(examples),
        "example_status_counts": dict(sorted(counts.items())),
        "single_sign_packets": sum(
            packet["mode"] == "SINGLE_SIGN" for packet in examples),
        "multi_sign_packets": sum(
            packet["mode"] == "MULTI_SIGN" for packet in examples),
        "hidden_evaluation_payload_present": False,
        "automatic_completion_allowed": False,
        "individual_option_truth_probability_available": False,
        "expert_judgment_ground_truth_effect":
            "QUARANTINED_PENDING_ADJUDICATION",
        "scoring_performed": False,
        "tracer_applicable": False,
        "test_side_accessed": False,
        "phase2_closeout": {
            "status": "COMPLETE_AS_EXPLORATORY_CHARACTERIZATION",
            "recoverability_map_produced": True,
            "evidence_layers_named": True,
            "horizon_and_uncertainty_limits_mapped": True,
            "abstention_boundary_implemented": True,
            "automatic_restoration_established": False,
            "per_option_probability_established": False,
            "test_side_remains_unspent": True,
            "probe_results_promoted_for_citation": False,
            "recommended_next_workstream":
                "expert UI prototype against contract v1.0.0",
        },
        "input_hashes": {
            "schema": sha256(SCHEMA_PATH),
            "evidence_registry": sha256(REGISTRY_PATH),
            "p2e4_packets": sha256(P2E4_PATH),
            "p2e4_manifest": sha256(P2E4_MANIFEST),
            "p2e6_packets": sha256(P2E6_PATH),
            "p2e6_manifest": sha256(P2E6_MANIFEST),
            "splits": sha256(SPLITS_PATH),
        },
    }

    manifest = ep.build_manifest(
        task="expert_decision_contract_adapter",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P2E4_PATH,
        split_manifest_path=SPLITS_PATH,
        config_path=SCHEMA_PATH,
        seed=20260723,
        declared_statistics_universe=(
            "deterministic integration sample: first governed P2-E4 dev "
            "packet plus one governed P2-E6 dev packet per recorded outcome; "
            "engineering transformation only, no rescoring or new corpus "
            "statistics; hidden evaluation payload removed"),
    )
    manifest.update({
        "contract_version": edc.CONTRACT_VERSION,
        "scoring_performed": False,
        "tracer_applicable": False,
        "test_side_accessed": False,
        "hidden_evaluation_payload_present": False,
        "source_input_hashes": summary["input_hashes"],
    })

    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    EXAMPLES_PATH.write_text(
        "".join(
            json.dumps(packet, ensure_ascii=False) + "\n"
            for packet in examples),
        encoding="utf-8",
    )
    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ep.write_manifest(manifest, MANIFEST_PATH)
    write_report(summary)
    print(
        f"P2-E7 complete: examples={len(examples)}, "
        f"statuses={dict(sorted(counts.items()))}.")
    print(
        f"Wrote {EXAMPLES_PATH}, {RESULT_PATH}, {MANIFEST_PATH}, "
        f"and {REPORT_PATH}.")


if __name__ == "__main__":
    main()
