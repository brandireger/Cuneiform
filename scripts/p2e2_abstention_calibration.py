#!/usr/bin/env python3
"""Phase 2 P2-E2: abstention-calibrated witness reconstruction.

The probe ranks variable-length middles observed between matching anchors in
independent same-CTH witnesses.  Ranking uses only the number of independent
witness families supporting each alternative.  An evidential tie is never
broken arbitrarily: the system abstains.

Calibration and evaluation use disjoint sets of dev compositions.  Rules are
chosen on calibration compositions by a lower Wilson reliability bound and
then frozen before evaluation on held-out dev compositions.  Test-side
content remains unread.

Usage:
    python scripts/p2e2_abstention_calibration.py
"""

import hashlib
import itertools
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

import p2e_witness_recoverability as p2e


CONFIG_PATH = Path("configs") / "p2e2_calibration.json"
P2_OUT = Path("p2_out")
P4_OUT = Path("p4_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2e2_abstention_calibration.json"
MANIFEST_PATH = OUT_DIR / "p2e2_abstention_calibration_manifest.json"
PACKET_PATH = OUT_DIR / "p2e2_evidence_packets.jsonl"
REPORT_PATH = Path("reports") / "phase2_p2e2_abstention_calibration.md"
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


def wilson_interval(successes, total, z=1.959963984540054):
    if total == 0:
        return [None, None]
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total))
        / denominator
    )
    return [round(max(0.0, center - half), 6),
            round(min(1.0, center + half), 6)]


def proposal_ranking(anchor_index, cth, key, excluded_family):
    """Rank alternatives by independent supporting witness-family count.

    Gold content, candidate IDs, token lexicography, and proposal length do
    not influence the evidence rank.  Lexicographic order is used only to
    serialize equal-evidence alternatives deterministically.
    """
    alternatives = []
    for proposal, families in anchor_index.get(cth, {}).get(key, {}).items():
        independent = sorted(
            family for family in families if family != excluded_family)
        if independent:
            alternatives.append({
                "proposal": tuple(proposal),
                "supporting_families": tuple(independent),
                "support_count": len(independent),
            })
    alternatives.sort(
        key=lambda value: (-value["support_count"], value["proposal"]))
    if not alternatives:
        return {
            "alternatives": [],
            "unique_top": False,
            "top_support": 0,
            "runner_up_support": 0,
            "support_margin": 0,
            "dominance": 0.0,
            "alternative_count": 0,
        }

    top_support = alternatives[0]["support_count"]
    tied_top = sum(
        1 for value in alternatives
        if value["support_count"] == top_support)
    runner_up = (
        alternatives[1]["support_count"] if len(alternatives) > 1 else 0)
    total_support = sum(value["support_count"] for value in alternatives)
    return {
        "alternatives": alternatives,
        "unique_top": tied_top == 1,
        "top_support": top_support,
        "runner_up_support": runner_up,
        "support_margin": top_support - runner_up,
        "dominance": top_support / total_support,
        "alternative_count": len(alternatives),
    }


def rank_signature(ranking):
    return tuple(
        (value["proposal"], value["support_count"])
        for value in ranking["alternatives"])


def rule_accepts(ranking, rule):
    if not ranking["alternatives"] or not ranking["unique_top"]:
        return False
    maximum = rule["maximum_alternatives"]
    return (
        ranking["top_support"] >= rule["minimum_top_support_families"]
        and ranking["support_margin"] >= rule["minimum_support_margin"]
        and ranking["dominance"] >= rule["minimum_dominance"]
        and (maximum is None or ranking["alternative_count"] <= maximum)
    )


def generate_rules(config):
    grid = config["rule_grid"]
    rules = []
    for top_support, margin, dominance, maximum in itertools.product(
            grid["minimum_top_support_families"],
            grid["minimum_support_margin"],
            grid["minimum_dominance"],
            grid["maximum_alternatives"]):
        rules.append({
            "minimum_top_support_families": int(top_support),
            "minimum_support_margin": int(margin),
            "minimum_dominance": float(dominance),
            "maximum_alternatives": maximum,
        })
    return rules


def rule_id(rule):
    maximum = (
        "any" if rule["maximum_alternatives"] is None
        else str(rule["maximum_alternatives"]))
    dominance = str(rule["minimum_dominance"]).replace(".", "p")
    return (
        f"s{rule['minimum_top_support_families']}"
        f"_m{rule['minimum_support_margin']}"
        f"_d{dominance}_a{maximum}"
    )


def build_span_records(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_index,
        anchor_length,
        mask_length,
        allowed_cths):
    """Build evaluation records for structurally eligible query spans."""
    cth_families = {
        cth: {fragment_families[fragment_id] for fragment_id in fragment_ids}
        for cth, fragment_ids in fragments_by_cth.items()
    }
    records = []
    for fragment_id in sorted(line_sequences):
        cth = fragment_cth[fragment_id]
        if cth not in allowed_cths:
            continue
        query_family = fragment_families[fragment_id]
        if not cth_families[cth].difference({query_family}):
            continue
        for span_ordinal, (key, gold) in enumerate(p2e.iter_masked_spans(
                line_sequences[fragment_id], anchor_length, mask_length)):
            ranking = proposal_ranking(
                anchor_index, cth, key, query_family)
            records.append({
                "fragment_id": fragment_id,
                "cth": cth,
                "query_family": query_family,
                "span_ordinal": span_ordinal,
                "left_anchor": key[0],
                "right_anchor": key[1],
                "gold": gold,
                "ranking": ranking,
            })
    return records


def evaluate_rule(records, rule):
    accepted = []
    supported = 0
    unique_top_supported = 0
    for record in records:
        ranking = record["ranking"]
        supported += int(bool(ranking["alternatives"]))
        unique_top_supported += int(
            bool(ranking["alternatives"]) and ranking["unique_top"])
        if rule_accepts(ranking, rule):
            accepted.append(record)

    top_exact = sum(
        record["ranking"]["alternatives"][0]["proposal"] == record["gold"]
        for record in accepted)
    gold_anywhere = sum(
        any(
            alternative["proposal"] == record["gold"]
            for alternative in record["ranking"]["alternatives"])
        for record in accepted)
    accepted_n = len(accepted)
    return {
        "rule_id": rule_id(rule),
        "rule": rule,
        "eligible_spans": len(records),
        "spans_with_any_witness_alternative": supported,
        "spans_with_unique_evidence_top": unique_top_supported,
        "accepted_spans": accepted_n,
        "coverage_percent_of_eligible": pct(accepted_n, len(records)),
        "coverage_percent_of_supported": pct(accepted_n, supported),
        "top1_exact_agreement_spans": top_exact,
        "top1_exact_agreement_percent": pct(top_exact, accepted_n),
        "top1_exact_agreement_fraction":
            top_exact / accepted_n if accepted_n else None,
        "top1_exact_wilson_95": wilson_interval(top_exact, accepted_n),
        "gold_anywhere_in_preserved_alternatives": gold_anywhere,
        "gold_anywhere_percent": pct(gold_anywhere, accepted_n),
        "mean_preserved_alternatives_when_accepted": (
            round(statistics.mean(
                record["ranking"]["alternative_count"]
                for record in accepted), 3)
            if accepted else None),
    }


def choose_rules(calibration_metrics, targets, minimum_accepts):
    """Choose maximum-coverage rules using calibration data only."""
    chosen = {}
    for target in targets:
        candidates = [
            metric for metric in calibration_metrics
            if metric["accepted_spans"] >= minimum_accepts
            and metric["top1_exact_wilson_95"][0] is not None
            and metric["top1_exact_wilson_95"][0] >= target
        ]
        candidates.sort(
            key=lambda metric: (
                -metric["coverage_percent_of_eligible"],
                -metric["top1_exact_wilson_95"][0],
                metric["rule_id"],
            ))
        chosen[str(target)] = candidates[0] if candidates else None
    return chosen


def evaluate_selected_rules(chosen, evaluation_records):
    evaluated = {}
    for target, calibration_metric in chosen.items():
        if calibration_metric is None:
            evaluated[target] = None
            continue
        evaluated[target] = {
            "selected_on_calibration": calibration_metric,
            "heldout_evaluation": evaluate_rule(
                evaluation_records, calibration_metric["rule"]),
        }
    return evaluated


def split_compositions(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_length,
        mask_length):
    """Greedily balance eligible primary-cell spans without using labels."""
    families_by_cth = {
        cth: {fragment_families[fragment_id] for fragment_id in fragment_ids}
        for cth, fragment_ids in fragments_by_cth.items()
    }
    weights = Counter()
    for fragment_id, lines in line_sequences.items():
        cth = fragment_cth[fragment_id]
        family = fragment_families[fragment_id]
        if not families_by_cth[cth].difference({family}):
            continue
        weights[cth] += sum(
            1 for _ in p2e.iter_masked_spans(
                lines, anchor_length, mask_length))

    calibration = set()
    evaluation = set()
    totals = {"calibration": 0, "evaluation": 0}
    for cth, weight in sorted(
            weights.items(), key=lambda item: (-item[1], item[0])):
        side = (
            "calibration"
            if totals["calibration"] <= totals["evaluation"]
            else "evaluation")
        if side == "calibration":
            calibration.add(cth)
        else:
            evaluation.add(cth)
        totals[side] += weight
    if not calibration or not evaluation or calibration & evaluation:
        raise AssertionError(
            "P2-E2: composition-disjoint calibration partition failed")
    return calibration, evaluation, totals, dict(weights)


def scramble_rank_tracer(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_index):
    """T1 for the new evidence ranking, plus candidate-order invariance."""
    synthetic_lines = {
        "w1": [["L1", "L2", "gold", "R1", "R2"]],
        "w2": [["L1", "L2", "gold", "R1", "R2"]],
        "w3": [["L1", "L2", "variant", "R1", "R2"]],
    }
    synthetic_families = {
        "w1": "family-1", "w2": "family-2", "w3": "family-3"}
    synthetic_cth = {fragment_id: 1 for fragment_id in synthetic_lines}
    key = (("L1", "L2"), ("R1", "R2"))
    requested = {1: {key}}
    original_index = p2e.build_anchor_index(
        synthetic_lines,
        synthetic_lines,
        synthetic_families,
        2,
        requested,
        synthetic_cth,
        max_middle=3,
    )
    original = proposal_ranking(
        original_index, 1, key, excluded_family="query")
    reversed_index = p2e.build_anchor_index(
        reversed(list(synthetic_lines)),
        synthetic_lines,
        synthetic_families,
        2,
        requested,
        synthetic_cth,
        max_middle=3,
    )
    reordered = proposal_ranking(
        reversed_index, 1, key, excluded_family="query")
    order_invariant = rank_signature(original) == rank_signature(reordered)

    corrupted_lines = {
        fragment_id: p2e.scramble_lines(lines, p2e.SEED + position)
        for position, (fragment_id, lines) in enumerate(
            sorted(synthetic_lines.items()))
    }
    corrupted_index = p2e.build_anchor_index(
        corrupted_lines,
        corrupted_lines,
        synthetic_families,
        2,
        requested,
        synthetic_cth,
        max_middle=3,
    )
    corrupted = proposal_ranking(
        corrupted_index, 1, key, excluded_family="query")
    synthetic_pass = (
        original["unique_top"]
        and original["alternatives"][0]["proposal"] == ("gold",)
        and rank_signature(original) != rank_signature(corrupted)
        and order_invariant
    )

    canaries = []
    for fragment_id in sorted(line_sequences):
        cth = fragment_cth[fragment_id]
        query_family = fragment_families[fragment_id]
        for key, _ in p2e.iter_masked_spans(
                line_sequences[fragment_id], 2, 1):
            ranking = proposal_ranking(
                anchor_index, cth, key, query_family)
            if ranking["alternatives"]:
                canaries.append(
                    (cth, query_family, key, rank_signature(ranking)))
                break
        if len(canaries) >= 12:
            break

    changed = 0
    for position, (cth, query_family, canary_key, signature) in enumerate(
            canaries):
        witness_ids = [
            fragment_id for fragment_id in fragments_by_cth[cth]
            if fragment_families[fragment_id] != query_family
        ]
        corrupted_witnesses = {
            fragment_id: p2e.scramble_lines(
                line_sequences[fragment_id],
                p2e.SEED + 100 + position)
            for fragment_id in witness_ids
        }
        local_cth = {fragment_id: cth for fragment_id in witness_ids}
        local_index = p2e.build_anchor_index(
            witness_ids,
            corrupted_witnesses,
            fragment_families,
            2,
            {cth: {canary_key}},
            local_cth,
        )
        new_signature = rank_signature(proposal_ranking(
            local_index, cth, canary_key, query_family))
        changed += int(new_signature != signature)

    required = max(1, math.ceil(len(canaries) / 3))
    real_pass = bool(canaries) and changed >= required
    result = {
        "synthetic_evidence_rank_pass": synthetic_pass,
        "candidate_order_invariance_pass": order_invariant,
        "real_canaries": len(canaries),
        "real_canaries_changed_under_token_order_scramble": changed,
        "real_canaries_required_to_change": required,
        "real_canary_pass": real_pass,
        "blocking_failures": int(not synthetic_pass) + int(not real_pass),
    }
    if result["blocking_failures"]:
        raise AssertionError(f"P2-E2 ranking tracer failed: {result}")
    return result


def packet_outcome(record, rule):
    ranking = record["ranking"]
    if not ranking["alternatives"]:
        return "abstain_no_anchor_evidence"
    if not ranking["unique_top"]:
        return "abstain_evidence_tie"
    if not rule_accepts(ranking, rule):
        return "abstain_calibrated_threshold"
    if ranking["alternatives"][0]["proposal"] == record["gold"]:
        return "accepted_exact_agreement"
    return "accepted_variant"


def evidence_packet(record, rule, policy_name):
    ranking = record["ranking"]
    outcome = packet_outcome(record, rule)
    accepted = outcome.startswith("accepted_")
    alternatives = [
        {
            "rank": rank,
            "middle": list(value["proposal"]),
            "independent_witness_family_count": value["support_count"],
            "supporting_witness_families":
                list(value["supporting_families"]),
            "evidence_class": "EDITORIAL_TRANSCRIPTION",
        }
        for rank, value in enumerate(ranking["alternatives"], 1)
    ]
    contradictions = [
        {
            "type": "WITNESS_VARIANT_OR_OMISSION",
            "middle": alternative["middle"],
            "independent_witness_family_count":
                alternative["independent_witness_family_count"],
        }
        for alternative in alternatives[1:]
    ]
    reason = {
        "abstain_no_anchor_evidence":
            "No independent witness supplies both anchors.",
        "abstain_evidence_tie":
            "Multiple alternatives have equal strongest witness support.",
        "abstain_calibrated_threshold":
            "Evidence does not satisfy the calibration-frozen reliability rule.",
    }.get(outcome)
    top_exact = (
        bool(alternatives)
        and tuple(alternatives[0]["middle"]) == record["gold"])
    return {
        "proposed_relation": "WITNESS_SUPPORTED_MISSING_CONTEXT",
        "decision": "ACCEPT" if accepted else "ABSTAIN",
        "outcome": outcome,
        "evidence_policy": policy_name,
        "query": {
            "fragment_id": record["fragment_id"],
            "cth": record["cth"],
            "span_ordinal": record["span_ordinal"],
            "left_anchor": list(record["left_anchor"]),
            "right_anchor": list(record["right_anchor"]),
        },
        "evidence": {
            "alternative_count": ranking["alternative_count"],
            "unique_top": ranking["unique_top"],
            "top_support_families": ranking["top_support"],
            "runner_up_support_families": ranking["runner_up_support"],
            "support_margin": ranking["support_margin"],
            "dominance": round(ranking["dominance"], 6),
        },
        "alternatives": alternatives,
        "support": alternatives[:1],
        "contradictions": contradictions,
        "enabled_assistance_layers": [
            "OBSERVED_DOCUMENT_STRUCTURE",
            "EDITORIAL_TRANSCRIPTION",
            "CATALOG_METADATA",
        ],
        "editorial_features_used": ["token"],
        "model_features_used": [],
        "abstention_reason": reason,
        "dev_evaluation_only": {
            "intentionally_held_out_attested_middle": list(record["gold"]),
            "top_exact_agreement": top_exact,
            "never_available_to_ranker": True,
        },
    }


def select_evidence_packets(records, rule, policy_name, per_outcome):
    selected = []
    counts = Counter()
    wanted = {
        "accepted_exact_agreement",
        "accepted_variant",
        "abstain_no_anchor_evidence",
        "abstain_evidence_tie",
        "abstain_calibrated_threshold",
    }
    for record in records:
        outcome = packet_outcome(record, rule)
        if outcome not in wanted or counts[outcome] >= per_outcome:
            continue
        selected.append(evidence_packet(record, rule, policy_name))
        counts[outcome] += 1
        if all(counts[value] >= per_outcome for value in wanted):
            break
    return selected, dict(counts)


def write_report(summary, elapsed_seconds):
    primary = summary["cells"][summary["primary_cell"]]
    baseline_cal = primary["baseline"]["calibration"]
    baseline_eval = primary["baseline"]["evaluation"]
    rows = []
    for target, result in primary["selected_rules"].items():
        if result is None:
            rows.append(
                f"| {float(target) * 100:.0f}% | unattainable | — | — | — |")
            continue
        calibration = result["selected_on_calibration"]
        evaluation = result["heldout_evaluation"]
        interval = evaluation["top1_exact_wilson_95"]
        rows.append(
            f"| {float(target) * 100:.0f}% | "
            f"`{calibration['rule_id']}` | "
            f"{calibration['coverage_percent_of_eligible']}% / "
            f"{calibration['top1_exact_agreement_percent']}% | "
            f"{evaluation['coverage_percent_of_eligible']}% | "
            f"{evaluation['top1_exact_agreement_percent']}% "
            f"[{interval[0] * 100:.1f}, {interval[1] * 100:.1f}] |")

    lines = [
        "# Phase 2 P2-E2 abstention calibration",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Tracer block",
        "",
        "- `00_tracers.py`: PASS, zero blocking failures; the existing D18 "
        "diagnostic remains visible and non-blocking.",
        f"- P2-E anchored scorer T1: PASS; "
        f"{summary['tracers']['p2e_t1']['real_canaries_changed_under_order_scramble']}/"
        f"{summary['tracers']['p2e_t1']['real_canaries']} real canaries changed.",
        f"- New evidence-ranker T1: PASS; "
        f"{summary['tracers']['p2e2_t1']['real_canaries_changed_under_token_order_scramble']}/"
        f"{summary['tracers']['p2e2_t1']['real_canaries']} real canaries "
        "changed, while candidate-order permutation left the rank unchanged.",
        "",
        "## Question",
        "",
        "Can independent witness votes identify a subset of missing-context "
        "proposals whose reliability is high enough to justify acceptance, "
        "while preserving alternatives and abstaining elsewhere?",
        "",
        "## What I did",
        "",
        f"Frozen dev compositions were divided into disjoint calibration "
        f"({summary['partition']['calibration_compositions']} CTHs) and "
        f"evaluation ({summary['partition']['evaluation_compositions']} CTHs) "
        "sets, balanced by primary-cell eligible spans without reading outcome "
        "labels. Alternatives were ranked only by the number of independent "
        "witness families supporting them. Evidence ties always abstain. "
        "Rules were selected by calibration coverage subject to a lower 95% "
        "Wilson reliability bound, then frozen for held-out-composition "
        "evaluation.",
        "",
        "## What I found — primary cell (two-sign anchors, one hidden sign)",
        "",
        f"The evidence-only unique-top baseline accepted "
        f"{baseline_eval['coverage_percent_of_eligible']}% of held-out eligible "
        f"spans at {baseline_eval['top1_exact_agreement_percent']}% top-1 "
        f"agreement (calibration: {baseline_cal['coverage_percent_of_eligible']}% "
        f"coverage, {baseline_cal['top1_exact_agreement_percent']}% agreement).",
        "",
        "| calibration lower-bound target | selected rule | "
        "calibration coverage / agreement | held-out coverage | "
        "held-out agreement [95% CI] |",
        "|---:|---|---:|---:|---:|",
        *rows,
        "",
        f"Typed evidence-packet samples preserve accepted alternatives, "
        f"witness-family support, contradictory variants, enabled assistance "
        f"layers, and explicit abstention reasons in `{PACKET_PATH}`. Full "
        "12-cell frontiers are in the machine-readable result.",
        "",
        "## What this rules in / out",
        "",
        "It rules in witness voting only where held-out-composition reliability "
        "and useful coverage coexist. It rules out forced completion, "
        "lexicographic tie-breaking, and treating catalog co-membership as "
        "evidence. This remains agreement against intentionally masked dev "
        "text—not proof of a genuinely lost reading.",
        "",
        f"Cost: {elapsed_seconds:.1f}s compute; budget ≤4 hours. Evidence profile "
        f"`{summary['evidence_policy']}`; no test content, restorations, `cu`, "
        "morphology, or model-generated text.",
        "",
        "**Falsifier:** this conclusion would be wrong if the selected rules "
        "lose their reliability when evaluated on a future untouched, "
        "composition-disjoint masked-attested benchmark.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    seed = int(config["seed"])
    policy_name = config["evidence_policy"]

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(policy_name, POLICIES_PATH)
    semantic_fields = ["token", "damage_state", "line_index_in_doc", "cth"]
    ep.validate_semantic_features(semantic_fields, registry, policy)

    base_tracers = p2e.run_base_tracers()
    _, _, _, edges, decomposed = p2e.load_dev_inputs()
    line_index = p2e.build_line_index(decomposed)
    line_sequences, canonical_flat = p2e.render_fragments(edges, line_index)
    tokenizer = ht.Tokenizer.load()
    encoded = tokenizer.encode(canonical_flat, strict=True)
    contracts.assert_encoding_sane(
        encoded, tokenizer, max_unk=0.05,
        label="P2-E2 dev attested-only")

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
    masks_by_anchor = defaultdict(set)
    for anchor_length, mask_length in cells:
        masks_by_anchor[anchor_length].add(mask_length)

    anchor_indices = {}
    for anchor_length, mask_lengths in sorted(masks_by_anchor.items()):
        requested_by_cth = defaultdict(set)
        for fragment_id, lines in line_sequences.items():
            requested_by_cth[fragment_cth[fragment_id]].update(
                p2e.requested_anchor_keys(
                    lines, anchor_length, sorted(mask_lengths)))
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
    p2e2_t1 = scramble_rank_tracer(
        line_sequences,
        fragment_cth,
        fragment_families,
        fragments_by_cth,
        anchor_indices[2],
    )

    primary_anchor = int(config["primary_cell"]["anchor_length"])
    primary_mask = int(config["primary_cell"]["mask_length"])
    calibration_cths, evaluation_cths, partition_totals, cth_weights = (
        split_compositions(
            line_sequences,
            fragment_cth,
            fragment_families,
            fragments_by_cth,
            primary_anchor,
            primary_mask,
        ))

    rules = generate_rules(config)
    baseline_rule = {
        "minimum_top_support_families": 1,
        "minimum_support_margin": 1,
        "minimum_dominance": 0.0,
        "maximum_alternatives": None,
    }
    cell_results = {}
    primary_eval_records = None
    primary_packet_rule = None

    for anchor_length, mask_length in cells:
        cell_name = f"a{anchor_length}_m{mask_length}"
        calibration_records = build_span_records(
            line_sequences,
            fragment_cth,
            fragment_families,
            fragments_by_cth,
            anchor_indices[anchor_length],
            anchor_length,
            mask_length,
            calibration_cths,
        )
        evaluation_records = build_span_records(
            line_sequences,
            fragment_cth,
            fragment_families,
            fragments_by_cth,
            anchor_indices[anchor_length],
            anchor_length,
            mask_length,
            evaluation_cths,
        )
        calibration_metrics = [
            evaluate_rule(calibration_records, rule) for rule in rules]
        chosen = choose_rules(
            calibration_metrics,
            config["calibration_targets"],
            int(config["minimum_calibration_accepts"]),
        )
        selected = evaluate_selected_rules(chosen, evaluation_records)
        cell_results[cell_name] = {
            "calibration_records": len(calibration_records),
            "evaluation_records": len(evaluation_records),
            "baseline": {
                "calibration":
                    evaluate_rule(calibration_records, baseline_rule),
                "evaluation":
                    evaluate_rule(evaluation_records, baseline_rule),
            },
            "selected_rules": selected,
            "targets_unattainable_on_calibration": [
                target for target, value in chosen.items() if value is None],
        }

        if (anchor_length, mask_length) == (primary_anchor, primary_mask):
            primary_eval_records = evaluation_records
            available = [
                (float(target), value)
                for target, value in selected.items() if value is not None
            ]
            if available:
                _, strictest = max(available, key=lambda item: item[0])
                primary_packet_rule = strictest[
                    "selected_on_calibration"]["rule"]
            else:
                primary_packet_rule = baseline_rule

    if primary_eval_records is None or primary_packet_rule is None:
        raise AssertionError("P2-E2: primary cell was not evaluated")

    packets, packet_counts = select_evidence_packets(
        primary_eval_records,
        primary_packet_rule,
        policy_name,
        int(config["evidence_packet_samples_per_outcome"]),
    )
    with open(PACKET_PATH, "w", encoding="utf-8") as destination:
        for packet in packets:
            destination.write(
                json.dumps(packet, ensure_ascii=False) + "\n")

    primary_name = f"a{primary_anchor}_m{primary_mask}"
    summary = {
        "probe": "P2-E2 abstention-calibrated witness reconstruction",
        "probe_label": "PROBE — not for citation",
        "evidence_policy": policy.name,
        "primary_cell": primary_name,
        "target_split": "dev with composition-disjoint internal calibration",
        "test_side_accessed": False,
        "restorations_included": False,
        "gold_available_to_ranker": False,
        "ranking_evidence": (
            "count of independent same-CTH witness families supporting each "
            "attested variable-length middle"),
        "tie_behavior": "abstain; no arbitrary evidence-tie breaker",
        "parameters": config,
        "partition": {
            "method": config["partition_method"],
            "calibration_compositions": len(calibration_cths),
            "evaluation_compositions": len(evaluation_cths),
            "calibration_cth": sorted(calibration_cths),
            "evaluation_cth": sorted(evaluation_cths),
            "primary_eligible_span_balance": partition_totals,
            "primary_eligible_spans_by_cth": {
                str(key): value for key, value in sorted(cth_weights.items())},
        },
        "tracers": {
            "base": base_tracers,
            "p2e_t1": p2e_t1,
            "p2e2_t1": p2e2_t1,
        },
        "cells": cell_results,
        "evidence_packets": {
            "path": str(PACKET_PATH),
            "count": len(packets),
            "outcome_counts": packet_counts,
            "selection_rule": primary_packet_rule,
            "dev_evaluation_only": True,
        },
        "interpretation_limits": [
            "Reliability is agreement with intentionally masked attested dev "
            "text, not truth for a genuine lacuna.",
            "Same-CTH membership is catalog-assisted candidate selection.",
            "Parallel witnesses may preserve variants or omissions; a "
            "nonmatching middle is not automatically an error.",
            "Calibration targets are exploratory and remain unpromoted.",
        ],
        "input_hashes": {
            "config": sha256(CONFIG_PATH),
            "edges_parquet": sha256(P2_OUT / "edges.parquet"),
            "decomposed_corpus_parquet":
                sha256(P4_OUT / "decomposed_corpus.parquet"),
            "splits_parquet": sha256(P2_OUT / "splits.parquet"),
            "tokenizer_json": sha256(Path("configs") / "tokenizer.json"),
        },
    }

    manifest = ep.build_manifest(
        task="duplicate_parallel_missing_context_calibration",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P4_OUT / "decomposed_corpus.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=CONFIG_PATH,
        seed=seed,
        declared_statistics_universe=(
            "calibration rules fit only on the recorded calibration CTHs "
            "within frozen unambiguous real-composition dev; held-out "
            "evaluation CTHs used only after rule selection; same-CTH "
            "independent attested witness alternatives; no test content"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "control_fields_observed": [
            "fragment_id", "parent_doc", "main_split"],
        "test_side_accessed": False,
        "restoration_included": False,
        "model_scoring_performed": False,
        "gold_available_to_ranker": False,
        "calibration_and_evaluation_composition_disjoint": True,
        "typed_evidence_packets_emitted": True,
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
        f"P2-E2 complete: {primary_name}, "
        f"{len(calibration_cths)} calibration CTHs / "
        f"{len(evaluation_cths)} evaluation CTHs.")
    print(
        f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, {PACKET_PATH}, "
        f"and {REPORT_PATH}")


if __name__ == "__main__":
    main()
