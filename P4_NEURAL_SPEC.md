# P4_NEURAL_SPEC.md — Tokenizer, Fracture Engine, Pre-training, Bi-encoder

Authority: P3 accepted (2026-07). Splits remain FROZEN (git 7b010cde).
Number to beat: tier-A joins recall@1 = 0.059 (bm25_sign, test_only),
0.0 (full_distractor). Duplicates are already near-solved by BM25;
P4's entire purpose is the join/continuation problem plus robustness
at realistic index scale. Engineering law applies to every training
script: checkpoint at natural units, atomic writes, resumable,
detached from the session (nohup/tmux), seeds + git hash + corpus
version logged in every artifact. All model training uses TRAIN side
only; dev side is for model selection; the test side is touched by
NOTHING in P4 (final test numbers happen once, in P6).

## H1 — Harness patch (do FIRST, then re-emit P3 tables)

- docID-family normalization: strip side/column/segment suffixes
  ("Vs. I", "Rs.", "+ obv." variants, "::N" member suffixes kept
  separate) to a family key; same-family candidates are EXCLUDED
  from ranking (neither positive nor negative). Log every exclusion.
- Exact-dedup groups (98): same treatment — identical-rendering
  candidates from the same family excluded; identical renderings
  across genuinely different objects stay (they are real formulaic
  collisions, part of the task).
- Re-run P3 scorers through the patched harness; re-emit tables as
  `results_p3_patched/`. Report deltas in `h1_patch_report.md`
  (expect small improvements; the honest bookkeeping matters more
  than the size).

## D12 — `12_tokenizer.py` — sign-level vocabulary

- Reuse the P3 bm25_sign tokenization exactly (documented there):
  hyphen-split syllabic signs lowercase; logograms (sGr/aGr) as
  single tokens; determinatives as tokens; `x` its own token;
  numerals -> <NUM>. Add specials: <PAD> <UNK> <MASK> <GAP>
  (unknown-length lost span), <LINE> (line break), <PAR> (parsep,
  scribe-drawn ruling), <EDGE_L> <EDGE_R> <EDGE_T> <EDGE_B>
  (fragment boundary markers, from edges.parquet states).
- Vocabulary from TRAIN-side + discovery-pool ATTESTED text only;
  min_df=2; report vocab size (expect low thousands), OOV rate on
  dev.
- Emit `tokenizer.json` + `tokenizer_report.md` (top tokens, size,
  OOV, examples of encoded lines round-tripped).

## D13 — `13_fracture.py` — the fracture engine

Purpose: manufacture labeled join pairs and self-supervised views by
breaking well-preserved fragments with damage sampled from the
corpus's own measured statistics. Editors nowhere in the loop.

- Calibration inputs (computed from TRAIN side): del-span length
  distribution; per-line left/right edge-loss profiles; top/bottom
  loss rates (edges.parquet); illegible-x rate; line-count
  distribution of real fragments; real seam geometry stats from
  tier stats (share of vertical vs horizontal, gap sizes where
  known). Emit `fracture_calibration.json` with all fitted
  distributions + histograms in the report.
- Cut operators (each records its parameters per generated pair):
  1. VERTICAL cut: split at a sampled line boundary; optionally
     delete a sampled-width band of whole lines at the seam
     (gap-join simulation).
  2. HORIZONTAL cut: choose a column offset path (sampled jitter
     around a mean offset); left member keeps signs before the
     path per line, right member after; optionally erode a
     sampled number of signs at the seam per line (crumb loss).
  3. EROSION pass (applied to every synthetic member): additional
     random edge damage + x-substitution at calibrated rates, so
     synthetic members match real fragments' damage statistics.
- Eligibility: TRAIN-side fragments (and discovery pool for
  self-supervised views only) with >= 8 lines and >= 60 attested
  signs; report eligible counts.
- Outputs: generator (seeded, streaming — do NOT materialize
  millions of pairs to disk; materialize a fixed dev-diagnostic
  set of 2,000 pairs for inspection) + `fracture_report.md` with
  10 rendered examples (before/after, both members, seam
  parameters) and a distribution-match table: synthetic member
  stats vs real fragment stats (line counts, attested-sign counts,
  edge-loss rates). Acceptance: synthetic marginals within
  reasonable range of real marginals, shown not asserted.
- Self-supervised views: two independent damage draws over the
  same source fragment = positive view pair (SimCLR-style);
  discovery pool ALLOWED here (no cross-fragment relations
  asserted). Never emit synthetic anything to test-side files.

## D14 — `14_pretrain.py` — encoder pre-training (single GPU)

- Architecture: from-scratch transformer encoder, sign-level vocab.
  Start small: ~6 layers, d_model 384, 6 heads, seq len 512 signs
  (covers the vast majority of fragments; report truncation rate).
  Config file, not hardcoded.
- Objectives (joint, weighted; weights in config, defaults 1.0):
  1. Masked span-infilling: T5-style variable-length span
     corruption using <MASK>/<GAP>; span lengths sampled from the
     calibrated del-span distribution (clay-realistic masking —
     cite-able difference from uniform Ithaca masking).
  2. Boundary-validity head: at <LINE> and <PAR> positions,
     binary head predicts whether the following unit is the true
     continuation or a shuffled/foreign impostor. Negatives
     curriculum: in-document shuffle -> cross-document same
     genre_band -> random. RULE: never draw negatives from other
     witnesses of the same composition (protects duplicate
     signal). Unit granularity: line-level and paragraph-level
     variants both trained (flagged tokens distinguish them).
- Data: TRAIN side ATTESTED rendering (FULL rendering ablation
  deferred to P6; do not train on FULL by default) + discovery
  pool ATTESTED. Dev-side loss curves for early stopping.
- Budget: target <= 24h wall-clock on the local GPU for the base
  run; checkpoint every N steps (config); log to
  `runs/pretrain_{tag}/` with loss curves CSV.
- Report: `pretrain_report.md` — final losses, span-infilling
  exact-match on dev masked spans (per span-length band),
  boundary-head AUC on dev (per negative type — the curriculum's
  hard negatives are the number that matters), 10 qualitative
  infilling examples (masked line -> model proposal vs editor's
  restoration where one exists; agreement rate on dev
  restoration spans = the restoration-agreement metric, reported
  but NEVER used as a training target on dev).

## D15 — `15_biencoder.py` — contrastive retrieval model

- Initialize from D14 encoder; mean-pool (or CLS) fragment
  embedding; train with InfoNCE.
- Positives, mixed per batch (ratios in config, ablatable):
  (a) fracture-engine synthetic join pairs (vertical + horizontal
  + gap variants); (b) self-supervised damage views; (c) REAL
  duplicate pairs from TRAIN-side same-CTH universe (the 234k
  universe restricted to train); (d) real TRAIN-side join pairs
  (few; oversampled modestly).
- Negatives: in-batch + hard negatives mined from BM25 top-ranked
  non-positives (BM25's confusions are exactly the formulaic
  collisions the encoder must learn to reject).
- Dev gates (model selection ONLY on dev):
  - dev duplicates recall@1 (must not regress far below BM25's
    dev number — report BM25 dev alongside);
  - dev-side real join pairs recall@k (the few dev joins, with
    CIs — small n, honest reporting);
  - synthetic held-out joins recall@k (large n, the smooth
    optimization signal; report the synthetic-vs-real gap
    explicitly — an expected and interpretable gap, per
    CLAUDE.md's findable-join bias note).
- Line/passage-level scoring variant: embed per-line windows,
  aggregate max-over-line-pairs — run as ablation against
  whole-fragment embeddings (spec'd since the matrix-model
  design; joins are local).
- Report: `biencoder_report.md` with the ablation grid (positive-
  mix ratios x pooling variant), dev tables vs BM25, and 10
  qualitative retrievals (5 successes, 5 failures) for dev joins.

## Explicitly deferred to P5/P6 (do not build yet)

Edge-continuation PMI scoring via span-infilling; cross-encoder /
boundary-head reranking cascade; full-distractor final runs;
test-side anything; discovery-pool assignment ranking (P7).

## Acceptance checks (`p4_report.md`)

1. H1 patch deltas reported; patched P3 tables emitted.
2. Tokenizer: vocab size, dev OOV < 1%, round-trip fidelity
   examples.
3. Fracture engine: distribution-match table PASS (synthetic ~
   real marginals), 10 inspected examples included.
4. Pre-training: boundary-head dev AUC by negative type;
   restoration-agreement rate on dev spans; loss curves attached.
5. Bi-encoder: dev tier-proxy table — synthetic joins, real dev
   joins, dev duplicates — each vs BM25 dev, with n and CIs.
   The pre-registered success criterion for proceeding to P5:
   real dev-join recall@10 meaningfully above BM25's dev-join
   recall@10 (state both numbers; judgment call documented, made
   jointly with the architect session, not silently).
6. All runs resumable-verified once (kill + resume = identical
   metrics on a small config).

Small artifacts back: p4_report.md, h1_patch_report.md,
tokenizer_report.md, fracture_report.md (with examples),
pretrain_report.md, biencoder_report.md, fracture_calibration.json.
No checkpoints, no parquet.
