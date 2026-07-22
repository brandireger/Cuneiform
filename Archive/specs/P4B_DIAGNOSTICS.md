# P4B_DIAGNOSTICS.md — Bi-encoder gate failure: diagnostics & pre-registered decision tree

Authority: follows P4_NEURAL_SPEC.md. Ratified jointly
(Ixca + architect session) 2026-07-22, on review of p4_report.md.

## Standing facts (do not relitigate)

The P4 pre-registered success criterion was NOT met: best
bi-encoder combo (real_only / line_max) real dev-join
recall@10 = 0.571 vs BM25 dev = 0.835. Everything below is a
DOCUMENTED DEVIATION PROCESS, not a reinterpretation of that
gate. This file is the written record.

Engineering law applies. ANALYSIS ONLY — zero GPU training hours,
all computations from existing run artifacts, checkpoints, and
the frozen dev split. Test side touched by NOTHING. Seeds + git
hash + corpus version in every artifact.

## B1 — Index-scale behavior (highest information value; run first)

- State explicitly which index variant produced the reported
  0.835 / 0.571 dev numbers.
- Re-run the SAME dev-join comparison (BM25 and best bi-encoder,
  identical candidate universes) at BOTH index variants:
  small/test_only-style AND full_distractor. Report recall@1 /
  @10 / @100 for each model at each scale, with n and Wilson CIs.
- The question on trial: P4's premise was robustness at realistic
  scale (BM25 test tier-A = 0.0 at full distractor). If the
  model ordering inverts or converges at full-distractor scale,
  the dev gate was measured on BM25's home turf and the verdict
  changes. If BM25 stays ahead at both scales, that is equally
  decisive in the other direction. Either way: measured, not
  argued.

## B2 — Complementarity & fusion

- Hit-set overlap on dev joins at k=10: both-hit / BM25-only /
  dense-only / neither (counts, not just rates).
- Union recall@10 (oracle upper bound for any fusion).
- Reciprocal-rank fusion (standard RRF, k=60 default, note the
  constant) over the two ranked lists: recall@1 / @10. One
  fusion method, no fusion-hyperparameter search (that would be
  gate-shopping).

## B3 — BM25 headroom curve

- BM25 dev-join recall@k for k in {10, 20, 50, 100, 200}, both
  index variants. This measures reranking headroom for a P5
  built directly over BM25 candidates: the ceiling any reranker
  inherits.

## B4 — Failure taxonomy

- Characterize the dev joins BM25 misses at k=10 (full-distractor
  variant): lexical-overlap quantile vs hit cases, attested-sign
  counts, damage rates, tier, genre band. One table, one
  paragraph: are the misses the low-overlap cases dense retrieval
  theoretically exists to catch — and does the bi-encoder in fact
  catch them (cross-reference B2's dense-only cell)?

## B5 — Synthetic autopsy

- On mixed-positive runs: correlate model similarity of
  fracture-engine synthetic pairs with plain lexical overlap
  (sign-level Jaccard or BM25 score) on a fixed sample (n >= 2k
  from the dev-diagnostic set). Report the correlation alongside
  the same correlation for real dev joins.
- Hypothesis on trial: synthetic positives taught global topical
  similarity (a worse copy of lexical overlap) rather than
  seam-local continuation — consistent with real_only winning
  the ablation. Confirmed/rejected in one paragraph.

## Pre-registered decision tree (set BEFORE B1–B5 numbers exist)

- BRANCH H (hybrid): if B1 shows the bi-encoder more robust at
  full-distractor scale (ordering inverts or gap closes
  substantially at @10/@100), OR B2 shows RRF fusion meaningfully
  above BM25-alone at the same scale -> the bi-encoder is kept as
  a COMPLEMENTARY candidate channel (BM25 union dense). Proceed
  to P5. New pre-registered gate: the full cascade must beat
  BM25-alone on dev joins at BOTH index scales (recall@10)
  before P6.
- BRANCH R (rerank-only): if the bi-encoder adds nothing at any
  scale (B1 ordering stands, B2 dense-only cell ~empty, fusion
  <= BM25) -> DROP the bi-encoder from the cascade. P5 = BM25
  retrieve-deep (k chosen from B3's curve) + rerank via D14's
  boundary-validity head and SHORT-HORIZON edge-continuation
  (D14 span-infilling collapses beyond length ~5; P5 design must
  respect that measured bound). D15 is written up as a clean
  negative result (BEIR-consistent: dense retrieval underperforms
  lexical in low-supervision, exact-match-heavy domains) in the
  paper and model card.
- BRANCH T (one retrain): ONLY if B4/B5 name a specific, fixable
  cause (e.g. BM25-top hard negatives punishing lexical overlap
  itself; synthetic positives dominating the loss) -> ONE
  time-boxed D15 retraining round implementing exactly the named
  fix (candidates: hard-negative ratio/mining-depth change;
  synthetic-pretrain -> real_only-finetune curriculum). Same
  gate as P4 originally set. One round. If it fails, fall to
  BRANCH R without further rounds.
- Branch selection is a joint call (Ixca + architect) made on the
  B1–B5 report; Code Claude recommends but does not decide.
  Ambiguity between H and R resolves toward R (the cheaper,
  BM25-anchored architecture) unless H's evidence is clear at
  full-distractor scale — pre-registered to prevent optimism
  bias.

## Demo interaction (informational)

The demo ships on BM25 regardless of branch; "Learned similarity
— pending P4" copy remains accurate until branch selection. On
BRANCH R, the score column is retired and the D15 negative
result enters the model card instead.

## Acceptance (p4b_report.md)

1. B1 table: 2 models x 2 scales x {r@1, r@10, r@100}, n + CIs;
   the originally-reported numbers' index variant identified.
2. B2 overlap counts, union, RRF results (constant stated).
3. B3 curve, both scales.
4. B4 table + paragraph, cross-referenced to B2.
5. B5 correlations + verdict paragraph.
6. A one-paragraph BRANCH RECOMMENDATION with the two or three
   numbers that drive it — recommendation only; selection
   reserved.

Small artifacts back: p4b_report.md only. No checkpoints, no
parquet, no new training runs.
