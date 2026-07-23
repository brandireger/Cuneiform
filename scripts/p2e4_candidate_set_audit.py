#!/usr/bin/env python3
"""P2-E4: candidate-set utility and observable disagreement audit.

The probe reuses P2-E3's dev-only, composition-folded witness ranker. It
does not adjudicate restorations or textual variants. It asks whether an
intentionally hidden attested middle remains in a compact expert-facing
candidate set and records observable properties of top-choice disagreements.

Usage:
    python scripts/p2e4_candidate_set_audit.py
"""

import hashlib
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts
import eval_harness as eh
import evidence_policy as ep
import hittite_tokenizer as ht

import p2e2_abstention_calibration as p2e2
import p2e3_cross_calibration as p2e3
import p2e_witness_recoverability as p2e


CONFIG_PATH = Path("configs") / "p2e4_candidate_set_audit.json"
P2_OUT = Path("p2_out")
P4_OUT = Path("p4_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2e4_candidate_set_audit.json"
PACKET_PATH = OUT_DIR / "p2e4_candidate_set_packets.jsonl"
MANIFEST_PATH = OUT_DIR / "p2e4_candidate_set_audit_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e4_candidate_set_audit.md"
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


def percentile(values, proportion):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(proportion * len(ordered)) - 1)
    return ordered[index]


def candidate_rank(record):
    for rank, alternative in enumerate(
            record["ranking"]["alternatives"], 1):
        if alternative["proposal"] == record["gold"]:
            return rank
    return None


def candidate_set_metrics(records, depths):
    """Measure hidden-attested inclusion without asserting genuine truth."""
    ranks = [candidate_rank(record) for record in records]
    set_sizes = [
        record["ranking"]["alternative_count"] for record in records]
    result = {
        "contexts": len(records),
        "top1_exact_agreement_contexts":
            sum(rank == 1 for rank in ranks),
        "attested_lower_ranked_contexts":
            sum(rank is not None and rank > 1 for rank in ranks),
        "attested_absent_contexts": sum(rank is None for rank in ranks),
        "full_set_attested_inclusion_contexts":
            sum(rank is not None for rank in ranks),
        "full_set_attested_inclusion_percent":
            pct(sum(rank is not None for rank in ranks), len(records)),
        "full_set_attested_inclusion_wilson_95":
            p2e2.wilson_interval(
                sum(rank is not None for rank in ranks), len(records)),
        "candidate_set_size": {
            "mean": (
                round(statistics.mean(set_sizes), 3)
                if set_sizes else None),
            "median": (
                round(statistics.median(set_sizes), 3)
                if set_sizes else None),
            "p90": percentile(set_sizes, 0.9),
            "maximum": max(set_sizes) if set_sizes else None,
        },
        "prefix_sets": {},
    }
    for depth in depths:
        included = sum(
            rank is not None and rank <= depth for rank in ranks)
        effective_sizes = [min(depth, size) for size in set_sizes]
        result["prefix_sets"][str(depth)] = {
            "attested_inclusion_contexts": included,
            "attested_inclusion_percent": pct(included, len(records)),
            "attested_inclusion_wilson_95":
                p2e2.wilson_interval(included, len(records)),
            "mean_displayed_set_size": (
                round(statistics.mean(effective_sizes), 3)
                if effective_sizes else None),
        }
    return result


def composition_macro_metrics(records, depths):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["cth"]].append(record)
    labels = [str(depth) for depth in depths] + ["all"]
    values = {label: [] for label in labels}
    for composition_records in grouped.values():
        ranks = [candidate_rank(record) for record in composition_records]
        for depth in depths:
            values[str(depth)].append(
                100.0 * sum(
                    rank is not None and rank <= depth for rank in ranks)
                / len(ranks))
        values["all"].append(
            100.0 * sum(rank is not None for rank in ranks) / len(ranks))
    return {
        "compositions_with_contexts": len(grouped),
        "attested_inclusion_percent": {
            label: {
                "mean": (
                    round(statistics.mean(percentages), 2)
                    if percentages else None),
                "median": (
                    round(statistics.median(percentages), 2)
                    if percentages else None),
                "minimum": (
                    round(min(percentages), 2) if percentages else None),
                "maximum": (
                    round(max(percentages), 2) if percentages else None),
            }
            for label, percentages in values.items()
        },
    }


def rank_calibration(records, rule, maximum_rank, estimand):
    accepted = [
        record for record in records
        if p2e2.rule_accepts(record["ranking"], rule)]
    result = {}
    for rank in range(1, maximum_rank + 1):
        available = [
            record for record in accepted
            if record["ranking"]["alternative_count"] >= rank]
        successes = sum(
            record["ranking"]["alternatives"][rank - 1]["proposal"]
            == record["gold"]
            for record in available)
        result[str(rank)] = {
            "estimand": estimand,
            "calibration_contexts_with_rank_available": len(available),
            "attested_agreement_contexts": successes,
            "calibrated_empirical_agreement": (
                round(successes / len(available), 6)
                if available else None),
            "wilson_95": p2e2.wilson_interval(
                successes, len(available)),
            "not_an_instance_truth_probability": True,
        }
    return result


def add_anchor_repeat_counts(records):
    counts = Counter(
        (
            record["fragment_id"],
            record["left_anchor"],
            record["right_anchor"],
        )
        for record in records
    )
    for record in records:
        record["query_anchor_occurrence_count"] = counts[(
            record["fragment_id"],
            record["left_anchor"],
            record["right_anchor"],
        )]
    return records


def add_line_indices(records, edges):
    line_indices = {}
    for row in edges.itertuples(index=False):
        line_indices[row.fragment_id] = [
            int(value["line_index_in_doc"])
            for value in sorted(
                json.loads(row.lines),
                key=lambda value: value["line_index_in_doc"])
        ]
    for record in records:
        positions = line_indices[record["fragment_id"]]
        position = record["line_position_in_fragment"]
        if position >= len(positions):
            raise AssertionError(
                "P2-E4: span line position exceeds fragment line map")
        record["line_index_in_doc"] = positions[position]
    return records


def disagreement_category(record):
    ranking = record["ranking"]
    top = ranking["alternatives"][0]["proposal"]
    rank = candidate_rank(record)
    if rank == 1:
        return "TOP_EXACT_ATTESTED_AGREEMENT"
    if rank is not None:
        return "ATTESTED_READING_LOWER_RANKED"
    if len(top) == 0:
        return "ATTESTED_READING_ABSENT_TOP_OMISSION"
    if len(top) < len(record["gold"]):
        return "ATTESTED_READING_ABSENT_TOP_SHORTER"
    if len(top) == len(record["gold"]):
        return "ATTESTED_READING_ABSENT_TOP_EQUAL_LENGTH_DIFFERENT"
    return "ATTESTED_READING_ABSENT_TOP_LONGER"


def disagreement_flags(record):
    ranking = record["ranking"]
    return {
        "multiple_attested_witness_middles":
            ranking["alternative_count"] > 1,
        "top_supported_by_multiple_independent_families":
            ranking["top_support"] > 1,
        "anchor_recurs_across_multiple_compositions":
            record["anchor_formulaicity_cth_df"] > 1,
        "same_anchor_repeats_within_query_fragment":
            record["query_anchor_occurrence_count"] > 1,
        "attested_reading_absent_from_all_witness_alternatives":
            candidate_rank(record) is None,
    }


def summarize_disagreements(records):
    disagreements = [
        record for record in records if candidate_rank(record) != 1]
    categories = Counter(
        disagreement_category(record) for record in disagreements)
    flags = Counter()
    for record in disagreements:
        flags.update({
            key: int(value)
            for key, value in disagreement_flags(record).items()
        })
    return {
        "disagreement_contexts": len(disagreements),
        "primary_observable_categories": {
            key: {
                "contexts": value,
                "percent_of_disagreements":
                    pct(value, len(disagreements)),
            }
            for key, value in sorted(categories.items())
        },
        "nonexclusive_observable_flags": {
            key: {
                "contexts": value,
                "percent_of_disagreements":
                    pct(value, len(disagreements)),
            }
            for key, value in sorted(flags.items())
        },
        "interpretation_rule": (
            "Categories describe observed sequence and witness behavior; "
            "they do not adjudicate variants, errors, or restorations."),
    }


def fold_candidate_sets(records, folds, rules, config):
    target = float(config["calibration_target"])
    target_key = str(target)
    maximum_rank = max(config["candidate_set_depths"])
    accepted = []
    fold_results = []
    for fold in folds:
        evaluation_cths = fold["cth"]
        calibration_records = [
            record for record in records
            if record["cth"] not in evaluation_cths]
        evaluation_records = [
            record for record in records
            if record["cth"] in evaluation_cths]
        metrics = p2e2.evaluate_rules_vectorized(
            calibration_records, rules)
        selected = p2e2.choose_rules(
            metrics,
            [target],
            int(config["minimum_calibration_accepts"]),
        )[target_key]
        if selected is None:
            fold_results.append({
                "fold": fold["fold"],
                "evaluation_cth": sorted(evaluation_cths),
                "selected_rule": None,
                "calibration_contexts": len(calibration_records),
                "evaluation_contexts": len(evaluation_records),
                "accepted_evaluation_contexts": 0,
                "rank_calibration": {},
            })
            continue
        rule = selected["rule"]
        calibration = rank_calibration(
            calibration_records,
            rule,
            maximum_rank,
            config["candidate_probability_estimand"],
        )
        fold_accepted = []
        for record in evaluation_records:
            if not p2e2.rule_accepts(record["ranking"], rule):
                continue
            copied = dict(record)
            copied["evaluation_fold"] = fold["fold"]
            copied["selected_rule"] = rule
            copied["rank_calibration"] = calibration
            fold_accepted.append(copied)
        accepted.extend(fold_accepted)
        fold_results.append({
            "fold": fold["fold"],
            "evaluation_cth": sorted(evaluation_cths),
            "selected_rule": rule,
            "selected_rule_calibration_metrics": selected,
            "calibration_contexts": len(calibration_records),
            "evaluation_contexts": len(evaluation_records),
            "accepted_evaluation_contexts": len(fold_accepted),
            "rank_calibration": calibration,
        })
    return accepted, fold_results


def candidate_packet(record, policy_name, maximum_alternatives):
    ranking = record["ranking"]
    flags = disagreement_flags(record)
    shown = ranking["alternatives"][:maximum_alternatives]
    alternatives = []
    for rank, alternative in enumerate(shown, 1):
        alternatives.append({
            "rank": rank,
            "middle": list(alternative["proposal"]),
            "independent_witness_family_count":
                alternative["support_count"],
            "supporting_witness_families":
                list(alternative["supporting_families"]),
            "evidence_class": "EDITORIAL_TRANSCRIPTION",
            "calibration": record["rank_calibration"].get(str(rank)),
        })
    return {
        "proposed_relation": "EXPERT_MISSING_CONTEXT_CANDIDATE_SET",
        "decision": "PRESENT_CANDIDATE_SET",
        "expert_action_required": True,
        "expert_may_select_reject_or_withhold_judgment": True,
        "expert_selection_becomes_ground_truth_automatically": False,
        "evidence_policy": policy_name,
        "query": {
            "fragment_id": record["fragment_id"],
            "cth": record["cth"],
            "span_ordinal": record["span_ordinal"],
            "line_index_in_doc": record["line_index_in_doc"],
            "sign_offset_in_line": record["sign_offset_in_line"],
            "left_anchor": list(record["left_anchor"]),
            "right_anchor": list(record["right_anchor"]),
        },
        "candidate_set": {
            "alternatives": alternatives,
            "total_alternatives": ranking["alternative_count"],
            "alternatives_truncated":
                ranking["alternative_count"] > len(alternatives),
            "other_or_unsupported_available": True,
            "probability_warning": (
                "Calibration values are rank-conditioned group estimates "
                "from other compositions, not probabilities that this "
                "particular lost reading is true."),
        },
        "evidence": {
            "unique_top": ranking["unique_top"],
            "top_support_families": ranking["top_support"],
            "runner_up_support_families": ranking["runner_up_support"],
            "support_margin": ranking["support_margin"],
            "dominance": round(ranking["dominance"], 6),
            "anchor_formulaicity_cth_df":
                record["anchor_formulaicity_cth_df"],
            "available_independent_witness_family_count":
                record["available_independent_witness_family_count"],
            "query_anchor_occurrence_count":
                record["query_anchor_occurrence_count"],
        },
        "observable_disagreement_category":
            disagreement_category(record),
        "observable_flags": flags,
        "support": alternatives[:1],
        "contradictions": alternatives[1:],
        "enabled_assistance_layers": [
            "OBSERVED_DOCUMENT_STRUCTURE",
            "EDITORIAL_TRANSCRIPTION",
            "CATALOG_METADATA",
        ],
        "editorial_features_used": ["token"],
        "model_features_used": [],
        "abstention_reason": None,
        "dev_evaluation_only": {
            "intentionally_hidden_attested_middle": list(record["gold"]),
            "attested_candidate_rank": candidate_rank(record),
            "never_available_to_ranker": True,
            "not_truth_for_a_genuine_lacuna": True,
        },
    }


def select_packets(records, policy_name, per_category, maximum_alternatives):
    grouped = defaultdict(list)
    for record in records:
        if candidate_rank(record) != 1:
            grouped[disagreement_category(record)].append(record)
    selected = []
    for category in sorted(grouped):
        ordered = sorted(
            grouped[category],
            key=lambda record: (
                record["cth"],
                record["fragment_id"],
                record["span_ordinal"],
            ),
        )
        chosen = []
        used_cths = set()
        for record in ordered:
            if record["cth"] in used_cths:
                continue
            chosen.append(record)
            used_cths.add(record["cth"])
            if len(chosen) == per_category:
                break
        if len(chosen) < per_category:
            chosen_ids = {
                (record["fragment_id"], record["span_ordinal"])
                for record in chosen}
            for record in ordered:
                identity = (record["fragment_id"], record["span_ordinal"])
                if identity in chosen_ids:
                    continue
                chosen.append(record)
                if len(chosen) == per_category:
                    break
        selected.extend(
            candidate_packet(record, policy_name, maximum_alternatives)
            for record in chosen)
    return selected


def candidate_set_tracer():
    ranking = {
        "alternatives": [
            {"proposal": ("variant",), "support_count": 2,
             "supporting_families": ("f1", "f2")},
            {"proposal": ("heldout",), "support_count": 1,
             "supporting_families": ("f3",)},
        ],
        "alternative_count": 2,
    }
    record = {"cth": 1, "gold": ("heldout",), "ranking": ranking}
    metrics = candidate_set_metrics([record], [1, 2])
    passed = (
        metrics["prefix_sets"]["1"]["attested_inclusion_contexts"] == 0
        and metrics["prefix_sets"]["2"]["attested_inclusion_contexts"] == 1
        and disagreement_category(record)
        == "ATTESTED_READING_LOWER_RANKED"
    )
    result = {
        "synthetic_top1_miss_top2_inclusion_pass": passed,
        "blocking_failures": int(not passed),
    }
    if not passed:
        raise AssertionError(f"P2-E4 candidate-set tracer failed: {result}")
    return result


def write_report(summary, elapsed_seconds):
    selected = summary["selector_accepted_candidate_sets"]["micro"]
    selected_macro = summary["selector_accepted_candidate_sets"][
        "composition_macro"]["attested_inclusion_percent"]["all"]
    supported = summary["all_witness_supported_candidate_sets"]["micro"]
    disagreements = summary["observable_disagreement_audit"]
    prefix_rows = []
    for depth, values in selected["prefix_sets"].items():
        interval = values["attested_inclusion_wilson_95"]
        prefix_rows.append(
            f"| {depth} | {values['mean_displayed_set_size']} | "
            f"{values['attested_inclusion_contexts']:,}/"
            f"{selected['contexts']:,} "
            f"({values['attested_inclusion_percent']}%) | "
            f"[{interval[0] * 100:.1f}, {interval[1] * 100:.1f}] |")
    category_rows = [
        f"| `{category}` | {values['contexts']:,} | "
        f"{values['percent_of_disagreements']}% |"
        for category, values in
        disagreements["primary_observable_categories"].items()
    ]
    lines = [
        "# Phase 2 P2-E4 expert candidate-set audit",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Tracer block",
        "",
        "- Base tracers: PASS, zero blocking failures; historical D18 T4 "
        "remains diagnostic and non-blocking.",
        "- Reused anchored scorer/ranker and formulaicity T1: PASS.",
        "- Candidate-set tracer: PASS; a synthetic rank-2 attested reading "
        "missed top-1 and was retained at top-2.",
        "",
        "## Question and method",
        "",
        "For Q0/Q3, does a compact ranked option set retain intentionally "
        "hidden attested text when top-1 differs, and what observable "
        "conditions characterize remaining disagreements? The primary "
        "two-anchor/one-sign P2-E3 records were reused under the same five "
        "composition-disjoint 90%-target selectors. No category below "
        "adjudicates a variant, error, or restoration.",
        "",
        "## Findings",
        "",
        f"Across all {supported['contexts']:,} witness-supported contexts, "
        f"the full preserved set included the hidden attested reading in "
        f"{supported['full_set_attested_inclusion_percent']}%; median set "
        f"size was {supported['candidate_set_size']['median']} and p90 was "
        f"{supported['candidate_set_size']['p90']}. The fold selectors "
        f"presented {selected['contexts']:,} contexts "
        f"({summary['selector_coverage_percent_of_all_eligible']}% of all "
        "eligible spans).",
        "",
        "| displayed depth | mean options shown | attested inclusion | "
        "95% Wilson CI |",
        "|---:|---:|---:|---:|",
        *prefix_rows,
        "",
        f"The complete preserved set included the attested reading in "
        f"{selected['full_set_attested_inclusion_contexts']:,}/"
        f"{selected['contexts']:,} "
        f"({selected['full_set_attested_inclusion_percent']}%). Thus "
        f"{selected['attested_lower_ranked_contexts']:,} top-1 misses were "
        "recoverable by showing alternatives; "
        f"{selected['attested_absent_contexts']:,} were absent from all "
        "independent-witness middles.",
        f"Across the {summary['selector_accepted_candidate_sets']['composition_macro']['compositions_with_contexts']} "
        f"CTHs with presented contexts, full-set composition-macro inclusion "
        f"had mean {selected_macro['mean']}% and median "
        f"{selected_macro['median']}% (range {selected_macro['minimum']}–"
        f"{selected_macro['maximum']}%), so the pooled result is not a "
        "uniform composition-level guarantee.",
        "",
        "| observable category among top-1 disagreements | contexts | share |",
        "|---|---:|---:|",
        *category_rows,
        "",
        f"Nonexclusive flags: "
        f"{disagreements['nonexclusive_observable_flags']['anchor_recurs_across_multiple_compositions']['percent_of_disagreements']}% "
        "used anchors recurring across multiple CTHs, and "
        f"{disagreements['nonexclusive_observable_flags']['same_anchor_repeats_within_query_fragment']['percent_of_disagreements']}% "
        "repeated the same anchors within the query fragment.",
        "",
        "Rank-conditioned calibration estimates with `n` and Wilson CIs are "
        "saved in every sampled packet. They are coarse group estimates "
        "from other compositions, not instance-level truth probabilities.",
        "",
        "## Interpretation",
        "",
        "The candidate-set formulation recovers some information hidden by "
        "top-1 exact match, but it does not turn every disagreement into a "
        "valid restoration. Cases where the attested middle is absent need "
        "alignment/variant-aware investigation or abstention; the typed "
        "packets preserve that distinction for expert review.",
        "",
        f"Cost: {elapsed_seconds:.1f}s compute; budget ≤"
        f"{summary['parameters']['time_budget_hours']}h. Profile "
        f"`{summary['evidence_policy']}`; dev only; test, restorations, `cu`, "
        "morphology, and model-generated text untouched.",
        "",
        "**Falsifier:** the candidate-set benefit would be wrong if an "
        "untouched composition-disjoint evaluation shows that additional "
        "displayed alternatives do not increase attested-span inclusion "
        "beyond top-1 at a comparably small set size.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    policy_name = config["evidence_policy"]
    seed = int(config["seed"])

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(policy_name, POLICIES_PATH)
    semantic_fields = [
        "token", "damage_state", "line_index_in_doc", "cth",
        "anchor_formulaicity_cth_df",
        "available_independent_witness_family_count",
        "query_anchor_occurrence_count",
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
        label="P2-E4 dev attested-only")

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_cth = {
        row.fragment_id: int(row.cth)
        for row in edges.itertuples(index=False)}
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)}
    fragments_by_cth = defaultdict(list)
    for fragment_id, cth in fragment_cth.items():
        fragments_by_cth[cth].append(fragment_id)

    anchor_length = int(config["anchor_length"])
    mask_length = int(config["mask_length"])
    requested_by_cth = defaultdict(set)
    for fragment_id, lines in line_sequences.items():
        requested_by_cth[fragment_cth[fragment_id]].update(
            p2e.requested_anchor_keys(
                lines, anchor_length, [mask_length]))
    requested = {
        anchor_length: set().union(*requested_by_cth.values())}
    anchor_index = p2e.build_anchor_index(
        line_sequences,
        line_sequences,
        fragment_families,
        anchor_length,
        requested_by_cth,
        fragment_cth,
        max_middle=int(config["maximum_witness_middle_length"]),
    )
    formulaicity, formulaicity_metadata = (
        p2e3.load_formulaicity_statistics(
            requested,
            int(config["maximum_witness_middle_length"])))

    p2e_t1 = p2e.run_p2e_t1(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_index,
    )
    p2e2_t1 = p2e2.scramble_rank_tracer(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_index,
    )
    formula_t1 = p2e3.formulaicity_tracer()
    candidate_t1 = candidate_set_tracer()

    records = p2e2.build_span_records(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_index,
        anchor_length,
        mask_length,
        set(fragment_cth.values()),
    )
    records = p2e3.enrich_records(
        records,
        anchor_length,
        formulaicity,
        fragment_families,
        fragments_by_cth,
        config["formulaicity_bins"],
        config["witness_availability_bins"],
    )
    add_anchor_repeat_counts(records)
    add_line_indices(records, edges)

    weights = Counter(record["cth"] for record in records)
    folds = p2e3.assign_composition_folds(
        weights, set(weights), int(config["folds"]))
    rules = p2e2.generate_rules(config)
    accepted, fold_results = fold_candidate_sets(
        records, folds, rules, config)
    supported = [
        record for record in records
        if record["ranking"]["alternatives"]]
    depths = [int(value) for value in config["candidate_set_depths"]]
    supported_metrics = candidate_set_metrics(supported, depths)
    selected_metrics = candidate_set_metrics(accepted, depths)
    packets = select_packets(
        accepted,
        policy.name,
        int(config["packets_per_disagreement_category"]),
        int(config["maximum_packet_alternatives"]),
    )

    summary = {
        "probe": "P2-E4 expert candidate-set audit",
        "probe_label": "PROBE — not for citation",
        "evidence_policy": policy.name,
        "target_split": "dev with five composition-disjoint held-out folds",
        "test_side_accessed": False,
        "restorations_included": False,
        "gold_available_to_ranker": False,
        "parameters": config,
        "eligible_contexts": len(records),
        "witness_supported_contexts": len(supported),
        "selector_accepted_contexts": len(accepted),
        "selector_coverage_percent_of_all_eligible":
            pct(len(accepted), len(records)),
        "formulaicity_statistics": formulaicity_metadata,
        "folds": fold_results,
        "tracers": {
            "base": base_tracers,
            "p2e_t1": p2e_t1,
            "p2e2_t1": p2e2_t1,
            "formulaicity_t1": formula_t1,
            "candidate_set_t1": candidate_t1,
        },
        "all_witness_supported_candidate_sets": {
            "micro": supported_metrics,
            "composition_macro":
                composition_macro_metrics(supported, depths),
        },
        "selector_accepted_candidate_sets": {
            "micro": selected_metrics,
            "composition_macro":
                composition_macro_metrics(accepted, depths),
        },
        "observable_disagreement_audit":
            summarize_disagreements(accepted),
        "evidence_packet_count": len(packets),
        "interpretation_limits": [
            "Agreement with intentionally masked attested text is not truth "
            "for a genuine lacuna.",
            "Observable disagreement categories do not adjudicate variants, "
            "errors, omissions, or restorations.",
            "Rank-conditioned calibration is a group estimate from other "
            "compositions, not an instance truth probability.",
            "Formulaicity, witness availability, and query-anchor recurrence "
            "are analysis fields, not ranking features.",
        ],
        "input_hashes": {
            "config": sha256(CONFIG_PATH),
            "evidence_registry": sha256(REGISTRY_PATH),
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "decomposed_corpus_parquet":
                sha256(P4_OUT / "decomposed_corpus.parquet"),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
            "tokenizer_json":
                sha256(Path("configs") / "tokenizer.json"),
        },
    }

    manifest = ep.build_manifest(
        task="duplicate_parallel_candidate_set_audit",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P4_OUT / "decomposed_corpus.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=CONFIG_PATH,
        seed=seed,
        declared_statistics_universe=(
            "primary a2_m1 records from frozen dev only; abstention rules "
            "and rank-conditioned calibration fit on the four non-held-out "
            "dev composition folds; formulaicity fit over unambiguous real-"
            "composition train+dev content; no test or discovery content"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "test_side_accessed": False,
        "restoration_included": False,
        "model_scoring_performed": False,
        "gold_available_to_ranker": False,
        "composition_disjoint_folds": int(config["folds"]),
        "input_hashes": summary["input_hashes"],
    })

    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    PACKET_PATH.write_text(
        "".join(
            json.dumps(packet, ensure_ascii=False) + "\n"
            for packet in packets),
        encoding="utf-8",
    )
    ep.write_manifest(manifest, MANIFEST_PATH)
    elapsed = time.perf_counter() - started
    write_report(summary, elapsed)
    print(
        f"P2-E4 complete: {len(records)} eligible, "
        f"{len(accepted)} selector-accepted, {len(packets)} packets.")
    print(
        f"Wrote {RESULT_PATH}, {PACKET_PATH}, {MANIFEST_PATH}, "
        f"and {REPORT_PATH}")


if __name__ == "__main__":
    main()
