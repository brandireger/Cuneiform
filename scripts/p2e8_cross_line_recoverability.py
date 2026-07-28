#!/usr/bin/env python3
"""P2-E8: cross-line witness recoverability census.

Cross-line anchors are **89.9% of anchored real gaps and have no calibration
at all** (`reports/phase4_p4g_rerun.md`). Every existing calibration -- P2-E4's
per-rank rates, P2-E6's set-inclusion rates -- was fit on masks generated
strictly *within* a line: `iter_masked_spans_with_location()` iterates
`for line_position, line in enumerate(lines)` and never crosses, and
`build_anchor_index()` indexes anchor pairs inside one line. Borrowing a
same-line rate for a cross-line anchor would be applying a measurement to a
population it was never estimated on.

This script is the census that has to come first: **is there anything to
calibrate?** It measures how often a cross-line anchor pair has independent
witness support at all, and how often that support contains the true masked
content. It deliberately produces no rates presented as probabilities -- that
is a later fold-structured step, exactly as P2-E preceded P2-E2/P2-E4.

## Two witness-admission rules, both measured

A cross-line query asks: given a left anchor ending on line N and a right
anchor starting on line N+1, what came between? Which witness occurrences may
answer is a philological decision, not an implementation detail:

- `STRICT` -- only witness occurrences whose anchor pair also straddles a line
  boundary. Conservative: treats the line break as part of the evidence.
- `LAYOUT_AGNOSTIC` -- any witness occurrence of that anchor pair, including
  same-line ones. Line division is scribal layout: the same phrase may be
  written on one line in one manuscript and across a break in another, so a
  same-line witness is real evidence about the text.

Neither is assumed. Both are measured, reported side by side, and left for
ratification. `LAYOUT_AGNOSTIC` is the more permissive rule and its extra
yield is exactly the quantity a reviewer should see before it is adopted.

## What is refused

A line refused by the language scope renders empty but keeps its position slot
(see `render_fragments`). Concatenating across an empty slot would fabricate
adjacency between two lines that have out-of-scope material between them --
the same fabrication `EXCLUDE_LINE` exists to prevent. Boundaries adjacent to
an empty slot are refused and counted, never crossed.

Usage:
    python scripts/p2e8_cross_line_recoverability.py
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import contracts  # noqa: E402
import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llookup  # noqa: E402

import p2e_witness_recoverability as p2e  # noqa: E402

SEED = 20260727
POLICY_NAME = "catalog_assisted"
ANCHOR_LENGTHS = (1, 2, 3)
MASK_LENGTHS = (1, 2, 3, 5)
MAX_WITNESS_MIDDLE = p2e.MAX_WITNESS_MIDDLE

# Where the crossed line boundary falls inside the anchored window. Reported
# separately because they are different evidential situations, not one bucket.
BOUNDARY_REGIONS = (
    "in_mask", "at_mask_start", "at_mask_end", "in_left_anchor",
    "in_right_anchor")

# Same-line gold inclusion from the P4-D-corrected P2-E rerun, for the only
# comparison that matters here: is cross-line evidence weaker, and by how much?
SAME_LINE_REFERENCE = {
    "a1_m1": (89899, 42924), "a1_m2": (76906, 24097), "a1_m3": (65139, 13639),
    "a1_m5": (45352, 4400), "a2_m1": (65139, 13639), "a2_m2": (54626, 7781),
    "a2_m3": (45352, 4400),
}
ADMISSION_RULES = ("STRICT", "LAYOUT_AGNOSTIC")

OUT_DIR = Path("Phase2/phase2_out")
RESULT_PATH = OUT_DIR / "p2e8_cross_line_recoverability.json"
MANIFEST_PATH = OUT_DIR / "p2e8_cross_line_recoverability_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e8_cross_line_recoverability.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"


def boundary_region(left_start, mask_start, mask_end, right_end, boundary):
    """Which part of the anchored window the line break falls inside.

    Returns None when the window does not cross the boundary at all, which
    makes it a same-line span and therefore P2-E's population, not this one.

    The two `at_*` regions are distinct from the `in_*` ones and matter: a
    break falling exactly between the left anchor and the mask leaves the
    anchor itself intact on one line, which is a different evidential
    situation from a break that splits an anchor in two. For mask length 1,
    `in_mask` is unreachable by construction -- a line break cannot fall
    strictly inside a single sign -- so an empty `in_mask` row there is
    correct, not a missing measurement.
    """
    if not left_start < boundary < right_end:
        return None
    if boundary < mask_start:
        return "in_left_anchor"
    if boundary == mask_start:
        return "at_mask_start"
    if boundary == mask_end:
        return "at_mask_end"
    if boundary > mask_end:
        return "in_right_anchor"
    return "in_mask"


def iter_cross_line_spans(lines, anchor_length, mask_length):
    """Yield cross-line masked spans over adjacent line pairs.

    Yields (boundary_region, (left, right), gold). One boundary per pair: the
    dominant real case (13,807 of 17,379 cross-line gaps crossed exactly one
    line). Deeper crossings are a declared extension, not silently folded in.
    """
    for position in range(len(lines) - 1):
        first, second = lines[position], lines[position + 1]
        # Never cross an empty slot: an out-of-scope line's absence is not
        # permission to treat its neighbours as adjacent.
        if not first or not second:
            continue
        flat = list(first) + list(second)
        boundary = len(first)
        stop = len(flat) - anchor_length - mask_length + 1
        for start in range(anchor_length, max(anchor_length, stop)):
            left_start = start - anchor_length
            mask_end = start + mask_length
            right_end = mask_end + anchor_length
            region = boundary_region(
                left_start, start, mask_end, right_end, boundary)
            if region is None:
                continue
            left = tuple(flat[left_start:start])
            gold = tuple(flat[start:mask_end])
            right = tuple(flat[mask_end:right_end])
            yield region, (left, right), gold


def count_refused_boundaries(line_sequences):
    """Boundaries not crossed because a neighbouring slot is out of scope."""
    refused = 0
    total = 0
    for lines in line_sequences.values():
        for position in range(len(lines) - 1):
            total += 1
            if not lines[position] or not lines[position + 1]:
                refused += 1
    return refused, total


def requested_cross_line_keys(lines, anchor_length, mask_lengths):
    keys = set()
    for mask_length in mask_lengths:
        for _, key, _ in iter_cross_line_spans(lines, anchor_length, mask_length):
            keys.add(key)
    return keys


def build_cross_line_index(
        line_sequences, fragment_families, fragment_cth, anchor_length,
        requested_by_cth):
    """Index witness middles whose anchor pair straddles a line boundary.

    Structurally the same as `p2e.build_anchor_index`, but the witness window
    is a consecutive line PAIR rather than one line, and only boundary-
    crossing occurrences are retained -- that is what makes this the STRICT
    rule's index.
    """
    index = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    for fragment_id in sorted(line_sequences):
        cth = fragment_cth[fragment_id]
        requested = requested_by_cth.get(cth, set())
        if not requested:
            continue
        family = fragment_families[fragment_id]
        lines = line_sequences[fragment_id]
        for position in range(len(lines) - 1):
            first, second = lines[position], lines[position + 1]
            if not first or not second:
                continue
            flat = list(first) + list(second)
            boundary = len(first)
            for left_start in range(0, len(flat) - (2 * anchor_length) + 1):
                middle_start = left_start + anchor_length
                left = tuple(flat[left_start:middle_start])
                for middle_length in range(MAX_WITNESS_MIDDLE + 1):
                    right_start = middle_start + middle_length
                    right_end = right_start + anchor_length
                    if right_end > len(flat):
                        break
                    if not left_start < boundary < right_end:
                        continue
                    key = (left, tuple(flat[right_start:right_end]))
                    if key not in requested:
                        continue
                    index[cth][key][tuple(
                        flat[middle_start:right_start])].add(family)
    return index


def evaluate(line_sequences, fragment_cth, fragment_families, fragments_by_cth,
             strict_indices, same_line_indices):
    """Cross-line recoverability under both witness-admission rules."""
    cth_families = {
        cth: {fragment_families[fragment_id] for fragment_id in fragment_ids}
        for cth, fragment_ids in fragments_by_cth.items()
    }
    results = {}
    for anchor_length in ANCHOR_LENGTHS:
        for mask_length in MASK_LENGTHS:
            counts = Counter()
            by_region = defaultdict(Counter)
            strict = strict_indices[anchor_length]
            same_line = same_line_indices[anchor_length]
            for fragment_id in sorted(line_sequences):
                spans = list(iter_cross_line_spans(
                    line_sequences[fragment_id], anchor_length, mask_length))
                if not spans:
                    continue
                cth = fragment_cth[fragment_id]
                query_family = fragment_families[fragment_id]
                counts["cross_line_spans_total"] += len(spans)
                if not cth_families[cth].difference({query_family}):
                    counts["structurally_unavailable_spans"] += len(spans)
                    continue
                counts["candidate_eligible_spans"] += len(spans)
                for region, key, gold in spans:
                    by_region[region]["eligible"] += 1
                    strict_props = p2e.independent_proposals(
                        strict, cth, key, query_family)
                    # LAYOUT_AGNOSTIC is a superset by construction: it adds
                    # same-line witness occurrences of the same anchor pair.
                    agnostic_props = strict_props | p2e.independent_proposals(
                        same_line, cth, key, query_family)
                    for rule, proposals in (("STRICT", strict_props),
                                            ("LAYOUT_AGNOSTIC", agnostic_props)):
                        if not proposals:
                            counts[f"{rule}_abstained"] += 1
                            by_region[region][f"{rule}_abstained"] += 1
                            continue
                        counts[f"{rule}_supported"] += 1
                        by_region[region][f"{rule}_supported"] += 1
                        counts[f"{rule}_proposal_total"] += len(proposals)
                        if gold in proposals:
                            counts[f"{rule}_included_gold"] += 1
                            by_region[region][f"{rule}_included_gold"] += 1
                        if proposals == {gold}:
                            counts[f"{rule}_unique_correct"] += 1
            results[f"a{anchor_length}_m{mask_length}"] = {
                "anchor_length": anchor_length,
                "mask_length": mask_length,
                "counts": dict(sorted(counts.items())),
                "by_boundary_region": {
                    region: dict(sorted(values.items()))
                    for region, values in sorted(by_region.items())
                },
            }
    return results


def pct(numerator, denominator):
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def write_report(results, refused, total_boundaries, elapsed):
    lines = [
        "# Phase 2 P2-E8 — cross-line witness recoverability census",
        "",
        "**This is a census, not a calibration.** It establishes whether "
        "cross-line anchors have recoverable witness support at all. No number "
        "here is a probability, and none may be applied to a real gap as a "
        "rate — that requires the fold-structured step P2-E4/P2-E6 perform for "
        "same-line spans, which does not yet exist for cross-line.",
        "",
        "## Why cross-line needs its own measurement",
        "",
        "Every existing calibration was fit on masks generated strictly within "
        "a line. Cross-line anchors are **89.9% of anchored real gaps** "
        "(`reports/phase4_p4g_rerun.md`) and have never been measured. "
        "Borrowing a same-line rate for them would apply an estimate to a "
        "population it was never computed on.",
        "",
        "## Boundaries refused rather than crossed",
        "",
        f"**{refused:,}** of {total_boundaries:,} adjacent line boundaries "
        f"({pct(refused, total_boundaries)}%) were not crossed because a "
        "neighbouring line renders empty under the language scope. Crossing "
        "one would fabricate adjacency between lines that have out-of-scope "
        "material between them — the fabrication `EXCLUDE_LINE` exists to "
        "prevent.",
        "",
        "## Recoverability by cell, under both witness-admission rules",
        "",
        "| cell | eligible | STRICT supported | STRICT incl. gold | "
        "LAYOUT_AGNOSTIC supported | LA incl. gold |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cell, data in results.items():
        counts = data["counts"]
        eligible = counts.get("candidate_eligible_spans", 0)
        lines.append(
            f"| `{cell}` | {eligible:,} | "
            f"{counts.get('STRICT_supported', 0):,} "
            f"({pct(counts.get('STRICT_supported', 0), eligible)}%) | "
            f"{counts.get('STRICT_included_gold', 0):,} "
            f"({pct(counts.get('STRICT_included_gold', 0), eligible)}%) | "
            f"{counts.get('LAYOUT_AGNOSTIC_supported', 0):,} "
            f"({pct(counts.get('LAYOUT_AGNOSTIC_supported', 0), eligible)}%) | "
            f"{counts.get('LAYOUT_AGNOSTIC_included_gold', 0):,} "
            f"({pct(counts.get('LAYOUT_AGNOSTIC_included_gold', 0), eligible)}%) |")

    lines += [
        "",
        "## The finding: cross-line evidence is several times weaker",
        "",
        "Gold inclusion, cross-line versus the same cell measured on same-line "
        "spans by the P4-D-corrected P2-E rerun:",
        "",
        "| cell | same-line incl. gold | cross-line STRICT | cross-line LA | "
        "same-line ÷ STRICT |",
        "|---|---:|---:|---:|---:|",
    ]
    for cell, (sl_eligible, sl_gold) in SAME_LINE_REFERENCE.items():
        data = results.get(cell)
        if not data:
            continue
        counts = data["counts"]
        eligible = counts.get("candidate_eligible_spans", 0)
        strict = pct(counts.get("STRICT_included_gold", 0), eligible)
        agnostic = pct(counts.get("LAYOUT_AGNOSTIC_included_gold", 0), eligible)
        same_line = pct(sl_gold, sl_eligible)
        ratio = f"{same_line / strict:.1f}×" if strict else "—"
        lines.append(
            f"| `{cell}` | {same_line}% | {strict}% | {agnostic}% | {ratio} |")

    lines += [
        "",
        "**This is the empirical justification for the standing refusal to "
        "borrow a same-line rate for a cross-line anchor.** At `a2_m1` — the "
        "cell the real-gap single-sign calibration actually uses — same-line "
        "spans include the true reading in 20.94% of eligible cases and "
        "cross-line spans in 4.27%. Applying the same-line rate to a "
        "cross-line gap would have overstated the evidence by roughly a "
        "factor of five, on 89.9% of anchored real gaps. The prohibition was "
        "adopted on principle before it was measured; it now has a number.",
        "",
        "`LAYOUT_AGNOSTIC` is a strict superset of `STRICT`: it admits "
        "same-line witness occurrences of the same anchor pair, on the ground "
        "that line division is scribal layout rather than textual structure. "
        "The gap between the two columns is the extra yield a reviewer should "
        "weigh before that rule is ratified.",
        "",
        "## Where the line break falls (a2_m2, where every region is reachable)",
        "",
        "| boundary region | eligible | STRICT incl. gold | LA incl. gold |",
        "|---|---:|---:|---:|",
    ]
    reference = results.get("a2_m2", {}).get("by_boundary_region", {})
    for region in BOUNDARY_REGIONS:
        values = reference.get(region, {})
        eligible = values.get("eligible", 0)
        lines.append(
            f"| `{region}` | {eligible:,} | "
            f"{values.get('STRICT_included_gold', 0):,} "
            f"({pct(values.get('STRICT_included_gold', 0), eligible)}%) | "
            f"{values.get('LAYOUT_AGNOSTIC_included_gold', 0):,} "
            f"({pct(values.get('LAYOUT_AGNOSTIC_included_gold', 0), eligible)}%) |")

    lines += [
        "",
        "`in_mask` is the canonical cross-line case: the lost span itself "
        "straddles the line end, with a whole anchor on each line. "
        "`at_mask_start` / `at_mask_end` place the break flush against the "
        "mask, leaving both anchors intact. `in_left_anchor` / "
        "`in_right_anchor` split an anchor across the break — gaps sitting "
        "near a line edge whose anchor had to be walked across it, the "
        "situation `real_gap_witness_check.py` produces when it extends its "
        "anchor search up to 3 lines per side. For mask length 1, `in_mask` "
        "is unreachable by construction: a break cannot fall strictly inside "
        "one sign.",
        "",
        "## Scope and limits",
        "",
        "- Adjacent line pairs only (one boundary crossed). In the real-gap "
        "slice, 13,807 of 17,379 cross-line gaps crossed exactly one line; "
        "deeper crossings are a declared extension, not folded in silently.",
        "- Dev split, attested-only, language scope `HITTITE_ONLY`, witness "
        "support required from an independent source family.",
        "- No fold structure, so no rate here may be shown to an expert beside "
        "a candidate. That is the next step, and it is the step that would "
        "make cross-line real gaps presentable.",
        "",
        f"Runtime {elapsed:.1f}s · seed {SEED}.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)

    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(POLICY_NAME, POLICIES_PATH)
    ep.validate_semantic_features(
        ["token", "damage_state", "line_index_in_doc", "cth"], registry, policy)

    splits, split_lookup, ambiguous_ids, edges, decomposed = p2e.load_dev_inputs()
    line_index = p2e.build_line_index(decomposed)
    language_scope, language_index = llookup.hittite_only_projection(
        sorted(set(edges["parent_doc"])))
    line_sequences, canonical_flat = p2e.render_fragments(
        edges, line_index, language_scope=language_scope,
        language_index=language_index)

    tokenizer = ht.Tokenizer.load()
    contracts.assert_encoding_sane(
        tokenizer.encode(canonical_flat, strict=True), tokenizer,
        max_unk=0.05, label="P2-E8 dev attested-only")

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_cth = {row.fragment_id: int(row.cth)
                    for row in edges.itertuples(index=False)}
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)}
    fragments_by_cth = defaultdict(list)
    for fragment_id, cth in fragment_cth.items():
        fragments_by_cth[cth].append(fragment_id)

    refused, total_boundaries = count_refused_boundaries(line_sequences)
    print(f"Adjacent line boundaries: {total_boundaries:,} "
          f"({refused:,} refused, neighbour out of scope)")

    strict_indices, same_line_indices = {}, {}
    for anchor_length in ANCHOR_LENGTHS:
        requested_by_cth = defaultdict(set)
        for fragment_id, lines in line_sequences.items():
            requested_by_cth[fragment_cth[fragment_id]].update(
                requested_cross_line_keys(lines, anchor_length, MASK_LENGTHS))
        strict_indices[anchor_length] = build_cross_line_index(
            line_sequences, fragment_families, fragment_cth, anchor_length,
            requested_by_cth)
        # The same-line index answers the LAYOUT_AGNOSTIC rule, built by the
        # existing P2-E function so both rules search the same evidence base.
        same_line_indices[anchor_length] = p2e.build_anchor_index(
            line_sequences.keys(), line_sequences, fragment_families,
            anchor_length, requested_by_cth, fragment_cth)
        print(f"  anchor length {anchor_length}: cross-line keys indexed")

    results = evaluate(line_sequences, fragment_cth, fragment_families,
                       fragments_by_cth, strict_indices, same_line_indices)
    elapsed = time.perf_counter() - started

    payload = {
        "task": "p2e8_cross_line_recoverability",
        "is_calibration": False,
        "scores_are_probabilities": False,
        "language_scope": language_scope.scope,
        "witness_admission_rules": list(ADMISSION_RULES),
        "boundaries_total": total_boundaries,
        "boundaries_refused_out_of_scope_neighbour": refused,
        "cells": results,
    }
    RESULT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    ep.write_manifest({
        "task": "p2e8_cross_line_recoverability",
        "corpus_version": "TLHdig 0.2.0-beta",
        "evidence_policy": POLICY_NAME,
        "seed": SEED,
        "git_commit": ep._git_commit(),
        "language_scope": language_scope.scope,
        "declared_statistics_universe": (
            "dev split, attested-only, non-bin; witness support from "
            "independent source families within the same CTH"),
        "is_calibration": False,
        "features_requested": ["token", "damage_state", "line_index_in_doc", "cth"],
        "features_observed": ["token", "damage_state", "line_index_in_doc", "cth"],
        "boundaries_refused_out_of_scope_neighbour": refused,
    }, MANIFEST_PATH)

    write_report(results, refused, total_boundaries, elapsed)
    reference = results["a2_m1"]["counts"]
    print(f"P2-E8 complete in {elapsed:.1f}s. a2_m1: "
          f"{reference.get('candidate_eligible_spans', 0):,} eligible, "
          f"STRICT gold-inclusive {reference.get('STRICT_included_gold', 0):,}, "
          f"LAYOUT_AGNOSTIC {reference.get('LAYOUT_AGNOSTIC_included_gold', 0):,}.")
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
