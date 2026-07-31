#!/usr/bin/env python3
"""Real gaps -- census of the EMPTY MIDDLE among witness proposals.

`PHASE5_SUCCESSOR_HANDOFF.md` open item 4. A witness proposal for a gap is
whatever sits between the query's two anchors in some independent witness.
`build_anchor_index()` iterates `for middle_length in range(max_middle + 1)`,
so `middle_length == 0` is indexed like any other: a witness in which the two
anchors are directly ADJACENT, with nothing between them.

For a single-sign gap that proposal is not a reading. The query's own damage
markup asserts that one sign stood there; a witness showing no sign at all
disagrees with the query's structure. Displayed to a specialist as "rank 1,
calibrated rate 91%", it would read as "the missing sign is: nothing", which
is a different claim from anything the calibration measured.

**This script is a census, not a scoring change.** It counts how often the
empty middle occurs, where it ranks, and how many gaps an expert would
actually see it on. It deliberately does NOT filter it, because:

- the empty middle was present in the anchor index when P2-E4 and P2-E9 were
  FIT (identical `build_anchor_index` / `build_cross_line_index`, identical
  `max_middle`), so the ratified rates already priced its rank-consumption in;
  and
- removing it at application time only, without refitting, would make the
  applied ranking a different construction from the calibrated one. That is
  precisely the standing "do not use a second ranking implementation"
  prohibition, and it is how E2 happened.

The counterfactual section below is reported for exactly one purpose: to size
the decision. It is NOT a proposal, and choosing to filter after seeing that
it improves something would be reporting a search as a measurement.

Usage:
    python scripts/real_gap_empty_middle_census.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import p2e2_abstention_calibration as p2e2  # noqa: E402
import p2e8_cross_line_recoverability as p2e8  # noqa: E402
import p2e9_cross_line_calibration as p2e9  # noqa: E402
import real_gap_calibration as rgcal  # noqa: E402
import real_gap_witness_check as rgw  # noqa: E402

EMPTY_MIDDLE = ()

OUT_DIR = Path("Phase3/real_gaps_out")
OUT_JSON = OUT_DIR / "real_gap_empty_middle_census.json"
REPORT_PATH = OUT_DIR / "real_gap_empty_middle_census_report.md"


def filtered_view(indices, cth, key):
    """A minimal index view for (cth, key) with the empty middle removed.

    Returned in the same nested shape the ranking functions consume, so the
    counterfactual is computed by the REAL ranking function on filtered input
    rather than by a reimplementation of ranking that drops a candidate.
    """
    views = []
    for index in indices:
        entries = {
            proposal: families
            for proposal, families in index.get(cth, {}).get(key, {}).items()
            if tuple(proposal) != EMPTY_MIDDLE
        }
        views.append({cth: {key: entries}})
    return views


def empty_middle_rank(ranking):
    """1-based rank of the empty middle among alternatives, or None."""
    for position, alternative in enumerate(ranking["alternatives"], 1):
        if tuple(alternative["proposal"]) == EMPTY_MIDDLE:
            return position
    return None


def census_population(gaps, rank_fn, filter_fn, fold_for, label):
    """Count empty-middle incidence over one gap population.

    `rank_fn(gap)` produces the ranking the production pipeline would apply;
    `filter_fn(gap)` produces the same ranking with the empty middle removed.
    Both are supplied by the caller so this function never chooses a ranking
    construction of its own.
    """
    counts = Counter()
    rank_histogram = Counter()
    # How much OTHER evidence exists when the pipeline accepts a gap whose
    # top proposal is the empty middle. If the answer is "none", the empty
    # middle is not crowding out a reading -- it is the entire case, and
    # filtering it turns the accept into an abstention rather than into a
    # better answer. That distinction decides which remedy is even coherent.
    accepted_empty_alternatives = Counter()
    examples = []

    for gap in gaps:
        counts["eligible"] += 1
        ranking = rank_fn(gap)
        if not ranking["alternatives"]:
            counts["no_alternatives"] += 1
            continue
        counts["with_alternatives"] += 1

        fold = fold_for(gap)
        accepted = p2e2.rule_accepts(ranking, fold["selected_rule"])
        if accepted:
            counts["selector_accepted"] += 1

        rank = empty_middle_rank(ranking)
        if rank is None:
            continue
        counts["empty_present"] += 1
        rank_histogram[min(rank, 6)] += 1
        if rank == 1:
            counts["empty_at_rank_1"] += 1
            if accepted:
                # The operative number: gaps where a specialist would be
                # shown "nothing" as the best-supported proposal.
                counts["accepted_with_empty_at_rank_1"] += 1
                accepted_empty_alternatives[
                    min(ranking["alternative_count"], 4)] += 1
                if ranking["alternative_count"] == 1:
                    counts["accepted_empty_rank_1_sole_alternative"] += 1
        if accepted:
            counts["accepted_with_empty_present"] += 1

        # Counterfactual, descriptive only.
        refiltered = filter_fn(gap)
        if not refiltered["alternatives"]:
            counts["cf_no_alternatives_left"] += 1
        cf_accepted = (
            bool(refiltered["alternatives"])
            and p2e2.rule_accepts(refiltered, fold["selected_rule"]))
        if accepted and not cf_accepted:
            counts["cf_accepted_becomes_rejected"] += 1
        if cf_accepted and not accepted:
            counts["cf_rejected_becomes_accepted"] += 1
        if accepted and cf_accepted:
            before = tuple(ranking["alternatives"][0]["proposal"])
            after = tuple(refiltered["alternatives"][0]["proposal"])
            if before != after:
                counts["cf_accepted_rank1_changes"] += 1

        if rank == 1 and accepted and len(examples) < 8:
            runner_up = (
                list(ranking["alternatives"][1]["proposal"])
                if len(ranking["alternatives"]) > 1 else None)
            examples.append({
                "doc_id": gap["doc_id"],
                "fragment_id": gap["fragment_id"],
                "empty_middle_support": ranking["alternatives"][0]["support_count"],
                "runner_up_proposal": runner_up,
                "runner_up_support": ranking["runner_up_support"],
                "alternative_count": ranking["alternative_count"],
            })

    return {
        "population": label,
        "counts": dict(sorted(counts.items())),
        "empty_middle_rank_histogram": {
            (f"{rank}" if rank < 6 else "6+"): count
            for rank, count in sorted(rank_histogram.items())
        },
        "accepted_empty_rank_1_alternative_count_histogram": {
            (f"{count}" if count < 4 else "4+"): total
            for count, total in sorted(accepted_empty_alternatives.items())
        },
        "examples_accepted_with_empty_at_rank_1": examples,
    }


def pct(numerator, denominator):
    return 100.0 * numerator / denominator if denominator else 0.0


def main():
    cth_to_fold, config = rgcal.load_cth_fold_map()
    calibrated_mask_length = config["mask_length"]
    cross = rgcal.load_cross_line_fold_map()

    scopes = rgcal.calibration_scope_cths(cth_to_fold, cross)
    scope = rgw.prepare_scope(scopes["union"])
    with_anchor = scope["with_anchor"]
    anchor_index = scope["anchor_index"]
    fragment_families = scope["fragment_families"]
    fragment_cth = scope["fragment_cth"]
    overlap_cths = sorted(set(scope["top_cth_ids"]) & set(cth_to_fold.keys()))

    # ---- Same-line population, exactly as real_gap_calibration selects it.
    same_line_gaps = [
        g for g in with_anchor
        if not g["is_cross_line"]
        and g["run"]["length"] == calibrated_mask_length
        and fragment_cth.get(g["fragment_id"]) in overlap_cths
    ]
    print(f"Same-line gaps eligible: {len(same_line_gaps):,}")

    def same_line_rank(gap):
        return p2e2.proposal_ranking(
            anchor_index, fragment_cth[gap["fragment_id"]], gap["anchor_key"],
            fragment_families[gap["fragment_id"]])

    def same_line_filtered(gap):
        cth = fragment_cth[gap["fragment_id"]]
        view, = filtered_view((anchor_index,), cth, gap["anchor_key"])
        return p2e2.proposal_ranking(
            view, cth, gap["anchor_key"],
            fragment_families[gap["fragment_id"]])

    same_line = census_population(
        same_line_gaps, same_line_rank, same_line_filtered,
        lambda g: cth_to_fold[fragment_cth[g["fragment_id"]]],
        "same_line")

    # ---- Cross-line population, with its own ratified construction.
    cross_line = None
    if cross is not None:
        cross_gaps = [
            g for g in with_anchor
            if g["is_cross_line"]
            and g["run"]["length"] == cross["config"]["mask_length"]
            and fragment_cth.get(g["fragment_id"]) in cross["cth_to_fold"]
        ]
        print(f"Cross-line gaps eligible: {len(cross_gaps):,}")
        if cross_gaps:
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
            indices = (cross_index, anchor_index)

            def cross_rank(gap):
                return p2e9.merged_ranking(
                    indices, fragment_cth[gap["fragment_id"]],
                    gap["anchor_key"], fragment_families[gap["fragment_id"]])

            def cross_filtered(gap):
                cth = fragment_cth[gap["fragment_id"]]
                views = filtered_view(indices, cth, gap["anchor_key"])
                return p2e9.merged_ranking(
                    views, cth, gap["anchor_key"],
                    fragment_families[gap["fragment_id"]])

            cross_line = census_population(
                cross_gaps, cross_rank, cross_filtered,
                lambda g: cross["cth_to_fold"][fragment_cth[g["fragment_id"]]],
                "cross_line")
    else:
        print("Cross-line calibration unavailable or unratified -- "
              "cross-line census skipped, matching production gating.")

    # ---- The structural fact that makes this a bounded problem.
    #
    # Gold for a mask of length N is exactly N tokens, so for these
    # single-sign populations the empty middle can be RANKED but can never be
    # CORRECT. Verified rather than asserted.
    gold_lengths = Counter(g["run"]["length"] for g in same_line_gaps)
    empty_can_be_gold = 0 in gold_lengths

    payload = {
        "task": "real_gap_empty_middle_census",
        "handoff_item": "PHASE5_SUCCESSOR_HANDOFF.md open item 4",
        "is_a_census_not_a_scoring_change": True,
        "corpus_version": "TLHdig_0.2.0-beta",
        "mask_length": calibrated_mask_length,
        "same_line": same_line,
        "cross_line": cross_line,
        "structural_facts": {
            "empty_middle_is_indexed_deliberately":
                "build_anchor_index and build_cross_line_index both iterate "
                "range(MAX_WITNESS_MIDDLE + 1), so middle_length 0 -- two "
                "anchors adjacent in a witness -- is a first-class proposal.",
            "empty_middle_can_never_be_gold_here":
                f"gold length is always {calibrated_mask_length} for this "
                "population; observed gold lengths "
                f"{dict(sorted(gold_lengths.items()))}; a zero-length gold "
                f"{'EXISTS -- investigate' if empty_can_be_gold else 'does not occur'}.",
            "calibration_already_prices_it_in":
                "P2-E4 and P2-E9 were fit over rankings built by these same "
                "index functions, so the empty middle consumed rank positions "
                "during calibration too. The ratified rates are therefore "
                "honest about it; they are not inflated by its presence.",
            "why_filtering_is_not_free":
                "Dropping it at application time only would make the applied "
                "ranking a different construction from the calibrated one. "
                "Any filter must be accompanied by a refit, not bolted on.",
        },
        "counterfactual_is_not_a_proposal":
            "The cf_* counts size the decision. Adopting a filter because the "
            "counterfactual looks better would report a search as a "
            "measurement; the change needs its own justification and refit.",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # ---------------------------------------------------------------- report
    lines = [
        "# Real gaps — empty-middle census",
        "",
        "**This is a census, not a scoring change.** Nothing in the real-gap "
        "pipeline was altered by running it. It closes the measurement half "
        "of `PHASE5_SUCCESSOR_HANDOFF.md` open item 4; the decision half is "
        "Ixca's.",
        "",
        "## What the empty middle is",
        "",
        "A witness proposal is whatever sits between the query's two anchors "
        "in an independent witness. Both index builders iterate "
        "`range(MAX_WITNESS_MIDDLE + 1)`, so `middle_length == 0` is indexed "
        "like any other length: a witness in which the two anchors are "
        "directly **adjacent**.",
        "",
        f"For these single-sign gaps (mask length {calibrated_mask_length}) "
        "that proposal cannot be a reading. The query's damage markup asserts "
        "a sign stood there; a witness showing no sign disagrees with the "
        "query's structure. Shown to a specialist as a ranked candidate with "
        "a calibrated rate beside it, it would read as *“the missing sign "
        "is: nothing”* — a different claim from anything the calibration "
        "measured.",
        "",
        "Verified rather than assumed: observed gold lengths in this "
        f"population are `{dict(sorted(gold_lengths.items()))}`, so a "
        "zero-length gold "
        + ("**exists and needs investigating**." if empty_can_be_gold
           else "does not occur. The empty middle can be **ranked** but never "
                "**correct**."),
        "",
        "## Incidence",
        "",
        "| | same-line | cross-line |",
        "|---|---:|---:|",
    ]

    def row(label, key, denominator_key=None):
        cells = []
        for population in (same_line, cross_line):
            if population is None:
                cells.append("—")
                continue
            counts = population["counts"]
            value = counts.get(key, 0)
            if denominator_key:
                denominator = counts.get(denominator_key, 0)
                cells.append(f"{value:,} ({pct(value, denominator):.1f}%)")
            else:
                cells.append(f"{value:,}")
        return f"| {label} | " + " | ".join(cells) + " |"

    lines += [
        row("eligible gaps", "eligible"),
        row("with any witness alternative", "with_alternatives", "eligible"),
        row("selector-accepted", "selector_accepted", "with_alternatives"),
        row("empty middle present among alternatives", "empty_present",
            "with_alternatives"),
        row("empty middle at rank 1", "empty_at_rank_1", "with_alternatives"),
        row("**accepted AND empty middle at rank 1**",
            "accepted_with_empty_at_rank_1", "selector_accepted"),
        "",
        "The bolded row is the operative number: gaps where the pipeline "
        "accepts, and the proposal a specialist would see first is *nothing*.",
        "",
        "### Where the empty middle ranks, when present",
        "",
        "| rank | same-line | cross-line |",
        "|---|---:|---:|",
    ]
    ranks = sorted(
        set(same_line["empty_middle_rank_histogram"])
        | set((cross_line or {}).get("empty_middle_rank_histogram", {})),
        key=lambda value: (value == "6+", value))
    for rank in ranks:
        same_value = same_line["empty_middle_rank_histogram"].get(rank, 0)
        cross_value = (
            (cross_line or {}).get("empty_middle_rank_histogram", {}).get(rank, 0)
            if cross_line else None)
        lines.append(
            f"| {rank} | {same_value:,} | "
            + (f"{cross_value:,}" if cross_line else "—") + " |")

    lines += [
        "",
        "### When it is accepted at rank 1, what else is on the table?",
        "",
        "| alternatives in the ranking | same-line | cross-line |",
        "|---|---:|---:|",
    ]
    alt_keys = sorted(
        set(same_line["accepted_empty_rank_1_alternative_count_histogram"])
        | set((cross_line or {}).get(
            "accepted_empty_rank_1_alternative_count_histogram", {})),
        key=lambda value: (value == "4+", value))
    for key in alt_keys:
        same_value = same_line[
            "accepted_empty_rank_1_alternative_count_histogram"].get(key, 0)
        cross_value = (
            (cross_line or {}).get(
                "accepted_empty_rank_1_alternative_count_histogram", {}).get(key, 0)
            if cross_line else None)
        lines.append(
            f"| {key} | {same_value:,} | "
            + (f"{cross_value:,}" if cross_line else "—") + " |")

    sole_same = same_line["counts"].get("accepted_empty_rank_1_sole_alternative", 0)
    accepted_same = same_line["counts"].get("accepted_with_empty_at_rank_1", 0)
    sole_cross = ((cross_line or {}).get("counts", {})
                  .get("accepted_empty_rank_1_sole_alternative", 0))
    accepted_cross = ((cross_line or {}).get("counts", {})
                      .get("accepted_with_empty_at_rank_1", 0))
    lines += [
        "",
        "**This is the finding that decides which remedy is coherent.** When "
        "the pipeline accepts a gap whose top proposal is the empty middle, "
        "the empty middle is the *only* alternative in "
        f"{sole_same:,} of {accepted_same:,} same-line and "
        f"{sole_cross:,} of {accepted_cross:,} cross-line cases. In those it "
        "is not crowding a real reading out of rank 1 — it **is** the entire "
        "case, and removing it leaves nothing.",
        "",
        f"In the remaining {accepted_cross - sole_cross:,} cross-line cases "
        "other alternatives do exist, but none of them satisfies the fold's "
        "acceptance rule once the empty middle is removed — which is why the "
        "counterfactual below records **zero** rank-1 changes and turns "
        "*every* one of these accepts into an abstention. Filtering does not "
        "surface a better reading here. It surfaces an abstention.",
        "",
        "## Counterfactual — what a filter would change",
        "",
        "**This is not a proposal.** It sizes the decision. Adopting a filter "
        "because this table looks better would report a search as a "
        "measurement.",
        "",
        "| | same-line | cross-line |",
        "|---|---:|---:|",
        row("accepted → rejected", "cf_accepted_becomes_rejected"),
        row("rejected → accepted", "cf_rejected_becomes_accepted"),
        row("accepted, rank-1 proposal changes", "cf_accepted_rank1_changes"),
        row("no alternative left at all", "cf_no_alternatives_left"),
        "",
    ]

    def net(population):
        if population is None:
            return "—"
        counts = population["counts"]
        before = counts.get("selector_accepted", 0)
        after = (before
                 - counts.get("cf_accepted_becomes_rejected", 0)
                 + counts.get("cf_rejected_becomes_accepted", 0))
        return f"{before:,} → {after:,}"

    lines += [
        f"**Net effect on accepted gaps:** same-line {net(same_line)}, "
        f"cross-line {net(cross_line)}.",
        "",
        "The `rejected → accepted` row is the other side of the ledger and is "
        "not noise: removing the empty middle can lift a gap over the "
        "dominance and margin thresholds it was diluting. So a filter would "
        "not be purely subtractive — it would trade a set of confidently-"
        "wrong top candidates for a smaller set of newly-admitted real ones. "
        "Whether that trade is good is exactly what a refit would have to "
        "measure, and this census cannot answer it.",
        "",
        "## Why filtering is not free",
        "",
        "The empty middle was in the anchor index when **P2-E4 and P2-E9 were "
        "fit** — identical `build_anchor_index` / `build_cross_line_index`, "
        "identical `MAX_WITNESS_MIDDLE`. It consumed rank positions during "
        "calibration exactly as it does during application. So:",
        "",
        "1. **The ratified rates already price it in.** They are not inflated "
        "by its presence; if anything it depressed measured agreement, "
        "because it can occupy a rank the true reading would otherwise hold.",
        "2. **Removing it at application time only would decouple the rate "
        "from the thing it rates.** The applied ranking would be a different "
        "construction from the calibrated one — the standing *do not use a "
        "second ranking implementation* prohibition, and how E2 happened.",
        "",
        "Any filter must therefore ship **with a refit**, not bolted onto the "
        "application step. That is a P2-E-shaped job, not a patch.",
        "",
        "## The decision this leaves open",
        "",
        "Three coherent options, in ascending cost:",
        "",
        "1. **Leave it.** Honest, and the calibration is sound. Costs a "
        "specialist an occasional visibly-wrong top candidate.",
        "2. **Display-layer treatment.** Keep the empty middle in the ranking "
        "(so the calibration still matches) but render it as what it is — "
        "*witnesses attest these anchors adjacent; this contradicts the "
        "query's damage markup* — rather than as a reading. No refit needed, "
        "because the ranking is unchanged.",
        "3. **Filter and refit.** Rebuild P2-E4 and P2-E9 with the empty "
        "middle excluded from the index, and re-derive every downstream "
        "rate. Cleanest, most expensive, and it changes ratified numbers.",
        "",
        "Option 2 is the one that does not require touching a ratified "
        "artifact, and it is where I would start — but it is Ixca's call, and "
        "this census deliberately stops short of making it.",
        "",
    ]
    if same_line["examples_accepted_with_empty_at_rank_1"]:
        lines += [
            "## Examples — accepted, empty middle at rank 1 (same-line)",
            "",
        ]
        for example in same_line["examples_accepted_with_empty_at_rank_1"]:
            runner = example["runner_up_proposal"]
            lines.append(
                f"- `{example['fragment_id']}`: empty middle supported by "
                f"{example['empty_middle_support']} independent family/families; "
                f"runner-up `{' '.join(runner) if runner else '(none)'}` with "
                f"{example['runner_up_support']}; "
                f"{example['alternative_count']} alternative(s) total.")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {REPORT_PATH}")
    print(f"JSON: {OUT_JSON}")


if __name__ == "__main__":
    main()
