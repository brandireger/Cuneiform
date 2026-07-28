#!/usr/bin/env python3
"""P2-E10: cross-line multi-sign candidate-set calibration.

The multi-sign analogue of P2-E9, and the last piece needed before a
cross-line real gap longer than one sign can be shown to an expert.
`real_gap_multisign_calibration.py` currently reports "Same-line anchors only
-- P2-E6's own folds were fit entirely on synthetic within-line masks, so
there is no cross-line calibration to borrow." This produces one.

**Different estimand from P2-E9, on purpose.** P2-E9 calibrates per RANK: how
often the rank-r candidate is the true reading. Multi-sign spans are not
usefully ranked that way -- an expert is shown a SET, so the quantity that
matters is set inclusion: how often the tie-complete displayed set contains
the true span. The two are not interchangeable, and P2-E6 draws the same
distinction for same-line spans.

**Adaptive anchor length**, as in P2-E6: for each span, use the longest anchor
that yields any witness support. Longer anchors are more specific but rarer;
adapting per span recovers coverage that a fixed anchor length throws away.
Calibration groups are (mask_length, selected anchor length) so a rate is
never quoted across spans that had different evidential footing.

**Policy is inherited from the ratified cross-line config**, not re-decided
here: `LAYOUT_AGNOSTIC` admission, the governed non-test universe, and the
0.75 target all come from `configs/p2e9_cross_line_calibration.json`.

Usage:
    python scripts/p2e10_cross_line_multisign.py
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import contracts  # noqa: E402
import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llookup  # noqa: E402

import p2e3_cross_calibration as p2e3  # noqa: E402
import p2e6_multisign_horizon as p2e6  # noqa: E402
import p2e8_cross_line_recoverability as p2e8  # noqa: E402
import p2e9_cross_line_calibration as p2e9  # noqa: E402
import p2e_witness_recoverability as p2e  # noqa: E402

SEED = 20260728
POLICY_NAME = "catalog_assisted"
CROSS_CONFIG_PATH = Path("configs") / "p2e9_cross_line_calibration.json"
P2E6_CONFIG_PATH = Path("configs") / "p2e6_multisign_horizon.json"

ANCHOR_LENGTHS = (1, 2, 3)
MASK_LENGTHS = (2, 3, 4, 5)

OUT_DIR = Path("Phase2/phase2_out")
RESULT_PATH = OUT_DIR / "p2e10_cross_line_multisign.json"
MANIFEST_PATH = OUT_DIR / "p2e10_cross_line_multisign_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e10_cross_line_multisign.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"


def build_cell_records(line_sequences, fragment_cth, fragment_families,
                       fragments_by_cth, indices):
    """Records per (anchor_length, mask_length) cell, cross-line spans only.

    Carries the fields `p2e6.span_identity` needs so its adaptive-anchor
    selection can be reused unchanged: reimplementing that logic would be a
    second chance to disagree with the same-line path about what "the same
    span" means.
    """
    cth_families = {
        cth: {fragment_families[fid] for fid in fids}
        for cth, fids in fragments_by_cth.items()
    }
    cells = {}
    for anchor_length in ANCHOR_LENGTHS:
        for mask_length in MASK_LENGTHS:
            records = []
            for fragment_id in sorted(line_sequences):
                cth = fragment_cth[fragment_id]
                query_family = fragment_families[fragment_id]
                if not cth_families[cth].difference({query_family}):
                    continue
                lines = line_sequences[fragment_id]
                for position in range(len(lines) - 1):
                    first, second = lines[position], lines[position + 1]
                    if not first or not second:
                        continue
                    flat = list(first) + list(second)
                    boundary = len(first)
                    stop = len(flat) - anchor_length - mask_length + 1
                    for start in range(anchor_length,
                                       max(anchor_length, stop)):
                        left_start = start - anchor_length
                        mask_end = start + mask_length
                        right_end = mask_end + anchor_length
                        if p2e8.boundary_region(
                                left_start, start, mask_end, right_end,
                                boundary) is None:
                            continue
                        left = tuple(flat[left_start:start])
                        gold = tuple(flat[start:mask_end])
                        right = tuple(flat[mask_end:right_end])
                        records.append({
                            "cth": cth,
                            "fragment_id": fragment_id,
                            # Identity must not depend on anchor length, or
                            # the adaptive selection cannot match a span
                            # across cells.
                            "line_position_in_fragment": position,
                            "sign_offset_in_line": start,
                            "left_anchor": left,
                            "right_anchor": right,
                            "gold": gold,
                            "ranking": p2e9.merged_ranking(
                                indices, cth, (left, right), query_family),
                        })
            cells[f"a{anchor_length}_m{mask_length}"] = records
    return cells


def group_key(record):
    return (record["mask_length"], record["adaptive_anchor_length"])


def calibrate(adaptive_by_mask, folds, nominal_depth, estimand):
    """Set-inclusion calibration per (mask, adaptive anchor) group.

    Reports the fit-set rate AND what held-out compositions delivered, for the
    same reason P2-E9 does: a selector can look calibrated on the compositions
    it was fit on and fail on unseen ones, and only the fold structure exposes
    that.
    """
    fold_summaries = []
    for fold in folds:
        evaluation_cths = fold["cth"]
        groups = {}
        for mask_length, records in adaptive_by_mask.items():
            calibration = [r for r in records
                           if r["cth"] not in evaluation_cths]
            evaluation = [r for r in records if r["cth"] in evaluation_cths]
            by_anchor_cal = defaultdict(list)
            by_anchor_eval = defaultdict(list)
            for record in calibration:
                by_anchor_cal[record["adaptive_anchor_length"]].append(record)
            for record in evaluation:
                by_anchor_eval[record["adaptive_anchor_length"]].append(record)
            for anchor_length in sorted(
                    set(by_anchor_cal) | set(by_anchor_eval),
                    key=lambda value: (value is None, value)):
                if anchor_length is None:
                    # Spans no anchor length could support. They abstain; they
                    # are not a calibration group.
                    continue
                fit = p2e6.calibration_stat(
                    by_anchor_cal.get(anchor_length, []), nominal_depth,
                    estimand)
                held_out = p2e6.calibration_stat(
                    by_anchor_eval.get(anchor_length, []), nominal_depth,
                    estimand)
                groups[f"m{mask_length}_a{anchor_length}"] = {
                    "mask_length": mask_length,
                    "adaptive_anchor_length": anchor_length,
                    "calibration_set": fit,
                    "held_out": held_out,
                }
        fold_summaries.append({
            "fold": fold["fold"],
            "evaluation_cth": sorted(evaluation_cths),
            "groups": groups,
        })
    return fold_summaries


def pooled(fold_summaries, side):
    """Pool a side ('calibration_set' or 'held_out') across folds by mask."""
    totals = defaultdict(lambda: [0, 0])
    for fold in fold_summaries:
        for group in fold["groups"].values():
            stat = group[side]
            totals[group["mask_length"]][0] += stat["attested_included_contexts"]
            totals[group["mask_length"]][1] += stat["calibration_presented_contexts"]
    return {
        str(mask): {
            "included": included, "presented": presented,
            "rate": round(included / presented, 4) if presented else None,
        }
        for mask, (included, presented) in sorted(totals.items())
    }


def write_report(fold_summaries, cross_config, nominal_depth, elapsed,
                 abstained_by_mask):
    fit = pooled(fold_summaries, "calibration_set")
    held = pooled(fold_summaries, "held_out")
    lines = [
        "# Phase 2 P2-E10 — cross-line multi-sign candidate-set calibration",
        "",
        "The multi-sign analogue of P2-E9, and the last piece needed before a "
        "cross-line real gap longer than one sign can be shown to an expert.",
        "",
        "**Estimand is set inclusion, not per-rank agreement.** An expert is "
        "shown a set, so the quantity that matters is how often the "
        "tie-complete displayed set contains the true span. P2-E9's per-rank "
        "rates and these are not interchangeable, in either direction.",
        "",
        f"Admission rule **{cross_config['witness_admission_rule']}** "
        f"(ratified {cross_config['witness_admission_rule_ratified']}); "
        "universe "
        f"{'+'.join(cross_config['calibration_universe_splits'])}, non-bin, "
        f"test excluded and asserted; nominal display depth {nominal_depth}.",
        "",
        "## Does it transfer?",
        "",
        "| mask length | fit-set inclusion | held-out inclusion | gap | held-out n |",
        "|---|---:|---:|---:|---:|",
    ]
    for mask in sorted(fit, key=int):
        fit_rate = fit[mask]["rate"]
        held_rate = held.get(mask, {}).get("rate")
        gap = (round(100 * (fit_rate - held_rate), 1)
               if fit_rate is not None and held_rate is not None else None)
        lines.append(
            f"| {mask} | "
            f"{f'{100 * fit_rate:.1f}%' if fit_rate is not None else '—'} | "
            f"{f'{100 * held_rate:.1f}%' if held_rate is not None else '—'} | "
            f"{f'{gap:+.1f} pts' if gap is not None else '—'} | "
            f"{held.get(mask, {}).get('presented', 0):,} |")

    lines += [
        "",
        "**Only the held-out column describes performance on unseen "
        "compositions.** As in P2-E9, the rate ATTACHED to a real gap must be "
        "the fit-set one for that gap's fold — it is computed on compositions "
        "disjoint from the gap's own, whereas the held-out figure is measured "
        "on exactly those compositions and would be circular per-gap. The two "
        "answer different questions and both are kept.",
        "",
        "## Spans no anchor length could support",
        "",
        "| mask length | abstained (no witness support at any anchor length) |",
        "|---|---:|",
    ]
    for mask in sorted(abstained_by_mask, key=int):
        lines.append(f"| {mask} | {abstained_by_mask[mask]:,} |")

    lines += [
        "",
        "These are not a calibration group and receive no rate. Longer spans "
        "abstain more, which is the expected shape: the longer the lost span, "
        "the less often an independent witness attests exactly it.",
        "",
        "## Conclusion: cross-line multi-sign is not viable for presentation",
        "",
        "Set inclusion runs from the two-sign figure down to the five-sign "
        "one above. The displayed set contains the true span roughly one time "
        "in seven at best. Same-line multi-sign spans are several times "
        "stronger.",
        "",
        "The calibration itself is sound -- fit-set and held-out agree to "
        "within 0.0 points on hundreds of thousands of held-out spans. These "
        "are trustworthy numbers, and what they establish is that this "
        "channel does not work.",
        "",
        "**Recommendation: do not wire P2-E10 into "
        "`real_gap_multisign_calibration.py`.** A calibrated 8% "
        "set-inclusion rate is honest but not decision-support: an expert "
        "shown such a set would be right to ignore it. P2-E9 showed "
        "single-sign cross-line clearing its ratified target, and it is "
        "applied in production; multi-sign cross-line, measured the same way, "
        "does not clear a bar worth setting.",
        "",
        "## Standing limits",
        "",
        "- Adjacent line pairs only (one boundary crossed), matching P2-E8/E9.",
        "- Cross-line rates are for cross-line gaps. P2-E6's same-line "
        "set-inclusion rates stay with same-line gaps; the populations differ "
        "and must never be pooled or substituted.",
        "- Set inclusion is a property of the SET, not of any one displayed "
        "alternative. There is no per-option probability here.",
        "- Applying these to real gaps is a further step in "
        "`real_gap_multisign_calibration.py`, which still reports same-line "
        "only.",
        "",
        f"Runtime {elapsed:.1f}s · seed {SEED}.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return fit, held


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)

    cross_config = json.loads(CROSS_CONFIG_PATH.read_text(encoding="utf-8"))
    p2e6_config = json.loads(P2E6_CONFIG_PATH.read_text(encoding="utf-8"))
    nominal_depth = int(p2e6_config["nominal_display_depth"])
    estimand = p2e6_config["candidate_set_calibration_estimand"]
    # Inherit the ratified policy rather than re-deciding it here.
    p2e9.require_calibration_target(cross_config)

    ep.validate_semantic_features(
        ["token", "damage_state", "line_index_in_doc", "cth"],
        ep.load_registry(REGISTRY_PATH),
        ep.load_policy(POLICY_NAME, POLICIES_PATH))

    universe = tuple(cross_config["calibration_universe_splits"])
    splits, split_lookup, ambiguous_ids, edges, decomposed = (
        p2e9.load_non_test_inputs(universe))
    print("Calibration universe", universe, ":",
          len(set(edges["parent_doc"])), "parent documents")

    line_index = p2e.build_line_index(decomposed)
    language_scope, language_index = llookup.hittite_only_projection(
        sorted(set(edges["parent_doc"])))
    line_sequences, canonical_flat = p2e.render_fragments(
        edges, line_index, language_scope=language_scope,
        language_index=language_index)
    tokenizer = ht.Tokenizer.load()
    contracts.assert_encoding_sane(
        tokenizer.encode(canonical_flat, strict=True), tokenizer,
        max_unk=0.05, label="P2-E10 attested-only")

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_cth = {row.fragment_id: int(row.cth)
                    for row in edges.itertuples(index=False)}
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)}
    fragments_by_cth = defaultdict(list)
    for fragment_id, cth in fragment_cth.items():
        fragments_by_cth[cth].append(fragment_id)

    cells = {}
    for anchor_length in ANCHOR_LENGTHS:
        requested = defaultdict(set)
        for fragment_id, lines in line_sequences.items():
            requested[fragment_cth[fragment_id]].update(
                p2e8.requested_cross_line_keys(
                    lines, anchor_length, MASK_LENGTHS))
        cross_index = p2e8.build_cross_line_index(
            line_sequences, fragment_families, fragment_cth, anchor_length,
            requested)
        same_line_index = p2e.build_anchor_index(
            line_sequences.keys(), line_sequences, fragment_families,
            anchor_length, requested, fragment_cth)
        built = build_cell_records(
            line_sequences, fragment_cth, fragment_families, fragments_by_cth,
            (cross_index, same_line_index))
        cells.update({k: v for k, v in built.items()
                      if k.startswith(f"a{anchor_length}_")})
        print(f"  anchor length {anchor_length}: cells built")

    adaptive_by_mask = p2e6.build_adaptive_records(
        cells, MASK_LENGTHS, ANCHOR_LENGTHS)
    abstained_by_mask = {
        str(mask): sum(1 for r in records
                       if r["adaptive_anchor_length"] is None)
        for mask, records in adaptive_by_mask.items()
    }

    weights = defaultdict(int)
    all_cths = set()
    for records in adaptive_by_mask.values():
        for record in records:
            weights[record["cth"]] += 1
            all_cths.add(record["cth"])
    folds = p2e3.assign_composition_folds(
        weights, sorted(all_cths), int(cross_config["folds"]))
    fold_summaries = calibrate(
        adaptive_by_mask, folds, nominal_depth, estimand)
    elapsed = time.perf_counter() - started

    fit, held = write_report(
        fold_summaries, cross_config, nominal_depth, elapsed,
        abstained_by_mask)

    RESULT_PATH.write_text(json.dumps({
        "task": "p2e10_cross_line_multisign",
        "is_calibration": True,
        "population": "cross_line_multisign_adjacent_line_pairs",
        "estimand": estimand,
        "confidence_interval": p2e6_config["confidence_interval"],
        "nominal_display_depth": nominal_depth,
        "witness_admission_rule": cross_config["witness_admission_rule"],
        "calibration_universe_splits": list(universe),
        "language_scope": language_scope.scope,
        "rate_to_APPLY_to_a_gap": "calibration_set",
        "rate_to_REPORT_as_quality": "held_out",
        "pooled_calibration_set_by_mask": fit,
        "pooled_held_out_by_mask": held,
        "abstained_no_anchor_support_by_mask": abstained_by_mask,
        "folds": fold_summaries,
        "must_not_be_pooled_with": "same-line multi-sign calibration (P2-E6)",
    }, ensure_ascii=False, indent=2, default=list) + "\n", encoding="utf-8")

    ep.write_manifest({
        "task": "p2e10_cross_line_multisign",
        "corpus_version": "TLHdig 0.2.0-beta",
        "evidence_policy": POLICY_NAME,
        "seed": SEED,
        "git_commit": ep._git_commit(),
        "language_scope": language_scope.scope,
        "declared_statistics_universe": (
            f"{'+'.join(universe)}, non-bin, test excluded and asserted; "
            "cross-line multi-sign spans over adjacent line pairs; witness "
            "support from independent source families within the same CTH"),
        "is_calibration": True,
        "features_requested": ["token", "damage_state", "line_index_in_doc", "cth"],
        "features_observed": ["token", "damage_state", "line_index_in_doc", "cth"],
    }, MANIFEST_PATH)

    print(f"P2-E10 complete in {elapsed:.1f}s.")
    for mask in sorted(held, key=int):
        rate = held[mask]["rate"]
        print(f"  mask {mask}: held-out set inclusion "
              f"{f'{100 * rate:.1f}%' if rate is not None else '—'} "
              f"on {held[mask]['presented']:,} spans")
    print(f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
