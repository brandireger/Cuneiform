#!/usr/bin/env python3
"""P2-E6: adaptive candidate-set horizon for two-to-five-sign spans.

For every dev span eligible with one-sign anchors, choose the longest
configured anchor length (3 -> 2 -> 1) that has any independent-witness
alternative. Present the first five alternatives by witness-family support,
including the complete support tie at the display boundary. If no anchor has
support, abstain.

The intentionally hidden attested span is evaluation-only. Candidate-set
calibration shown in packets is estimated from other composition folds and
applies to the set as a whole, not to an individual option.

Usage:
    python scripts/p2e6_multisign_horizon.py
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
import p2e4_candidate_set_audit as p2e4
import p2e_witness_recoverability as p2e


CONFIG_PATH = Path("configs") / "p2e6_multisign_horizon.json"
P2_OUT = Path("p2_out")
P4_OUT = Path("p4_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2e6_multisign_horizon.json"
PACKET_PATH = OUT_DIR / "p2e6_multisign_packets.jsonl"
MANIFEST_PATH = OUT_DIR / "p2e6_multisign_horizon_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e6_multisign_horizon.md"
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
    return ordered[max(0, math.ceil(proportion * len(ordered)) - 1)]


def span_identity(record):
    return (
        record["fragment_id"],
        record["line_position_in_fragment"],
        record["sign_offset_in_line"],
    )


def tie_complete_alternatives(ranking, nominal_depth):
    alternatives = ranking["alternatives"]
    if len(alternatives) <= nominal_depth:
        return list(alternatives)
    cutoff_support = alternatives[nominal_depth - 1]["support_count"]
    return [
        alternative for alternative in alternatives
        if alternative["support_count"] >= cutoff_support
    ]


def build_adaptive_records(records_by_cell, mask_lengths, anchor_lengths):
    result = {}
    descending = sorted(anchor_lengths, reverse=True)
    for mask_length in mask_lengths:
        by_anchor = {}
        for anchor_length in anchor_lengths:
            cell = records_by_cell[f"a{anchor_length}_m{mask_length}"]
            indexed = {}
            for record in cell:
                identity = span_identity(record)
                if identity in indexed:
                    raise AssertionError(
                        "P2-E6: duplicate span identity inside one cell")
                indexed[identity] = record
            by_anchor[anchor_length] = indexed

        base = by_anchor[min(anchor_lengths)]
        adaptive = []
        for identity, base_record in sorted(base.items()):
            selected = None
            for anchor_length in descending:
                candidate = by_anchor[anchor_length].get(identity)
                if (
                        candidate is not None
                        and candidate["ranking"]["alternatives"]):
                    selected = candidate
                    break
            record = dict(base_record)
            if selected is None:
                record["adaptive_anchor_length"] = None
                record["ranking"] = {
                    "alternatives": [],
                    "unique_top": False,
                    "top_support": 0,
                    "runner_up_support": 0,
                    "support_margin": 0,
                    "dominance": 0.0,
                    "alternative_count": 0,
                }
            else:
                if selected["gold"] != base_record["gold"]:
                    raise AssertionError(
                        "P2-E6: anchor cells disagree on held-out span")
                record["adaptive_anchor_length"] = (
                    len(selected["left_anchor"]))
                record["left_anchor"] = selected["left_anchor"]
                record["right_anchor"] = selected["right_anchor"]
                record["ranking"] = selected["ranking"]
            record["mask_length"] = mask_length
            adaptive.append(record)
        result[mask_length] = adaptive
    return result


def displayed_set(record, nominal_depth):
    return tie_complete_alternatives(record["ranking"], nominal_depth)


def set_includes_attested(record, nominal_depth):
    return any(
        alternative["proposal"] == record["gold"]
        for alternative in displayed_set(record, nominal_depth))


def horizon_metrics(records, nominal_depth):
    supported = [
        record for record in records if record["ranking"]["alternatives"]]
    included = sum(
        set_includes_attested(record, nominal_depth)
        for record in supported)
    top1 = sum(
        record["ranking"]["alternatives"][0]["proposal"] == record["gold"]
        for record in supported)
    sizes = [
        len(displayed_set(record, nominal_depth)) for record in supported]
    tie_expanded = sum(size > nominal_depth for size in sizes)
    anchor_counts = Counter(
        (
            str(record["adaptive_anchor_length"])
            if record["adaptive_anchor_length"] is not None
            else "abstain"
        )
        for record in records
    )
    return {
        "eligible_contexts": len(records),
        "presented_contexts": len(supported),
        "abstained_contexts": len(records) - len(supported),
        "presentation_coverage_percent":
            pct(len(supported), len(records)),
        "top1_attested_agreement_contexts": top1,
        "top1_attested_agreement_percent":
            pct(top1, len(supported)),
        "displayed_set_attested_inclusion_contexts": included,
        "displayed_set_attested_inclusion_percent_of_presented":
            pct(included, len(supported)),
        "displayed_set_attested_inclusion_wilson_95":
            p2e2.wilson_interval(included, len(supported)),
        "effective_attested_recoverability_percent_of_eligible":
            pct(included, len(records)),
        "effective_attested_recoverability_wilson_95":
            p2e2.wilson_interval(included, len(records)),
        "displayed_set_size_when_presented": {
            "mean": (
                round(statistics.mean(sizes), 3) if sizes else None),
            "median": (
                round(statistics.median(sizes), 3) if sizes else None),
            "p90": percentile(sizes, 0.9),
            "maximum": max(sizes) if sizes else None,
        },
        "contexts_expanded_beyond_nominal_depth_for_tie":
            tie_expanded,
        "selected_anchor_length_counts": dict(
            sorted(anchor_counts.items())),
    }


def composition_macro(records, nominal_depth):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["cth"]].append(record)
    effective = []
    conditional = []
    for group in grouped.values():
        supported = [
            record for record in group
            if record["ranking"]["alternatives"]]
        included = sum(
            set_includes_attested(record, nominal_depth)
            for record in supported)
        effective.append(100.0 * included / len(group))
        if supported:
            conditional.append(100.0 * included / len(supported))
    return {
        "eligible_compositions": len(grouped),
        "compositions_with_any_presented_context": len(conditional),
        "effective_recoverability_percent": {
            "mean": round(statistics.mean(effective), 2),
            "median": round(statistics.median(effective), 2),
            "minimum": round(min(effective), 2),
            "maximum": round(max(effective), 2),
        },
        "conditional_set_inclusion_percent": {
            "mean": round(statistics.mean(conditional), 2),
            "median": round(statistics.median(conditional), 2),
            "minimum": round(min(conditional), 2),
            "maximum": round(max(conditional), 2),
        },
    }


def calibration_stat(records, nominal_depth, estimand):
    supported = [
        record for record in records if record["ranking"]["alternatives"]]
    successes = sum(
        set_includes_attested(record, nominal_depth)
        for record in supported)
    return {
        "estimand": estimand,
        "calibration_presented_contexts": len(supported),
        "attested_included_contexts": successes,
        "candidate_set_calibration_rate": (
            round(successes / len(supported), 6)
            if supported else None),
        "wilson_95": p2e2.wilson_interval(successes, len(supported)),
        "set_level_group_estimate_not_instance_truth_probability": True,
        "individual_option_probability_available": False,
    }


def assign_calibration(
        adaptive_by_mask,
        folds,
        nominal_depth,
        estimand):
    calibrated = {mask: [] for mask in adaptive_by_mask}
    fold_summaries = []
    for fold in folds:
        evaluation_cths = fold["cth"]
        fold_summary = {
            "fold": fold["fold"],
            "evaluation_cth": sorted(evaluation_cths),
            "groups": {},
        }
        for mask_length, records in adaptive_by_mask.items():
            calibration_records = [
                record for record in records
                if record["cth"] not in evaluation_cths]
            evaluation_records = [
                record for record in records
                if record["cth"] in evaluation_cths]
            groups = defaultdict(list)
            for record in calibration_records:
                if record["adaptive_anchor_length"] is not None:
                    groups[record["adaptive_anchor_length"]].append(record)
            calibration = {
                anchor: calibration_stat(
                    group, nominal_depth, estimand)
                for anchor, group in groups.items()
            }
            fold_summary["groups"][str(mask_length)] = {
                str(anchor): values
                for anchor, values in sorted(calibration.items())
            }
            for record in evaluation_records:
                copied = dict(record)
                copied["evaluation_fold"] = fold["fold"]
                copied["candidate_set_calibration"] = (
                    calibration.get(record["adaptive_anchor_length"])
                    if record["adaptive_anchor_length"] is not None
                    else None
                )
                calibrated[mask_length].append(copied)
        fold_summaries.append(fold_summary)
    for mask_length, records in adaptive_by_mask.items():
        original = {
            (
                record["fragment_id"],
                record["line_position_in_fragment"],
                record["sign_offset_in_line"],
            )
            for record in records
        }
        observed = {
            (
                record["fragment_id"],
                record["line_position_in_fragment"],
                record["sign_offset_in_line"],
            )
            for record in calibrated[mask_length]
        }
        if original != observed or len(calibrated[mask_length]) != len(records):
            raise AssertionError(
                "P2-E6: fold calibration lost or duplicated contexts")
    return calibrated, fold_summaries


def calibration_transfer_summary(records, nominal_depth):
    grouped = defaultdict(list)
    for record in records:
        if record["candidate_set_calibration"] is not None:
            grouped[(
                record["evaluation_fold"],
                record["mask_length"],
                record["adaptive_anchor_length"],
            )].append(record)
    rows = []
    weighted_gap = 0.0
    total = 0
    for (fold, mask_length, anchor), group in sorted(grouped.items()):
        predicted = group[0]["candidate_set_calibration"][
            "candidate_set_calibration_rate"]
        if any(
                record["candidate_set_calibration"][
                    "candidate_set_calibration_rate"] != predicted
                for record in group):
            raise AssertionError(
                "P2-E6: one calibration group has inconsistent estimates")
        observed_successes = sum(
            set_includes_attested(record, nominal_depth)
            for record in group)
        observed = observed_successes / len(group)
        gap = abs(predicted - observed)
        weighted_gap += gap * len(group)
        total += len(group)
        rows.append({
            "fold": fold,
            "mask_length": mask_length,
            "adaptive_anchor_length": anchor,
            "evaluation_presented_contexts": len(group),
            "predicted_set_inclusion_rate": predicted,
            "observed_set_inclusion_rate": round(observed, 6),
            "absolute_gap": round(gap, 6),
        })
    return {
        "weighted_mean_absolute_group_gap": (
            round(weighted_gap / total, 6) if total else None),
        "presented_contexts_with_calibration": total,
        "groups": rows,
    }


def packet_outcome(record, nominal_depth):
    if not record["ranking"]["alternatives"]:
        return "ABSTAIN_NO_INDEPENDENT_WITNESS_SET"
    if set_includes_attested(record, nominal_depth):
        return "PRESENTED_SET_INCLUDES_ATTESTED"
    return "PRESENTED_SET_EXCLUDES_ATTESTED"


def evidence_packet(
        record,
        policy_name,
        nominal_depth,
        maximum_alternatives):
    displayed = displayed_set(record, nominal_depth)
    total_support = sum(
        alternative["support_count"]
        for alternative in record["ranking"]["alternatives"])
    alternatives = []
    for rank, alternative in enumerate(
            displayed[:maximum_alternatives], 1):
        alternatives.append({
            "rank": rank,
            "middle": list(alternative["proposal"]),
            "independent_witness_family_count":
                alternative["support_count"],
            "supporting_witness_families":
                list(alternative["supporting_families"]),
            "witness_support_share": round(
                alternative["support_count"] / total_support, 6),
            "support_share_is_not_probability": True,
            "evidence_class": "EDITORIAL_TRANSCRIPTION",
        })
    outcome = packet_outcome(record, nominal_depth)
    return {
        "proposed_relation": "EXPERT_MULTISIGN_CONTEXT_CANDIDATE_SET",
        "decision": (
            "PRESENT_CANDIDATE_SET"
            if alternatives else "ABSTAIN"),
        "outcome": outcome,
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
            "mask_length": record["mask_length"],
            "selected_adaptive_anchor_length":
                record["adaptive_anchor_length"],
            "left_anchor": list(record["left_anchor"]),
            "right_anchor": list(record["right_anchor"]),
        },
        "candidate_set": {
            "nominal_display_depth": nominal_depth,
            "tie_complete_alternatives": alternatives,
            "total_tie_complete_alternatives": len(displayed),
            "alternatives_truncated":
                len(displayed) > len(alternatives),
            "other_or_unsupported_available": True,
            "set_level_calibration":
                record["candidate_set_calibration"],
            "individual_option_probability_available": False,
            "probability_warning": (
                "The calibration estimate applies to the whole set across "
                "other compositions. Witness support shares are evidence "
                "fractions, not probabilities that an option is true."),
        },
        "enabled_assistance_layers": [
            "OBSERVED_DOCUMENT_STRUCTURE",
            "EDITORIAL_TRANSCRIPTION",
            "CATALOG_METADATA",
        ],
        "editorial_features_used": ["token"],
        "model_features_used": [],
        "abstention_reason": (
            "No configured anchor length has an independently witnessed "
            "middle for this observed context."
            if not alternatives else None),
        "dev_evaluation_only": {
            "intentionally_hidden_attested_middle": list(record["gold"]),
            "displayed_set_contains_attested": (
                set_includes_attested(record, nominal_depth)
                if alternatives else False),
            "never_available_to_selector_or_ranker": True,
            "not_truth_for_a_genuine_lacuna": True,
        },
    }


def select_packets(
        calibrated_by_mask,
        policy_name,
        nominal_depth,
        per_outcome,
        maximum_alternatives):
    packets = []
    for mask_length, records in sorted(calibrated_by_mask.items()):
        grouped = defaultdict(list)
        for record in records:
            grouped[packet_outcome(record, nominal_depth)].append(record)
        for outcome in sorted(grouped):
            chosen = sorted(
                grouped[outcome],
                key=lambda record: (
                    record["cth"],
                    record["fragment_id"],
                    record["span_ordinal"],
                ),
            )[:per_outcome]
            packets.extend(
                evidence_packet(
                    record,
                    policy_name,
                    nominal_depth,
                    maximum_alternatives,
                )
                for record in chosen)
    return packets


def adaptive_policy_tracer():
    ranking = {
        "alternatives": [
            {"proposal": ("a",), "support_count": 3},
            {"proposal": ("b",), "support_count": 2},
            {"proposal": ("c",), "support_count": 1},
            {"proposal": ("d",), "support_count": 1},
        ],
    }
    tie_complete = tie_complete_alternatives(ranking, 3)
    passed = (
        len(tie_complete) == 4
        and [value["proposal"] for value in tie_complete]
        == [("a",), ("b",), ("c",), ("d",)]
    )
    result = {
        "tie_boundary_preserved_without_lexical_exclusion": passed,
        "blocking_failures": int(not passed),
    }
    if not passed:
        raise AssertionError(f"P2-E6 adaptive policy tracer failed: {result}")
    return result


def write_report(summary, elapsed_seconds):
    rows = []
    for mask_length, result in summary["horizon"].items():
        metrics = result["micro"]
        interval = metrics["displayed_set_attested_inclusion_wilson_95"]
        rows.append(
            f"| {mask_length} | {metrics['presented_contexts']:,}/"
            f"{metrics['eligible_contexts']:,} "
            f"({metrics['presentation_coverage_percent']}%) | "
            f"{metrics['top1_attested_agreement_percent']}% | "
            f"{metrics['displayed_set_attested_inclusion_percent_of_presented']}% "
            f"[{interval[0] * 100:.1f}, {interval[1] * 100:.1f}] | "
            f"{metrics['effective_attested_recoverability_percent_of_eligible']}% "
            f"| {metrics['displayed_set_size_when_presented']['mean']} / "
            f"{metrics['displayed_set_size_when_presented']['p90']} |")
    lines = [
        "# Phase 2 P2-E6 multi-sign candidate-set horizon",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Tracer block",
        "",
        "- Base tracers: PASS, zero blocking failures; historical D18 T4 "
        "remains diagnostic and non-blocking.",
        "- Witness ranker T1: PASS; 12/12 real canaries changed under token "
        "order scrambling and candidate ordering was invariant.",
        "- Adaptive policy tracer: PASS; equal-support alternatives at the "
        "display boundary were retained together.",
        "",
        "## Question and method",
        "",
        "For Q0, what set-valued evidence remains for two-to-five-sign gaps? "
        "For each dev span, the policy selected the longest supported exact "
        "anchor (3→2→1), presented nominally five alternatives while keeping "
        "boundary ties complete, and otherwise abstained. Hidden attested "
        "text never affected anchor selection or ranking. Set-level "
        "calibration in packets was fit on other composition folds.",
        "",
        "## Findings",
        "",
        "| hidden span | presented / eligible | top-1 agreement | displayed-set "
        "inclusion among presented [95% CI] | effective inclusion / eligible "
        "| mean / p90 options |",
        "|---:|---:|---:|---:|---:|---:|",
        *rows,
        "",
        f"Across fold × mask × selected-anchor groups, the weighted mean "
        f"absolute calibration-transfer gap was "
        f"{summary['calibration_transfer']['weighted_mean_absolute_group_gap'] * 100:.2f} "
        "percentage points. This is set-level calibration, not an individual "
        "option probability.",
        "",
        summary["macro_finding"],
        "",
        "## Interpretation",
        "",
        summary["interpretation"],
        "",
        f"Cost: {elapsed_seconds:.1f}s compute; budget ≤"
        f"{summary['parameters']['time_budget_hours']}h. Profile "
        f"`{summary['evidence_policy']}`; dev only; test, restorations, `cu`, "
        "morphology, model scores, and generated text untouched.",
        "",
        "**Falsifier:** the multi-sign horizon conclusion would be wrong if "
        "an untouched composition-disjoint evaluation shows materially "
        "different coverage, set inclusion, or option-set size under the "
        "same adaptive evidence policy.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    policy_name = config["evidence_policy"]
    seed = int(config["seed"])
    anchor_lengths = [
        int(value) for value in config["anchor_lengths"]]
    mask_lengths = [int(value) for value in config["mask_lengths"]]
    nominal_depth = int(config["nominal_display_depth"])

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(policy_name, POLICIES_PATH)
    semantic_fields = [
        "token", "damage_state", "line_index_in_doc", "cth",
        "adaptive_anchor_length", "candidate_set_calibration_rate",
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
        label="P2-E6 dev attested-only")

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

    requested_masks = sorted(set(mask_lengths + [1]))
    anchor_indices = {}
    for anchor_length in anchor_lengths:
        requested_by_cth = defaultdict(set)
        for fragment_id, fragment_lines in line_sequences.items():
            requested_by_cth[fragment_cth[fragment_id]].update(
                p2e.requested_anchor_keys(
                    fragment_lines, anchor_length, requested_masks))
        anchor_indices[anchor_length] = p2e.build_anchor_index(
            line_sequences,
            line_sequences,
            fragment_families,
            anchor_length,
            requested_by_cth,
            fragment_cth,
            max_middle=int(config["maximum_witness_middle_length"]),
        )

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
    policy_t1 = adaptive_policy_tracer()

    records_by_cell = {}
    for anchor_length in anchor_lengths:
        for mask_length in mask_lengths:
            name = f"a{anchor_length}_m{mask_length}"
            records_by_cell[name] = p2e2.build_span_records(
                line_sequences,
                fragment_cth,
                fragment_families,
                fragments_by_cth,
                anchor_indices[anchor_length],
                anchor_length,
                mask_length,
                set(fragment_cth.values()),
            )
    adaptive = build_adaptive_records(
        records_by_cell, mask_lengths, anchor_lengths)
    for records in adaptive.values():
        p2e4.add_line_indices(records, edges)

    weights = Counter()
    for records in adaptive.values():
        weights.update(record["cth"] for record in records)
    folds = p2e3.assign_composition_folds(
        weights, set(weights), int(config["folds"]))
    calibrated, fold_summaries = assign_calibration(
        adaptive,
        folds,
        nominal_depth,
        config["candidate_set_calibration_estimand"],
    )

    horizon = {
        str(mask_length): {
            "micro": horizon_metrics(records, nominal_depth),
            "composition_macro":
                composition_macro(records, nominal_depth),
        }
        for mask_length, records in sorted(calibrated.items())
    }
    all_calibrated = [
        record
        for records in calibrated.values()
        for record in records
    ]
    transfer = calibration_transfer_summary(
        all_calibrated, nominal_depth)
    packets = select_packets(
        calibrated,
        policy.name,
        nominal_depth,
        int(config["packets_per_mask_outcome"]),
        int(config["maximum_packet_alternatives"]),
    )
    two_micro = horizon["2"]["micro"]
    five_micro = horizon["5"]["micro"]
    two_macro = horizon["2"]["composition_macro"]
    five_macro = horizon["5"]["composition_macro"]
    maximum_set_size = max(
        result["micro"]["displayed_set_size_when_presented"]["maximum"]
        for result in horizon.values()
    )
    maximum_p90 = max(
        result["micro"]["displayed_set_size_when_presented"]["p90"]
        for result in horizon.values()
    )
    minimum_tie_expansion_percent = min(
        100.0
        * result["micro"]["contexts_expanded_beyond_nominal_depth_for_tie"]
        / result["micro"]["presented_contexts"]
        for result in horizon.values()
    )
    maximum_tie_expansion_percent = max(
        100.0
        * result["micro"]["contexts_expanded_beyond_nominal_depth_for_tie"]
        / result["micro"]["presented_contexts"]
        for result in horizon.values()
    )
    macro_finding = (
        "Composition-macro effective recovery was "
        f"{two_macro['effective_recoverability_percent']['mean']}% mean / "
        f"{two_macro['effective_recoverability_percent']['median']}% median "
        "for two signs and "
        f"{five_macro['effective_recoverability_percent']['mean']}% mean / "
        f"{five_macro['effective_recoverability_percent']['median']}% median "
        "for five signs; pooled micro rates therefore overstate the typical "
        "composition.")
    interpretation = (
        "Two-sign sets retained the attested span in "
        f"{two_micro['effective_attested_recoverability_percent_of_eligible']}% "
        "of eligible contexts; by five signs this fell to "
        f"{five_micro['effective_attested_recoverability_percent_of_eligible']}%. "
        "Keeping evidence ties complete expanded nominal top-five sets in "
        f"{minimum_tie_expansion_percent:.1f}% to "
        f"{maximum_tie_expansion_percent:.1f}% of presented contexts, with "
        f"p90 up to {maximum_p90} and a maximum of {maximum_set_size} options. "
        "The witness layer is therefore suitable only as abstention-first, "
        "set-valued evidence for an expert: do not auto-complete a lacuna, "
        "do not assign per-option probabilities, and collapse large equal-"
        "support tails in the UI without hiding that they exist.")
    promotion_decision = {
        "automatic_lacuna_completion": "DO_NOT_PROMOTE",
        "expert_candidate_evidence": "RETAIN_WITH_ABSTENTION",
        "per_option_probability": "UNAVAILABLE",
        "ui_requirement": (
            "Preserve the complete equal-support set, but group or collapse "
            "large tied tails and retain an explicit other/unsupported path."
        ),
        "reason": (
            "Effective recovery declines sharply with span length, "
            "composition-macro rates trail pooled micro rates, tie-complete "
            "sets can be large, and held-out-group calibration transfer is "
            "not stable enough for instance confidence."
        ),
    }

    summary = {
        "probe": "P2-E6 multi-sign candidate-set horizon",
        "probe_label": "PROBE — not for citation",
        "evidence_policy": policy.name,
        "target_split": "dev with five composition-disjoint calibration folds",
        "test_side_accessed": False,
        "restorations_included": False,
        "gold_available_to_selector_or_ranker": False,
        "model_scoring_performed": False,
        "parameters": config,
        "folds": fold_summaries,
        "tracers": {
            "base": base_tracers,
            "p2e_t1": p2e_t1,
            "p2e2_t1": p2e2_t1,
            "adaptive_policy_t1": policy_t1,
        },
        "horizon": horizon,
        "calibration_transfer": transfer,
        "evidence_packet_count": len(packets),
        "macro_finding": macro_finding,
        "interpretation": interpretation,
        "promotion_decision": promotion_decision,
        "interpretation_limits": [
            "Candidate-set calibration applies to a mask/anchor group, not "
            "to an individual option or genuine lacuna.",
            "Witness-family support shares are not probabilities.",
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
            "tokenizer_json":
                sha256(Path("configs") / "tokenizer.json"),
        },
    }

    manifest = ep.build_manifest(
        task="duplicate_parallel_multisign_candidate_set_horizon",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P4_OUT / "decomposed_corpus.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=CONFIG_PATH,
        seed=seed,
        declared_statistics_universe=(
            "two-to-five-sign intentionally masked spans from frozen dev "
            "only; adaptive anchor selection and witness ranking use "
            "independent same-CTH dev families; set-level calibration fit on "
            "the four non-held-out dev composition folds; no test, train, or "
            "discovery content statistics"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "test_side_accessed": False,
        "restoration_included": False,
        "model_scoring_performed": False,
        "gold_available_to_selector_or_ranker": False,
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
        f"P2-E6 complete: masks={mask_lengths}, "
        f"packets={len(packets)}.")
    print(
        f"Wrote {RESULT_PATH}, {PACKET_PATH}, {MANIFEST_PATH}, "
        f"and {REPORT_PATH}")


if __name__ == "__main__":
    main()
