#!/usr/bin/env python3
"""Phase 2 P2-E3: five-fold composition cross-calibration audit.

This probe reuses P2-E2's traced evidence-only witness ranker.  It asks
whether calibration-selected abstention rules transfer when every eligible
dev composition is held out once.  The three one-sign cells that qualified
in P2-E2 are tested; multi-sign reconstruction is not reopened.

Formulaicity is an analysis stratum, never a ranking feature.  It is measured
as cross-composition document frequency of the exact attested left/right
anchor pair with any bounded 0-12-sign middle, over the declared full
real-composition non-test universe (train + dev).  Witness availability and
per-CTH outcomes are reported separately.

Usage:
    python scripts/p2e3_cross_calibration.py
"""

import hashlib
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts
import eval_harness as eh
import evidence_policy as ep
import hittite_tokenizer as ht
from phase2_io import split_lookup_fail_closed

import p2e2_abstention_calibration as p2e2
import p2e_witness_recoverability as p2e


CONFIG_PATH = Path("configs") / "p2e3_cross_calibration.json"
P2_OUT = Path("p2_out")
P4_OUT = Path("p4_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2e3_cross_calibration.json"
MANIFEST_PATH = OUT_DIR / "p2e3_cross_calibration_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e3_cross_calibration.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(numerator, denominator):
    return round(100.0 * numerator / denominator, 2) if denominator else None


def anchored_key_document_frequency(
        sequences_by_cth, requested_by_anchor, max_middle):
    """Cross-CTH DF of requested anchor pairs with a bounded middle."""
    result = {length: Counter() for length in requested_by_anchor}
    for _, lines in sorted(sequences_by_cth.items()):
        seen = {length: set() for length in requested_by_anchor}
        for line in lines:
            for length, requested in requested_by_anchor.items():
                for left_start in range(
                        0, len(line) - (2 * length) + 1):
                    middle_start = left_start + length
                    left = tuple(line[left_start:middle_start])
                    for middle_length in range(max_middle + 1):
                        right_start = middle_start + middle_length
                        right_end = right_start + length
                        if right_end > len(line):
                            break
                        key = (
                            left,
                            tuple(line[right_start:right_end]),
                        )
                        if key in requested:
                            seen[length].add(key)
        for length in requested_by_anchor:
            result[length].update(seen[length])
    return result


def load_formulaicity_statistics(requested_by_anchor, max_middle):
    """Fit cross-CTH anchor frequency over real train+dev only.

    The allowlist is formed from split/control metadata before the content
    parquet reader is called.  Test and discovery content never enter.
    """
    splits = pd.read_parquet(
        P2_OUT / "splits.parquet",
        columns=["doc_id", "cth", "is_bin", "main_split"],
    )
    split_lookup, ambiguous = split_lookup_fail_closed(splits)
    allowed_rows = splits[
        (~splits["doc_id"].isin(ambiguous))
        & (~splits["is_bin"])
        & (splits["main_split"].isin(["train", "dev"]))
    ].drop_duplicates("doc_id")
    allowed_doc_cth = {
        row.doc_id: int(row.cth)
        for row in allowed_rows.itertuples(index=False)
    }
    allowed_ids = sorted(allowed_doc_cth)
    if not allowed_ids:
        raise AssertionError("P2-E3: formulaicity universe is empty")

    decomposed = pd.read_parquet(
        P4_OUT / "decomposed_corpus.parquet",
        columns=[
            "doc_id", "line_index_in_doc", "word_pos", "token",
            "damage_state",
        ],
        filters=[("doc_id", "in", allowed_ids)],
    )
    returned_ids = set(decomposed["doc_id"])
    unexpected = returned_ids.difference(allowed_doc_cth)
    if unexpected:
        raise AssertionError(
            "P2-E3: formulaicity reader returned prohibited parents: "
            f"{sorted(unexpected)[:5]}")
    contracts.assert_no_test(
        returned_ids, split_lookup, label="P2-E3 formulaicity universe")

    ordered = decomposed.sort_values(
        ["doc_id", "line_index_in_doc", "word_pos"])
    lines_by_cth = defaultdict(list)
    for (doc_id, line_idx), group in ordered.groupby(
            ["doc_id", "line_index_in_doc"], sort=False):
        token_states = list(zip(group["token"], group["damage_state"]))
        line = p2e.informative_attested_line(int(line_idx), token_states)
        if line:
            lines_by_cth[allowed_doc_cth[doc_id]].append(line)

    frequencies = anchored_key_document_frequency(
        lines_by_cth, requested_by_anchor, max_middle)
    universe_name = "real_composition_train_plus_dev_cth_formulaicity"
    stamped = contracts.stamp_stats(
        frequencies,
        universe_name,
        len(lines_by_cth),
        content_hash=sha256(P4_OUT / "decomposed_corpus.parquet"),
    )
    contracts.assert_stats_provenance(
        stamped, universe_name, len(lines_by_cth))
    metadata = {
        "universe_name": universe_name,
        "n_compositions": len(lines_by_cth),
        "n_documents": len(returned_ids),
        "n_decomposed_rows": len(decomposed),
        "ambiguous_doc_ids_quarantined": len(ambiguous),
        "requested_anchor_pair_counts": {
            str(length): len(requested_by_anchor[length])
            for length in requested_by_anchor
        },
        "observed_anchor_pair_counts": {
            str(length): len(frequencies[length])
            for length in requested_by_anchor
        },
        "maximum_middle_length": max_middle,
        "content_hash": stamped["content_hash"],
    }
    return stamped, metadata


def bin_value(value, specifications):
    for specification in specifications:
        minimum = int(specification["minimum"])
        maximum = specification["maximum"]
        if value >= minimum and (
                maximum is None or value <= int(maximum)):
            return specification["name"]
    raise AssertionError(f"P2-E3: value {value} fits no configured bin")


def enrich_records(
        records,
        anchor_length,
        formulaicity_stats,
        fragment_families,
        fragments_by_cth,
        formula_bins,
        witness_bins):
    families_by_cth = {
        cth: {fragment_families[fragment_id] for fragment_id in fragment_ids}
        for cth, fragment_ids in fragments_by_cth.items()
    }
    frequencies = formulaicity_stats["stats"][anchor_length]
    for record in records:
        key = (record["left_anchor"], record["right_anchor"])
        formulaicity = int(frequencies.get(key, 0))
        if formulaicity < 1:
            raise AssertionError(
                "P2-E3: dev anchor absent from declared formulaicity universe")
        available = len(
            families_by_cth[record["cth"]].difference(
                {record["query_family"]}))
        if available < 1:
            raise AssertionError(
                "P2-E3: structurally eligible record has no witness family")
        record["anchor_formulaicity_cth_df"] = formulaicity
        record["formulaicity_stratum"] = bin_value(
            formulaicity, formula_bins)
        record["available_independent_witness_family_count"] = available
        record["witness_availability_stratum"] = bin_value(
            available, witness_bins)
    return records


def assign_composition_folds(weights, all_cths, n_folds):
    """Deterministic greedy span balancing with CTH as the indivisible unit."""
    folds = [
        {"fold": index, "cth": set(), "primary_eligible_spans": 0}
        for index in range(n_folds)
    ]
    ordered = sorted(
        all_cths, key=lambda cth: (-weights.get(cth, 0), cth))
    for cth in ordered:
        destination = min(
            folds,
            key=lambda fold: (
                fold["primary_eligible_spans"],
                len(fold["cth"]),
                fold["fold"],
            ),
        )
        destination["cth"].add(cth)
        destination["primary_eligible_spans"] += weights.get(cth, 0)

    covered = set().union(*(fold["cth"] for fold in folds))
    if covered != set(all_cths):
        raise AssertionError("P2-E3: fold assignment lost compositions")
    for left in folds:
        for right in folds:
            if left["fold"] < right["fold"] and left["cth"] & right["cth"]:
                raise AssertionError("P2-E3: composition leaked across folds")
    return folds


def empty_counts():
    return Counter({
        "eligible_spans": 0,
        "spans_with_any_witness_alternative": 0,
        "accepted_spans": 0,
        "top1_exact_agreement_spans": 0,
        "gold_anywhere_in_preserved_alternatives": 0,
    })


def update_counts(counts, records, rule):
    for record in records:
        ranking = record["ranking"]
        counts["eligible_spans"] += 1
        counts["spans_with_any_witness_alternative"] += int(
            bool(ranking["alternatives"]))
        if rule is None or not p2e2.rule_accepts(ranking, rule):
            continue
        counts["accepted_spans"] += 1
        top = ranking["alternatives"][0]["proposal"]
        counts["top1_exact_agreement_spans"] += int(top == record["gold"])
        counts["gold_anywhere_in_preserved_alternatives"] += int(any(
            alternative["proposal"] == record["gold"]
            for alternative in ranking["alternatives"]))


def finalize_counts(counts):
    eligible = counts["eligible_spans"]
    supported = counts["spans_with_any_witness_alternative"]
    accepted = counts["accepted_spans"]
    exact = counts["top1_exact_agreement_spans"]
    result = dict(counts)
    result.update({
        "coverage_percent_of_eligible": pct(accepted, eligible),
        "coverage_percent_of_supported": pct(accepted, supported),
        "top1_exact_agreement_percent": pct(exact, accepted),
        "top1_exact_wilson_95": p2e2.wilson_interval(exact, accepted),
        "gold_anywhere_percent": pct(
            counts["gold_anywhere_in_preserved_alternatives"], accepted),
    })
    return result


def accumulate_strata(destination, records, rule):
    for record in records:
        for dimension, key in (
            ("formulaicity", record["formulaicity_stratum"]),
            ("witness_availability",
             record["witness_availability_stratum"]),
            ("composition", str(record["cth"])),
        ):
            update_counts(destination[dimension][key], [record], rule)


def finalize_strata(destination):
    return {
        dimension: {
            key: finalize_counts(counts)
            for key, counts in sorted(groups.items())
        }
        for dimension, groups in destination.items()
    }


def cross_calibrate_cell(records, folds, rules, config):
    targets = [str(value) for value in config["calibration_targets"]]
    fold_results = []
    strata = {
        "formulaicity": defaultdict(empty_counts),
        "witness_availability": defaultdict(empty_counts),
        "composition": defaultdict(empty_counts),
    }
    stratification_target = str(config["stratification_target"])

    for fold in folds:
        eval_cths = fold["cth"]
        calibration_records = [
            record for record in records if record["cth"] not in eval_cths]
        evaluation_records = [
            record for record in records if record["cth"] in eval_cths]
        calibration_metrics = p2e2.evaluate_rules_vectorized(
            calibration_records, rules)
        chosen = p2e2.choose_rules(
            calibration_metrics,
            config["calibration_targets"],
            int(config["minimum_calibration_accepts"]),
        )
        evaluated = p2e2.evaluate_selected_rules(
            chosen, evaluation_records)
        baseline = p2e2.evaluate_rule(
            evaluation_records, {
                "minimum_top_support_families": 1,
                "minimum_support_margin": 1,
                "minimum_dominance": 0.0,
                "maximum_alternatives": None,
            })
        fold_results.append({
            "fold": fold["fold"],
            "evaluation_cth": sorted(eval_cths),
            "calibration_records": len(calibration_records),
            "evaluation_records": len(evaluation_records),
            "baseline": baseline,
            "selected_rules": evaluated,
        })
        selected = evaluated.get(stratification_target)
        selected_rule = (
            selected["selected_on_calibration"]["rule"]
            if selected is not None else None)
        accumulate_strata(strata, evaluation_records, selected_rule)

    aggregate = {}
    for target in targets:
        counts = empty_counts()
        available_folds = 0
        point_target_met = 0
        lower_target_met = 0
        for fold, result in zip(folds, fold_results):
            evaluation_records = [
                record for record in records if record["cth"] in fold["cth"]]
            selected = result["selected_rules"][target]
            rule = (
                selected["selected_on_calibration"]["rule"]
                if selected is not None else None)
            update_counts(counts, evaluation_records, rule)
            if selected is None:
                continue
            available_folds += 1
            heldout = selected["heldout_evaluation"]
            point_target_met += int(
                heldout["top1_exact_agreement_fraction"] is not None
                and heldout["top1_exact_agreement_fraction"] >= float(target))
            lower = heldout["top1_exact_wilson_95"][0]
            lower_target_met += int(
                lower is not None and lower >= float(target))
        aggregate[target] = {
            **finalize_counts(counts),
            "folds_with_calibration_rule": available_folds,
            "folds_heldout_point_target_met": point_target_met,
            "folds_heldout_lower_bound_target_met": lower_target_met,
            "total_folds": len(folds),
        }

    baseline_counts = empty_counts()
    baseline_rule = {
        "minimum_top_support_families": 1,
        "minimum_support_margin": 1,
        "minimum_dominance": 0.0,
        "maximum_alternatives": None,
    }
    update_counts(baseline_counts, records, baseline_rule)
    return {
        "folds": fold_results,
        "baseline_pooled": finalize_counts(baseline_counts),
        "targets_pooled": aggregate,
        "strata_at_target": {
            "target": float(config["stratification_target"]),
            "metrics": finalize_strata(strata),
        },
    }


def formulaicity_tracer():
    original = {
        1: [["A", "B", "x", "C", "D"]],
        2: [["A", "B", "y", "C", "D"]],
        3: [["X", "Y", "z", "Q", "R"]],
    }
    key = (("A", "B"), ("C", "D"))
    requested = {2: {key}}
    original_df = anchored_key_document_frequency(
        original, requested, max_middle=2)[2]
    corrupted = {
        1: [["A", "B", "x", "C", "D"]],
        2: [["D", "C", "y", "B", "A"]],
        3: [["X", "Y", "z", "Q", "R"]],
    }
    corrupted_df = anchored_key_document_frequency(
        corrupted, requested, max_middle=2)[2]
    passed = (
        original_df[key] == 2
        and corrupted_df[key] == 1
    )
    result = {
        "synthetic_cross_cth_frequency_pass": passed,
        "token_order_perturbation_changed_frequency": (
            original_df[key] != corrupted_df[key]),
        "blocking_failures": int(not passed),
    }
    if not passed:
        raise AssertionError(f"P2-E3 formulaicity tracer failed: {result}")
    return result


def composition_summary(composition_metrics):
    accepted = [
        value for value in composition_metrics.values()
        if value["accepted_spans"] > 0]
    reliable = [
        value for value in accepted
        if value["accepted_spans"] >= 20
        and value["top1_exact_agreement_percent"] is not None]
    accuracies = [
        value["top1_exact_agreement_percent"] for value in reliable]
    return {
        "compositions_total": len(composition_metrics),
        "compositions_with_any_accept": len(accepted),
        "compositions_with_at_least_20_accepts": len(reliable),
        "median_agreement_percent_at_least_20_accepts": (
            round(statistics.median(accuracies), 2) if accuracies else None),
        "minimum_agreement_percent_at_least_20_accepts": (
            min(accuracies) if accuracies else None),
        "maximum_agreement_percent_at_least_20_accepts": (
            max(accuracies) if accuracies else None),
    }


def write_report(summary, elapsed_seconds):
    rows = []
    for cell_name, result in summary["cells"].items():
        baseline = result["baseline_pooled"]
        target = result["targets_pooled"]["0.9"]
        interval = target["top1_exact_wilson_95"]
        interval_text = (
            "—" if interval[0] is None
            else f"[{interval[0] * 100:.1f}, {interval[1] * 100:.1f}]")
        rows.append(
            f"| {cell_name} | {baseline['coverage_percent_of_eligible']}% / "
            f"{baseline['top1_exact_agreement_percent']}% | "
            f"{target['folds_with_calibration_rule']}/5 | "
            f"{target['coverage_percent_of_eligible']}% / "
            f"{target['top1_exact_agreement_percent']}% {interval_text} | "
            f"{target['folds_heldout_lower_bound_target_met']}/5 |")

    primary = summary["cells"][summary["primary_cell"]]
    formula = primary["strata_at_target"]["metrics"]["formulaicity"]
    witness = primary["strata_at_target"]["metrics"]["witness_availability"]
    composition = summary["primary_composition_summary"]
    lines = [
        "# Phase 2 P2-E3 five-fold cross-calibration",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Tracer block",
        "",
        "- Base tracers: PASS, zero blocking failures; D18's historical "
        "diagnostic remains visible and non-blocking.",
        "- Anchored scorer and witness-ranker T1: PASS, 12/12 real canaries "
        "changed under token-order scrambling; candidate-order invariant.",
        "- Formulaicity T1: PASS; scrambling changed the synthetic "
        "cross-CTH n-gram frequency.",
        "",
        "## Question and method",
        "",
        "Do abstention rules transfer across compositions when every eligible "
        "dev CTH is held out once? Five CTH-disjoint folds were balanced by "
        "eligible spans. Rules were recalibrated on four folds and frozen for "
        "the fifth. Formulaicity was fit over the declared real-composition "
        "train+dev universe and used only for analysis.",
        "",
        "## Findings",
        "",
        "| cell | unique-top baseline coverage / agreement | folds with 90% "
        "calibration rule | pooled 90%-selector coverage / agreement [95% CI] "
        "| held-out folds retaining 90% lower bound |",
        "|---|---:|---:|---:|---:|",
        *rows,
        "",
        f"Primary a2_m1 formulaicity: rare (`cth_df_1`) "
        f"{formula['cth_df_1']['coverage_percent_of_eligible']}% coverage / "
        f"{formula['cth_df_1']['top1_exact_agreement_percent']}% agreement; "
        f"moderate (`cth_df_2_5`) "
        f"{formula['cth_df_2_5']['coverage_percent_of_eligible']}% / "
        f"{formula['cth_df_2_5']['top1_exact_agreement_percent']}%; common "
        f"(`cth_df_6_plus`) "
        f"{formula['cth_df_6_plus']['coverage_percent_of_eligible']}% / "
        f"{formula['cth_df_6_plus']['top1_exact_agreement_percent']}%.",
        f"Witness availability: one family "
        f"{witness['one_family']['coverage_percent_of_eligible']}% / "
        f"{witness['one_family']['top1_exact_agreement_percent']}%; two–three "
        f"{witness['two_to_three_families']['coverage_percent_of_eligible']}% / "
        f"{witness['two_to_three_families']['top1_exact_agreement_percent']}%; "
        f"four+ {witness['four_plus_families']['coverage_percent_of_eligible']}% / "
        f"{witness['four_plus_families']['top1_exact_agreement_percent']}%.",
        f"Composition heterogeneity: {composition['compositions_with_any_accept']}/"
        f"{composition['compositions_total']} CTHs received any acceptance; "
        f"among {composition['compositions_with_at_least_20_accepts']} with "
        f"≥20 accepts, median agreement was "
        f"{composition['median_agreement_percent_at_least_20_accepts']}% "
        f"(range {composition['minimum_agreement_percent_at_least_20_accepts']}–"
        f"{composition['maximum_agreement_percent_at_least_20_accepts']}%).",
        "",
        "## Interpretation",
        "",
        "The output distinguishes a reproducible pooled signal from fold- and "
        "composition-specific calibration failure. Formulaic and witness-rich "
        "contexts are reported, not silently treated as universal evidence. "
        "This remains masked-attested agreement, not truth for a real lacuna.",
        "",
        f"Cost: {elapsed_seconds:.1f}s compute; budget ≤"
        f"{summary['parameters']['time_budget_hours']}h. Profile "
        f"`{summary['evidence_policy']}`; test, restorations, `cu`, morphology, "
        "and model-generated text untouched.",
        "",
        "**Falsifier:** the instability conclusion would be wrong if a future "
        "untouched composition-disjoint benchmark retains the selected "
        "reliability lower bound consistently across folds and strata.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    policy_name = config["evidence_policy"]
    seed = int(config["seed"])

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(policy_name, POLICIES_PATH)
    semantic_fields = [
        "token", "damage_state", "line_index_in_doc", "cth",
        "anchor_formulaicity_cth_df",
        "available_independent_witness_family_count",
    ]
    ep.validate_semantic_features(semantic_fields, registry, policy)

    base_tracers = p2e.run_base_tracers()
    _, _, _, edges, decomposed = p2e.load_dev_inputs()
    line_index = p2e.build_line_index(decomposed)
    line_sequences, canonical_flat = p2e.render_fragments(edges, line_index)
    tokenizer = ht.Tokenizer.load()
    encoded = tokenizer.encode(canonical_flat, strict=True)
    contracts.assert_encoding_sane(
        encoded, tokenizer, max_unk=0.05,
        label="P2-E3 dev attested-only")

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_cth = {
        row.fragment_id: int(row.cth)
        for row in edges.itertuples(index=False)
    }
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)
    }
    fragments_by_cth = defaultdict(list)
    for fragment_id, cth in fragment_cth.items():
        fragments_by_cth[cth].append(fragment_id)

    cells = [
        (int(cell["anchor_length"]), int(cell["mask_length"]))
        for cell in config["cells"]
    ]
    anchor_lengths = sorted({anchor for anchor, _ in cells})
    anchor_indices = {}
    requested_by_anchor = {}
    for anchor_length in anchor_lengths:
        mask_lengths = sorted({
            mask for anchor, mask in cells if anchor == anchor_length})
        requested_by_cth = defaultdict(set)
        for fragment_id, lines in line_sequences.items():
            requested_by_cth[fragment_cth[fragment_id]].update(
                p2e.requested_anchor_keys(
                    lines, anchor_length, mask_lengths))
        requested_by_anchor[anchor_length] = set().union(
            *requested_by_cth.values())
        anchor_indices[anchor_length] = p2e.build_anchor_index(
            line_sequences,
            line_sequences,
            fragment_families,
            anchor_length,
            requested_by_cth,
            fragment_cth,
            max_middle=int(config["maximum_witness_middle_length"]),
        )

    formulaicity_stats, formulaicity_metadata = (
        load_formulaicity_statistics(
            requested_by_anchor,
            int(config["maximum_witness_middle_length"])))

    p2e_t1 = p2e.run_p2e_t1(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_indices[2],
    )
    p2e2_t1 = p2e2.scramble_rank_tracer(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_indices[2],
    )
    formula_t1 = formulaicity_tracer()

    records_by_cell = {}
    for anchor_length, mask_length in cells:
        name = f"a{anchor_length}_m{mask_length}"
        records = p2e2.build_span_records(
            line_sequences,
            fragment_cth,
            fragment_families,
            fragments_by_cth,
            anchor_indices[anchor_length],
            anchor_length,
            mask_length,
            set(fragment_cth.values()),
        )
        records_by_cell[name] = enrich_records(
            records,
            anchor_length,
            formulaicity_stats,
            fragment_families,
            fragments_by_cth,
            config["formulaicity_bins"],
            config["witness_availability_bins"],
        )

    primary_name = (
        f"a{config['primary_cell']['anchor_length']}"
        f"_m{config['primary_cell']['mask_length']}")
    primary_weights = Counter(
        record["cth"] for record in records_by_cell[primary_name])
    all_cths = set().union(*(
        {record["cth"] for record in records}
        for records in records_by_cell.values()))
    folds = assign_composition_folds(
        primary_weights, all_cths, int(config["folds"]))
    rules = p2e2.generate_rules(config)

    cell_results = {
        name: cross_calibrate_cell(records, folds, rules, config)
        for name, records in records_by_cell.items()
    }
    primary_compositions = cell_results[primary_name][
        "strata_at_target"]["metrics"]["composition"]
    summary = {
        "probe": "P2-E3 five-fold composition cross-calibration",
        "probe_label": "PROBE — not for citation",
        "evidence_policy": policy.name,
        "primary_cell": primary_name,
        "target_split": "dev with five composition-disjoint held-out folds",
        "test_side_accessed": False,
        "restorations_included": False,
        "gold_available_to_ranker": False,
        "formulaicity_available_to_ranker": False,
        "witness_availability_available_to_ranker": False,
        "parameters": config,
        "formulaicity_statistics": formulaicity_metadata,
        "folds": [
            {
                "fold": fold["fold"],
                "cth": sorted(fold["cth"]),
                "composition_count": len(fold["cth"]),
                "primary_eligible_spans": fold["primary_eligible_spans"],
            }
            for fold in folds
        ],
        "tracers": {
            "base": base_tracers,
            "p2e_t1": p2e_t1,
            "p2e2_t1": p2e2_t1,
            "formulaicity_t1": formula_t1,
        },
        "cells": cell_results,
        "primary_composition_summary":
            composition_summary(primary_compositions),
        "interpretation_limits": [
            "Cross-validation remains entirely inside dev and is exploratory.",
            "Formulaicity and witness availability are analysis strata, not "
            "ranking features.",
            "Agreement with intentionally masked attested text is not truth "
            "for a genuine lacuna.",
            "Parallel witnesses can preserve legitimate variants or omissions.",
        ],
        "input_hashes": {
            "config": sha256(CONFIG_PATH),
            "evidence_registry": sha256(REGISTRY_PATH),
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "decomposed_corpus_parquet":
                sha256(P4_OUT / "decomposed_corpus.parquet"),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
            "tokenizer_json": sha256(Path("configs") / "tokenizer.json"),
        },
    }

    manifest = ep.build_manifest(
        task="duplicate_parallel_cross_calibration",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P4_OUT / "decomposed_corpus.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=CONFIG_PATH,
        seed=seed,
        declared_statistics_universe=(
            "abstention rules recalibrated within each recorded four-fold dev "
            "composition universe and evaluated on the fifth; formulaicity "
            "CTH document frequencies fit over all unambiguous real-composition "
            "train+dev content; no test or discovery content"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "test_side_accessed": False,
        "restoration_included": False,
        "model_scoring_performed": False,
        "gold_available_to_ranker": False,
        "formulaicity_used_for_stratification_only": True,
        "witness_availability_used_for_stratification_only": True,
        "composition_disjoint_folds": int(config["folds"]),
        "input_hashes": summary["input_hashes"],
    })

    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ep.write_manifest(manifest, MANIFEST_PATH)
    elapsed = time.perf_counter() - started
    write_report(summary, elapsed)
    print(
        f"P2-E3 complete: {len(all_cths)} CTHs across "
        f"{len(folds)} folds; cells={sorted(cell_results)}.")
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
