#!/usr/bin/env python3
"""
24b_p4b_report.py -- aggregates p4_out/p4b_b1..b5.json into p4b_report.md
per specs/P4B_DIAGNOSTICS.md's acceptance checklist. Run after
24_p4b_diagnostics.py.

Usage:
    python scripts/24b_p4b_report.py
"""
import json
from pathlib import Path

OUT = Path("p4_out")


def load(name):
    with open(OUT / name, encoding="utf-8") as f:
        return json.load(f)


def main():
    b1 = load("p4b_b1.json")
    b2 = load("p4b_b2.json")
    b3 = load("p4b_b3.json")
    b4 = load("p4b_b4.json")
    b5 = load("p4b_b5.json")

    def r(scale, model, k):
        return b1[scale][model][f"recall@{k}"]

    def fmt(scale, model, k):
        d = r(scale, model, k)
        lo, hi = d["ci_wilson"]
        return f"{d['mean']:.3f} [{lo:.3f},{hi:.3f}] (n={d['n']})"

    lines = [
        "# P4B Report -- Bi-encoder Gate Failure Diagnostics", "",
        "Per specs/P4B_DIAGNOSTICS.md. ANALYSIS ONLY -- zero GPU training hours; "
        "everything re-embeds/re-scores through the already-trained real_only/"
        "line_max checkpoint (the reported-best combo) and existing BM25 "
        "infrastructure. Test side touched by nothing.",
        "",
        "## B1 -- Index-scale behavior", "",
        "Originally-reported numbers' index variant: **test_only** "
        f"(dev-side-only candidates, n={b1['test_only']['n_candidates']}) -- "
        "confirmed by reproducing 0.835/0.571 exactly before extending to "
        f"full_distractor (n={b1['full_distractor']['n_candidates']}, "
        "everything except test side).",
        "",
        "| model | scale | recall@1 | recall@10 | recall@100 |",
        "|---|---|---|---|---|",
        f"| BM25 | test_only | {fmt('test_only','bm25',1)} | {fmt('test_only','bm25',10)} | {fmt('test_only','bm25',100)} |",
        f"| BM25 | full_distractor | {fmt('full_distractor','bm25',1)} | {fmt('full_distractor','bm25',10)} | {fmt('full_distractor','bm25',100)} |",
        f"| dense (mean_pool) | test_only | {fmt('test_only','dense_mean_pool',1)} | {fmt('test_only','dense_mean_pool',10)} | {fmt('test_only','dense_mean_pool',100)} |",
        f"| dense (mean_pool) | full_distractor | {fmt('full_distractor','dense_mean_pool',1)} | {fmt('full_distractor','dense_mean_pool',10)} | {fmt('full_distractor','dense_mean_pool',100)} |",
        f"| dense (line_max, best) | test_only | {fmt('test_only','dense_line_max',1)} | {fmt('test_only','dense_line_max',10)} | {fmt('test_only','dense_line_max',100)} |",
        f"| dense (line_max, best) | full_distractor | {fmt('full_distractor','dense_line_max',1)} | {fmt('full_distractor','dense_line_max',10)} | {fmt('full_distractor','dense_line_max',100)} |",
        "",
        f"**Verdict: the gap WIDENS at realistic scale, it does not close.** BM25 "
        f"recall@10 degrades only modestly (test_only {r('test_only','bm25',10)['mean']:.3f} "
        f"-> full_distractor {r('full_distractor','bm25',10)['mean']:.3f}, "
        f"-{r('test_only','bm25',10)['mean']-r('full_distractor','bm25',10)['mean']:.3f}); "
        f"dense (line_max) collapses much harder "
        f"({r('test_only','dense_line_max',10)['mean']:.3f} -> "
        f"{r('full_distractor','dense_line_max',10)['mean']:.3f}, "
        f"-{r('test_only','dense_line_max',10)['mean']-r('full_distractor','dense_line_max',10)['mean']:.3f}). "
        "This is the OPPOSITE of the pattern Branch H requires (ordering does not "
        "invert; gap does not close). No evidence here that dense retrieval is "
        "'more robust at scale' for this task -- if anything, the reverse: BM25 "
        "is the one that holds up.",
        "",
        "## B2 -- Complementarity & fusion (full_distractor scale)", "",
        f"Hit-set overlap at k=10 (n={b2['hit_set_overlap_at_k10']['n']}): "
        f"both-hit={b2['hit_set_overlap_at_k10']['both_hit']}, "
        f"BM25-only={b2['hit_set_overlap_at_k10']['bm25_only']}, "
        f"**dense-only={b2['hit_set_overlap_at_k10']['dense_only']}**, "
        f"neither={b2['hit_set_overlap_at_k10']['neither']}.",
        "",
        f"- Union recall@10 (oracle upper bound for any fusion): "
        f"**{b2['union_recall_at_10']:.3f}** -- barely above BM25-alone's "
        f"{r('full_distractor','bm25',10)['mean']:.3f}, because dense-only is "
        f"essentially empty ({b2['hit_set_overlap_at_k10']['dense_only']} case "
        "out of 182 queries).",
        f"- RRF fusion (k={b2['rrf_k']}): recall@1={b2['rrf_recall@1']:.3f}, "
        f"**recall@10={b2['rrf_recall@10']:.3f}** -- fusion is WORSE than "
        f"BM25-alone ({r('full_distractor','bm25',10)['mean']:.3f}). Blending in "
        "a much weaker, largely-redundant ranker actively hurts the combined "
        "ranking rather than helping it.",
        "",
        "**Verdict: the bi-encoder is not a complementary channel.** It adds "
        "essentially one recoverable query BM25 missed, at the cost of dragging "
        "the fused ranking down when combined naively.",
        "",
        "## B3 -- BM25 headroom curve", "",
        "| k | test_only | full_distractor |", "|---|---|---|",
    ]
    for k in (10, 20, 50, 100, 200):
        lines.append(f"| {k} | {b3['test_only'][f'recall@{k}']:.3f} | {b3['full_distractor'][f'recall@{k}']:.3f} |")
    lines += [
        "",
        f"Reranking headroom for a P5 built directly over BM25 candidates: "
        f"full_distractor recall@200 = {b3['full_distractor']['recall@200']:.3f} -- "
        "a reranker over BM25's top-~100-200 candidates has a real ceiling to "
        "work with, well above the current dense-retrieval recall@10.",
        "",
        "## B4 -- Failure taxonomy (full_distractor, BM25 misses at k=10)", "",
        f"BM25 hits (n={b4['bm25_hits_at10']['n']}): mean attested-sign count = "
        f"{b4['bm25_hits_at10']['mean_n_attested']:.1f}, mean BM25 score to true "
        f"partner = {b4['bm25_hits_at10']['mean_bm25_score_to_true_partner']:.1f}, "
        f"genre bands = {b4['bm25_hits_at10']['genre_band_dist']}.",
        "",
        f"BM25 misses (n={b4['bm25_misses_at10']['n']}): mean attested-sign count = "
        f"{b4['bm25_misses_at10']['mean_n_attested']:.1f}, mean BM25 score to true "
        f"partner = **{b4['bm25_misses_at10']['mean_bm25_score_to_true_partner']:.1f}** "
        f"(vs {b4['bm25_hits_at10']['mean_bm25_score_to_true_partner']:.1f} for hits "
        f"-- much lower), genre bands = {b4['bm25_misses_at10']['genre_band_dist']}.",
        "",
        f"**Cross-referenced to B2's dense-only cell: of these "
        f"{b4['n_total_misses']} genuinely low-lexical-overlap misses -- exactly "
        f"the cases dense retrieval theoretically exists to catch -- the "
        f"bi-encoder recovers only {b4['n_misses_recovered_by_dense_only']} "
        f"({100*b4['n_misses_recovered_by_dense_only']/b4['n_total_misses']:.1f}%).** "
        "The misses are not shorter/sparser fragments (mean attested-sign count "
        "is actually HIGHER for misses than hits) -- they are lower-overlap "
        "cases the model was specifically supposed to help with, and doesn't.",
        "",
        "## B5 -- Synthetic autopsy", "",
        f"Correlation of model similarity vs. lexical overlap (sign-level "
        f"Jaccard), fixed samples: synthetic pairs (n={b5['n_synthetic_pairs']}, "
        f"from fracture_dev_diagnostic.jsonl) = **{b5['corr_model_vs_lexical_synthetic']:.3f}**; "
        f"real dev joins (n={b5['n_real_pairs']}) = "
        f"**{b5['corr_model_vs_lexical_real']:.3f}**.",
        "",
        "**Hypothesis CONFIRMED**: the two correlations are nearly identical "
        "(~0.56 in both cases), meaning the model's learned similarity signal "
        "is substantially just a noisier copy of plain lexical overlap, on both "
        "synthetic and real data -- not an independent seam-local-continuation "
        "signal. This is consistent with real_only winning the ablation (removing "
        "synthetic training data helps a little), but note: real_only's own "
        "real-dev-join recall@10 (0.571 best case) is STILL 0.264 below BM25 -- "
        "i.e. the 'no synthetic contamination' endpoint has ALREADY been tried "
        "via the ablation grid, and it does not close the gap. This is not a "
        "narrow, targeted bug (like hard-negative mining specifically punishing "
        "lexical matches -- ruled less likely, since model/lexical correlation "
        "is POSITIVE and substantial, not negative or near-zero); it reads as a "
        "more fundamental representation-learning shortfall at this data scale.",
        "",
        "## Branch recommendation", "",
        "**Recommend BRANCH R (rerank-only, drop the bi-encoder from the "
        "cascade).** Driving numbers: (1) B1 -- the BM25-vs-dense gap WIDENS at "
        f"full-distractor scale ({r('test_only','bm25',10)['mean']-r('test_only','dense_line_max',10)['mean']:.3f} "
        f"-> {r('full_distractor','bm25',10)['mean']-r('full_distractor','dense_line_max',10)['mean']:.3f}), "
        "the opposite of what Branch H requires; (2) B2 -- dense-only hits are "
        f"essentially zero ({b2['hit_set_overlap_at_k10']['dense_only']}/182) and "
        "RRF fusion actively underperforms BM25-alone; (3) B5 -- the one "
        "candidate fix Branch T would require (retrain without synthetic "
        "contamination) has effectively already been tried via the real_only "
        "ablation arm and still leaves a 0.264 gap. Per the decision tree's own "
        "pre-registered tie-break (\"ambiguity between H and R resolves toward "
        "R... unless H's evidence is clear\"), and H's evidence here points the "
        "other way, R is the recommendation. Branch selection remains a joint "
        "call, not made here.",
    ]

    with open("p4b_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Done. p4b_report.md written.")


if __name__ == "__main__":
    main()
