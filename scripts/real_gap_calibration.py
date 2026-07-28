#!/usr/bin/env python3
"""Real-gaps production pipeline -- Step 3: apply existing calibration.

Ixca's direction: one step at a time, evaluate before continuing. This
step attaches the ALREADY-COMPUTED, ALREADY-FROZEN calibration from
Phase2/phase2_out/p2e4_candidate_set_audit.json (5-fold, composition-
disjoint rank_calibration tables -- the same numbers the demo's own
packets already display, e.g. "90.9% [90.0-91.6%], n=5214" for rank 1)
to real gaps, instead of the synthetic evaluation contexts it was
originally computed on. No recalibration happens here -- this is
reuse, not re-derivation.

First increment (frozen in history, see git log) scoped to step 2's
top-5-gap-count CTHs (628, 627, 701, 577, 647) and found only **CTH
627** overlapped any fold's `evaluation_cth` list -- the P2-E4
calibration was built over a different sample of the corpus than "top
gap count." Rather than keep intersecting with that unrelated
selection criterion, this step now scopes DIRECTLY to the full set of
CTHs the existing 5 folds actually cover (union of every fold's
`evaluation_cth`) and asks `real_gap_witness_check.prepare_scope()` for
that scope from scratch -- still no recalibration, just applying the
same frozen rates to a properly-matched, much larger scope.

Further scope, for the same reason: only same-line anchors (cross-line
has no calibration of its own yet -- flagged, not borrowed), and only
single-sign gaps (run length == 1), since this specific calibration file
was computed at anchor_length=2, mask_length=1 (configs/
p2e4_candidate_set_audit.json). Multi-sign real gaps would need the
analogous P2-E6 fold structure, not this one -- a separate increment.

Usage:
    python scripts/real_gap_calibration.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import p2e2_abstention_calibration as p2e2  # noqa: E402
import p2e8_cross_line_recoverability as p2e8  # noqa: E402
import p2e9_cross_line_calibration as p2e9  # noqa: E402
import real_gap_witness_check as rgw  # noqa: E402

P2E4_AUDIT_PATH = Path("Phase2/phase2_out/p2e4_candidate_set_audit.json")
P2E4_CONFIG_PATH = Path("configs/p2e4_candidate_set_audit.json")
P2E9_AUDIT_PATH = Path("Phase2/phase2_out/p2e9_cross_line_calibration.json")
P2E9_CONFIG_PATH = Path("configs/p2e9_cross_line_calibration.json")

OUT_DIR = Path("Phase3/real_gaps_out")
OUT_JSON = OUT_DIR / "real_gap_calibration.json"
REPORT_PATH = OUT_DIR / "real_gap_calibration_report.md"


def load_cth_fold_map():
    audit = json.loads(P2E4_AUDIT_PATH.read_text(encoding="utf-8"))
    config = json.loads(P2E4_CONFIG_PATH.read_text(encoding="utf-8"))
    cth_to_fold = {}
    for fold in audit["folds"]:
        for cth in fold["evaluation_cth"]:
            cth_to_fold[cth] = fold
    return cth_to_fold, config


def load_cross_line_fold_map():
    """CTH -> P2-E9 fold, for the ratified cross-line admission rule.

    Returns None when the cross-line artifacts are absent or the calibration
    target is unratified -- cross-line then stays gated, exactly as before,
    rather than silently borrowing the same-line rates.
    """
    if not (P2E9_AUDIT_PATH.exists() and P2E9_CONFIG_PATH.exists()):
        return None
    config = json.loads(P2E9_CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        p2e9.require_calibration_target(config)
    except p2e9.UnratifiedPolicyError:
        return None
    audit = json.loads(P2E9_AUDIT_PATH.read_text(encoding="utf-8"))
    adopted = audit["witness_admission_rule_adopted"]
    results = audit["results"][adopted]
    cth_to_fold = {}
    for fold in results["folds"]:
        if fold["no_rule_met_target"]:
            continue
        for cth in fold["evaluation_cth"]:
            cth_to_fold[int(cth)] = fold
    return {
        "cth_to_fold": cth_to_fold,
        "admission_rule": adopted,
        "config": config,
        "held_out_quality": {
            "pooled_held_out_top1_agreement": results[
                "pooled_held_out_top1_agreement"],
            "pooled_held_out_n": results["pooled_held_out_n"],
            "calibration_transfer_gap": results["calibration_transfer_gap"],
        },
    }


def main():
    cth_to_fold, config = load_cth_fold_map()
    calibrated_anchor_length = config["anchor_length"]
    calibrated_mask_length = config["mask_length"]

    calibration_cths = sorted(cth_to_fold.keys())
    print(f"CTHs with applicable existing calibration ({len(calibration_cths)}): {calibration_cths}")

    scope = rgw.prepare_scope(calibration_cths)
    with_anchor = scope["with_anchor"]
    anchor_index = scope["anchor_index"]
    fragment_families = scope["fragment_families"]
    fragment_cth = scope["fragment_cth"]

    # scope is already restricted to calibration-covered CTHs above, but
    # keep the membership check explicit rather than assuming it -- cheap,
    # and it's the actual correctness condition for looking up cth_to_fold.
    overlap_cths = sorted(set(scope["top_cth_ids"]) & set(cth_to_fold.keys()))

    # Same-line: the original population, P2-E4 rates.
    eligible = [
        g for g in with_anchor
        if not g["is_cross_line"]
        and g["run"]["length"] == calibrated_mask_length
        and fragment_cth.get(g["fragment_id"]) in overlap_cths
    ]
    print(f"Real gaps eligible for this calibration "
          f"(same-line, length=={calibrated_mask_length}, CTH in overlap): {len(eligible):,}")

    # Cross-line: its OWN calibration (P2-E9), never the same-line rates. The
    # two populations differ by roughly 5x in gold inclusion, so they are
    # scored separately and reported separately -- never pooled into one
    # headline number.
    cross = load_cross_line_fold_map()
    cross_eligible = []
    cross_index = None
    if cross is not None:
        cross_eligible = [
            g for g in with_anchor
            if g["is_cross_line"]
            and g["run"]["length"] == cross["config"]["mask_length"]
            and fragment_cth.get(g["fragment_id"]) in cross["cth_to_fold"]
        ]
        if cross_eligible:
            anchor_length = int(cross["config"]["anchor_length"])
            requested = {}
            for fragment_id, lines in scope["line_sequences"].items():
                requested.setdefault(fragment_cth[fragment_id], set()).update(
                    p2e8.requested_cross_line_keys(
                        lines, anchor_length,
                        (cross["config"]["mask_length"],)))
            cross_index = p2e8.build_cross_line_index(
                scope["line_sequences"], fragment_families, fragment_cth,
                anchor_length, requested)
        print(f"Real gaps eligible for CROSS-LINE calibration "
              f"({cross['admission_rule']}): {len(cross_eligible):,}")
    else:
        print("Cross-line calibration unavailable or unratified -- "
              "cross-line gaps remain gated.")

    n_selector_accepted = 0
    n_selector_rejected = 0
    n_restored_checked = 0
    n_restored_match_total = 0
    n_restored_contradiction_total = 0
    n_restored_no_rate_available = 0
    rank1_rate_examples = []
    restored_with_calibrated_match = []
    restored_with_calibrated_contradiction = []

    for g in eligible:
        cth = fragment_cth[g["fragment_id"]]
        family = fragment_families[g["fragment_id"]]
        fold = cth_to_fold[cth]
        ranking = p2e2.proposal_ranking(
            anchor_index, cth, g["anchor_key"], family)
        accepted = p2e2.rule_accepts(ranking, fold["selected_rule"])
        if not accepted:
            n_selector_rejected += 1
            continue
        n_selector_accepted += 1

        rank1_calibration = fold["rank_calibration"].get("1")
        if rank1_calibration and rank1_calibration["calibrated_empirical_agreement"] is not None:
            if len(rank1_rate_examples) < 8:
                rank1_rate_examples.append({
                    "doc_id": g["doc_id"], "fragment_id": g["fragment_id"],
                    "rank1_proposal": list(ranking["alternatives"][0]["proposal"]),
                    "rank1_calibrated_rate": rank1_calibration["calibrated_empirical_agreement"],
                    "rank1_wilson_95": rank1_calibration["wilson_95"],
                    "rank1_sample_size": rank1_calibration["calibration_contexts_with_rank_available"],
                })

        if g["run"]["is_pure_restored"]:
            n_restored_checked += 1
            editor_reading = tuple(g["run"]["tokens"])
            editor_rank = None
            for i, alt in enumerate(ranking["alternatives"], 1):
                if alt["proposal"] == editor_reading:
                    editor_rank = i
                    break
            if editor_rank is not None:
                rate = fold["rank_calibration"].get(str(editor_rank))
                if rate and rate["calibrated_empirical_agreement"] is not None:
                    n_restored_match_total += 1
                    if len(restored_with_calibrated_match) < 8:
                        restored_with_calibrated_match.append({
                            "doc_id": g["doc_id"], "fragment_id": g["fragment_id"],
                            "editor_reading": list(editor_reading),
                            "editor_rank": editor_rank,
                            "calibrated_rate_at_that_rank": rate["calibrated_empirical_agreement"],
                            "wilson_95": rate["wilson_95"],
                            "sample_size": rate["calibration_contexts_with_rank_available"],
                        })
                else:
                    n_restored_no_rate_available += 1
            elif rank1_calibration and rank1_calibration["calibrated_empirical_agreement"] is not None:
                n_restored_contradiction_total += 1
                # Editor's restoration doesn't match ANY ranked witness
                # alternative -- the rank-1 alternative (which DOES have a
                # calibrated track record) proposes something different.
                if len(restored_with_calibrated_contradiction) < 8:
                    restored_with_calibrated_contradiction.append({
                        "doc_id": g["doc_id"], "fragment_id": g["fragment_id"],
                        "editor_reading": list(editor_reading),
                        "rank1_proposal": list(ranking["alternatives"][0]["proposal"]),
                        "rank1_calibrated_rate": rank1_calibration["calibrated_empirical_agreement"],
                        "rank1_wilson_95": rank1_calibration["wilson_95"],
                        "rank1_sample_size": rank1_calibration["calibration_contexts_with_rank_available"],
                    })
            else:
                # Neither the editor's reading matches a ranked alternative
                # NOR does rank 1 have a usable calibrated rate -- nothing
                # to report either way, counted so the totals still add up.
                n_restored_no_rate_available += 1

    # ---- Cross-line scoring, kept structurally separate from same-line.
    cross_summary = None
    if cross is not None and cross_eligible and cross_index is not None:
        same_line_index = anchor_index
        cross_accepted = 0
        cross_rejected = 0
        cross_rank1_examples = []
        cross_restored_checked = 0
        cross_restored_match = 0
        for g in cross_eligible:
            cth = fragment_cth[g["fragment_id"]]
            family = fragment_families[g["fragment_id"]]
            fold = cross["cth_to_fold"][cth]
            # LAYOUT_AGNOSTIC: both indices, family sets merged so a witness
            # appearing in both is counted once. Identical construction to
            # what P2-E9 calibrated -- a second ranking implementation here
            # would silently decouple the rate from the thing it rates.
            ranking = p2e9.merged_ranking(
                (cross_index, same_line_index), cth, g["anchor_key"], family)
            if not p2e2.rule_accepts(ranking, fold["selected_rule"]):
                cross_rejected += 1
                continue
            cross_accepted += 1
            # APPLY the calibration-set table: it is fit on compositions
            # disjoint from this fold's evaluation_cth, so it is not measured
            # on the composition this gap came from. rank_calibration_held_out
            # IS measured on those compositions and would be circular here --
            # it is the quality claim, reported separately below.
            rank1 = fold["rank_calibration_calibration_set"].get("1")
            if rank1 and rank1["calibrated_empirical_agreement"] is not None:
                if len(cross_rank1_examples) < 8:
                    cross_rank1_examples.append({
                        "doc_id": g["doc_id"],
                        "fragment_id": g["fragment_id"],
                        "lines_crossed": g.get("lines_crossed"),
                        "rank1_proposal": list(
                            ranking["alternatives"][0]["proposal"]),
                        "rank1_calibrated_rate":
                            rank1["calibrated_empirical_agreement"],
                        "rank1_wilson_95": rank1["wilson_95"],
                        "rank1_sample_size": rank1[
                            "calibration_contexts_with_rank_available"],
                        "population": "CROSS_LINE",
                    })
            if g["run"]["is_pure_restored"]:
                cross_restored_checked += 1
                editor_reading = tuple(g["run"]["tokens"])
                if any(alt["proposal"] == editor_reading
                       for alt in ranking["alternatives"]):
                    cross_restored_match += 1
        cross_summary = {
            "admission_rule": cross["admission_rule"],
            "calibration_target": cross["config"]["calibration_target"],
            "eligible_gaps": len(cross_eligible),
            "selector_accepted": cross_accepted,
            "selector_rejected": cross_rejected,
            "restored_checked": cross_restored_checked,
            "restored_matching_a_ranked_alternative": cross_restored_match,
            "rank1_rate_examples": cross_rank1_examples,
            "rate_applied": "rank_calibration_calibration_set",
            "rate_applied_note": (
                "Fit on compositions disjoint from this fold's evaluation "
                "CTHs, matching how the same-line path applies P2-E4."),
            "held_out_quality": cross["held_out_quality"],
            "must_not_be_pooled_with_same_line": (
                "Cross-line and same-line differ by roughly 5x in gold "
                "inclusion and have different ratified targets (0.75 vs "
                "0.90). A combined count would describe neither."),
        }
        print(f"  cross-line: {cross_accepted:,} accepted, "
              f"{cross_rejected:,} rejected")

    result = {
        "cross_line": cross_summary,
        "calibration_scope_cths": scope["top_cth_ids"],
        "cths_with_applicable_calibration": overlap_cths,
        "scope_documents": len(scope["slice_doc_ids"]),
        **scope["language_scope"].manifest_entry(),
        **scope["language_index"].manifest_entry(),
        "gaps_excluded_by_language": scope["gaps_excluded_by_language"],
        "query_language_counts": scope["query_language_counts"],
        "calibrated_anchor_length": calibrated_anchor_length,
        "calibrated_mask_length": calibrated_mask_length,
        "eligible_gaps": len(eligible),
        "selector_accepted": n_selector_accepted,
        "selector_rejected": n_selector_rejected,
        "restored_checked": n_restored_checked,
        "restored_match_total": n_restored_match_total,
        "restored_contradiction_total": n_restored_contradiction_total,
        "restored_no_rate_available_total": n_restored_no_rate_available,
        "rank1_rate_examples": rank1_rate_examples,
        "restored_with_calibrated_match": restored_with_calibrated_match,
        "restored_with_calibrated_contradiction": restored_with_calibrated_contradiction,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    report_lines = [
        "# Real-gap calibration application (step 3)",
        "",
        "Reuses the already-computed, already-frozen fold calibration from "
        "`Phase2/phase2_out/p2e4_candidate_set_audit.json` -- no recalibration, "
        "the same rank-by-rank rates the demo's own packets already display.",
        "",
        f"Scoped directly to the **{len(result['cths_with_applicable_calibration'])} CTHs** any "
        "fold's held-out evaluation set actually covers (union of all 5 folds' `evaluation_cth` "
        "lists) -- widened from the first increment, which only intersected step 2's unrelated "
        "\"top gap count\" list and found just CTH 627 overlapping. This increment asks "
        f"`prepare_scope()` for the calibration-covered CTHs directly: "
        f"**{result['scope_documents']:,} documents** in scope, vs. step 2's original 867.",
        "",
        f"Further scoped to same-line anchors and length-{calibrated_mask_length} gaps only "
        f"(this calibration file is anchor_length={calibrated_anchor_length}, "
        f"mask_length={calibrated_mask_length} specifically -- other lengths and cross-line "
        "anchors have no matching calibration and are not guessed at).",
        "",
        f"- **{result['eligible_gaps']:,}** real gaps eligible under this scope.",
        f"- **{result['selector_accepted']:,}** pass the fold's own selector rule (a real "
        f"candidate set would be presented); **{result['selector_rejected']:,}** do not "
        "(the evidence doesn't meet the bar the calibration itself was computed under -- "
        "these would abstain, not receive an unreliable rate).",
        "",
        f"Of **{result['restored_checked']:,}** selector-accepted `restored` spans checked against "
        f"the calibrated ranking: **{result['restored_match_total']:,}** match a ranked witness "
        f"alternative (a calibrated rate applies), **{result['restored_contradiction_total']:,}** "
        "are contradicted by the best-witnessed (rank-1) alternative, and "
        f"**{result['restored_no_rate_available_total']:,}** have no usable calibrated rate either "
        "way. All totals below are full counts, not just the samples shown.",
        "",
        "## Sample: rank-1 candidate with its calibrated track record",
        "",
    ]
    for ex in result["rank1_rate_examples"]:
        pct = ex["rank1_calibrated_rate"] * 100
        lo, hi = ex["rank1_wilson_95"][0] * 100, ex["rank1_wilson_95"][1] * 100
        report_lines.append(
            f"- `{ex['fragment_id']}`: rank-1 witness proposal `{' '.join(ex['rank1_proposal']) or '(empty)'}` "
            f"-- historically correct at rank 1 about {pct:.1f}% of the time "
            f"(95% CI {lo:.1f}-{hi:.1f}%, n={ex['rank1_sample_size']:,}).")

    report_lines += ["", f"## Editor's restoration matches a ranked witness alternative ({result['restored_match_total']:,} total, up to 8 shown)", ""]
    for ex in result["restored_with_calibrated_match"]:
        pct = ex["calibrated_rate_at_that_rank"] * 100
        lo, hi = ex["wilson_95"][0] * 100, ex["wilson_95"][1] * 100
        report_lines.append(
            f"- `{ex['fragment_id']}`: editor reading `{' '.join(ex['editor_reading']) or '(empty)'}` "
            f"matches the rank-{ex['editor_rank']} witness alternative -- candidates at that rank "
            f"have historically been correct about {pct:.1f}% of the time "
            f"(95% CI {lo:.1f}-{hi:.1f}%, n={ex['sample_size']:,}).")

    report_lines += ["", f"## Editor's restoration contradicted by the rank-1 (best-supported) alternative ({result['restored_contradiction_total']:,} total, up to 8 shown)", ""]
    for ex in result["restored_with_calibrated_contradiction"]:
        pct = ex["rank1_calibrated_rate"] * 100
        lo, hi = ex["rank1_wilson_95"][0] * 100, ex["rank1_wilson_95"][1] * 100
        report_lines.append(
            f"- `{ex['fragment_id']}`: editor reading `{' '.join(ex['editor_reading']) or '(empty)'}`, "
            f"but the best-witnessed alternative is `{' '.join(ex['rank1_proposal']) or '(empty)'}` -- "
            f"candidates at rank 1 have historically been correct about {pct:.1f}% of the time "
            f"(95% CI {lo:.1f}-{hi:.1f}%, n={ex['rank1_sample_size']:,}). This is NOT the "
            "probability the editor is wrong -- it is the rank's historical track record, "
            "reported per the same rule as everywhere else in this project.",
        )

    report_lines += [
        "",
        "## What this still does not establish",
        "",
        "A calibrated rank-1 rate is a property of many past comparisons at that rank, not this "
        "specific instance -- exactly the distinction Ixca asked to have made clearer in the "
        "demo UI. This is still the full extent of what these 5 folds cover -- CTHs outside "
        "this list have no P2-E4 calibration at all, and widening further would mean computing "
        "new folds, not reusing these. Multi-sign real gaps need the analogous P2-E6 fold "
        "structure; cross-line anchors have no calibration at all yet. Each is a real, "
        "separately-scoped next step, not something to fold in silently.",
    ]
    if cross_summary is not None:
        held = cross_summary["held_out_quality"]
        report_lines += [
            "",
            "## Cross-line gaps (separate population, separate calibration)",
            "",
            f"Admission rule **{cross_summary['admission_rule']}**, ratified "
            f"target **{cross_summary['calibration_target']}**. Cross-line has "
            "its own calibration (P2-E9) and its own target; this is NOT the "
            "same-line 0.90 rate applied to a wider population.",
            "",
            f"- **{cross_summary['eligible_gaps']:,}** cross-line gaps eligible "
            "(single-sign, CTH covered by a usable P2-E9 fold).",
            f"- **{cross_summary['selector_accepted']:,}** pass the fold's own "
            f"selector; {cross_summary['selector_rejected']:,} do not, and "
            "abstain rather than receive an uncertified rate.",
            f"- Of {cross_summary['restored_checked']:,} selector-accepted "
            f"`restored` spans, "
            f"{cross_summary['restored_matching_a_ranked_alternative']:,} have "
            "the editor's reading somewhere among the witness-ranked "
            "alternatives -- corroboration, never proof.",
            "",
            f"**Which rate is attached.** `{cross_summary['rate_applied']}` -- "
            "fit on compositions disjoint from this fold's evaluation CTHs, "
            "matching how the same-line path applies P2-E4. The held-out table "
            "is the quality claim, not the per-gap number: it is measured on "
            "the very compositions these gaps come from, so attaching it here "
            "would be circular.",
            "",
            "**How good is that calibration?** It transfers: "
            f"{100 * held['pooled_held_out_top1_agreement']:.1f}% rank-1 "
            f"agreement on {held['pooled_held_out_n']:,} held-out spans, "
            f"transfer gap {100 * held['calibration_transfer_gap']:.1f} points.",
            "",
            "**Never pool these with the same-line counts above.** "
            + cross_summary["must_not_be_pooled_with_same_line"],
            "",
            "**Observation for review:** a rank-1 proposal may be the *empty* "
            "middle -- witnesses attesting the two anchors adjacent with "
            "nothing between. For a one-sign gap that is evidence of "
            "disagreement with the query's own structure, not a reading. It "
            "arises identically in the same-line path and is left as-is; "
            "filtering it would be a scoring change needing its own "
            "justification.",
            "",
        ]

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
