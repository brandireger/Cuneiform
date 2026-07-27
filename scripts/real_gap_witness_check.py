#!/usr/bin/env python3
"""Real-gaps production pipeline -- Step 2: witness coverage + editor check.

Ixca's direction (2026-07-25): one step at a time, evaluate before
continuing. Step 1 (scripts/real_gap_census.py) found 181,051 real gaps
across 6,767 train/dev documents, concentrated heavily in a handful of
large multi-witness compositions. This step asks, for a scoped slice of
that population (the top-5 CTHs by gap count -- richest witness coverage,
smallest first slice to verify):

  (a) does ANY independent witness exist for each real gap's exact
      anchor context, using the SAME witness-index machinery P2-E4/P2-E6
      already use (scripts/p2e_witness_recoverability.py's
      build_anchor_index/independent_proposals -- confirmed reusable,
      not tied to the synthetic-masking evaluation methodology, applied
      here to genuinely damaged spans instead);
  (b) for `restored` spans specifically: does the editor's own proposed
      reading match, or fail to match, what independent witnesses
      actually attest -- "let the artifacts do the talking, not the
      editors" (Ixca's framing). The editor's restoration is never
      treated as ground truth here; it is one hypothesis checked against
      independent evidence, same as any other candidate.

Still no packets, no calibration application, no UI -- this step reports
coverage and agreement rates only, so the next step (deciding how to
package this for review) is grounded in real numbers.

`prepare_scope()` takes an explicit CTH list rather than picking one
itself, so other callers (real_gap_calibration.py) can scope to a
different, honestly-derived CTH selection -- e.g. "CTHs the existing
P2-E4 calibration folds actually cover" -- without this module's own
"top gap count" choice leaking into calibration's scope decision.

Usage:
    python scripts/real_gap_witness_check.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import contracts  # noqa: E402
import eval_harness as eh  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402

import pandas as pd  # noqa: E402

import p2e_witness_recoverability as p2e  # noqa: E402
import language_lookup_v2 as llookup  # noqa: E402
import real_gap_census as rgc  # noqa: E402

EDGES_PATH = Path("Phase1_pipeline/p2_out/edges.parquet")
ANCHOR_LENGTH = 2  # matches configs/p2e2_calibration.json's primary_cell
MAX_WITNESS_MIDDLE = 12  # matches scripts/p2e_witness_recoverability.py
TOP_N_CTHS = 5
# Cap on how many adjacent lines the anchor search may cross per side.
# Ixca's call after seeing the uncapped distribution (67.1% of cross-line
# cases cross just 1 line, 80.5% cross <=3, but a real tail runs to 39):
# beyond a few lines, "anchor context" is no longer meaningfully nearby.
# Gaps that would need more than this are treated as having no anchor,
# not kept with a distant, less trustworthy one.
MAX_LINES_CROSSED_PER_SIDE = 3

OUT_DIR = Path("Phase3/real_gaps_out")
OUT_JSON = OUT_DIR / "real_gap_witness_check.json"
REPORT_PATH = OUT_DIR / "real_gap_witness_check_report.md"


def build_line_owner_map(edges):
    """(parent_doc, line_index_in_doc) -> fragment_id (the specific
    witness member covering that physical line). Most documents have
    exactly one member (fragment_id == parent_doc); composite joins
    have several, each covering a distinct line range."""
    owner = {}
    for row in edges.itertuples(index=False):
        for record in json.loads(row.lines):
            key = (row.parent_doc, int(record["line_index_in_doc"]))
            owner[key] = row.fragment_id
    return owner


def build_fragment_line_order(edges):
    """fragment_id -> sorted list of line_index_in_doc values it covers,
    in document order -- lets cross-line anchor extension find "the next
    line this same witness actually preserves", never a line the witness
    doesn't have."""
    order = {}
    for row in edges.itertuples(index=False):
        idxs = sorted(int(r["line_index_in_doc"]) for r in json.loads(row.lines))
        order[row.fragment_id] = idxs
    return order


def attested_only(raw_pairs):
    """[(token, damage_state), ...] -> attested-only token list, via the
    canonical filter (drop 'restored', then drop illegible-'x' literals)."""
    flat = ht.encode_fragment_window([(0, raw_pairs)], include_restored=False)
    return [t for t in flat if t not in ht.SPECIALS and t != "x"]


def compute_anchor_key_crossline(
        doc_id, fragment_id, line_idx, gap_word_positions,
        raw_tokens_by_line, fragment_line_order,
        anchor_length=ANCHOR_LENGTH,
        max_lines_crossed_per_side=MAX_LINES_CROSSED_PER_SIDE):
    """Like the same-line anchor, but when a line runs out of attested
    context on a side, walks to the adjacent line THIS SAME WITNESS
    actually preserves (never invents one) and keeps collecting until
    anchor_length is met or the witness's own line range is exhausted --
    a real edge, not a coverage gap this can close.

    anchor_length and max_lines_crossed_per_side default to this
    module's single-sign constants; callers needing other anchor
    lengths (e.g. the multi-sign adaptive-anchor calibration, which
    needs 1/2/3-sign anchors) or a same-line-only variant (pass
    max_lines_crossed_per_side=0) can override either explicitly --
    existing callers are unaffected.

    Returns (anchor_key, lines_crossed_left, lines_crossed_right) or
    None if even the witness's full preserved range doesn't have enough
    attested context on both sides."""
    raw_tokens = raw_tokens_by_line[(doc_id, line_idx)]
    gap_start = min(gap_word_positions)
    gap_end = max(gap_word_positions)
    same_line_before = [(t, s) for wp, t, s in raw_tokens if wp < gap_start]
    same_line_after = [(t, s) for wp, t, s in raw_tokens if wp > gap_end]

    left_flat = attested_only(same_line_before)
    lines_crossed_left = 0
    order = fragment_line_order.get(fragment_id, [line_idx])
    pos = order.index(line_idx) if line_idx in order else None
    cursor = pos
    while (len(left_flat) < anchor_length and cursor is not None and cursor > 0
           and lines_crossed_left < max_lines_crossed_per_side):
        cursor -= 1
        prev_line_idx = order[cursor]
        prev_tokens = raw_tokens_by_line.get((doc_id, prev_line_idx), [])
        prev_pairs = [(t, s) for _, t, s in prev_tokens]
        left_flat = attested_only(prev_pairs) + left_flat
        lines_crossed_left += 1

    right_flat = attested_only(same_line_after)
    lines_crossed_right = 0
    cursor = pos
    while (len(right_flat) < anchor_length and cursor is not None
           and cursor < len(order) - 1
           and lines_crossed_right < max_lines_crossed_per_side):
        cursor += 1
        next_line_idx = order[cursor]
        next_tokens = raw_tokens_by_line.get((doc_id, next_line_idx), [])
        next_pairs = [(t, s) for _, t, s in next_tokens]
        right_flat = right_flat + attested_only(next_pairs)
        lines_crossed_right += 1

    if len(left_flat) < anchor_length or len(right_flat) < anchor_length:
        return None
    key = (tuple(left_flat[-anchor_length:]), tuple(right_flat[:anchor_length]))
    return key, lines_crossed_left, lines_crossed_right


def top_cths_by_gap_count(n):
    """The step-1 census's own top-N-by-gap-count CTH list -- kept as a
    named helper so this script's default scope (used by its own
    coverage/editor-check report) stays exactly as before, while other
    callers (real_gap_calibration.py) can pass a differently-derived
    CTH list into prepare_scope() instead."""
    census = json.loads(rgc.OUT_JSON.read_text(encoding="utf-8"))
    return [row["cth"] for row in census["top_15_cths_by_real_gap_count"][:n]]


def prepare_scope(cth_ids):
    """Everything through building the witness index -- shared by this
    script's own coverage/editor-check report and by
    real_gap_calibration.py's calibration-application step, so scope
    resolution and anchor-finding are computed once, identically, not
    re-derived a third time. cth_ids is an explicit CTH list the caller
    has already decided on (top-N-by-gap-count, calibration-covered
    CTHs, or any other honestly-derived list) -- this function does not
    pick a scope itself."""
    allowed_ids, split_lookup, ambiguous_ids = rgc.load_allowed_doc_ids()

    doc_table = pd.read_parquet(
        rgc.DOC_TABLE_PATH, columns=["doc_id", "cth"])
    doc_cth = dict(zip(doc_table["doc_id"], doc_table["cth"]))

    top_cth_ids = list(cth_ids)
    preview = top_cth_ids if len(top_cth_ids) <= 10 else top_cth_ids[:10] + ["..."]
    print(f"Scoping to {len(top_cth_ids)} CTH(s): {preview}")

    slice_doc_ids = {d for d in allowed_ids if doc_cth.get(d) in top_cth_ids}
    print(f"Documents in scope for this slice: {len(slice_doc_ids):,}")

    decomposed = pd.read_parquet(
        rgc.DECOMPOSED_PATH,
        columns=["doc_id", "line_index_in_doc", "word_pos", "token",
                  "damage_state", "word_index_in_line"],
        filters=[("doc_id", "in", list(slice_doc_ids))],
    )
    contracts.assert_no_test(
        set(decomposed["doc_id"]), split_lookup, label="real-gap witness check decomposed")
    decomposed = decomposed.sort_values(["doc_id", "line_index_in_doc", "word_pos"])

    edges = pd.read_parquet(
        EDGES_PATH,
        columns=["fragment_id", "parent_doc", "cth", "lines",
                  "top_edge_lost", "bottom_edge_lost",
                  "preserves_left_edge", "preserves_right_edge"],
        filters=[("parent_doc", "in", list(slice_doc_ids))],
    )
    contracts.assert_no_test(
        set(edges["parent_doc"]), split_lookup, label="real-gap witness check edges")
    contracts.assert_unique_docids(edges)

    # Whether this witness has ANY original tablet surface left at all, vs.
    # being a chip with every side lost to breakage -- distinguishes "this
    # damage is genuinely interior to a surviving surface" from "this whole
    # piece is edge material, join-relevant on every side" (Ixca's question:
    # is a heavily-damaged fragment a join-training candidate or a separate,
    # composition-binning concern? Answer depends on which of these it is).
    fragment_has_any_preserved_edge = {
        row.fragment_id: not (
            bool(row.top_edge_lost) and bool(row.bottom_edge_lost)
            and not bool(row.preserves_left_edge) and not bool(row.preserves_right_edge)
        )
        for row in edges.itertuples(index=False)
    }

    line_index = p2e.build_line_index(decomposed)
    language_scope, language_index = llookup.hittite_only_projection(
        sorted(set(edges["parent_doc"])))
    line_sequences, _ = p2e.render_fragments(
        edges, line_index, language_scope=language_scope,
        language_index=language_index)
    line_owner = build_line_owner_map(edges)
    fragment_line_order = build_fragment_line_order(edges)

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)}
    fragment_cth = {
        row.fragment_id: int(row.cth) for row in edges.itertuples(index=False)}

    raw_tokens_by_line = {}
    for (doc_id, line_idx), group in decomposed.groupby(
            ["doc_id", "line_index_in_doc"], sort=False):
        raw_tokens_by_line[(doc_id, int(line_idx))] = [
            (int(r.word_pos), r.token, r.damage_state)
            for r in group.itertuples(index=False)]

    # ---- Pass 1: find every real gap in scope, compute its anchor key
    # directly from find_runs()'s own word_pos_start/word_pos_end -- exact
    # by construction, no re-matching by content (which would be fragile
    # if a duplicate token+damage_state sequence occurs twice in one line).
    # Anchor context now extends across line breaks within the SAME
    # witness fragment when one line runs out of attested tokens on a
    # side -- tagged with how many lines were crossed, so cross-line
    # results are never silently pooled with the same-line population
    # the existing calibration was computed on.
    #
    # P4-D: the QUERY side is language-resolved here, not just the witness
    # index. Before this, render_fragments filtered which witness lines could
    # supply evidence, but every line in the corpus slice could still ASK --
    # so a Hurrian gap was counted in the same denominator as a Hittite one
    # and simply found no coverage. That failed safe but made the reported
    # coverage rate a mixed-language quantity with no way to tell the two
    # populations apart. Out-of-scope gaps are now excluded from the
    # population and counted by reason instead.
    resolved_gaps = []
    excluded_gaps_by_reason = Counter()
    query_language_counts = Counter()
    for (doc_id, line_idx), raw_tokens in raw_tokens_by_line.items():
        fragment_id = line_owner.get((doc_id, line_idx))
        if fragment_id is None:
            continue
        query_decision = language_index.line_decision(
            language_scope, doc_id, line_idx,
            n_source_tokens=len(raw_tokens), record=False)
        runs = list(rgc.find_runs(
            doc_id, int(line_idx),
            [(wp, t, s, None) for wp, t, s in raw_tokens]))
        if not runs:
            continue
        if not query_decision.in_scope:
            excluded_gaps_by_reason[query_decision.reason] += len(runs)
            continue
        query_language_counts[query_decision.sole_language] += len(runs)
        for run in runs:
            gap_word_positions = set(
                range(run["word_pos_start"], run["word_pos_end"] + 1))
            anchor_result = compute_anchor_key_crossline(
                doc_id, fragment_id, line_idx, gap_word_positions,
                raw_tokens_by_line, fragment_line_order)
            anchor_key, crossed_left, crossed_right = (
                anchor_result if anchor_result else (None, 0, 0))
            resolved_gaps.append({
                "doc_id": doc_id, "line_index_in_doc": line_idx,
                "fragment_id": fragment_id, "run": run,
                "anchor_key": anchor_key,
                "lines_crossed": (crossed_left + crossed_right) if anchor_key else 0,
                "is_cross_line": bool(anchor_key) and (crossed_left + crossed_right) > 0,
                "has_preserved_edge": fragment_has_any_preserved_edge.get(fragment_id),
                "query_language": query_decision.sole_language,
            })

    n_excluded = sum(excluded_gaps_by_reason.values())
    print(f"Real gap runs in scope: {len(resolved_gaps):,} "
          f"({n_excluded:,} excluded by language scope "
          f"{language_scope.describe()}: {dict(excluded_gaps_by_reason)})")
    with_anchor = [g for g in resolved_gaps if g["anchor_key"] is not None]
    n_same_line = sum(1 for g in with_anchor if not g["is_cross_line"])
    n_cross_line = sum(1 for g in with_anchor if g["is_cross_line"])
    print(f"Gaps with a full {ANCHOR_LENGTH}-token anchor on both sides: {len(with_anchor):,} "
          f"of {len(resolved_gaps):,} ({n_same_line:,} same-line, {n_cross_line:,} cross-line)")

    # Edge-profile breakdown for ALL real gaps in scope (not just anchored
    # ones): is this witness a chip with every side lost to breakage (pure
    # join material -- damage here isn't separable from edge/join
    # concerns), or does it retain at least one original tablet surface
    # (damage here is genuinely interior, a missing-text question, not a
    # join one)?
    n_no_preserved_edge = sum(
        1 for g in resolved_gaps if g["has_preserved_edge"] is False)
    n_has_preserved_edge = sum(
        1 for g in resolved_gaps if g["has_preserved_edge"] is True)
    n_edge_unknown = len(resolved_gaps) - n_no_preserved_edge - n_has_preserved_edge
    print(f"Gaps in fragments with NO preserved original edge (pure chip): {n_no_preserved_edge:,}")
    print(f"Gaps in fragments with at least one preserved edge (genuinely interior): {n_has_preserved_edge:,}")

    # ---- Pass 2: build the witness index over exactly the anchor keys
    # these real gaps need ----
    requested_by_cth = {}
    for g in with_anchor:
        cth = fragment_cth.get(g["fragment_id"])
        requested_by_cth.setdefault(cth, set()).add(g["anchor_key"])

    anchor_index = p2e.build_anchor_index(
        list(line_sequences.keys()), line_sequences, fragment_families,
        ANCHOR_LENGTH, requested_by_cth, fragment_cth,
        max_middle=MAX_WITNESS_MIDDLE)

    return {
        "top_cth_ids": top_cth_ids,
        "slice_doc_ids": slice_doc_ids,
        "resolved_gaps": resolved_gaps,
        "with_anchor": with_anchor,
        "n_same_line": n_same_line,
        "n_cross_line": n_cross_line,
        "n_no_preserved_edge": n_no_preserved_edge,
        "n_has_preserved_edge": n_has_preserved_edge,
        "n_edge_unknown": n_edge_unknown,
        "anchor_index": anchor_index,
        "fragment_families": fragment_families,
        "fragment_cth": fragment_cth,
        "language_scope": language_scope,
        "language_index": language_index,
        "gaps_excluded_by_language": dict(excluded_gaps_by_reason),
        "query_language_counts": {
            (lang or "UNRESOLVED"): count
            for lang, count in query_language_counts.items()},
    }


def main():
    scope = prepare_scope(top_cths_by_gap_count(TOP_N_CTHS))
    top_cth_ids = scope["top_cth_ids"]
    slice_doc_ids = scope["slice_doc_ids"]
    resolved_gaps = scope["resolved_gaps"]
    with_anchor = scope["with_anchor"]
    n_same_line = scope["n_same_line"]
    n_cross_line = scope["n_cross_line"]
    anchor_index = scope["anchor_index"]
    fragment_families = scope["fragment_families"]
    fragment_cth = scope["fragment_cth"]
    n_no_preserved_edge = scope["n_no_preserved_edge"]
    n_has_preserved_edge = scope["n_has_preserved_edge"]
    n_edge_unknown = scope["n_edge_unknown"]
    lines_crossed_histogram = Counter(
        g["lines_crossed"] for g in with_anchor if g["is_cross_line"])

    # ---- Pass 3: query + compare, stratified same-line vs cross-line ----
    def new_bucket():
        return {
            "n_with_coverage": 0, "n_no_coverage": 0,
            "restored_match": 0, "restored_no_match": 0, "restored_no_coverage": 0,
            "match_examples": [], "mismatch_examples": [],
        }

    buckets = {"same_line": new_bucket(), "cross_line": new_bucket()}

    for g in with_anchor:
        bucket = buckets["cross_line" if g["is_cross_line"] else "same_line"]
        cth = fragment_cth.get(g["fragment_id"])
        family = fragment_families.get(g["fragment_id"])
        proposals = p2e.independent_proposals(
            anchor_index, cth, g["anchor_key"], family)
        has_coverage = bool(proposals)
        if has_coverage:
            bucket["n_with_coverage"] += 1
        else:
            bucket["n_no_coverage"] += 1

        if g["run"]["is_pure_restored"]:
            editor_reading = tuple(g["run"]["tokens"])
            if not has_coverage:
                bucket["restored_no_coverage"] += 1
            elif editor_reading in proposals:
                bucket["restored_match"] += 1
                if len(bucket["match_examples"]) < 5:
                    bucket["match_examples"].append({
                        "doc_id": g["doc_id"], "fragment_id": g["fragment_id"],
                        "editor_reading": list(editor_reading),
                        "witness_proposal_count": len(proposals),
                        "lines_crossed": g["lines_crossed"],
                    })
            else:
                bucket["restored_no_match"] += 1
                if len(bucket["mismatch_examples"]) < 5:
                    bucket["mismatch_examples"].append({
                        "doc_id": g["doc_id"], "fragment_id": g["fragment_id"],
                        "editor_reading": list(editor_reading),
                        "witness_proposals_sample": [list(p) for p in list(proposals)[:5]],
                        "witness_proposal_count": len(proposals),
                        "lines_crossed": g["lines_crossed"],
                    })

    result = {
        "scope_cths": top_cth_ids,
        "scope_documents": len(slice_doc_ids),
        **scope["language_scope"].manifest_entry(),
        **scope["language_index"].manifest_entry(),
        "gaps_excluded_by_language": scope["gaps_excluded_by_language"],
        "query_language_counts": scope["query_language_counts"],
        "gaps_in_scope": len(resolved_gaps),
        "gaps_with_full_anchor": len(with_anchor),
        "gaps_same_line_anchor": n_same_line,
        "gaps_cross_line_anchor": n_cross_line,
        "cross_line_lines_crossed_histogram": dict(sorted(lines_crossed_histogram.items())),
        "gaps_in_fragments_with_no_preserved_edge": n_no_preserved_edge,
        "gaps_in_fragments_with_preserved_edge": n_has_preserved_edge,
        "gaps_edge_status_unknown": n_edge_unknown,
        "same_line": buckets["same_line"],
        "cross_line": buckets["cross_line"],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    def bucket_report(label, b, n_anchored):
        checked = b["restored_match"] + b["restored_no_match"] + b["restored_no_coverage"]
        lines = [
            f"## {label} ({n_anchored:,} gaps)",
            "",
            f"- **{b['n_with_coverage']:,}** "
            f"({b['n_with_coverage'] / max(1, n_anchored) * 100:.1f}%) have at least one "
            f"independent-witness proposal; **{b['n_no_coverage']:,}** have none.",
            f"- Of **{checked:,}** `restored` spans checkable here: "
            f"**{b['restored_match']:,}** ({b['restored_match'] / max(1, checked) * 100:.1f}%) match "
            f"independent witnesses, **{b['restored_no_match']:,}** "
            f"({b['restored_no_match'] / max(1, checked) * 100:.1f}%) disagree with them, "
            f"**{b['restored_no_coverage']:,}** ({b['restored_no_coverage'] / max(1, checked) * 100:.1f}%) "
            "have no independent evidence either way.",
            "",
        ]
        if b["match_examples"]:
            lines.append("Sample matches:")
            for ex in b["match_examples"]:
                crossed_note = (f" ({ex['lines_crossed']} line(s) crossed for anchor context)"
                                 if ex["lines_crossed"] else "")
                lines.append(
                    f"- `{ex['fragment_id']}`: editor reading `{' '.join(ex['editor_reading']) or '(empty)'}` "
                    f"matches {ex['witness_proposal_count']} independent proposal(s){crossed_note}.")
            lines.append("")
        if b["mismatch_examples"]:
            lines.append("Sample mismatches:")
            for ex in b["mismatch_examples"]:
                samples = "; ".join(" ".join(p) or "(empty)" for p in ex["witness_proposals_sample"])
                crossed_note = f" ({ex['lines_crossed']} line(s) crossed)" if ex["lines_crossed"] else ""
                lines.append(
                    f"- `{ex['fragment_id']}`: editor reading `{' '.join(ex['editor_reading']) or '(empty)'}`, "
                    f"{ex['witness_proposal_count']} independent proposal(s), none matching -- e.g. {samples}{crossed_note}.")
            lines.append("")
        return lines

    report_lines = [
        "# Real-gap witness coverage + editor check (step 2, cross-line anchor extension)",
        "",
        f"Scope: top {TOP_N_CTHS} CTHs by gap count from step 1 -- "
        f"CTH {top_cth_ids}, {result['scope_documents']:,} documents. Cross-line anchor search "
        f"capped at **{MAX_LINES_CROSSED_PER_SIDE} lines per side** (Ixca's call, after seeing the "
        "uncapped distribution ran as far as 39 lines for a small tail -- capped rather than kept, "
        "since \"anchor context\" stops being meaningfully nearby well before that).",
        "",
        f"- **{result['gaps_in_scope']:,}** real gaps in scope; "
        f"**{result['gaps_with_full_anchor']:,}** now have a full {ANCHOR_LENGTH}-sign attested "
        "anchor on both sides -- up from 1,960 (7.7%) with no cross-line extension at all.",
        f"  - **{result['gaps_same_line_anchor']:,}** same-line (the original, already-calibrated "
        "category).",
        f"  - **{result['gaps_cross_line_anchor']:,}** required crossing into an adjacent line "
        "this same witness preserves -- a methodologically distinct category, reported "
        "separately below rather than pooled, since the existing calibration was computed "
        "same-line only.",
        "",
        "### How many lines were crossed to find an anchor",
        "",
        "| lines crossed | count |",
        "|---|---|",
    ]
    for n_crossed, count in result["cross_line_lines_crossed_histogram"].items():
        report_lines.append(f"| {n_crossed} | {count:,} |")
    report_lines += [
        "",
        "### Is this damage interior, or is the whole fragment edge material?",
        "",
        "Cross-referenced against `edges.parquet`'s own edge-loss flags -- distinguishes "
        "\"this witness retains at least one original tablet surface, so the damage is "
        "genuinely interior\" from \"this witness is a chip with every side already lost to "
        "breakage,\" which matters for a different question entirely: whether a heavily-damaged "
        "fragment is join-training material (Task B -- concerned with the fragment's own "
        "physical edges) versus a missing-text / composition-binning question (Task A and this "
        "project's core objective -- concerned with what survives inside).",
        "",
        f"- **{result['gaps_in_fragments_with_no_preserved_edge']:,}** real gaps sit in fragments "
        "with no preserved original edge at all -- every side already a break. For these, "
        "interior damage and join-candidacy are not really separable questions: the whole piece "
        "is edge material.",
        f"- **{result['gaps_in_fragments_with_preserved_edge']:,}** real gaps sit in fragments "
        "that retain at least one original surface -- for these, the damage is genuinely "
        "interior and belongs to the missing-text objective, not the join-training one.",
        f"- **{result['gaps_edge_status_unknown']:,}** could not be matched to an edges.parquet "
        "row (not resolved as a fault -- reported, not silently dropped).",
        "",
        "None of this promotes the editor's restoration to truth, nor witness agreement to "
        "truth -- it reports whether independent artifact evidence corroborates, contradicts, "
        "or says nothing about each editorial hypothesis.",
        "",
    ]
    report_lines += bucket_report("Same-line anchors", result["same_line"], n_same_line)
    report_lines += bucket_report("Cross-line anchors", result["cross_line"], n_cross_line)

    report_lines += [
        "## What this does not yet tell us",
        "",
        "Whether a witness-proposed alternative is MORE likely correct than the editor's own "
        "restoration -- that needs the calibration-application layer (step 3), and even then "
        "only as a historical group audit rate, never an instance-level probability. Cross-line "
        "anchors specifically have never been calibrated at all -- their coverage/agreement "
        "numbers above are descriptive only; using them in a scored product would need their "
        "own calibration pass, not a borrowed same-line rate.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Report: {REPORT_PATH}")
    print(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
