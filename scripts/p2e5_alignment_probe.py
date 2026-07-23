#!/usr/bin/env python3
"""P2-E5: observed-context alignment diagnostic for exact-anchor absences.

This dev-only probe asks whether a deterministic, inspectable two-flank
alignment can recover compact candidate middles for P2-E4 contexts where the
intentionally hidden attested sign was absent from every exact-anchor witness
alternative. The hidden sign defines the post-hoc diagnostic subset and is
used for evaluation only; it is never passed to retrieval or alignment.

Usage:
    python scripts/p2e5_alignment_probe.py
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
import sequence_alignment as sa

import p2e2_abstention_calibration as p2e2
import p2e3_cross_calibration as p2e3
import p2e4_candidate_set_audit as p2e4
import p2e_witness_recoverability as p2e


CONFIG_PATH = Path("configs") / "p2e5_alignment_probe.json"
P2_OUT = Path("p2_out")
P4_OUT = Path("p4_out")
OUT_DIR = Path("phase2_out")
RESULT_PATH = OUT_DIR / "p2e5_alignment_probe.json"
PACKET_PATH = OUT_DIR / "p2e5_alignment_packets.jsonl"
MANIFEST_PATH = OUT_DIR / "p2e5_alignment_probe_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e5_alignment_probe.md"
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


def ngrams(tokens, n):
    tokens = tuple(tokens)
    return {
        tokens[index:index + n]
        for index in range(max(0, len(tokens) - n + 1))
    }


def line_indices_by_fragment(edges):
    return {
        row.fragment_id: [
            int(value["line_index_in_doc"])
            for value in sorted(
                json.loads(row.lines),
                key=lambda value: value["line_index_in_doc"])
        ]
        for row in edges.itertuples(index=False)
    }


def build_witness_line_index(
        line_sequences,
        fragment_cth,
        fragment_families,
        line_indices,
        seed_ngram):
    lines = {}
    seed_index = defaultdict(lambda: defaultdict(set))
    for fragment_id in sorted(line_sequences):
        cth = fragment_cth[fragment_id]
        family = fragment_families[fragment_id]
        positions = line_indices[fragment_id]
        if len(positions) != len(line_sequences[fragment_id]):
            raise AssertionError(
                "P2-E5: line sequence and locator counts disagree")
        for line_position, tokens in enumerate(
                line_sequences[fragment_id]):
            line_id = (fragment_id, line_position)
            lines[line_id] = {
                "line_id": line_id,
                "fragment_id": fragment_id,
                "family": family,
                "cth": cth,
                "line_position_in_fragment": line_position,
                "line_index_in_doc": positions[line_position],
                "tokens": tuple(tokens),
            }
            for seed in ngrams(tokens, seed_ngram):
                seed_index[cth][seed].add(line_id)
    return lines, seed_index


def observed_flanks(record, line_sequences, flank_window, mask_length):
    line = line_sequences[record["fragment_id"]][
        record["line_position_in_fragment"]]
    offset = record["sign_offset_in_line"]
    hidden = tuple(line[offset:offset + mask_length])
    if hidden != record["gold"]:
        raise AssertionError(
            "P2-E5: locator does not identify the held-out evaluation span")
    left = tuple(line[max(0, offset - flank_window):offset])
    right = tuple(
        line[
            offset + mask_length:
            offset + mask_length + flank_window
        ])
    if len(left) < 2 or len(right) < 2:
        raise AssertionError(
            "P2-E5: P2-E4 record lacks its required two-sided context")
    return left, right


def seeded_witness_lines(
        cth,
        query_family,
        left_flank,
        right_flank,
        lines,
        seed_index,
        config):
    seed_n = int(config["seed_ngram"])
    left_seeds = ngrams(left_flank, seed_n)
    right_seeds = ngrams(right_flank, seed_n)
    left_ids = set().union(*(
        seed_index[cth].get(seed, set()) for seed in left_seeds))
    right_ids = set().union(*(
        seed_index[cth].get(seed, set()) for seed in right_seeds))
    candidates = []
    for line_id in left_ids & right_ids:
        line = lines[line_id]
        if line["family"] == query_family:
            continue
        line_seeds = ngrams(line["tokens"], seed_n)
        seed_overlap = (
            len(left_seeds & line_seeds)
            + len(right_seeds & line_seeds)
        )
        candidates.append({**line, "seed_overlap": seed_overlap})
    candidates.sort(
        key=lambda value: (
            -value["seed_overlap"],
            value["fragment_id"],
            value["line_position_in_fragment"],
        ))
    maximum = int(config["maximum_seeded_witness_lines"])
    return candidates[:maximum], {
        "seeded_independent_witness_lines": len(candidates),
        "seeded_witness_lines_scored": min(len(candidates), maximum),
        "seeded_witness_lines_truncated":
            max(0, len(candidates) - maximum),
    }


def _alignment_evidence(line, alignment):
    return {
        "witness_fragment_id": line["fragment_id"],
        "witness_family": line["family"],
        "line_position_in_fragment":
            line["line_position_in_fragment"],
        "line_index_in_doc": line["line_index_in_doc"],
        "seed_overlap": line["seed_overlap"],
        "candidate_middle": list(alignment["middle"]),
        "alignment_score": alignment["score"],
        "normalized_alignment_score":
            alignment["normalized_score"],
        "exact_context_matches": alignment["exact_matches"],
        "candidate_left_boundary": alignment["left_boundary"],
        "candidate_right_boundary": alignment["right_boundary"],
        "left_alignment": {
            "query": list(alignment["left"]["aligned_query"]),
            "witness": list(alignment["left"]["aligned_witness"]),
            "exact_matches": alignment["left"]["exact_matches"],
            "mismatches": alignment["left"]["mismatches"],
            "query_gaps": alignment["left"]["query_gaps"],
            "witness_gaps": alignment["left"]["witness_gaps"],
        },
        "right_alignment": {
            "query": list(alignment["right"]["aligned_query"]),
            "witness": list(alignment["right"]["aligned_witness"]),
            "exact_matches": alignment["right"]["exact_matches"],
            "mismatches": alignment["right"]["mismatches"],
            "query_gaps": alignment["right"]["query_gaps"],
            "witness_gaps": alignment["right"]["witness_gaps"],
        },
        "evidence_class": "EDITORIAL_TRANSCRIPTION",
        "score_class": "MODEL_DERIVED",
    }


def generate_alignment_candidates(
        left_flank,
        right_flank,
        witness_lines,
        config):
    """Aggregate best inspectable alignment per proposal and witness family."""
    evidence_by_proposal = defaultdict(dict)
    for line in sorted(
            witness_lines,
            key=lambda value: (
                value["fragment_id"],
                value["line_position_in_fragment"],
            )):
        alignments = sa.bounded_two_flank_alignments(
            left_flank,
            right_flank,
            line["tokens"],
            maximum_middle_length=int(
                config["maximum_middle_length"]),
            minimum_exact_matches_per_flank=int(
                config["minimum_exact_matches_per_flank"]),
            minimum_normalized_score=float(
                config["minimum_normalized_score"]),
            match_score=int(config["match_score"]),
            mismatch_score=int(config["mismatch_score"]),
            gap_score=int(config["gap_score"]),
        )
        for alignment in alignments[
                :int(config["maximum_alignments_per_witness_line"])]:
            proposal = alignment["middle"]
            evidence = _alignment_evidence(line, alignment)
            previous = evidence_by_proposal[proposal].get(line["family"])
            signature = (
                evidence["alignment_score"],
                evidence["exact_context_matches"],
                evidence["seed_overlap"],
            )
            if previous is None:
                evidence_by_proposal[proposal][line["family"]] = evidence
            else:
                previous_signature = (
                    previous["alignment_score"],
                    previous["exact_context_matches"],
                    previous["seed_overlap"],
                )
                if signature > previous_signature:
                    evidence_by_proposal[proposal][line["family"]] = evidence

    alternatives = []
    for proposal, by_family in evidence_by_proposal.items():
        evidence = sorted(
            by_family.values(),
            key=lambda value: (
                -value["alignment_score"],
                -value["exact_context_matches"],
                value["witness_family"],
                value["witness_fragment_id"],
            ),
        )
        scores = [
            value["normalized_alignment_score"] for value in evidence]
        alternatives.append({
            "proposal": proposal,
            "supporting_families": tuple(sorted(by_family)),
            "support_count": len(by_family),
            "mean_normalized_alignment_score":
                round(statistics.mean(scores), 6),
            "best_normalized_alignment_score": max(scores),
            "alignments": evidence,
        })
    alternatives.sort(
        key=lambda value: (
            -value["support_count"],
            -value["mean_normalized_alignment_score"],
            -value["best_normalized_alignment_score"],
            value["proposal"],
        ))
    return {
        "alternatives": alternatives,
        "alternative_count": len(alternatives),
    }


def score_observed_context(
        record,
        left_flank,
        right_flank,
        lines,
        seed_index,
        alignment_config):
    witness_lines, retrieval = seeded_witness_lines(
        record["cth"],
        record["query_family"],
        left_flank,
        right_flank,
        lines,
        seed_index,
        alignment_config,
    )
    scorer_config = {
        **alignment_config,
        "maximum_middle_length":
            alignment_config["maximum_witness_middle_length"],
    }
    ranking = generate_alignment_candidates(
        left_flank, right_flank, witness_lines, scorer_config)
    return {
        "observed_left_flank": left_flank,
        "observed_right_flank": right_flank,
        "retrieval": retrieval,
        "ranking": ranking,
    }


def alignment_candidate_rank(record):
    for rank, alternative in enumerate(
            record["alignment"]["ranking"]["alternatives"], 1):
        if alternative["proposal"] == record["gold"]:
            return rank
    return None


def alignment_metrics(records, depths):
    ranks = [alignment_candidate_rank(record) for record in records]
    supported = [
        record for record in records
        if record["alignment"]["ranking"]["alternatives"]]
    set_sizes = [
        record["alignment"]["ranking"]["alternative_count"]
        for record in supported]
    result = {
        "diagnostic_contexts": len(records),
        "contexts_with_alignment_candidates": len(supported),
        "alignment_candidate_coverage_percent":
            pct(len(supported), len(records)),
        "exact_rescue_anywhere_contexts":
            sum(rank is not None for rank in ranks),
        "exact_rescue_anywhere_percent":
            pct(sum(rank is not None for rank in ranks), len(records)),
        "exact_rescue_anywhere_wilson_95":
            p2e2.wilson_interval(
                sum(rank is not None for rank in ranks), len(records)),
        "no_exact_rescue_contexts":
            sum(rank is None for rank in ranks),
        "candidate_set_size_when_supported": {
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
        "retrieval": {
            "contexts_with_seed_truncation": sum(
                record["alignment"]["retrieval"][
                    "seeded_witness_lines_truncated"] > 0
                for record in records),
            "total_seeded_independent_witness_lines": sum(
                record["alignment"]["retrieval"][
                    "seeded_independent_witness_lines"]
                for record in records),
            "total_seeded_witness_lines_scored": sum(
                record["alignment"]["retrieval"][
                    "seeded_witness_lines_scored"]
                for record in records),
        },
    }
    for depth in depths:
        rescued = sum(
            rank is not None and rank <= depth for rank in ranks)
        displayed_sizes = [
            min(
                depth,
                record["alignment"]["ranking"]["alternative_count"])
            for record in records
        ]
        result["prefix_sets"][str(depth)] = {
            "exact_rescue_contexts": rescued,
            "exact_rescue_percent": pct(rescued, len(records)),
            "exact_rescue_wilson_95":
                p2e2.wilson_interval(rescued, len(records)),
            "mean_options_added_per_diagnostic_context":
                round(statistics.mean(displayed_sizes), 3),
        }
    return result


def composition_macro(records, depth):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["cth"]].append(record)
    percentages = []
    for group in grouped.values():
        rescued = sum(
            (
                rank := alignment_candidate_rank(record)
            ) is not None and rank <= depth
            for record in group
        )
        percentages.append(100.0 * rescued / len(group))
    return {
        "compositions_with_diagnostic_contexts": len(grouped),
        "mean_exact_rescue_percent":
            round(statistics.mean(percentages), 2) if percentages else None,
        "median_exact_rescue_percent":
            round(statistics.median(percentages), 2) if percentages else None,
        "minimum_exact_rescue_percent":
            round(min(percentages), 2) if percentages else None,
        "maximum_exact_rescue_percent":
            round(max(percentages), 2) if percentages else None,
    }


def breakdown(records, depths):
    groups = defaultdict(list)
    for record in records:
        groups[p2e4.disagreement_category(record)].append(record)
    return {
        key: alignment_metrics(value, depths)
        for key, value in sorted(groups.items())
    }


def outcome(record, maximum_depth):
    ranking = record["alignment"]["ranking"]
    if not ranking["alternatives"]:
        return "ABSTAIN_NO_ALIGNMENT_CANDIDATE"
    rank = alignment_candidate_rank(record)
    if rank is not None and rank <= maximum_depth:
        return "ALIGNMENT_EXACT_RESCUE"
    return "ALIGNMENT_SUPPORTED_NO_EXACT_RESCUE"


def alignment_packet(
        record,
        policy_name,
        maximum_depth,
        maximum_alignments):
    ranking = record["alignment"]["ranking"]
    alternatives = []
    for rank, alternative in enumerate(
            ranking["alternatives"][:maximum_depth], 1):
        alternatives.append({
            "rank": rank,
            "middle": list(alternative["proposal"]),
            "independent_witness_family_count":
                alternative["support_count"],
            "supporting_witness_families":
                list(alternative["supporting_families"]),
            "mean_normalized_alignment_score":
                alternative["mean_normalized_alignment_score"],
            "best_normalized_alignment_score":
                alternative["best_normalized_alignment_score"],
            "score_is_not_probability": True,
            "inspectable_alignments":
                alternative["alignments"][:maximum_alignments],
        })
    packet_outcome = outcome(record, maximum_depth)
    return {
        "proposed_relation":
            "DIAGNOSTIC_ALIGNMENT_MISSING_CONTEXT_CANDIDATE_SET",
        "decision": (
            "PRESENT_DIAGNOSTIC_CANDIDATE_SET"
            if alternatives else "ABSTAIN"),
        "outcome": packet_outcome,
        "expert_action_required": True,
        "expert_selection_becomes_ground_truth_automatically": False,
        "evidence_policy": policy_name,
        "query": {
            "fragment_id": record["fragment_id"],
            "cth": record["cth"],
            "span_ordinal": record["span_ordinal"],
            "line_index_in_doc": record["line_index_in_doc"],
            "sign_offset_in_line": record["sign_offset_in_line"],
            "observed_left_flank":
                list(record["alignment"]["observed_left_flank"]),
            "observed_right_flank":
                list(record["alignment"]["observed_right_flank"]),
        },
        "candidate_set": {
            "alternatives": alternatives,
            "total_alignment_alternatives":
                ranking["alternative_count"],
            "other_or_unsupported_available": True,
            "probability_available": False,
            "probability_reason": (
                "P2-E5 alignment scores are uncalibrated diagnostic scores, "
                "not probabilities. Calibration is a later decision only "
                "if this probe finds recoverable signal."),
        },
        "retrieval": record["alignment"]["retrieval"],
        "enabled_assistance_layers": [
            "OBSERVED_DOCUMENT_STRUCTURE",
            "EDITORIAL_TRANSCRIPTION",
            "CATALOG_METADATA",
            "MODEL_DERIVED",
        ],
        "editorial_features_used": ["token"],
        "model_features_used": ["local_alignment_score"],
        "abstention_reason": (
            "No independent witness line shared observed bigram evidence "
            "on both sides and passed the alignment constraints."
            if not alternatives else None),
        "dev_evaluation_only": {
            "posthoc_subset_reason":
                "attested reading absent from exact-anchor alternatives",
            "intentionally_hidden_attested_middle": list(record["gold"]),
            "alignment_candidate_rank":
                alignment_candidate_rank(record),
            "never_available_to_alignment_scorer": True,
            "not_truth_for_a_genuine_lacuna": True,
        },
    }


def select_packets(
        records,
        policy_name,
        per_outcome,
        maximum_depth,
        maximum_alignments):
    grouped = defaultdict(list)
    for record in records:
        grouped[outcome(record, maximum_depth)].append(record)
    packets = []
    for label in sorted(grouped):
        ordered = sorted(
            grouped[label],
            key=lambda record: (
                record["cth"],
                record["fragment_id"],
                record["span_ordinal"],
            ))
        chosen = []
        used_cths = set()
        for record in ordered:
            if record["cth"] in used_cths:
                continue
            chosen.append(record)
            used_cths.add(record["cth"])
            if len(chosen) == per_outcome:
                break
        packets.extend(
            alignment_packet(
                record,
                policy_name,
                maximum_depth,
                maximum_alignments,
            )
            for record in chosen)
    return packets


def ranking_signature(result, depth=5):
    return tuple(
        (
            alternative["proposal"],
            alternative["support_count"],
            alternative["mean_normalized_alignment_score"],
        )
        for alternative in result["ranking"]["alternatives"][:depth]
    )


def synthetic_alignment_tracer(alignment_config):
    record = {"cth": 1, "query_family": "query"}
    lines = {
        ("w1", 0): {
            "line_id": ("w1", 0),
            "fragment_id": "w1",
            "family": "f1",
            "cth": 1,
            "line_position_in_fragment": 0,
            "line_index_in_doc": 0,
            "tokens": ("A", "B", "C", "X", "D", "E", "F"),
        },
    }
    seed_index = defaultdict(lambda: defaultdict(set))
    for line_id, line in lines.items():
        for seed in ngrams(
                line["tokens"], int(alignment_config["seed_ngram"])):
            seed_index[1][seed].add(line_id)
    original = score_observed_context(
        record,
        ("A", "B", "C"),
        ("D", "E", "F"),
        lines,
        seed_index,
        alignment_config,
    )
    reversed_lines = dict(reversed(list(lines.items())))
    invariant = score_observed_context(
        record,
        ("A", "B", "C"),
        ("D", "E", "F"),
        reversed_lines,
        seed_index,
        alignment_config,
    )
    scrambled = score_observed_context(
        record,
        ("C", "B", "A"),
        ("F", "E", "D"),
        lines,
        seed_index,
        alignment_config,
    )
    passed = (
        original["ranking"]["alternatives"]
        and original["ranking"]["alternatives"][0]["proposal"] == ("X",)
        and ranking_signature(original) == ranking_signature(invariant)
        and ranking_signature(original) != ranking_signature(scrambled)
    )
    result = {
        "exact_middle_recovered": bool(
            original["ranking"]["alternatives"]
            and original["ranking"]["alternatives"][0]["proposal"]
            == ("X",)),
        "witness_line_order_invariant":
            ranking_signature(original) == ranking_signature(invariant),
        "token_order_scramble_changed_output":
            ranking_signature(original) != ranking_signature(scrambled),
        "blocking_failures": int(not passed),
    }
    if not passed:
        raise AssertionError(f"P2-E5 synthetic tracer failed: {result}")
    return result


def real_alignment_tracer(
        residual_records,
        line_sequences,
        lines,
        seed_index,
        alignment_config):
    canaries = []
    for record in sorted(
            residual_records,
            key=lambda value: (
                value["cth"],
                value["fragment_id"],
                value["span_ordinal"],
            )):
        left, right = observed_flanks(
            record,
            line_sequences,
            int(alignment_config["flank_window"]),
            1,
        )
        if left == tuple(reversed(left)) or right == tuple(reversed(right)):
            continue
        original = score_observed_context(
            record, left, right, lines, seed_index, alignment_config)
        if not original["ranking"]["alternatives"]:
            continue
        reversed_lines = dict(reversed(list(lines.items())))
        invariant = score_observed_context(
            record,
            left,
            right,
            reversed_lines,
            seed_index,
            alignment_config,
        )
        scrambled = score_observed_context(
            record,
            tuple(reversed(left)),
            tuple(reversed(right)),
            lines,
            seed_index,
            alignment_config,
        )
        canaries.append({
            "order_invariant":
                ranking_signature(original) == ranking_signature(invariant),
            "scramble_changed":
                ranking_signature(original) != ranking_signature(scrambled),
        })
        if len(canaries) == 12:
            break
    if not canaries:
        raise AssertionError("P2-E5: no real alignment tracer canaries")
    changed = sum(value["scramble_changed"] for value in canaries)
    invariant = sum(value["order_invariant"] for value in canaries)
    required = max(1, math.ceil(0.75 * len(canaries)))
    passed = changed >= required and invariant == len(canaries)
    result = {
        "real_canaries": len(canaries),
        "real_canaries_changed_under_token_order_scramble": changed,
        "real_canaries_required_to_change": required,
        "real_canaries_witness_line_order_invariant": invariant,
        "blocking_failures": int(not passed),
    }
    if not passed:
        raise AssertionError(f"P2-E5 real tracer failed: {result}")
    return result


def write_report(summary, elapsed_seconds):
    metrics = summary["alignment_residual_diagnostic"]["micro"]
    macro = summary["alignment_residual_diagnostic"]["composition_macro_at_5"]
    rows = []
    for depth, values in metrics["prefix_sets"].items():
        interval = values["exact_rescue_wilson_95"]
        rows.append(
            f"| {depth} | {values['mean_options_added_per_diagnostic_context']} "
            f"| {values['exact_rescue_contexts']}/"
            f"{metrics['diagnostic_contexts']} "
            f"({values['exact_rescue_percent']}%) | "
            f"[{interval[0] * 100:.1f}, {interval[1] * 100:.1f}] |")
    breakdown_rows = []
    for category, values in summary[
            "alignment_residual_diagnostic"]["by_prior_observable_category"].items():
        at_five = values["prefix_sets"]["5"]
        breakdown_rows.append(
            f"| `{category}` | {values['diagnostic_contexts']} | "
            f"{at_five['exact_rescue_contexts']} "
            f"({at_five['exact_rescue_percent']}%) |")
    lines = [
        "# Phase 2 P2-E5 observed-context alignment diagnostic",
        "",
        "**[PROBE — not for citation]**",
        "",
        "## Tracer block",
        "",
        "- Base tracers: PASS, zero blocking failures; historical D18 T4 "
        "remains diagnostic and non-blocking.",
        "- Existing witness-ranker/formulaicity controls: PASS.",
        f"- New alignment T1: PASS; "
        f"{summary['tracers']['alignment_real_t1']['real_canaries_changed_under_token_order_scramble']}/"
        f"{summary['tracers']['alignment_real_t1']['real_canaries']} real "
        "canaries changed under token-order scrambling, and witness-line "
        "order was invariant.",
        "",
        "## Question and method",
        "",
        "For Q0/Q3, can observed-context alignment recover a compact option "
        "set for the P2-E4 cases where the hidden attested sign was absent "
        "from every exact-anchor alternative? This is a post-hoc residual "
        "diagnostic, not a deployable selector. Retrieval required observed "
        "bigram evidence on both sides; two flanks were aligned monotonically "
        "around a bounded 0–12-sign witness middle. The hidden sign was used "
        "only after ranking.",
        "",
        "## Findings",
        "",
        f"{metrics['contexts_with_alignment_candidates']}/"
        f"{metrics['diagnostic_contexts']} contexts produced any alignment "
        f"candidate ({metrics['alignment_candidate_coverage_percent']}%).",
        "",
        "| displayed alignment depth | mean added options / residual context "
        "| exact rescue | 95% Wilson CI |",
        "|---:|---:|---:|---:|",
        *rows,
        "",
        f"At depth five, composition-macro rescue across "
        f"{macro['compositions_with_diagnostic_contexts']} CTHs had mean "
        f"{macro['mean_exact_rescue_percent']}% and median "
        f"{macro['median_exact_rescue_percent']}% (range "
        f"{macro['minimum_exact_rescue_percent']}–"
        f"{macro['maximum_exact_rescue_percent']}%).",
        "",
        "| prior exact-anchor disagreement | contexts | exact rescue @5 |",
        "|---|---:|---:|",
        *breakdown_rows,
        "",
        "Every packet persists aligned query/witness rows, gaps, boundaries, "
        "source families, and contradictions. Alignment scores are explicitly "
        "uncalibrated and are not displayed as probabilities.",
        "",
        "## Interpretation",
        "",
        summary["interpretation"],
        "",
        f"Cost: {elapsed_seconds:.1f}s compute; budget ≤"
        f"{summary['parameters']['time_budget_hours']}h. Profile "
        f"`{summary['evidence_policy']}`; dev-only residual diagnostic; test, "
        "restorations, `cu`, morphology, and generated text untouched.",
        "",
        "**Falsifier:** the alignment-rescue conclusion would be wrong if a "
        "non-residual composition-disjoint evaluation selected without hidden "
        "labels fails to retain the same attested-span gain at comparable set "
        "size and alignment constraints.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    started = time.perf_counter()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    policy_name = config["evidence_policy"]
    seed = int(config["seed"])
    alignment_config = {
        **config["alignment"],
        "maximum_witness_middle_length":
            int(config["maximum_witness_middle_length"]),
    }

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(policy_name, POLICIES_PATH)
    semantic_fields = [
        "token", "damage_state", "line_index_in_doc", "cth",
        "anchor_formulaicity_cth_df",
        "available_independent_witness_family_count",
        "query_anchor_occurrence_count",
        "local_alignment_score",
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
        label="P2-E5 dev attested-only")

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
    for fragment_id, fragment_lines in line_sequences.items():
        requested_by_cth[fragment_cth[fragment_id]].update(
            p2e.requested_anchor_keys(
                fragment_lines, anchor_length, [mask_length]))
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
    synthetic_t1 = synthetic_alignment_tracer(alignment_config)

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
    p2e4.add_anchor_repeat_counts(records)
    p2e4.add_line_indices(records, edges)
    weights = Counter(record["cth"] for record in records)
    folds = p2e3.assign_composition_folds(
        weights, set(weights), int(config["folds"]))
    rules = p2e2.generate_rules(config)
    accepted, fold_results = p2e4.fold_candidate_sets(
        records, folds, rules, config)
    residuals = [
        record for record in accepted
        if p2e4.candidate_rank(record) is None]

    locators = line_indices_by_fragment(edges)
    witness_lines, seed_index = build_witness_line_index(
        line_sequences,
        fragment_cth,
        fragment_families,
        locators,
        int(alignment_config["seed_ngram"]),
    )
    real_t1 = real_alignment_tracer(
        residuals,
        line_sequences,
        witness_lines,
        seed_index,
        alignment_config,
    )

    scored = []
    for record in residuals:
        left, right = observed_flanks(
            record,
            line_sequences,
            int(alignment_config["flank_window"]),
            mask_length,
        )
        copied = dict(record)
        copied["alignment"] = score_observed_context(
            record,
            left,
            right,
            witness_lines,
            seed_index,
            alignment_config,
        )
        scored.append(copied)

    depths = [int(value) for value in config["candidate_set_depths"]]
    metrics = alignment_metrics(scored, depths)
    maximum_depth = max(depths)
    packets = select_packets(
        scored,
        policy.name,
        int(config["packets_per_outcome"]),
        maximum_depth,
        int(config["maximum_packet_alignments_per_alternative"]),
    )
    rescue_at_five = metrics["prefix_sets"][str(maximum_depth)][
        "exact_rescue_contexts"]
    interpretation = (
        "Observed-context alignment recovered some exact alternatives that "
        "the exact-anchor set omitted; the next step is a composition-folded "
        "non-residual calibration study before any UI probability is shown."
        if rescue_at_five
        else
        "The bounded alignment did not recover exact hidden readings in the "
        "residual diagnostic; preserve exact-anchor candidate sets and "
        "abstention rather than adding this alignment layer."
    )
    summary = {
        "probe": "P2-E5 observed-context alignment diagnostic",
        "probe_label": "PROBE — not for citation",
        "evidence_policy": policy.name,
        "target_split":
            "post-hoc P2-E4 exact-anchor-absence subset inside dev",
        "test_side_accessed": False,
        "restorations_included": False,
        "gold_available_to_alignment_scorer": False,
        "model_generated_content_included": False,
        "parameters": config,
        "p2e4_selector_accepted_contexts": len(accepted),
        "posthoc_exact_anchor_absence_contexts": len(residuals),
        "formulaicity_statistics": formulaicity_metadata,
        "folds": fold_results,
        "tracers": {
            "base": base_tracers,
            "p2e_t1": p2e_t1,
            "p2e2_t1": p2e2_t1,
            "formulaicity_t1": formula_t1,
            "alignment_synthetic_t1": synthetic_t1,
            "alignment_real_t1": real_t1,
        },
        "alignment_residual_diagnostic": {
            "micro": metrics,
            "composition_macro_at_5":
                composition_macro(scored, maximum_depth),
            "by_prior_observable_category":
                breakdown(scored, depths),
        },
        "evidence_packet_count": len(packets),
        "interpretation": interpretation,
        "interpretation_limits": [
            "The 387-context diagnostic subset was selected post hoc using "
            "the hidden attested evaluation reading; it is not a deployable "
            "selector or unbiased end-to-end estimate.",
            "Alignment retrieval and ranking used observed context only; the "
            "hidden reading entered evaluation after ranking.",
            "Alignment scores are MODEL_DERIVED uncalibrated diagnostics, "
            "not probabilities.",
            "Agreement with intentionally masked attested text is not truth "
            "for a genuine lacuna.",
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
        task="duplicate_parallel_alignment_residual_diagnostic",
        evidence_policy=policy.name,
        features_requested=semantic_fields,
        registry=registry,
        policy=policy,
        dataset_manifest_path=P4_OUT / "decomposed_corpus.parquet",
        split_manifest_path=P2_OUT / "splits.parquet",
        config_path=CONFIG_PATH,
        seed=seed,
        declared_statistics_universe=(
            "post-hoc exact-anchor-absence contexts among P2-E4's "
            "composition-folded dev selector acceptances; alignment witness "
            "retrieval restricted to independent same-CTH dev families; "
            "formulaicity fit over unambiguous real-composition train+dev; "
            "no test or discovery content"),
    )
    manifest.update({
        "probe_label": "PROBE — not for citation",
        "test_side_accessed": False,
        "restoration_included": False,
        "model_scoring_performed": True,
        "model_generated_content_included": False,
        "gold_available_to_alignment_scorer": False,
        "diagnostic_subset_selected_posthoc_with_evaluation_label": True,
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
        f"P2-E5 complete: {len(residuals)} residual contexts, "
        f"{rescue_at_five} exact rescues@{maximum_depth}, "
        f"{len(packets)} packets.")
    print(
        f"Wrote {RESULT_PATH}, {PACKET_PATH}, {MANIFEST_PATH}, "
        f"and {REPORT_PATH}")


if __name__ == "__main__":
    main()
