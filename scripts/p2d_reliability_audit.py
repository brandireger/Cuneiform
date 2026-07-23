#!/usr/bin/env python3
"""Phase 2 P2-D probe: audit the evidential basis of dev join labels.

This is a metadata-only audit.  It applies the frozen split gate before
decoding relation rows and never reads transliteration, restoration, ``cu``,
or test-side relation payloads.

Usage:
    python scripts/p2d_reliability_audit.py
"""

import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts
import evidence_policy as ep
from phase2_io import iter_allowed_join_metadata, split_lookup_fail_closed


SEED = 20260723
TIME_BUDGET_HOURS = 2
TARGET_SPLIT = "dev"
P2_OUT = Path("p2_out")
HARD_SET_PATH = Path("p4_out") / "p5_hard_set.json"
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2d_reliability.json"
MANIFEST_PATH = OUT_DIR / "p2d_reliability_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2d_reliability.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"

DIRECT = "direct_plus"
INDIRECT = "indirect_parenthesized_plus"
INFERRED = "line_cooccurrence_inferred"
UNKNOWN = "unsupported_or_unknown"
WEAKER_BASES = frozenset({INDIRECT, INFERRED})


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_relation(pair):
    """Map only source-supported field combinations; fail closed otherwise."""
    join_type = pair.get("join_type")
    declared = pair.get("declared_adjacent")
    if declared is True and join_type == "direct":
        return DIRECT
    if declared is True and join_type == "indirect":
        return INDIRECT
    if declared is False and join_type == "inferred_from_shared_lines":
        return INFERRED
    return UNKNOWN


def fisher_exact_2x2(table):
    """Two-sided and directional Fisher exact probabilities, stdlib only."""
    (a, b), (c, d) = table
    values = (a, b, c, d)
    if any(not isinstance(value, int) or value < 0 for value in values):
        raise ValueError("Fisher table cells must be non-negative integers")

    row_one = a + b
    col_one = a + c
    total = sum(values)
    denominator = math.comb(total, row_one)

    def probability(x):
        return (
            math.comb(col_one, x)
            * math.comb(total - col_one, row_one - x)
            / denominator
        )

    low = max(0, row_one - (total - col_one))
    high = min(row_one, col_one)
    observed = probability(a)
    support = range(low, high + 1)
    two_sided = sum(
        probability(x) for x in support
        if probability(x) <= observed + 1e-15
    )
    greater = sum(probability(x) for x in support if x >= a)
    less = sum(probability(x) for x in support if x <= a)
    odds_ratio = (
        math.inf if b * c == 0 and a * d > 0
        else 0.0 if a * d == 0
        else (a * d) / (b * c)
    )
    return {
        "odds_ratio": odds_ratio,
        "p_two_sided": min(1.0, two_sided),
        "p_enrichment_greater": min(1.0, greater),
        "p_depletion_less": min(1.0, less),
    }


def basis_family(bases):
    unique = sorted(set(bases))
    return unique[0] + "_only" if len(unique) == 1 else "mixed:" + "+".join(unique)


def has_weaker_basis(bases):
    return bool(set(bases).intersection(WEAKER_BASES))


def pct(numerator, denominator):
    return 100.0 * numerator / denominator if denominator else None


def write_report(summary, elapsed_seconds):
    relation = summary["relation_level"]
    query = summary["query_level"]
    parent = summary["parent_level_robustness"]
    hard = query["hard"]
    nonhard = query["nonhard"]
    query_test = query["fisher_exact_exploratory"]
    parent_test = parent["fisher_exact_exploratory"]

    lines = [
        "# Phase 2 P2-D ground-truth reliability audit",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Question",
        "",
        "Does TLHdig record different evidential bases for dev join labels, "
        "and is the frozen 46-query BM25 hard set enriched for weaker bases?",
        "",
        "## What I did",
        "",
        f"Audited all {relation['mapped_pairs']} canonical dev relation pairs "
        f"({query['all_queries']} query fragments) using only `join_type`, "
        "`declared_adjacent`, technical IDs, and the frozen hard-set list. "
        "The split gate ran before JSON decoding; no transliteration, "
        "restoration, `cu`, model score, or test-side payload was read. "
        f"Seed {SEED}; paths: `p2_out/join_pairs.jsonl`, "
        "`p2_out/splits.parquet`, `p2_out/edges.parquet`, and "
        "`p4_out/p5_hard_set.json`.",
        "",
        "## What I found",
        "",
        "| recorded basis | dev pairs | interpretation |",
        "|---|---:|---|",
        f"| direct `+` | {relation['basis_counts'][DIRECT]} | editor-declared "
        "direct physical join notation; not independently reverified here |",
        f"| indirect `(+)` | {relation['basis_counts'][INDIRECT]} | same "
        "object, not a direct physical fit; attributed on textual/content grounds |",
        f"| inferred from shared-line tags | "
        f"{relation['basis_counts'][INFERRED]} | parser-derived relation "
        "between non-adjacent members co-occurring in editor-supplied line tags |",
        f"| unsupported/unknown | {relation['basis_counts'][UNKNOWN]} | field "
        "combination does not support a stronger classification |",
        "",
        f"- [PROBE] {relation['weaker_known_pairs']} / "
        f"{relation['mapped_pairs']} pairs "
        f"({relation['weaker_known_pair_percent']:.1f}%) are indirect or "
        "shared-line-inferred rather than direct `+` pairs.",
        f"- [PROBE] At the frozen query unit, {hard['weaker_queries']} / "
        f"{hard['queries']} hard queries ({hard['weaker_percent']:.1f}%) "
        f"touch a weaker-basis relation versus {nonhard['weaker_queries']} / "
        f"{nonhard['queries']} non-hard queries "
        f"({nonhard['weaker_percent']:.1f}%). The hard set is not enriched; "
        f"the observed odds ratio is {query_test['odds_ratio']:.3f} "
        f"(one-sided enrichment p={query_test['p_enrichment_greater']:.3f}; "
        f"two-sided p={query_test['p_two_sided']:.3f}).",
        f"- [PROBE] Query rows are dependent within composite parents. A "
        f"parent-level robustness view changes direction but remains "
        f"inconclusive: {parent['hard_parents_with_weaker']} / "
        f"{parent['hard_parents']} hard-associated parents versus "
        f"{parent['nonhard_parents_with_weaker']} / "
        f"{parent['nonhard_parents']} other parents "
        f"(odds ratio {parent_test['odds_ratio']:.3f}, two-sided "
        f"p={parent_test['p_two_sided']:.3f}).",
        "- [PROBE] No source field in the governed relation artifacts marks "
        "a join as `proposed` or supplies a certainty grade. That requested "
        "category is unavailable, not zero.",
        f"- [PROBE] {relation['missing_fragment_mapping']} dev relation rows "
        "lack one or both canonical fragment mappings; "
        f"{relation['ambiguous_parent_rows_skipped']} ambiguous-parent row "
        "was quarantined before payload decoding.",
        "",
        "## What it rules in / rules out",
        "",
        "The dev gold is heterogeneous: a substantial share is indirect or "
        "algorithmically expanded from editorial shared-line attribution, "
        "so future physical-join reporting must keep these bases separate. "
        "This probe does **not** support the hypothesis that the BM25 hard "
        "set is hard because it contains more weak editorial claims. It also "
        "cannot measure absolute correctness or certainty: direct `+` is a "
        "notation class, not an independent physical re-fit audit.",
        "",
        "No content scoring occurred, so the tracer block is not applicable.",
        "",
        "## Cost",
        "",
        f"{elapsed_seconds:.1f} seconds elapsed against a "
        f"{TIME_BUDGET_HOURS}-hour budget.",
        "",
        "## Falsifier",
        "",
        "This conclusion would be wrong if a TLHdig field not materialized "
        "in the governed relation artifacts records proposal/certainty "
        "status and is systematically concentrated in the hard set.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy("artifact_strict", POLICIES_PATH)

    splits = pd.read_parquet(
        P2_OUT / "splits.parquet", columns=["doc_id", "main_split"])
    split_lookup, ambiguous_ids = split_lookup_fail_closed(splits)
    allowed_parents = {
        doc_id for doc_id, split in split_lookup.items()
        if split == TARGET_SPLIT
    }

    edges = pd.read_parquet(
        P2_OUT / "edges.parquet", columns=["fragment_id", "parent_doc"])
    edges = edges[edges["parent_doc"].isin(allowed_parents)].copy()
    contracts.assert_unique_docids(edges)
    fragment_splits = {
        fragment_id: split_lookup[parent_doc]
        for fragment_id, parent_doc
        in zip(edges["fragment_id"], edges["parent_doc"])
    }
    contracts.assert_no_test(
        edges["fragment_id"], fragment_splits,
        label="P2-D canonical dev fragment universe")
    valid_fragment_ids = set(edges["fragment_id"])

    hard_payload = json.loads(HARD_SET_PATH.read_text(encoding="utf-8"))
    hard_queries = set(hard_payload["hard_set_query_ids"])
    counters = Counter()
    pair_rows = []
    parent_bases = defaultdict(list)
    query_bases = defaultdict(list)

    join_path = P2_OUT / "join_pairs.jsonl"
    for pair in iter_allowed_join_metadata(
            join_path, split_lookup, ambiguous_ids, TARGET_SPLIT, counters):
        counters["relation_rows"] += 1
        fragment_a = (
            f"{pair['parent_doc']}::{pair['member_a']['siglum']}")
        fragment_b = (
            f"{pair['parent_doc']}::{pair['member_b']['siglum']}")
        if (fragment_a not in valid_fragment_ids
                or fragment_b not in valid_fragment_ids):
            counters["missing_fragment_mapping"] += 1
            continue

        basis = classify_relation(pair)
        pair_rows.append({
            "fragment_a": fragment_a,
            "fragment_b": fragment_b,
            "parent_doc": pair["parent_doc"],
            "basis": basis,
        })
        query_bases[fragment_a].append(basis)
        query_bases[fragment_b].append(basis)
        parent_bases[pair["parent_doc"]].append(basis)

    all_queries = set(query_bases)
    if not hard_queries.issubset(all_queries):
        missing = sorted(hard_queries - all_queries)
        raise AssertionError(
            f"hard-set query IDs absent from canonical dev relations: {missing}")
    if hard_payload["n_total"] != len(all_queries):
        raise AssertionError(
            "hard-set declared universe does not match canonical dev queries")
    if hard_payload["n_hard"] != len(hard_queries):
        raise AssertionError("hard-set declared count disagrees with IDs")

    nonhard_queries = all_queries - hard_queries
    basis_counts = Counter(row["basis"] for row in pair_rows)
    family_counts = {
        "all": Counter(basis_family(query_bases[q]) for q in all_queries),
        "hard": Counter(basis_family(query_bases[q]) for q in hard_queries),
        "nonhard": Counter(
            basis_family(query_bases[q]) for q in nonhard_queries),
    }
    hard_weaker = sum(
        has_weaker_basis(query_bases[q]) for q in hard_queries)
    nonhard_weaker = sum(
        has_weaker_basis(query_bases[q]) for q in nonhard_queries)
    query_table = [
        [hard_weaker, len(hard_queries) - hard_weaker],
        [nonhard_weaker, len(nonhard_queries) - nonhard_weaker],
    ]

    hard_parents = {
        row["parent_doc"] for row in pair_rows
        if row["fragment_a"] in hard_queries
        or row["fragment_b"] in hard_queries
    }
    nonhard_parents = set(parent_bases) - hard_parents
    hard_parents_weaker = sum(
        has_weaker_basis(parent_bases[parent]) for parent in hard_parents)
    nonhard_parents_weaker = sum(
        has_weaker_basis(parent_bases[parent]) for parent in nonhard_parents)
    parent_table = [
        [hard_parents_weaker, len(hard_parents) - hard_parents_weaker],
        [
            nonhard_parents_weaker,
            len(nonhard_parents) - nonhard_parents_weaker,
        ],
    ]

    summary = {
        "label": "PROBE — not for citation",
        "target_split": TARGET_SPLIT,
        "time_budget_hours": TIME_BUDGET_HOURS,
        "classification_contract": {
            DIRECT: "declared_adjacent=true and join_type=direct",
            INDIRECT: "declared_adjacent=true and join_type=indirect",
            INFERRED: (
                "declared_adjacent=false and "
                "join_type=inferred_from_shared_lines"
            ),
            UNKNOWN: "all other field combinations",
            "proposed_status_available": False,
            "certainty_grade_available": False,
        },
        "relation_level": {
            "relation_rows": counters["relation_rows"],
            "mapped_pairs": len(pair_rows),
            "missing_fragment_mapping":
                counters["missing_fragment_mapping"],
            "ambiguous_parent_rows_skipped":
                counters["ambiguous_parent_rows_skipped"],
            "basis_counts": {
                basis: basis_counts[basis]
                for basis in (DIRECT, INDIRECT, INFERRED, UNKNOWN)
            },
            "weaker_known_pairs":
                basis_counts[INDIRECT] + basis_counts[INFERRED],
            "weaker_known_pair_percent": pct(
                basis_counts[INDIRECT] + basis_counts[INFERRED],
                len(pair_rows),
            ),
        },
        "query_level": {
            "all_queries": len(all_queries),
            "hard": {
                "queries": len(hard_queries),
                "weaker_queries": hard_weaker,
                "weaker_percent": pct(hard_weaker, len(hard_queries)),
            },
            "nonhard": {
                "queries": len(nonhard_queries),
                "weaker_queries": nonhard_weaker,
                "weaker_percent":
                    pct(nonhard_weaker, len(nonhard_queries)),
            },
            "basis_family_counts": {
                group: dict(sorted(counts.items()))
                for group, counts in family_counts.items()
            },
            "fisher_table": query_table,
            "fisher_table_columns": ["any_weaker_basis", "direct_only"],
            "fisher_exact_exploratory": fisher_exact_2x2(query_table),
            "dependence_warning": (
                "Query fragments from the same composite parent are not "
                "independent; the Fisher result is exploratory."
            ),
        },
        "parent_level_robustness": {
            "hard_parents": len(hard_parents),
            "hard_parents_with_weaker": hard_parents_weaker,
            "nonhard_parents": len(nonhard_parents),
            "nonhard_parents_with_weaker": nonhard_parents_weaker,
            "fisher_table": parent_table,
            "fisher_table_columns": ["any_weaker_basis", "direct_only"],
            "fisher_exact_exploratory": fisher_exact_2x2(parent_table),
        },
        "input_hashes": {
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "hard_set_json": sha256(HARD_SET_PATH),
            "join_pairs_jsonl": sha256(join_path),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
        },
    }

    manifest = ep.build_manifest(
        task="physical_join_p2d_reliability",
        evidence_policy=policy.name,
        features_requested=[],
        registry=registry,
        policy=policy,
        dataset_manifest_path=join_path,
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=POLICIES_PATH,
        seed=SEED,
        declared_statistics_universe=(
            "canonical mapped dev join relations and their frozen BM25 "
            "hard-set query stratification"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "control_fields_observed": [
            "fragment_id", "parent_doc", "siglum", "main_split"],
        "labels_observed": ["join_type", "declared_adjacent"],
        "label_evidence_class": "EDITORIAL_RELATION",
        "stratification_fields_observed": ["hard_set_membership"],
        "stratification_evidence_class": "MODEL_DERIVED",
        "test_side_accessed": False,
        "content_scoring_performed": False,
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
