#!/usr/bin/env python3
"""Real-gaps production pipeline -- Step 4: multi-sign calibration application.

Step 3 (real_gap_calibration.py) applied P2-E4's single-sign, fixed-anchor-
length (anchor_length=2, mask_length=1) calibration to real gaps. Multi-sign
real gaps (a contiguous run of 2-5 restored/illegible_x signs) need a
different, already-computed calibration: P2-E6's fold structure in
Phase2/phase2_out/p2e6_multisign_horizon.json, which is NOT a per-rank
"rank R historically correct X%" table like P2-E4's. It calibrates a
different estimand entirely -- "does the tie-complete displayed candidate
set (adaptively built by trying the longest anchor length with any witness
support: 3 signs, then 2, then 1, before abstaining) contain the true
attested span," keyed by (mask_length, adaptive_anchor_length), not by rank.

This step is a straight structural replication of P2-E6's own adaptive-
anchor selection (scripts/p2e6_multisign_horizon.py's build_adaptive_records
and tie_complete_alternatives), applied to the real-gap witness index
instead of P2-E6's synthetic dev masks -- no recalibration, reuse only,
exactly the same posture as step 3.

Scope, matching step 3's own reasoning:
  - Restricted to the CTHs the existing 5 P2-E6 folds actually cover (union
    of every fold's evaluation_cth), so every gap in scope has an
    applicable fold to calibrate against.
  - Same-line anchors only. P2-E6's calibration folds were built entirely
    from synthetic within-line masks (iter_masked_spans_with_location never
    crosses a line boundary) -- there is no cross-line analogue to borrow,
    so cross-line multi-sign gaps are out of scope here, exactly as
    cross-line single-sign gaps were out of scope for step 3. A cross-line
    calibration pass, for both single- and multi-sign gaps, remains a
    separate, unstarted step.
  - Mask lengths 2-5 and anchor lengths 1/2/3, matching
    configs/p2e6_multisign_horizon.json exactly (the file this step reuses
    was fit under exactly this configuration; using any other value would
    not be reuse).

Usage:
    python scripts/real_gap_multisign_calibration.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import contracts  # noqa: E402
import eval_harness as eh  # noqa: E402

import pandas as pd  # noqa: E402

import p2e2_abstention_calibration as p2e2  # noqa: E402
import p2e6_multisign_horizon as p2e6  # noqa: E402
import p2e_witness_recoverability as p2e  # noqa: E402
from line_lang_lookup import load_line_lang_lookup  # noqa: E402
import real_gap_census as rgc  # noqa: E402
import real_gap_witness_check as rgw  # noqa: E402

P2E6_HORIZON_PATH = Path("Phase2/phase2_out/p2e6_multisign_horizon.json")
P2E6_CONFIG_PATH = Path("configs/p2e6_multisign_horizon.json")
EDGES_PATH = Path("Phase1_pipeline/p2_out/edges.parquet")
MAX_WITNESS_MIDDLE = 12  # matches scripts/p2e_witness_recoverability.py

OUT_DIR = Path("Phase3/real_gaps_out")
OUT_JSON = OUT_DIR / "real_gap_multisign_calibration.json"
REPORT_PATH = OUT_DIR / "real_gap_multisign_calibration_report.md"


def load_cth_fold_map():
    horizon = json.loads(P2E6_HORIZON_PATH.read_text(encoding="utf-8"))
    config = json.loads(P2E6_CONFIG_PATH.read_text(encoding="utf-8"))
    cth_to_fold = {}
    for fold in horizon["folds"]:
        for cth in fold["evaluation_cth"]:
            cth_to_fold[cth] = fold
    return cth_to_fold, config


def prepare_multisign_scope(cth_ids, mask_lengths, anchor_lengths):
    """Same-line-only scope for multi-sign real gaps, resolving an anchor
    key at EACH configured anchor_length so the adaptive selection
    (longest anchor with support first) can be replicated. Mirrors
    real_gap_witness_check.prepare_scope's data loading, but needs
    anchor keys/indices at three anchor lengths instead of one fixed
    ANCHOR_LENGTH, so it is its own function rather than a variant call
    into that one."""
    allowed_ids, split_lookup, ambiguous_ids = rgc.load_allowed_doc_ids()

    doc_table = pd.read_parquet(
        rgc.DOC_TABLE_PATH, columns=["doc_id", "cth"])
    doc_cth = dict(zip(doc_table["doc_id"], doc_table["cth"]))

    slice_doc_ids = {d for d in allowed_ids if doc_cth.get(d) in cth_ids}
    print(f"Documents in scope for this slice: {len(slice_doc_ids):,}")

    decomposed = pd.read_parquet(
        rgc.DECOMPOSED_PATH,
        columns=["doc_id", "line_index_in_doc", "word_pos", "token",
                  "damage_state", "word_index_in_line"],
        filters=[("doc_id", "in", list(slice_doc_ids))],
    )
    contracts.assert_no_test(
        set(decomposed["doc_id"]), split_lookup,
        label="real-gap multisign decomposed")
    decomposed = decomposed.sort_values(
        ["doc_id", "line_index_in_doc", "word_pos"])

    edges = pd.read_parquet(
        EDGES_PATH,
        columns=["fragment_id", "parent_doc", "cth", "lines"],
        filters=[("parent_doc", "in", list(slice_doc_ids))],
    )
    contracts.assert_no_test(
        set(edges["parent_doc"]), split_lookup,
        label="real-gap multisign edges")
    contracts.assert_unique_docids(edges)

    line_index = p2e.build_line_index(decomposed)
    line_sequences, _ = p2e.render_fragments(
        edges, line_index, line_lang_lookup=load_line_lang_lookup())
    line_owner = rgw.build_line_owner_map(edges)
    fragment_line_order = rgw.build_fragment_line_order(edges)

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)}
    fragment_cth = {
        row.fragment_id: int(row.cth)
        for row in edges.itertuples(index=False)}

    raw_tokens_by_line = {}
    for (doc_id, line_idx), group in decomposed.groupby(
            ["doc_id", "line_index_in_doc"], sort=False):
        raw_tokens_by_line[(doc_id, int(line_idx))] = [
            (int(r.word_pos), r.token, r.damage_state)
            for r in group.itertuples(index=False)]

    mask_length_set = set(mask_lengths)
    descending_anchors = sorted(anchor_lengths, reverse=True)
    base_anchor = min(anchor_lengths)

    gaps = []
    for (doc_id, line_idx), raw_tokens in raw_tokens_by_line.items():
        fragment_id = line_owner.get((doc_id, line_idx))
        if fragment_id is None:
            continue
        for run in rgc.find_runs(
                doc_id, int(line_idx),
                [(wp, t, s, None) for wp, t, s in raw_tokens]):
            if run["length"] not in mask_length_set:
                continue
            gap_word_positions = set(
                range(run["word_pos_start"], run["word_pos_end"] + 1))
            anchor_keys = {}
            for anchor_length in anchor_lengths:
                resolved = rgw.compute_anchor_key_crossline(
                    doc_id, fragment_id, line_idx, gap_word_positions,
                    raw_tokens_by_line, fragment_line_order,
                    anchor_length=anchor_length,
                    max_lines_crossed_per_side=0)
                anchor_keys[anchor_length] = resolved[0] if resolved else None
            gaps.append({
                "doc_id": doc_id, "line_index_in_doc": line_idx,
                "fragment_id": fragment_id, "run": run,
                "anchor_keys": anchor_keys,
            })

    print(f"Multi-sign real gaps in scope (mask length in "
          f"{sorted(mask_length_set)}): {len(gaps):,}")
    eligible = [g for g in gaps if g["anchor_keys"][base_anchor] is not None]
    print(f"Eligible (same-line {base_anchor}-sign anchor on both sides): "
          f"{len(eligible):,}")

    requested_by_cth = {al: {} for al in anchor_lengths}
    for g in eligible:
        cth = fragment_cth.get(g["fragment_id"])
        for al in anchor_lengths:
            key = g["anchor_keys"][al]
            if key is not None:
                requested_by_cth[al].setdefault(cth, set()).add(key)

    anchor_index_by_length = {
        al: p2e.build_anchor_index(
            list(line_sequences.keys()), line_sequences, fragment_families,
            al, requested_by_cth[al], fragment_cth,
            max_middle=MAX_WITNESS_MIDDLE)
        for al in anchor_lengths
    }

    return {
        "slice_doc_ids": slice_doc_ids,
        "gaps_in_scope": len(gaps),
        "eligible": eligible,
        "anchor_index_by_length": anchor_index_by_length,
        "fragment_families": fragment_families,
        "fragment_cth": fragment_cth,
        "descending_anchors": descending_anchors,
    }


def adaptive_ranking(scope, gap):
    """Try the longest anchor length with any witness support first,
    falling back to shorter anchors, abstaining only if none has support
    -- exactly scripts/p2e6_multisign_horizon.py's build_adaptive_records
    selection rule, replicated one gap at a time instead of over
    pre-built per-cell record tables."""
    fragment_id = gap["fragment_id"]
    cth = scope["fragment_cth"].get(fragment_id)
    family = scope["fragment_families"].get(fragment_id)
    for anchor_length in scope["descending_anchors"]:
        key = gap["anchor_keys"].get(anchor_length)
        if key is None:
            continue
        ranking = p2e2.proposal_ranking(
            scope["anchor_index_by_length"][anchor_length], cth, key, family)
        if ranking["alternatives"]:
            return anchor_length, ranking
    return None, {
        "alternatives": [], "unique_top": False, "top_support": 0,
        "runner_up_support": 0, "support_margin": 0, "dominance": 0.0,
        "alternative_count": 0,
    }


def main():
    cth_to_fold, config = load_cth_fold_map()
    anchor_lengths = [int(v) for v in config["anchor_lengths"]]
    mask_lengths = [int(v) for v in config["mask_lengths"]]
    nominal_depth = int(config["nominal_display_depth"])
    estimand = config["candidate_set_calibration_estimand"]

    calibration_cths = sorted(cth_to_fold.keys())
    print(f"CTHs with applicable P2-E6 multi-sign calibration "
          f"({len(calibration_cths)}): {calibration_cths}")

    scope = prepare_multisign_scope(calibration_cths, mask_lengths, anchor_lengths)
    # Keep the membership check explicit rather than assuming it, per the
    # same convention step 3 uses -- scope is already restricted to
    # calibration_cths, so this should never drop anything, but the
    # correctness condition for looking up cth_to_fold deserves stating,
    # not assuming.
    eligible = [
        g for g in scope["eligible"]
        if scope["fragment_cth"].get(g["fragment_id"]) in cth_to_fold
    ]

    n_presented = 0
    n_restored_checked = 0
    n_restored_included = 0
    n_restored_not_included = 0
    n_restored_no_rate_available = 0
    anchor_length_counts = Counter()
    mask_length_counts = Counter()
    included_examples = []
    not_included_examples = []

    for g in eligible:
        cth = scope["fragment_cth"].get(g["fragment_id"])
        fold = cth_to_fold[cth]
        mask_length = g["run"]["length"]
        mask_length_counts[mask_length] += 1

        adaptive_anchor_length, ranking = adaptive_ranking(scope, g)
        if adaptive_anchor_length is None:
            anchor_length_counts["abstain"] += 1
            continue
        n_presented += 1
        anchor_length_counts[str(adaptive_anchor_length)] += 1

        if not g["run"]["is_pure_restored"]:
            continue
        n_restored_checked += 1

        group = fold["groups"].get(str(mask_length), {}).get(
            str(adaptive_anchor_length))
        if group is None or group["candidate_set_calibration_rate"] is None:
            n_restored_no_rate_available += 1
            continue

        editor_reading = tuple(g["run"]["tokens"])
        displayed = p2e6.tie_complete_alternatives(ranking, nominal_depth)
        included = any(
            alt["proposal"] == editor_reading for alt in displayed)
        example = {
            "doc_id": g["doc_id"], "fragment_id": g["fragment_id"],
            "mask_length": mask_length,
            "adaptive_anchor_length": adaptive_anchor_length,
            "editor_reading": list(editor_reading),
            "displayed_set_size": len(displayed),
            "group_calibration_rate": group["candidate_set_calibration_rate"],
            "group_wilson_95": group["wilson_95"],
            "group_sample_size": group["calibration_presented_contexts"],
        }
        if included:
            n_restored_included += 1
            if len(included_examples) < 8:
                included_examples.append(example)
        else:
            n_restored_not_included += 1
            example["top_alternative"] = (
                list(ranking["alternatives"][0]["proposal"])
                if ranking["alternatives"] else None)
            if len(not_included_examples) < 8:
                not_included_examples.append(example)

    result = {
        "calibration_scope_cths": calibration_cths,
        "scope_documents": len(scope["slice_doc_ids"]),
        "calibrated_anchor_lengths": anchor_lengths,
        "calibrated_mask_lengths": mask_lengths,
        "nominal_display_depth": nominal_depth,
        "candidate_set_calibration_estimand": estimand,
        "gaps_in_scope": scope["gaps_in_scope"],
        "eligible_gaps": len(eligible),
        "presented_gaps": n_presented,
        "abstained_gaps": len(eligible) - n_presented,
        "mask_length_counts": dict(sorted(mask_length_counts.items())),
        "selected_anchor_length_counts": dict(
            sorted(anchor_length_counts.items())),
        "restored_checked": n_restored_checked,
        "restored_included_in_displayed_set": n_restored_included,
        "restored_not_included_in_displayed_set": n_restored_not_included,
        "restored_no_rate_available": n_restored_no_rate_available,
        "included_examples": included_examples,
        "not_included_examples": not_included_examples,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report_lines = [
        "# Real-gap multi-sign calibration application (step 4)",
        "",
        "Reuses the already-computed, already-frozen fold calibration from "
        "`Phase2/phase2_out/p2e6_multisign_horizon.json` -- no recalibration. "
        "Unlike step 3's per-rank P2-E4 rates, this calibration is a "
        "**set-inclusion rate**, keyed by (mask_length, adaptive_anchor_length): "
        f"\"{estimand}\"",
        "",
        f"Scoped to the **{len(calibration_cths)} CTHs** the existing 5 P2-E6 "
        "folds actually cover (union of all folds' `evaluation_cth` lists): "
        f"**{result['scope_documents']:,} documents** in scope.",
        "",
        "Same-line anchors only -- P2-E6's own folds were fit entirely on "
        "synthetic within-line masks, so there is no cross-line calibration "
        "to borrow (same posture as step 3's single-sign application).",
        "",
        f"- **{result['gaps_in_scope']:,}** real gaps with mask length in "
        f"{mask_lengths} found in scope.",
        f"- **{result['eligible_gaps']:,}** eligible (a same-line "
        f"{min(anchor_lengths)}-sign anchor exists on both sides -- the base "
        "population P2-E6 itself starts from before trying longer anchors).",
        f"- **{result['presented_gaps']:,}** presented (some anchor length "
        f"1-{max(anchor_lengths)} found independent witness support -- the "
        "adaptive selection rule, longest anchor first); "
        f"**{result['abstained_gaps']:,}** abstained (no anchor length had "
        "any support at all).",
        "",
        "### Mask-length distribution among eligible gaps",
        "",
        "| mask length | count |",
        "|---|---|",
    ]
    for length, count in result["mask_length_counts"].items():
        report_lines.append(f"| {length} | {count:,} |")
    report_lines += [
        "",
        "### Selected adaptive anchor length among eligible gaps",
        "",
        "| anchor length | count |",
        "|---|---|",
    ]
    for length, count in result["selected_anchor_length_counts"].items():
        report_lines.append(f"| {length} | {count:,} |")

    report_lines += [
        "",
        f"Of **{result['restored_checked']:,}** presented `restored` spans "
        f"checked against the calibrated candidate set: "
        f"**{result['restored_included_in_displayed_set']:,}** have the "
        "editor's reading included in the tie-complete displayed set (a "
        "calibrated set-inclusion rate applies), "
        f"**{result['restored_not_included_in_displayed_set']:,}** do not "
        "(the editor's reading is absent from every witnessed alternative "
        "at the selected anchor length), and "
        f"**{result['restored_no_rate_available']:,}** have no usable "
        "calibrated rate for their (mask_length, anchor_length) group "
        "(that combination never occurred in the OTHER folds' calibration "
        "data for this fold).",
        "",
        "## Editor's restoration included in the calibrated candidate set "
        f"({result['restored_included_in_displayed_set']:,} total, up to 8 shown)",
        "",
    ]
    for ex in result["included_examples"]:
        rate = ex["group_calibration_rate"] * 100
        lo, hi = ex["group_wilson_95"][0] * 100, ex["group_wilson_95"][1] * 100
        report_lines.append(
            f"- `{ex['fragment_id']}`: {ex['mask_length']}-sign editor reading "
            f"`{' '.join(ex['editor_reading']) or '(empty)'}` is one of "
            f"{ex['displayed_set_size']} displayed alternatives (adaptive "
            f"anchor length {ex['adaptive_anchor_length']}) -- candidate sets "
            f"in this (mask={ex['mask_length']}, anchor={ex['adaptive_anchor_length']}) "
            f"group have historically included the true attested span about "
            f"{rate:.1f}% of the time (95% CI {lo:.1f}-{hi:.1f}%, "
            f"n={ex['group_sample_size']:,}).")

    report_lines += [
        "",
        "## Editor's restoration NOT found among the calibrated candidate set "
        f"({result['restored_not_included_in_displayed_set']:,} total, up to 8 shown)",
        "",
    ]
    for ex in result["not_included_examples"]:
        rate = ex["group_calibration_rate"] * 100
        lo, hi = ex["group_wilson_95"][0] * 100, ex["group_wilson_95"][1] * 100
        top = " ".join(ex["top_alternative"]) if ex["top_alternative"] else "(empty)"
        report_lines.append(
            f"- `{ex['fragment_id']}`: {ex['mask_length']}-sign editor reading "
            f"`{' '.join(ex['editor_reading']) or '(empty)'}` does not match any "
            f"of {ex['displayed_set_size']} displayed alternatives (adaptive "
            f"anchor length {ex['adaptive_anchor_length']}; best-witnessed "
            f"alternative is `{top}`) -- candidate sets in this "
            f"(mask={ex['mask_length']}, anchor={ex['adaptive_anchor_length']}) "
            f"group have historically included the true attested span about "
            f"{rate:.1f}% of the time (95% CI {lo:.1f}-{hi:.1f}%, "
            f"n={ex['group_sample_size']:,}). This is NOT the probability the "
            "editor is wrong -- it is the group's historical inclusion rate, "
            "reported per the same rule as everywhere else in this project.")

    report_lines += [
        "",
        "## What this still does not establish",
        "",
        "A group's candidate-set calibration rate is a property of many past "
        "comparisons within that (mask_length, adaptive_anchor_length) group, "
        "not this specific instance. It also describes the SET as a whole, "
        "not any individual displayed alternative -- there is no "
        "per-alternative probability here, unlike step 3's per-rank rates. "
        "Cross-line multi-sign gaps remain entirely uncalibrated, as do all "
        "cross-line single-sign gaps from step 3. Both are real, "
        "separately-scoped next steps, not folded in silently here.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
