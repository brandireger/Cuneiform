# P3_BASELINES_SPEC.md — Evaluation Harness + Classical Baselines

Authority: P2/P2.5 accepted outputs; splits FROZEN 2026-07-21 (git
7b010cde). Nothing in P3 may alter corpus.parquet, splits, join
tiers, or bin flags. P3 produces the harness all later phases reuse,
plus the first numbers. Cleanroom rules from CLAUDE.md apply: all
reported evaluation uses ATTESTED rendering unless the metric is the
explicit FULL-vs-ATTESTED leakage ablation.

## Deliverable 1 — `11_eval_harness.py` (build FIRST; everything
depends on it)

A reusable module, not a script: any scorer implementing
`score(query_fragment, candidate_fragment) -> float` (or a
batch/index variant) plugs in and gets the full report matrix.

### Task B — pairwise retrieval (joins + duplicates)
- Queries: every test-side fragment (real-composition docs +
  reconstructed join members whose parent doc is test-side).
- Index (two variants, both reported):
  (a) `test_only`: all test-side fragments except the query.
  (b) `full_distractor`: (a) + all train/dev fragments + discovery
      pool as unlabeled distractors. NOTE in output: discovery pool
      may contain unknown true positives scored as negatives —
      metrics are therefore conservative lower bounds; state this
      in every report that uses (b).
- Positives:
  - JOINS: frozen join_pairs where both members are test-side.
    Report per tier × join_type. Tier A = headline; tier B
    secondary; tier C ONLY via exclusive-content rendering
    (excluding exclusive_untestable), full-reconstruction number
    alongside labeled UPPER BOUND (contaminated).
  - DUPLICATES: same-CTH pairs among test-side real-composition
    docs (the 234,263-pair universe restricted to test side).
  - POOLED: union, plus joins-only and duplicates-only — the
    standing three-way matrix.
- Metrics: recall@{1,5,10,100}, MRR; stratified by fragment length
  band (attested-sign quartiles) and genre_band. Bootstrap 95% CIs
  (resample queries, >=1000 reps) on all headline numbers — test-
  side pair counts are small (expect ~10% of 1,581 joins; tier A
  test-side possibly ~30-60 pairs; NEVER report a small-n number
  without its CI and its n).

### Task A — zero-shot composition assignment (special case of B)
- For each test-side real-composition fragment: rank compositions
  by best-matching OTHER test-side witness (leave-one-out).
  Composition-level recall@{1,5,10}, MRR. This is zero-shot: no
  scorer may have trained on test compositions (guaranteed by
  frozen composition-disjoint split; assert anyway).
- Single-witness test compositions have no LOO evidence: count
  them, exclude from Task A metrics, report the exclusion.

### Renderings & ablation
- Default: ATTESTED queries, ATTESTED index.
- Leakage ablation (run for every scorer, cheap): FULL/FULL,
  FULL/ATTESTED, ATTESTED/FULL, ATTESTED/ATTESTED — the 2x2. The
  delta vs ATTESTED/ATTESTED is the restoration-leakage
  measurement. This matrix is a headline result even at BM25 level.

### Harness outputs
- `results/{scorer_name}/metrics.json` (every cell of the matrix,
  with n and CI), `report.md` (human-readable), and
  `failures.jsonl` (top-20 highest-ranked false positives + 20
  worst-ranked true positives per task, with renderings — error
  analysis fuel for the paper and for P5 design).

## Deliverable 2 — `09_bm25.py` (classical retrieval baselines)

Scorers, each a separate named run through the harness:
1. `bm25_sign`: BM25 over sign unigrams+bigrams. Tokenization:
   hyphen-split syllabic signs; logograms (sGr/aGr content) as
   single tokens; determinatives as tokens; `x` kept as its own
   token; numerals normalized to <NUM>. Document the tokenizer in
   the report — it is reused by P4's sign-level vocabulary.
2. `bm25_lemma`: BM25 over lemma candidates from mrp fields (union
   of candidate lemmas per word; words with no mrp analysis fall
   back to surface). CLEANROOM NOTE, must appear in report:
   mrp annotations are editorial products; the ATTESTED rendering
   already excludes mrp of fully-restored words (P2), but lemma
   features on attested words remain editor-derived — mark
   bm25_lemma as "editor-assisted" in all tables, distinct from
   "artifact-only" bm25_sign. Both are legitimate; the distinction
   must stay visible (project principle: artifacts vs editors).
3. `tfidf_cosine_sign`: TF-IDF cosine, sign tokens — sanity
   triangulation for BM25.
Implementation: rank_bm25 or sklearn (pin versions); exact-dedup
guard (identical rendered strings) reported.

## Deliverable 3 — `10_tyndall.py` (fenced replication)

Comparability experiment using TYNDALL'S split semantics (fragment-
level 10-fold CV WITHIN compositions), clearly fenced from our
frozen splits — labeled `protocol=tyndall2012` in all outputs,
never mixed into harness tables.
- Approximate-scale variant: restrict to compositions with >=2
  witnesses; sample to ~36 compositions / ~389 fragments
  (seeded) approximating his corpus; classifiers: sklearn
  MultinomialNB and LogisticRegression (MaxEnt equivalent —
  document the substitution for MALLET); features: all-token
  counts and ideogram-only counts (his two tokenizations); both
  FULL-ish (restorations kept, his "Brackets Removed" analog) and
  ATTESTED variants — his 0.67 corresponds to restorations-kept;
  the ATTESTED delta retro-quantifies the leakage in the 2012
  result. Handle his protocol's within-fold class coverage
  honestly (folds stratified by composition).
- Full-scale variant: same protocol, all >=2-witness real
  compositions (543-universe subset), reported alongside.
- Output: `results/tyndall_replication/report.md` with direct
  comparison table vs his published 0.55/0.61/0.44/0.51 (plain)
  and 0.64/0.67/0.49/0.54 (brackets-removed) numbers.

## Acceptance checks (`p3_report.md`)

1. Harness determinism: two runs of bm25_sign produce identical
   metrics.json (byte-diff or numeric-exact) — PASS/FAIL.
2. Test-side positive counts stated up front: join pairs per tier ×
   join_type on test side; duplicate pairs test side; Task A
   eligible query count and single-witness exclusions.
3. The 2x2 leakage matrix for bm25_sign, with deltas.
4. Tyndall replication table vs published numbers, both scales,
   with the ATTESTED-variant delta.
5. Headline preliminary table: bm25_sign vs bm25_lemma vs tfidf on
   Task A and Task B (tier A headline), test_only and
   full_distractor, with CIs and n everywhere.
6. failures.jsonl spot-read: 5 illustrative failures quoted in the
   report with one-line diagnoses (formulaic collision? length?
   genre?) — the first error-analysis seeds for P4/P5.

Small artifacts back to the browser session: p3_report.md and each
scorer's report.md + metrics.json. failures.jsonl too (it is
small). No indexes, no models.
