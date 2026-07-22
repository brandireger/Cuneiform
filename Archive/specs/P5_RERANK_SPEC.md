# P5_RERANK_SPEC.md — Branch R: retrieve-deep + seam-local rerank

Authority: CLAUDE.md + P4_NEURAL_SPEC.md + P4B_DIAGNOSTICS.md.
BRANCH R RATIFIED jointly (Ixca + architect session) 2026-07-22 on
p4b_report.md: the bi-encoder is DROPPED from the cascade (B1 gap
widens at scale 0.264 -> 0.412; B2 dense-only = 1/182, RRF fusion
underperforms BM25-alone; B5 rules out a named fixable cause —
model similarity is a noisier copy of lexical overlap, r~0.56, and
the real_only arm already tested the only candidate fix). D15 is
written up as a clean negative result (paper + model card), not
retrained. D14 (encoder, boundary-validity head, span-infilling)
remains a live asset and is the core of P5.

Splits FROZEN (git 7b010cde). Dev for model selection; test
touched by NOTHING (P6 only). Engineering law applies: checkpoint
at natural units, atomic writes, resumable, detached, seeds + git
hash + corpus version in every artifact. All learned components
train on TRAIN side only.

## P5.0 — Stratification preliminaries (analysis-only; run FIRST;
## gates the rest of this spec's gate definitions)

1. Tier-stratify the 182 dev joins (tier A / B / C-exclusive) and
   re-emit P4B's B1 and B3 tables with per-tier rows (both index
   scales, n + CIs per cell — cells will be small; report them
   honestly, no pooling to hide it).
2. HARD SET definition (pre-registered here, before numbers):
   dev joins whose BM25 score to the true partner falls in the
   bottom quartile of the 182 (i.e. the B4 miss-profile core,
   defined by a fixed corpus statistic rather than by hit/miss
   at some k, so it cannot drift with the retriever). Emit the
   hard-set membership list to `p5_hard_set.json` — frozen for
   the remainder of P5/P6.
3. CEILING measurement: fraction of (a) all dev joins, (b) hard
   set, (c) each tier, whose true partner appears in BM25
   full-distractor top-200. This is the reranker's recall
   ceiling; every later table restates it alongside results.
   If the hard-set ceiling is very low (< ~0.5), flag before
   building D17/D18 — reranking cannot fix retrieval, and the
   seam-aware retrieval ablation (D16b) gets promoted from
   ablation to requirement.

## D16 — `21_retrieve.py` — candidate generation

- BM25_sign, full_distractor universe, top-k=200 per query
  (headroom: recall@200 = 0.896). H1 same-family exclusions
  apply. Emit per-query candidate lists once, cached, reused by
  all rerankers (identical candidates for every scorer — no
  scorer-specific retrieval).
- D16b — SEAM-AWARE LEXICAL ABLATION: a second BM25 index over
  EDGE WINDOWS only (first N and last N lines per fragment;
  N in {3, 5}, config) and, per query-candidate pair, the max
  edge-window-to-edge-window score. Report: does
  union(whole-fragment top-200, edge-window top-200) raise the
  hard-set ceiling? If yes at meaningful size, the union becomes
  the P5 candidate set (documented decision, architect+Ixca).

## D17 — `22_seam_scorer.py` — boundary-head reranking

- For each (query, candidate) pair: construct seam sequences at
  candidate placements and score with D14's boundary-validity
  head (line-level variant primary; paragraph-level as ablation).
- OFFSET SEARCH is the point (joins are local; line_max beat
  mean-pool): score over candidate line-offsets (vertical seams:
  query-bottom to candidate-top and the reverse; horizontal
  handling deferred to the matrix model's column-path variant if
  time permits — flag, don't improvise). Aggregate per pair:
  max over offsets of the mean over aligned line-pairs at that
  offset; ALSO emit the argmax offset (this is the demo's
  placement, and P7's assignment evidence).
- Seq construction: attested rendering only; <EDGE_*> markers per
  D12; truncate per D14's 512 budget; report truncation rate on
  seam sequences (should be tiny — seams are local by design).
- No fine-tuning in the base run: D17 scores with the FROZEN D14
  head first (zero training risk, establishes the floor). D17b
  (optional, only if the frozen floor shows signal): fine-tune
  the boundary head on fracture-engine seam pairs REBUILT to be
  seam-local (short windows around the cut, not whole-fragment
  views — this is the corrected use of the fracture engine per
  B5's autopsy: synthetic data for seam objectives, never for
  global-similarity objectives). One round, time-boxed <= 12h
  GPU.

## D18 — `23_edge_continuation.py` — short-horizon infilling score

- PMI-style continuation lift at the seam via D14 span-infilling:
  mask the first H signs of the candidate's seam-adjacent line,
  score the model's probability of the candidate's actual signs
  given the query context vs given a null context; H <= 5 HARD
  CAP (D14 measured collapse at 6+; do not spend compute past
  the measured horizon). Report per-H results (H in {1,3,5}).

## D19 — `24_cascade.py` — combination & gates

- Features per pair: BM25 whole-fragment score, edge-window
  score (D16b), boundary-head seam score + argmax-offset
  agreement count (D17), edge-continuation lift (D18).
- Combiner: ONE simple monotone combiner, pre-committed: logistic
  regression over the listed features, trained on TRAIN-side
  real joins + seam-local synthetic pairs, NEVER fit on dev.
  Dev is used once per ablation row for selection, per spec.
  No combiner-architecture search; no per-tier combiners.
- Ablation grid (each row = dev tables at full_distractor):
  BM25-alone (baseline row, restated) / +D17 frozen / +D17b (if
  built) / +D18 / full cascade / full cascade over D16b-union
  candidates (if promoted).

### Pre-registered gates (all at full_distractor, dev)

- G1 (primary): cascade recall@1 AND recall@10 on all 182 dev
  joins meaningfully above BM25-alone (0.676 / 0.808), CIs
  reported. "Meaningfully" = the joint-call standard from P4,
  judged against CIs, decided with the architect session — not
  a point-estimate whisker.
- G2 (the real fight): cascade recall@10 on the HARD SET above
  BM25-alone's hard-set recall@10, with the P5.0 ceiling
  restated in the same table row. G1 without G2 = polishing the
  easy 80% — reported as such, not celebrated.
- G3 (per-tier honesty): per-tier tables emitted for every
  ablation row (small n, CIs, no pooling); tier-A row explicitly
  discussed even if n makes it indicative only.
- G4 (no-regression): dev duplicates recall@1 not meaningfully
  below BM25's (duplicates remain BM25's win; the cascade must
  not break what works).
- Proceed-to-P6 rule: G1 + G4 required; G2 strongly preferred —
  if G1/G4 pass but G2 fails, P6 MAY proceed with the paper
  reframed accordingly (contribution = ranking quality on
  moderate-overlap joins; hard-core continuation stated as open),
  joint call, documented. If G1 fails, stop: architect check-in
  before any further build.

## Consequential edits elsewhere (small, do now)

- Demo (DM track): retire the "Learned similarity" score column;
  "Edge fit — pending P5" remains and becomes D17/D18-backed on
  G1 pass. Model card gains the D15 negative result, one
  paragraph, plain language, with the B1/B2 numbers.
- data_card_notes.md gains the third known-limitations line
  (per the 2026-07-22 review): "The training corpus included 28
  ambiguous-duplicate documents with merged token content;
  evaluation excluded them; effect on trained models negligible
  but nonzero." (DM1 export-time exclusion of the 28 doc_ids
  already tracked from dm0_audit_report.md.)
- Paper notes: the B1 scale-degradation finding (dense degrades
  FASTER than lexical at realistic index scale on a formulaic
  corpus) is a headline negative result — keep the 2x2x3 table.

## Explicitly deferred

P6 (final test runs, once, after P5 gates); P7 (discovery-pool
assignment using cascade scores + argmax offsets); horizontal
column-path offset search (flag if vertical-only proves
limiting); any new pre-training.

## Acceptance checks (`p5_report.md`)

1. P5.0 per-tier B1/B3 tables; hard-set list frozen and counted;
   ceilings for all/hard/per-tier stated.
2. D16 candidate cache emitted once, hash-stamped; D16b verdict
   (ceiling delta) with the promotion decision recorded.
3. D17 frozen-head floor vs D17b (if built), per-tier; argmax
   offsets emitted for the demo/P7.
4. D18 per-H table; confirmation no H > 5 was run.
5. D19 full ablation grid; G1–G4 verdicts each stated PASS/FAIL
   with numbers and CIs; proceed-to-P6 recommendation (Code
   Claude recommends, selection reserved for the joint call).
6. Resumability: any component that trains (D17b, combiner)
   kill+resume verified per the D14 standard.

Small artifacts back: p5_report.md, p5_hard_set.json,
per-deliverable reports as usual. No checkpoints, no parquet.
