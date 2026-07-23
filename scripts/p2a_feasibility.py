#!/usr/bin/env python3
"""Phase 2 P2-A feasibility probe: is a true seam target encoded?

This probe consumes only split/control metadata, editorial join relations as
labels, and structural fragment line membership. It does not read
transliteration, ``cu``, restorations, or model output, and computes no score.

Usage:
    python scripts/p2a_feasibility.py
"""

import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts
import evidence_policy as ep


SEED = 20260723
TIME_BUDGET_HOURS = 2
TARGET_SPLIT = "dev"
P2_OUT = Path("p2_out")
OUT_DIR = Path("phase2_out")
REPORT_PATH = Path("reports") / "phase2_p2a_feasibility.md"
RESULT_PATH = OUT_DIR / "p2a_feasibility.json"
MANIFEST_PATH = OUT_DIR / "p2a_feasibility_manifest.json"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"

# parent_doc is deliberately the first field in join_pairs.jsonl. Extract it
# before decoding any other field so disallowed splits are never parsed.
PARENT_PREFIX = re.compile(
    rb'^\{"parent_doc":\s*("(?:\\.|[^"])*")')
EXCLUSIVE_CONTENT_MARKER = b', "exclusive_content":'


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_lookup_fail_closed(splits):
    grouped = splits.groupby("doc_id", sort=False)["main_split"].agg(
        lambda values: frozenset(values))
    lookup = {}
    ambiguous = set()
    for doc_id, values in grouped.items():
        if len(values) != 1:
            ambiguous.add(doc_id)
        else:
            lookup[doc_id] = next(iter(values))
    return lookup, ambiguous


def iter_allowed_join_metadata(path, split_lookup, ambiguous_ids,
                               allowed_split, audit_counts):
    """Decode metadata only for parents already proven to be allowed.

    The large ``exclusive_content`` payload is removed before JSON decoding.
    Rows outside ``allowed_split`` are neither decoded nor yielded.
    """
    with open(path, "rb") as source:
        for line_number, raw_line in enumerate(source, 1):
            match = PARENT_PREFIX.match(raw_line)
            if not match:
                raise ValueError(
                    f"{path}:{line_number}: parent_doc is not the first "
                    "decodable field")
            parent_doc = json.loads(match.group(1).decode("utf-8"))
            if parent_doc in ambiguous_ids:
                audit_counts["ambiguous_parent_rows_skipped"] += 1
                continue
            if parent_doc not in split_lookup:
                raise AssertionError(
                    f"{path}:{line_number}: parent_doc {parent_doc!r} is "
                    "absent from the frozen split map")
            if split_lookup[parent_doc] != allowed_split:
                continue

            marker_at = raw_line.find(EXCLUSIVE_CONTENT_MARKER)
            metadata_raw = (
                raw_line[:marker_at] + b"}"
                if marker_at >= 0 else raw_line
            )
            record = json.loads(metadata_raw.decode("utf-8"))
            if record["parent_doc"] != parent_doc:
                raise AssertionError(
                    f"{path}:{line_number}: parent prefix disagrees with "
                    "decoded metadata")
            yield record


def structural_relation(lines_a, lines_b):
    set_a, set_b = set(lines_a), set(lines_b)
    shared = sorted(set_a.intersection(set_b))
    positions_a = {line: pos for pos, line in enumerate(lines_a)}
    positions_b = {line: pos for pos, line in enumerate(lines_b)}
    row_deltas = sorted({
        positions_b[line] - positions_a[line] for line in shared
    })

    if shared:
        ordering = "overlap"
    elif max(lines_a) < min(lines_b):
        ordering = "a_before_b"
    elif max(lines_b) < min(lines_a):
        ordering = "b_before_a"
    else:
        ordering = "interleaved_without_shared_rows"

    return {
        "shared_rows": len(shared),
        "ordering": ordering,
        "row_offset_identifiable": bool(shared) and len(row_deltas) == 1,
        "row_offset_consistent": len(row_deltas) <= 1,
        "n_distinct_row_deltas": len(row_deltas),
    }


def write_report(summary, elapsed_seconds):
    tier_rows = []
    for tier in sorted(summary["by_tier"]):
        values = summary["by_tier"][tier]
        tier_rows.append(
            f"| {tier} | {values['pairs']} | "
            f"{values['row_offset_identifiable']} | "
            f"{values['ordering_only']} | "
            f"{values['interleaved_without_shared_rows']} | "
            f"{values['inconsistent_row_offsets']} |")

    lines = [
        "# Phase 2 P2-A feasibility probe",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Question",
        "",
        "Does TLHdig/P2 encode a true within-line seam and offset that can "
        "serve as the target for P2-A's handed-over-truth localization test?",
        "",
        "## What I did",
        "",
        f"Inspected {summary['relation_rows']} `{TARGET_SPLIT}` relation "
        f"rows, of which {summary['mapped_pairs']} mapped to the canonical "
        "fragment universe. The probe decoded no "
        "transliteration, `cu`, restoration, test-side join payload, or "
        "model output. Budget: "
        f"{TIME_BUDGET_HOURS} hours; elapsed: {elapsed_seconds:.1f} seconds.",
        "",
        "## What I found",
        "",
        f"- [PROBE] {summary['row_offset_identifiable']} / "
        f"{summary['mapped_pairs']} mapped pairs have an editor-derived, consistent "
        "row-alignment offset because their member line sets share at least "
        "one parent-document row.",
        f"- [PROBE] {summary['ordering_only']} / "
        f"{summary['mapped_pairs']} mapped pairs "
        "identify only which member's row range comes first; they do not "
        "identify a row offset.",
        f"- [PROBE] {summary['interleaved_without_shared_rows']} / "
        f"{summary['mapped_pairs']} mapped pairs have interleaved ranges without a shared "
        "row and therefore supply neither a unique row offset nor simple "
        "ordering.",
        f"- [PROBE] {summary['inconsistent_row_offsets']} / "
        f"{summary['mapped_pairs']} mapped pairs have shared rows but more "
        "than one positional row delta, so they do not supply one consistent "
        "offset.",
        f"- [PROBE] {summary['missing_fragment_mapping']} dev relation rows "
        "were excluded because one or both fragment IDs are absent from the "
        "canonical edge universe.",
        f"- [PROBE] {summary['shared_count_mismatches']} pair records "
        "disagree with the line-set intersection count.",
        f"- [PROBE] {summary['ambiguous_parent_rows_skipped']} relation "
        "row was excluded before payload decoding because its parent "
        "`doc_id` has conflicting frozen split assignments.",
        "- [PROBE] 0 pairs encode a member-specific within-line sign span or "
        "fracture column. Shared `{€N+M}` rows are represented as one fused "
        "parent line assigned to both members, not as separate left/right "
        "halves.",
        "",
        "| tier | pairs | identifiable row offset | ordering only | interleaved | inconsistent offset |",
        "|---|---:|---:|---:|---:|---:|",
        *tier_rows,
        "",
        "## What it rules in / rules out",
        "",
        "The corpus supports a row-alignment probe for the subset with shared "
        "rows. It does **not** support the P2-A test as worded—scoring a true "
        "within-line seam against wrong seam offsets—because the target seam "
        "column is absent. The existing D17 `offset` skips whole leading rows "
        "of a candidate; it is not an editor-supplied fracture-column label "
        "and must not be relabeled as ground truth.",
        "",
        "No scoring occurred, so a tracer block is not applicable.",
        "",
        "## Cost",
        "",
        f"{elapsed_seconds:.1f} seconds elapsed against a "
        f"{TIME_BUDGET_HOURS}-hour budget.",
        "",
        "## Falsifier",
        "",
        "This conclusion would be wrong if a source field not materialized in "
        "`edges.parquet` or the metadata-only join records encodes separate "
        "per-member within-line spans or an explicit fracture column.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("artifact_strict", POLICIES_PATH)
    ep.validate_semantic_features(["lines"], registry, policy)

    splits = pd.read_parquet(
        P2_OUT / "splits.parquet", columns=["doc_id", "main_split"])
    split_lookup, ambiguous_ids = split_lookup_fail_closed(splits)
    allowed_parents = {
        doc_id for doc_id, split in split_lookup.items()
        if split == TARGET_SPLIT
    }

    edges = pd.read_parquet(
        P2_OUT / "edges.parquet",
        columns=["fragment_id", "parent_doc", "siglum", "lines"])
    edges = edges[edges["parent_doc"].isin(allowed_parents)].copy()
    contracts.assert_unique_docids(edges)
    fragment_splits = {
        fragment_id: split_lookup[parent_doc]
        for fragment_id, parent_doc
        in zip(edges["fragment_id"], edges["parent_doc"])
    }
    contracts.assert_no_test(
        edges["fragment_id"], fragment_splits,
        label="P2-A feasibility edge universe")

    line_sets = {}
    for row in edges.itertuples(index=False):
        line_records = json.loads(row.lines)
        line_sets[row.fragment_id] = sorted(
            item["line_index_in_doc"] for item in line_records)

    counters = Counter()
    by_tier = {}
    join_path = P2_OUT / "join_pairs.jsonl"
    for pair in iter_allowed_join_metadata(
            join_path, split_lookup, ambiguous_ids, TARGET_SPLIT, counters):
        counters["pairs"] += 1
        fid_a = (
            f"{pair['parent_doc']}::{pair['member_a']['siglum']}")
        fid_b = (
            f"{pair['parent_doc']}::{pair['member_b']['siglum']}")
        if fid_a not in line_sets or fid_b not in line_sets:
            counters["missing_fragment_mapping"] += 1
            continue

        relation = structural_relation(line_sets[fid_a], line_sets[fid_b])
        tier = pair["tier"]
        tier_counts = by_tier.setdefault(
            tier, {"pairs": 0, "row_offset_identifiable": 0,
                   "ordering_only": 0,
                   "interleaved_without_shared_rows": 0,
                   "inconsistent_row_offsets": 0})
        tier_counts["pairs"] += 1

        if relation["row_offset_identifiable"]:
            counters["row_offset_identifiable"] += 1
            tier_counts["row_offset_identifiable"] += 1
        elif relation["ordering"] in {"a_before_b", "b_before_a"}:
            counters["ordering_only"] += 1
            tier_counts["ordering_only"] += 1
        elif relation["ordering"] == "interleaved_without_shared_rows":
            counters["interleaved_without_shared_rows"] += 1
            tier_counts["interleaved_without_shared_rows"] += 1

        if not relation["row_offset_consistent"]:
            tier_counts["inconsistent_row_offsets"] += 1

        if relation["shared_rows"] != pair["n_shared_lines"]:
            counters["shared_count_mismatches"] += 1
        if not relation["row_offset_consistent"]:
            counters["inconsistent_row_offsets"] += 1

    summary = {
        "label": "PROBE — not for citation",
        "target_split": TARGET_SPLIT,
        "time_budget_hours": TIME_BUDGET_HOURS,
        "relation_rows": counters["pairs"],
        "mapped_pairs": counters["pairs"] -
            counters["missing_fragment_mapping"],
        "missing_fragment_mapping": counters["missing_fragment_mapping"],
        "row_offset_identifiable": counters["row_offset_identifiable"],
        "ordering_only": counters["ordering_only"],
        "interleaved_without_shared_rows":
            counters["interleaved_without_shared_rows"],
        "shared_count_mismatches": counters["shared_count_mismatches"],
        "ambiguous_parent_rows_skipped":
            counters["ambiguous_parent_rows_skipped"],
        "inconsistent_row_offsets": counters["inconsistent_row_offsets"],
        "within_line_seam_targets": 0,
        "by_tier": by_tier,
        "input_hashes": {
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "join_pairs_jsonl": sha256(join_path),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
        },
    }
    manifest = ep.build_manifest(
        task="physical_join_p2a_feasibility",
        evidence_policy=policy.name,
        features_requested=["lines"],
        registry=registry,
        policy=policy,
        dataset_manifest_path=P2_OUT / "edges.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=POLICIES_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "dev relation rows; canonical mapped join-pair subset"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "control_fields_observed": [
            "fragment_id", "parent_doc", "siglum", "main_split"],
        "labels_observed": ["join_tier", "join_type"],
        "label_evidence_class": "EDITORIAL_RELATION",
        "test_side_accessed": False,
        "scoring_performed": False,
        "input_hashes": summary["input_hashes"],
    })

    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    ep.write_manifest(manifest, MANIFEST_PATH)

    elapsed = time.perf_counter() - started
    write_report(summary, elapsed)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
