#!/usr/bin/env python3
"""P2-E9: fold-structured per-rank calibration for CROSS-LINE anchors.

P2-E8 established that cross-line anchors carry real but much weaker evidence
than same-line ones (gold inclusion 4.27% vs 20.94% at `a2_m1` — a ~5x gap).
That census deliberately produced no rates. This script produces them, under
the same leakage-safe machinery P2-E4 uses for same-line spans, so a
cross-line real gap can finally be presented with a calibrated quantity
instead of abstained on by default.

**What the rates mean.** Exactly what P2-E4's mean, on a different population:
among selector-accepted spans from *calibration* compositions where a given
candidate rank exists, the fraction whose intentionally hidden attested middle
occurs at that rank. It is a property of many past comparisons at that rank in
that stratum — never the probability that one particular lost reading is true.

**Leakage safety is inherited, not reimplemented.** Composition folds come
from `p2e3.assign_composition_folds` (CTH is the indivisible unit), the
selector rule is fit on calibration compositions and applied to held-out
evaluation compositions, and witness support must come from a source family
other than the query's own. Reusing those functions rather than writing
parallel ones is deliberate: a second implementation is a second chance to
get leakage wrong.

**`LAYOUT_AGNOSTIC` is the ratified admission rule** (Ixca, 2026-07-28):
line division is scribal layout, not textual structure, so a same-line witness
occurrence is real evidence about a cross-line gap. `STRICT` is retained as a
declared ablation rather than deleted -- adopting a rule should never destroy
the comparison that justified it. Both are calibrated, in
`configs/p2e9_cross_line_calibration.json`.

**The calibration target is deliberately still null, and every consumer fails
closed on it.** Cross-line tops out near 81% rank-1 under the ratified rule,
so silently inheriting same-line's 0.90 would encode permanent abstention as
if it were a policy, and choosing a lower value in code after seeing which one
yields output would report a search as a measurement.

Usage:
    python scripts/p2e9_cross_line_calibration.py
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import contracts  # noqa: E402
import pandas as pd  # noqa: E402
import phase2_io  # noqa: E402
import eval_harness as eh  # noqa: E402
import evidence_policy as ep  # noqa: E402
import hittite_tokenizer as ht  # noqa: E402
import language_lookup_v2 as llookup  # noqa: E402

import p2e2_abstention_calibration as p2e2  # noqa: E402
import p2e3_cross_calibration as p2e3  # noqa: E402
import p2e4_candidate_set_audit as p2e4  # noqa: E402
import p2e8_cross_line_recoverability as p2e8  # noqa: E402
import p2e_witness_recoverability as p2e  # noqa: E402

SEED = 20260728
POLICY_NAME = "catalog_assisted"
# Rule grid and estimand wording are shared with same-line; the POLICY (which
# admission rule, which target) is cross-line's own, in its own file.
CONFIG_PATH = Path("configs") / "p2e4_candidate_set_audit.json"
CROSS_LINE_CONFIG_PATH = Path("configs") / "p2e9_cross_line_calibration.json"


class UnratifiedPolicyError(RuntimeError):
    """Raised when a consumer needs a policy value no one has ratified."""


def require_calibration_target(cross_config):
    """The cross-line calibration target, or refuse.

    Null in the config is deliberate, not an oversight. Same-line uses 0.90
    and clears it; cross-line tops out near 81%, so inheriting 0.90 silently
    would encode permanent abstention as if it were a decision, and picking a
    lower one here -- in code, after seeing which target yields output --
    would report a search as a measurement. Fail closed until it is ratified.
    """
    target = cross_config.get("calibration_target")
    if target is None or cross_config.get(
            "calibration_target_status") != "RATIFIED":
        raise UnratifiedPolicyError(
            "cross-line calibration_target is UNRATIFIED. The sensitivity "
            "sweep in reports/phase2_p2e9_cross_line_calibration.md is "
            "evidence for that decision, not a substitute for it. Set both "
            "calibration_target and calibration_target_status in "
            f"{CROSS_LINE_CONFIG_PATH} once Ixca has ratified a value.")
    return float(target)

# The cell the real-gap single-sign pipeline actually applies. Calibrating the
# whole grid would produce rates nothing consumes yet; this is the one that
# unblocks cross-line real gaps.
ANCHOR_LENGTH = 2
MASK_LENGTH = 1

OUT_DIR = Path("Phase2/phase2_out")
RESULT_PATH = OUT_DIR / "p2e9_cross_line_calibration.json"
MANIFEST_PATH = OUT_DIR / "p2e9_cross_line_calibration_manifest.json"
REPORT_PATH = Path("reports") / "phase2_p2e9_cross_line_calibration.md"
REGISTRY_PATH = Path("configs") / "evidence_registry.yaml"
POLICIES_PATH = Path("configs") / "evidence_policies.yaml"



def load_non_test_inputs(universe_splits):
    """Load the governed non-test calibration universe (train + dev, non-bin).

    P2-E's own loader is hard-gated to dev by `assert_dev_only_selection`,
    which is correct for a *probe*. A calibration distribution is a different
    thing: the standing rule is that corpus statistics are fit over the
    declared universe for their phase, typically the full non-test universe.
    Cross-line spans are scarce enough that dev alone left folds with 45/5/1/4
    held-out accepts -- three of four folds carrying no weight at all.

    Widening is safe here for a specific reason: this calibration consumes no
    model. It counts independent witness families in an anchor index, so
    including train compositions cannot leak anything a model was fit on.
    Folds remain composition-level, so a CTH is wholly in calibration or
    wholly in evaluation either way.

    Bin (discovery) documents stay out: a bin fragment is unlabeled, not
    negative, and must not enter a supervision or metric truth set. Test is
    excluded and then asserted, not assumed.
    """
    splits = pd.read_parquet(
        p2e.P2_OUT / "splits.parquet",
        columns=["doc_id", "cth", "is_bin", "main_split"])
    split_lookup, ambiguous_ids = phase2_io.split_lookup_fail_closed(splits)
    allowed = sorted(
        doc_id for doc_id, split in split_lookup.items()
        if split in universe_splits)
    if not allowed:
        raise AssertionError("P2-E9: universe selection produced no parents")

    bins = set(splits.loc[splits["is_bin"], "doc_id"])
    allowed = [doc_id for doc_id in allowed if doc_id not in bins]

    edges = pd.read_parquet(
        p2e.P2_OUT / "edges.parquet",
        columns=["fragment_id", "parent_doc", "cth", "lines"],
        filters=[("parent_doc", "in", allowed)])
    unexpected = set(edges["parent_doc"]).difference(allowed)
    if unexpected:
        raise AssertionError(
            f"P2-E9: edge reader returned out-of-universe parents: "
            f"{sorted(unexpected)[:5]}")
    contracts.assert_unique_docids(edges)
    # Belt and braces: the reader filtered, now prove it.
    contracts.assert_no_test(
        sorted(set(edges["parent_doc"])), split_lookup,
        label="P2-E9 calibration universe")

    decomposed = pd.read_parquet(
        p2e.P4_OUT / "decomposed_corpus.parquet",
        columns=["doc_id", "line_index_in_doc", "word_pos", "token",
                 "damage_state"],
        filters=[("doc_id", "in", allowed)])
    contracts.assert_no_test(
        set(decomposed["doc_id"]), split_lookup,
        label="P2-E9 decomposed content")
    return splits, split_lookup, ambiguous_ids, edges, decomposed


def merged_ranking(indices, cth, key, excluded_family):
    """Rank alternatives over the union of several anchor indices.

    `LAYOUT_AGNOSTIC` searches both the cross-line and same-line indices, and
    one proposal may be supported by different families in each. Merging the
    FAMILY SETS before counting keeps a family that witnesses the same
    proposal in both indices from being counted twice -- support is a count of
    independent sources, and double-counting one would inflate exactly the
    quantity the selector rule thresholds on.
    """
    families_by_proposal = defaultdict(set)
    for index in indices:
        for proposal, families in index.get(cth, {}).get(key, {}).items():
            families_by_proposal[tuple(proposal)].update(families)

    alternatives = []
    for proposal, families in families_by_proposal.items():
        independent = sorted(f for f in families if f != excluded_family)
        if independent:
            alternatives.append({
                "proposal": proposal,
                "supporting_families": tuple(independent),
                "support_count": len(independent),
            })
    alternatives.sort(key=lambda value: (-value["support_count"],
                                         value["proposal"]))
    if not alternatives:
        return {"alternatives": [], "unique_top": False, "top_support": 0,
                "runner_up_support": 0, "support_margin": 0, "dominance": 0.0,
                "alternative_count": 0}
    top = alternatives[0]["support_count"]
    tied = sum(1 for v in alternatives if v["support_count"] == top)
    runner_up = alternatives[1]["support_count"] if len(alternatives) > 1 else 0
    total = sum(v["support_count"] for v in alternatives)
    return {
        "alternatives": alternatives,
        "unique_top": tied == 1,
        "top_support": top,
        "runner_up_support": runner_up,
        "support_margin": top - runner_up,
        "dominance": top / total,
        "alternative_count": len(alternatives),
    }


def build_records(line_sequences, fragment_cth, fragment_families,
                  fragments_by_cth, indices_by_rule):
    """One record per eligible cross-line span, ranked under each rule."""
    cth_families = {
        cth: {fragment_families[fid] for fid in fids}
        for cth, fids in fragments_by_cth.items()
    }
    records = {rule: [] for rule in indices_by_rule}
    for fragment_id in sorted(line_sequences):
        cth = fragment_cth[fragment_id]
        query_family = fragment_families[fragment_id]
        if not cth_families[cth].difference({query_family}):
            continue
        for region, key, gold in p2e8.iter_cross_line_spans(
                line_sequences[fragment_id], ANCHOR_LENGTH, MASK_LENGTH):
            for rule_name, indices in indices_by_rule.items():
                ranking = merged_ranking(indices, cth, key, query_family)
                if not ranking["alternatives"]:
                    continue
                records[rule_name].append({
                    "cth": cth,
                    "fragment_id": fragment_id,
                    "boundary_region": region,
                    "gold": gold,
                    "ranking": ranking,
                })
    return records


def calibrate(records, config, rules, target, estimand):
    """Fit on calibration compositions, report on held-out ones.

    `target` is passed in from the CROSS-LINE policy, never read from the
    same-line config. Reading it from `config` is the exact substitution this
    whole exercise exists to prevent.
    """
    weights = defaultdict(int)
    for record in records:
        weights[record["cth"]] += 1
    folds = p2e3.assign_composition_folds(
        weights, sorted({r["cth"] for r in records}), int(config["folds"]))

    target_key = str(target)
    maximum_rank = max(config["candidate_set_depths"])
    fold_results = []
    accepted_total = 0
    for fold in folds:
        evaluation_cths = fold["cth"]
        calibration_records = [r for r in records
                               if r["cth"] not in evaluation_cths]
        evaluation_records = [r for r in records
                              if r["cth"] in evaluation_cths]
        selected = p2e2.choose_rules(
            p2e2.evaluate_rules_vectorized(calibration_records, rules),
            [target], int(config["minimum_calibration_accepts"]),
        )[target_key]
        if selected is None:
            # No rule reached the calibration target with enough accepts.
            # Reported as a fold that abstains, never softened by lowering the
            # target until something passes.
            fold_results.append({
                "fold": fold["fold"],
                "evaluation_cth": sorted(evaluation_cths),
                "selected_rule": None,
                "no_rule_met_target": True,
                "calibration_contexts": len(calibration_records),
                "evaluation_contexts": len(evaluation_records),
                "accepted_evaluation_contexts": 0,
                "rank_calibration": {},
            })
            continue
        rule = selected["rule"]
        fold_accepted = [r for r in evaluation_records
                         if p2e2.rule_accepts(r["ranking"], rule)]
        accepted_total += len(fold_accepted)
        fold_results.append({
            "fold": fold["fold"],
            "evaluation_cth": sorted(evaluation_cths),
            "selected_rule": rule,
            "no_rule_met_target": False,
            "calibration_contexts": len(calibration_records),
            "evaluation_contexts": len(evaluation_records),
            "accepted_evaluation_contexts": len(fold_accepted),
            "held_out_top1_agreement": (
                round(sum(
                    r["ranking"]["alternatives"][0]["proposal"] == r["gold"]
                    for r in fold_accepted) / len(fold_accepted), 6)
                if fold_accepted else None),
            # Fit-set rates, retained for the transfer comparison only.
            "rank_calibration_calibration_set": p2e4.rank_calibration(
                calibration_records, rule, maximum_rank, estimand),
            # What held-out compositions actually delivered. THIS is the rate
            # a consumer may display; the fit-set one describes the fit.
            "rank_calibration_held_out": p2e4.rank_calibration(
                evaluation_records, rule, maximum_rank, estimand),
        })
    return folds, fold_results, accepted_total


def target_sensitivity(records, rules, minimum_accepts, targets):
    """What each calibration target would yield — a sensitivity analysis.

    Reported because the inherited 0.9 target turns out to be unreachable for
    cross-line evidence, and the difference between "unreachable" and
    "reachable at a lower bar" is the decision Ixca actually faces.

    This is NOT a proposal to lower the target. Choosing a target after seeing
    which one produces output is how a search gets reported as a measurement.
    The numbers are here so the choice can be made deliberately, in the open,
    and recorded as a ratification.
    """
    sweep = []
    for target in targets:
        best_rate, best_accepts = 0.0, 0
        for rule in rules:
            accepted = [r for r in records
                        if p2e2.rule_accepts(r["ranking"], rule)]
            if len(accepted) < minimum_accepts:
                continue
            rate = sum(
                r["ranking"]["alternatives"][0]["proposal"] == r["gold"]
                for r in accepted) / len(accepted)
            if rate >= target and len(accepted) > best_accepts:
                best_rate, best_accepts = rate, len(accepted)
        sweep.append({
            "target": target,
            "reachable": best_accepts > 0,
            "spans_accepted_at_best_rule": best_accepts,
            "achieved_rate": round(best_rate, 4) if best_accepts else None,
        })
    return sweep


def achievable_ceiling(records, rules, minimum_accepts):
    """Highest rank-1 agreement any grid rule reaches with enough accepts."""
    best = {"rate": None, "accepted": 0, "rule": None}
    for rule in rules:
        accepted = [r for r in records
                    if p2e2.rule_accepts(r["ranking"], rule)]
        if len(accepted) < minimum_accepts:
            continue
        rate = sum(
            r["ranking"]["alternatives"][0]["proposal"] == r["gold"]
            for r in accepted) / len(accepted)
        if best["rate"] is None or rate > best["rate"]:
            best = {"rate": round(rate, 4), "accepted": len(accepted),
                    "rule": rule}
    return best


def write_report(results, elapsed, cross_config):
    lines = [
        "# Phase 2 P2-E9 — cross-line per-rank calibration",
        "",
        f"Cell `a{ANCHOR_LENGTH}_m{MASK_LENGTH}` — the cell the real-gap "
        "single-sign pipeline applies. Composition-folded, fit on calibration "
        "compositions and reported on held-out ones, witness support required "
        "from an independent source family.",
        "",
        "**A rate here is a property of many past comparisons at that rank in "
        "that stratum. It is never the probability that one particular lost "
        "reading is true.** Cross-line rates may not be applied to same-line "
        "gaps, or the reverse.",
        "",
        f"## Admission rule: `{cross_config['witness_admission_rule']}` "
        "(**RATIFIED** "
        f"{cross_config['witness_admission_rule_ratified']})",
        "",
        cross_config["witness_admission_rule_rationale"],
        "",
        f"`{cross_config['witness_admission_rule_retained_as_ablation']}` is "
        "retained below as a declared ablation, not deleted: adopting a rule "
        "should never destroy the comparison that justified it.",
        "",
        "| rule | eligible spans | folds with a usable rule | accepted (held-out) |",
        "|---|---:|---:|---:|",
    ]
    for rule_name, data in results.items():
        usable = sum(1 for f in data["folds"] if not f["no_rule_met_target"])
        lines.append(
            f"| `{rule_name}` | {data['eligible_spans']:,} | "
            f"{usable}/{len(data['folds'])} | "
            f"{data['accepted_evaluation_contexts']:,} |")

    for rule_name, data in results.items():
        lines += [
            "",
            f"### `{rule_name}` — per-rank calibration by fold",
            "",
            "| fold | held-out accepts | rank-1 (HELD-OUT) | 95% CI | n |",
            "|---|---:|---:|---|---:|",
        ]
        for fold in data["folds"]:
            if fold["no_rule_met_target"]:
                lines.append(
                    f"| {fold['fold']} | — | *no rule met the calibration "
                    "target* | — | — |")
                continue
            rank1 = fold["rank_calibration_held_out"].get("1", {})
            rate = rank1.get("calibrated_empirical_agreement")
            interval = rank1.get("wilson_95") or ["—", "—"]
            n = rank1.get("calibration_contexts_with_rank_available", 0)
            lines.append(
                f"| {fold['fold']} | {fold['accepted_evaluation_contexts']:,} "
                f"| {f'{100 * rate:.1f}%' if rate is not None else '—'} | "
                f"{interval[0]}–{interval[1]} | {n:,} |")

    lines += [
        "",
        "## Ceiling against the same-line bar",
        "",
        "What the grid can reach at all, against same-line's 0.90 bar:",
        "",
        "| rule | raw top-1 | best rule reaching ≥50 accepts | vs 0.90 target |",
        "|---|---:|---:|---|",
    ]
    for rule_name, data in results.items():
        ceiling = data["achievable_ceiling"]
        rate = ceiling["rate"]
        best = (f"{100 * rate:.1f}% on n={ceiling['accepted']:,}"
                if rate is not None else "—")
        raw = 100 * data["raw_top1_agreement"]
        lines.append(
            f"| `{rule_name}` | {raw:.1f}% | {best} | **short of target** |")

    lines += [
        "",
        "Same-line spans at this cell reach ~91% at rank 1, which is why 0.90 "
        "was a sensible bar for them. Cross-line does not reach it, which is "
        "why cross-line has its own ratified target rather than inheriting "
        "one. A cross-line rate must always be displayed as a cross-line "
        "rate: the populations differ by roughly 5x in gold inclusion, and "
        "substituting one for the other is the error this whole line of work "
        "exists to prevent.",
        "",
        "### What each target would yield — sensitivity, NOT a proposal",
        "",
        "The gap between *unreachable* and *reachable at a lower bar* is the "
        "decision this raises. These numbers exist so that decision can be "
        "made deliberately and recorded, not so a target can be picked "
        "because it produced output.",
        "",
        "| target | " + " | ".join(f"`{r}`" for r in results) + " |",
        "|---|" + "---|" * len(results),
    ]
    targets = [0.70, 0.75, 0.80, 0.85, 0.90]
    for index, target in enumerate(targets):
        cells = []
        for data in results.values():
            entry = data["target_sensitivity_not_adopted"][index]
            cells.append(
                f"{entry['spans_accepted_at_best_rule']:,} spans @ "
                f"{100 * entry['achieved_rate']:.1f}%"
                if entry["reachable"] else "unreachable")
        lines.append(f"| {target:.2f} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "**Nothing here is adopted.** Lowering a calibration target changes "
        "what an expert is told a candidate is worth. That is Ixca's call, and "
        "it should be ratified in the open with these numbers in view.",
        "",
        "## Does the calibration transfer? (the check that matters)",
        "",
        "A selector fit on calibration compositions can look well-calibrated "
        "*there* and fail on compositions it has never seen. Fold structure "
        "exists to expose that, so it is reported before anything else is "
        "believed:",
        "",
        "| rule | calibrated rank-1 (promised) | held-out top-1 (delivered) | "
        "gap | held-out n |",
        "|---|---:|---:|---:|---:|",
    ]
    for rule_name, data in results.items():
        promised_rate = data["mean_calibrated_rank1_promised"]
        delivered = data["pooled_held_out_top1_agreement"]
        gap = data["calibration_transfer_gap"]
        lines.append(
            f"| `{rule_name}` | "
            f"{f'{100 * promised_rate:.1f}%' if promised_rate else '—'} | "
            f"{f'{100 * delivered:.1f}%' if delivered is not None else '—'} | "
            f"{f'{100 * gap:.1f} pts' if gap is not None else '—'} | "
            f"{data['pooled_held_out_n']:,} |")

    lines += [
        "",
        "**Only the held-out column may be displayed.** The fit-set figure "
        "reports how well a selector fit its own calibration compositions, "
        "which is not what an expert needs to know. Where the two diverge, "
        "the fit-set number is optimistic.",
        "",
        "An earlier dev-only run showed a 12.8-point gap on 55 held-out "
        "spans, with per-fold accepts of 45/5/1/4 — three of four folds "
        "carrying no weight at all. That gap was a small-sample artifact, not "
        "a property of cross-line evidence: widening the calibration universe "
        "to the governed non-test set closed it. The lesson is kept here "
        "because the optimistic reading was available first.",
        "",
        "## How to read the abstentions",
        "",
        "A fold with *no rule met the calibration target* is a fold where no "
        "selector in the grid reached the target agreement with enough "
        "calibration accepts. That is reported as-is. The target was not "
        "lowered until something passed — a rate obtained that way would "
        "describe the search, not the evidence.",
        "",
        "## Standing limits",
        "",
        "- Adjacent line pairs only (one boundary crossed), matching P2-E8.",
        f"- `{cross_config['witness_admission_rule']}` is the **ratified** "
        f"admission rule ({cross_config['witness_admission_rule_ratified']}); "
        f"`{cross_config['witness_admission_rule_retained_as_ablation']}` is "
        "retained as a declared ablation and is not a fallback.",
        f"- Calibration target **{cross_config['calibration_target']}** "
        f"({cross_config['calibration_target_status']}, "
        f"{cross_config.get('calibration_target_ratified', 'n/a')}). "
        "Same-line keeps 0.90 in its own config; the two must never be pooled "
        "or substituted.",
        "- Calibration universe: "
        f"{'+'.join(cross_config['calibration_universe_splits'])}, non-bin, "
        "test excluded and asserted. Bin documents are unlabeled, not "
        "negative, and stay out of every truth set.",
        "- These rates are for cross-line anchors only. P2-E4's same-line "
        "rates remain the same-line ones; the two populations differ by "
        "roughly 5x in gold inclusion and must never be pooled or "
        "substituted.",
        "- Applying these to real gaps is a further step "
        "(`real_gap_calibration.py` currently gates on "
        "`if not g[\"is_cross_line\"]`), and needs its own review.",
        "",
        f"Runtime {elapsed:.1f}s · seed {SEED}.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    started = time.perf_counter()
    OUT_DIR.mkdir(exist_ok=True)
    REPORT_PATH.parent.mkdir(exist_ok=True)

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cross_config = json.loads(
        CROSS_LINE_CONFIG_PATH.read_text(encoding="utf-8"))
    adopted_rule = cross_config["witness_admission_rule"]
    ablation_rule = cross_config["witness_admission_rule_retained_as_ablation"]
    registry = ep.load_registry(REGISTRY_PATH)
    policy = ep.load_policy(POLICY_NAME, POLICIES_PATH)
    ep.validate_semantic_features(
        ["token", "damage_state", "line_index_in_doc", "cth"], registry, policy)

    universe = tuple(cross_config["calibration_universe_splits"])
    splits, split_lookup, ambiguous_ids, edges, decomposed = (
        load_non_test_inputs(universe))
    parent_count = len(set(edges['parent_doc']))
    print('Calibration universe', universe, ':', parent_count,
          'parent documents')
    line_index = p2e.build_line_index(decomposed)
    language_scope, language_index = llookup.hittite_only_projection(
        sorted(set(edges["parent_doc"])))
    line_sequences, canonical_flat = p2e.render_fragments(
        edges, line_index, language_scope=language_scope,
        language_index=language_index)

    tokenizer = ht.Tokenizer.load()
    contracts.assert_encoding_sane(
        tokenizer.encode(canonical_flat, strict=True), tokenizer,
        max_unk=0.05, label=f"P2-E9 {'+'.join(universe)} attested-only")

    family_map = eh.build_family_map(edges[["parent_doc"]])
    fragment_cth = {row.fragment_id: int(row.cth)
                    for row in edges.itertuples(index=False)}
    fragment_families = {
        row.fragment_id: family_map.get(row.parent_doc, row.parent_doc)
        for row in edges.itertuples(index=False)}
    fragments_by_cth = defaultdict(list)
    for fragment_id, cth in fragment_cth.items():
        fragments_by_cth[cth].append(fragment_id)

    requested_by_cth = defaultdict(set)
    for fragment_id, lines in line_sequences.items():
        requested_by_cth[fragment_cth[fragment_id]].update(
            p2e8.requested_cross_line_keys(
                lines, ANCHOR_LENGTH, (MASK_LENGTH,)))
    cross_index = p2e8.build_cross_line_index(
        line_sequences, fragment_families, fragment_cth, ANCHOR_LENGTH,
        requested_by_cth)
    same_line_index = p2e.build_anchor_index(
        line_sequences.keys(), line_sequences, fragment_families,
        ANCHOR_LENGTH, requested_by_cth, fragment_cth)

    available = {
        "STRICT": (cross_index,),
        "LAYOUT_AGNOSTIC": (cross_index, same_line_index),
    }
    # Ratified rule first; the other is retained as a declared ablation rather
    # than deleted, so adopting one never destroys the comparison that
    # justified it.
    indices_by_rule = {adopted_rule: available[adopted_rule],
                       ablation_rule: available[ablation_rule]}
    records = build_records(line_sequences, fragment_cth, fragment_families,
                            fragments_by_cth, indices_by_rule)

    target = require_calibration_target(cross_config)
    rules = p2e2.generate_rules(config)
    results = {}
    for rule_name, rule_records in records.items():
        folds, fold_results, accepted = calibrate(
            rule_records, config, rules, target,
            cross_config["candidate_probability_estimand"])
        minimum_accepts = int(config["minimum_calibration_accepts"])
        # The honesty check the fold structure exists to make possible: what
        # the calibrated rate PROMISED versus what held-out compositions
        # actually delivered. A selector fit on one set of compositions can
        # look well-calibrated there and fail to transfer.
        graded = [(f["accepted_evaluation_contexts"],
                   f["held_out_top1_agreement"])
                  for f in fold_results if not f["no_rule_met_target"]
                  and f["accepted_evaluation_contexts"]]
        held_out_n = sum(n for n, _ in graded)
        pooled_held_out = (
            round(sum(n * rate for n, rate in graded) / held_out_n, 4)
            if held_out_n else None)
        promised = [f["rank_calibration_calibration_set"]["1"][
                        "calibrated_empirical_agreement"]
                    for f in fold_results if not f["no_rule_met_target"]
                    and f["rank_calibration_calibration_set"].get("1", {}).get(
                        "calibrated_empirical_agreement") is not None]
        pooled_promised = (
            round(sum(promised) / len(promised), 4) if promised else None)
        results[rule_name] = {
            "eligible_spans": len(rule_records),
            "compositions": len({r["cth"] for r in rule_records}),
            "accepted_evaluation_contexts": accepted,
            "raw_top1_agreement": round(sum(
                r["ranking"]["alternatives"][0]["proposal"] == r["gold"]
                for r in rule_records) / len(rule_records), 4),
            "achievable_ceiling": achievable_ceiling(
                rule_records, rules, minimum_accepts),
            "target_sensitivity_not_adopted": target_sensitivity(
                rule_records, rules, minimum_accepts,
                [0.70, 0.75, 0.80, 0.85, 0.90]),
            "pooled_held_out_top1_agreement": pooled_held_out,
            "pooled_held_out_n": held_out_n,
            "mean_calibrated_rank1_promised": pooled_promised,
            "calibration_transfer_gap": (
                round(pooled_promised - pooled_held_out, 4)
                if pooled_promised is not None and pooled_held_out is not None
                else None),
            "folds": fold_results,
        }
        print(f"{rule_name}: {len(rule_records):,} eligible, "
              f"{accepted:,} accepted on held-out compositions")

    elapsed = time.perf_counter() - started
    RESULT_PATH.write_text(json.dumps({
        "task": "p2e9_cross_line_calibration",
        "cell": f"a{ANCHOR_LENGTH}_m{MASK_LENGTH}",
        "is_calibration": True,
        "population": "cross_line_anchors_adjacent_line_pairs",
        # Two different questions, two different tables. Conflating them is
        # a live footgun: one is leakage-safe to attach to a gap, the other
        # is not.
        "rate_to_APPLY_to_a_gap": "rank_calibration_calibration_set",
        "rate_to_APPLY_note": (
            "Attach this one to a real gap. It is fit on compositions "
            "DISJOINT from the fold's evaluation_cth, so applying it to a gap "
            "whose CTH sits in that fold uses evidence from other "
            "compositions -- the same leakage-safe pattern P2-E4 uses. "
            "rank_calibration_held_out is measured ON those same "
            "compositions and attaching it to a gap drawn from them would be "
            "circular."),
        "rate_to_REPORT_as_quality": "rank_calibration_held_out",
        "rate_to_REPORT_note": (
            "Use this to state how well the calibration transfers to unseen "
            "compositions. It is the honest quality claim and belongs in "
            "reports; it is not the number to hang on an individual gap."),
        "scores_are_probabilities": False,
        "estimand": cross_config["candidate_probability_estimand"],
        "confidence_interval": cross_config["confidence_interval"],
        "language_scope": language_scope.scope,
        "witness_admission_rule_adopted": adopted_rule,
        "witness_admission_rule_ablation": ablation_rule,
        "witness_admission_rule_ratified": cross_config[
            "witness_admission_rule_ratified"],
        "calibration_target_status": cross_config["calibration_target_status"],
        "calibration_target": cross_config["calibration_target"],
        "results": results,
    }, ensure_ascii=False, indent=2, default=list) + "\n", encoding="utf-8")

    ep.write_manifest({
        "task": "p2e9_cross_line_calibration",
        "corpus_version": "TLHdig 0.2.0-beta",
        "evidence_policy": POLICY_NAME,
        "seed": SEED,
        "git_commit": ep._git_commit(),
        "language_scope": language_scope.scope,
        "declared_statistics_universe": (
            "dev split, attested-only, non-bin; cross-line spans over adjacent "
            "line pairs; witness support from independent source families "
            "within the same CTH; selector fit on calibration compositions "
            "and applied to held-out evaluation compositions"),
        "is_calibration": True,
        "features_requested": ["token", "damage_state", "line_index_in_doc", "cth"],
        "features_observed": ["token", "damage_state", "line_index_in_doc", "cth"],
    }, MANIFEST_PATH)

    write_report(results, elapsed, cross_config)
    print(f"P2-E9 complete in {elapsed:.1f}s. "
          f"Wrote {RESULT_PATH}, {MANIFEST_PATH}, and {REPORT_PATH}")


if __name__ == "__main__":
    main()
