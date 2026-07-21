#!/usr/bin/env python3
"""
15_p3_report.py -- P3 master acceptance-check report.

Usage:
    python 15_p3_report.py

Aggregates all 6 acceptance checks from P3_BASELINES_SPEC.md. Check 1
(determinism) actually re-runs bm25_sign's Task B pooled test_only
suite a second time and numerically compares it against the saved
results/bm25_sign/metrics.json, rather than assuming determinism.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import eval_harness as eh

RESULTS = Path("results")
P25_OUT = Path("p25_out")


def check_determinism():
    """Re-run bm25_sign's pooled/test_only suite once more and compare
    numerically against the saved metrics.json."""
    with open(RESULTS / "bm25_sign" / "metrics.json", encoding="utf-8") as f:
        saved = json.load(f)
    saved_pooled = saved["task_b"]["index_variants"]["test_only"]["pooled"]

    frags, splits, doc_table = eh.load_fragment_universe()
    join_pairs = eh.build_join_positives(frags)
    join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"])) for p in join_pairs}
    dup_pairs = eh.build_duplicate_positives(frags, join_pair_set)

    test_frags = frags[frags["main_split"] == "test"]
    cand_ids = test_frags["fragment_id"].tolist()
    cand_toks = [eh.add_bigrams(json.loads(s)) for s in test_frags["sign_attested"]]
    frag_lookup = test_frags.set_index("fragment_id")

    join_by_frag, dup_by_frag = {}, {}
    for p in join_pairs:
        if p["test_side"]:
            join_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
            join_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    for p in dup_pairs:
        dup_by_frag.setdefault(p["fragment_id_a"], set()).add(p["fragment_id_b"])
        dup_by_frag.setdefault(p["fragment_id_b"], set()).add(p["fragment_id_a"])
    pooled_pos = {k: set(v) for k, v in join_by_frag.items()}
    for k, v in dup_by_frag.items():
        pooled_pos.setdefault(k, set()).update(v)

    qids = [q for q in pooled_pos if q in frag_lookup.index]
    qtoks = [eh.add_bigrams(json.loads(s)) for s in frag_lookup.loc[qids, "sign_attested"]]
    _, rerun_pooled = eh.run_retrieval(qids, qtoks, cand_ids, cand_toks, pooled_pos, method="bm25")

    keys_to_check = ["n", "recall@1", "recall@5", "recall@10", "recall@100", "mrr"]
    mismatches = []
    for k in keys_to_check:
        a, b = saved_pooled.get(k), rerun_pooled.get(k)
        if isinstance(a, dict):
            if a.get("mean") != b.get("mean") or a.get("ci") != b.get("ci"):
                mismatches.append((k, a, b))
        elif a != b:
            mismatches.append((k, a, b))

    return {"pass": len(mismatches) == 0, "mismatches": mismatches,
            "saved_recall@1": saved_pooled["recall@1"], "rerun_recall@1": rerun_pooled["recall@1"]}


def main():
    det = check_determinism()
    print("Check 1 (determinism):", "PASS" if det["pass"] else "FAIL", det["mismatches"])

    # ---- check 2: test-side positive counts
    frags, splits, doc_table = eh.load_fragment_universe()
    join_pairs = eh.build_join_positives(frags)
    join_pair_set = {frozenset((p["fragment_id_a"], p["fragment_id_b"])) for p in join_pairs}
    dup_pairs = eh.build_duplicate_positives(frags, join_pair_set)
    test_joins = [p for p in join_pairs if p["test_side"]]
    from collections import Counter
    tier_counts = Counter(p["tier"] for p in test_joins)
    tier_jointype = Counter((p["tier"], p["join_type"]) for p in test_joins)

    with open(RESULTS / "bm25_sign" / "metrics.json", encoding="utf-8") as f:
        bm25_sign_metrics = json.load(f)
    task_a_n = bm25_sign_metrics["task_a"]["n"]
    task_a_excl = bm25_sign_metrics["task_a"]["n_excluded_single_witness"]

    # ---- check 3: 2x2 leakage matrix, bm25_sign
    leakage = bm25_sign_metrics["leakage_2x2"]

    # ---- check 4: Tyndall
    with open(RESULTS / "tyndall_replication" / "metrics.json", encoding="utf-8") as f:
        tyndall = json.load(f)

    # ---- check 5: headline table
    summary_path = RESULTS / "p3_summary.json"
    with open(summary_path, encoding="utf-8") as f:
        p3_summary = json.load(f)
    scorer_metrics = {}
    for name in ("bm25_sign", "bm25_lemma", "tfidf_cosine_sign"):
        with open(RESULTS / name / "metrics.json", encoding="utf-8") as f:
            scorer_metrics[name] = json.load(f)

    lines = ["# P3 Master Acceptance Report", "",
             "## Corpus caveat discovered in P3 (documented, not silently patched)", "",
             "28 doc_id values in the frozen splits.parquet are ambiguous: "
             "either literal duplicate files cross-filed under two CTH "
             "folders in the source zip (e.g. `KUB 4.1.xml` exists under "
             "both `CTH 552_XML/` and `CTH 422_XML/`), or two DIFFERENT "
             "files whose `<docID>` text happens to collide (e.g. "
             "`Bo 3964.xml` and the composite `KBo 59.207+.xml` both "
             "report docID \"Bo 3964\"). Per P3's constraint (nothing may "
             "alter frozen corpus/splits/join tiers/bin flags), these are "
             "excluded from the fragment universe in eval_harness.py "
             "rather than silently resolved to one side -- a real "
             "cleanroom risk was averted (some pairs straddled train/"
             "test). Flagged here for a future P2.5-style patch upstream.",
             "",
             "## Check 1 -- harness determinism", "",
             f"**{'PASS' if det['pass'] else 'FAIL'}** -- re-ran bm25_sign's "
             f"pooled/test_only Task B suite a second time and compared "
             f"numerically (not just byte-diff, since JSON key order "
             f"could differ) against the saved metrics.json.",
             f"- saved recall@1: {det['saved_recall@1']}",
             f"- rerun recall@1: {det['rerun_recall@1']}",
             "",
             "## Check 2 -- test-side positive counts", "",
             f"- Join pairs (test-side): {len(test_joins)} / {len(join_pairs)} total",
             "",
             "| tier | join_type | count |", "|---|---|---|"]
    for (tier, jt), cnt in sorted(tier_jointype.items(), key=lambda x: (x[0][0], x[0][1] or "")):
        lines.append(f"| {tier} | {jt} | {cnt} |")
    lines += [f"| **totals** | | A={tier_counts.get('A',0)}, B={tier_counts.get('B',0)}, "
              f"C={tier_counts.get('C',0)} |", "",
              f"- Duplicate pairs (test-side, fragment-level, join-excluded): {len(dup_pairs):,}",
              f"- Task A eligible queries: {task_a_n} (single-witness exclusions: {task_a_excl})",
              "",
              "## Check 3 -- 2x2 leakage matrix (bm25_sign, pooled, test_only)", "",
              "| query render | index render | recall@1 | MRR | n | delta vs ATTESTED/ATTESTED |",
              "|---|---|---|---|---|---|"]
    baseline = leakage["query_attested_index_attested"]["recall@1"]["mean"]
    for combo, agg in leakage.items():
        qr, cr = combo.replace("query_", "").split("_index_")
        r1 = agg["recall@1"]["mean"]
        lines.append(f"| {qr} | {cr} | {r1:.4f} | {agg['mrr']['mean']:.4f} | "
                     f"{agg['n']} | {r1 - baseline:+.4f} |")

    lines += ["", "## Check 4 -- Tyndall replication vs published numbers", "",
              "See `results/tyndall_replication/report.md` for the full "
              "table (fenced, protocol=tyndall2012, never mixed with the "
              "tables above). Headline:", ""]
    for scale in ("approx_scale", "full_scale"):
        s = tyndall["scales"][scale]
        r = s["results"]
        full_v = r.get("MaxEnt_alltoken_full", {}).get("accuracy")
        att_v = r.get("MaxEnt_alltoken_attested", {}).get("accuracy")
        lines.append(f"- **{scale}** ({s['n_compositions']} comps, {s['n_docs']} docs): "
                     f"MaxEnt all-token FULL={full_v:.3f}, ATTESTED={att_v:.3f}, "
                     f"delta={full_v - att_v:+.3f} (published brackets-removed "
                     f"MaxEnt_alltoken={tyndall['published_reference']['brackets_removed']['MaxEnt_alltoken']})")

    lines += ["", "## Check 5 -- headline preliminary table (Task A + Task B tier A)", "",
              "| scorer | task | index | n | recall@1 | CI | MRR |",
              "|---|---|---|---|---|---|---|"]
    for name, m in scorer_metrics.items():
        ta = m["task_a"]
        lines.append(f"| {name} | Task A (LOO) | test-side comps | {ta['n']} | "
                     f"{ta['recall@1']['mean']:.4f} | {ta['recall@1']['ci']} | {ta['mrr']['mean']:.4f} |")
        for variant in ("test_only", "full_distractor"):
            tb = m["task_b"]["index_variants"][variant]["joins_tier_A"]
            lines.append(f"| {name} | Task B tier A (joins) | {variant} | {tb['n']} | "
                         f"{tb['recall@1']['mean']:.4f} | {tb['recall@1']['ci']} | {tb['mrr']['mean']:.4f} |")

    lines += ["", "## Check 6 -- failures spot-read (5 illustrative examples, "
              "bm25_sign, task_b_pooled)", "",
              "1. **KUB 3.44** (query = `\"ŠEŠ dá\"`, 2 tokens) -- true "
              "positive buried at rank 680. **Diagnosis: length failure** "
              "-- a 2-sign query carries almost no discriminating lexical "
              "signal for BM25.",
              "2. **KBo 12.38+::1 / KUB 26.39 / KUB 33.97** -- three "
              "unrelated damaged queries ALL false-top-1 to the same "
              "candidate, **KUB 14.4** (rendering dominated by very "
              "common short syllables: `i da la u x x x ... ku it ki`). "
              "**Diagnosis: formulaic/high-frequency-token collision** -- "
              "a lexically generic document acts as a BM25 \"magnet\" for "
              "many short, damaged, unrelated queries.",
              "3. **KUB 7.58** -> predicted **KUB 7.58 Vs. I**, with "
              "BYTE-IDENTICAL ATTESTED renderings. **Diagnosis: not a "
              "real retrieval failure** -- this is one of the 98 exact-"
              "dedup groups (dedup guard). BM25 correctly found true "
              "duplicate content that isn't registered as a ground-truth "
              "positive pair; this is a genuine candidate for the "
              "expert-verification queue (CLAUDE.md cleanroom rule 5), "
              "not a scorer weakness.",
              "4. **KBo 32.193** (query rendering = empty string -- zero "
              "attested signs). **Diagnosis: degenerate/empty query** -- "
              "ATTESTED-only evaluation's harshest edge case; nothing "
              "for any lexical method to match on.",
              "5. **FHL 158** (query rendering = `\"x x\"`, illegible-"
              "only). **Diagnosis: illegible-only query**, a milder "
              "version of #4 -- tokens exist but carry zero identifying "
              "content.",
              "",
              "## Overall",
              f"**{'ALL CHECKS ADDRESSED' if det['pass'] else 'CHECK 1 FAILED -- investigate before treating P3 as accepted'}**"]

    with open(P25_OUT.parent / "p3_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Done. p3_report.md written.")


if __name__ == "__main__":
    main()
