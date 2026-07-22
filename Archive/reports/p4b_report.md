# P4B Report -- Bi-encoder Gate Failure Diagnostics

Per specs/P4B_DIAGNOSTICS.md. ANALYSIS ONLY -- zero GPU training hours; everything re-embeds/re-scores through the already-trained real_only/line_max checkpoint (the reported-best combo) and existing BM25 infrastructure. Test side touched by nothing.

## B1 -- Index-scale behavior

Originally-reported numbers' index variant: **test_only** (dev-side-only candidates, n=883) -- confirmed by reproducing 0.835/0.571 exactly before extending to full_distractor (n=21896, everything except test side).

| model | scale | recall@1 | recall@10 | recall@100 |
|---|---|---|---|---|
| BM25 | test_only | 0.709 [0.639,0.770] (n=182) | 0.835 [0.774,0.882] (n=182) | 0.912 [0.862,0.945] (n=182) |
| BM25 | full_distractor | 0.676 [0.605,0.740] (n=182) | 0.808 [0.744,0.858] (n=182) | 0.885 [0.830,0.923] (n=182) |
| dense (mean_pool) | test_only | 0.302 [0.240,0.372] (n=182) | 0.522 [0.450,0.593] (n=182) | 0.791 [0.726,0.844] (n=182) |
| dense (mean_pool) | full_distractor | 0.187 [0.137,0.250] (n=182) | 0.330 [0.266,0.401] (n=182) | 0.495 [0.423,0.567] (n=182) |
| dense (line_max, best) | test_only | 0.363 [0.296,0.435] (n=182) | 0.571 [0.499,0.641] (n=182) | 0.830 [0.768,0.877] (n=182) |
| dense (line_max, best) | full_distractor | 0.236 [0.180,0.303] (n=182) | 0.396 [0.327,0.468] (n=182) | 0.549 [0.477,0.620] (n=182) |

**Verdict: the gap WIDENS at realistic scale, it does not close.** BM25 recall@10 degrades only modestly (test_only 0.835 -> full_distractor 0.808, -0.027); dense (line_max) collapses much harder (0.571 -> 0.396, -0.176). This is the OPPOSITE of the pattern Branch H requires (ordering does not invert; gap does not close). No evidence here that dense retrieval is 'more robust at scale' for this task -- if anything, the reverse: BM25 is the one that holds up.

## B2 -- Complementarity & fusion (full_distractor scale)

Hit-set overlap at k=10 (n=182): both-hit=71, BM25-only=76, **dense-only=1**, neither=34.

- Union recall@10 (oracle upper bound for any fusion): **0.813** -- barely above BM25-alone's 0.808, because dense-only is essentially empty (1 case out of 182 queries).
- RRF fusion (k=60): recall@1=0.462, **recall@10=0.769** -- fusion is WORSE than BM25-alone (0.808). Blending in a much weaker, largely-redundant ranker actively hurts the combined ranking rather than helping it.

**Verdict: the bi-encoder is not a complementary channel.** It adds essentially one recoverable query BM25 missed, at the cost of dragging the fused ranking down when combined naively.

## B3 -- BM25 headroom curve

| k | test_only | full_distractor |
|---|---|---|
| 10 | 0.835 | 0.808 |
| 20 | 0.874 | 0.819 |
| 50 | 0.901 | 0.846 |
| 100 | 0.912 | 0.885 |
| 200 | 0.934 | 0.896 |

Reranking headroom for a P5 built directly over BM25 candidates: full_distractor recall@200 = 0.896 -- a reranker over BM25's top-~100-200 candidates has a real ceiling to work with, well above the current dense-retrieval recall@10.

## B4 -- Failure taxonomy (full_distractor, BM25 misses at k=10)

BM25 hits (n=147): mean attested-sign count = 163.7, mean BM25 score to true partner = 94.2, genre bands = {'0': 24, '200': 5, '300': 3, '600': 111, '700': 4}.

BM25 misses (n=35): mean attested-sign count = 194.9, mean BM25 score to true partner = **36.5** (vs 94.2 for hits -- much lower), genre bands = {'0': 7, '200': 1, '600': 27}.

**Cross-referenced to B2's dense-only cell: of these 35 genuinely low-lexical-overlap misses -- exactly the cases dense retrieval theoretically exists to catch -- the bi-encoder recovers only 1 (2.9%).** The misses are not shorter/sparser fragments (mean attested-sign count is actually HIGHER for misses than hits) -- they are lower-overlap cases the model was specifically supposed to help with, and doesn't.

## B5 -- Synthetic autopsy

Correlation of model similarity vs. lexical overlap (sign-level Jaccard), fixed samples: synthetic pairs (n=2000, from fracture_dev_diagnostic.jsonl) = **0.556**; real dev joins (n=182) = **0.560**.

**Hypothesis CONFIRMED**: the two correlations are nearly identical (~0.56 in both cases), meaning the model's learned similarity signal is substantially just a noisier copy of plain lexical overlap, on both synthetic and real data -- not an independent seam-local-continuation signal. This is consistent with real_only winning the ablation (removing synthetic training data helps a little), but note: real_only's own real-dev-join recall@10 (0.571 best case) is STILL 0.264 below BM25 -- i.e. the 'no synthetic contamination' endpoint has ALREADY been tried via the ablation grid, and it does not close the gap. This is not a narrow, targeted bug (like hard-negative mining specifically punishing lexical matches -- ruled less likely, since model/lexical correlation is POSITIVE and substantial, not negative or near-zero); it reads as a more fundamental representation-learning shortfall at this data scale.

## Branch recommendation

**Recommend BRANCH R (rerank-only, drop the bi-encoder from the cascade).** Driving numbers: (1) B1 -- the BM25-vs-dense gap WIDENS at full-distractor scale (0.264 -> 0.412), the opposite of what Branch H requires; (2) B2 -- dense-only hits are essentially zero (1/182) and RRF fusion actively underperforms BM25-alone; (3) B5 -- the one candidate fix Branch T would require (retrain without synthetic contamination) has effectively already been tried via the real_only ablation arm and still leaves a 0.264 gap. Per the decision tree's own pre-registered tie-break ("ambiguity between H and R resolves toward R... unless H's evidence is clear"), and H's evidence here points the other way, R is the recommendation. Branch selection remains a joint call, not made here.