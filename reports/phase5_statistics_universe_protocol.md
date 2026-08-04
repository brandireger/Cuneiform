# Statistics-universe and full-distractor control — PROTOCOL

**Status: PRE-REGISTERED 2026-08-04, committed before the run.**
**Dev queries only; test is never loaded. Training-free; no gradients.**

Executes step 1 of the required sequence in
`reports/phase5_classical_control_review.md` ("Required sequence before P6"),
which is also self-doubt 6.1 and 6.2 of
`reports/phase5_classical_control_handoff.md`.

## 1. The question

Every arm in the Phase 5 classical-control line fits its corpus statistics —
BM25 IDF and average document length, and the TF-IDF vocabularies and IDF —
on the **876 dev fragments that are also the candidate index**. `CLAUDE.md`
("Engineering standards") requires corpus statistics to be fit over the
declared universe for the phase, "never over query-derived subsets". The
reported deltas may therefore be inflated, and by an unknown amount, because
n-gram vocabularies are far larger and sparser than unigram vocabularies and
may benefit differently from a small fitting set than BM25 does.

Two distinct threats are bundled in that setup, and this protocol separates
them rather than testing their sum:

- **T1, the statistics universe.** IDF and avgdl estimated on 876 documents.
- **T2, the distractor pool.** A query competes against 876 candidate
  fragments drawn from roughly 53 compositions, not against the corpus.

## 2. Design — three universes, one fixed arm set

The query set is **identical in all three universes** (dev fragments, real
compositions only, ≥4 content tokens — `phase5_ladder_screen.load_dev_fragments`,
imported and not copied), so every comparison is paired per query.

| universe | statistics fit over | candidate index | isolates |
|---|---|---|---|
| `U1_dev_fit_dev_index` | dev fragments | dev fragments | historical reproduction |
| `U2_full_fit_dev_index` | full non-test labeled universe | dev fragments | **T1** |
| `U3_full_fit_full_index` | full non-test labeled universe | full non-test labeled universe | **T1 + T2** |

The **declared statistics universe** for U2 and U3 is the labeled non-test
universe: fragments with `main_split ∈ {train, dev}`. Bin/catch-all documents
carry `main_split='discovery'` and are therefore already excluded, keeping the
labeled evaluation index and the unlabeled discovery pool distinct as the
review requires. Test is never read.

U2 is obtained by fitting on the full universe, scoring dev queries against
the full universe, and then **restricting the score matrix to the dev
columns**. This is exact, not an approximation: a BM25 or TF-IDF score of
query *i* against document *j* depends only on globally-fit quantities (IDF,
avgdl, vocabulary) and on document *j* itself, so column restriction is
identical to scoring against a dev-only pool under full-universe statistics.

**The arm set is held fixed at what was historically measured.** This run
changes the universe and nothing else. It is not the factorial control; that
is step 2 of the review's sequence and is deliberately not attempted here,
because a design that moves universe, rendering and arm structure together
cannot attribute a collapse to any of them.

| arm | signal added to BM25 |
|---|---|
| `bm25` | — (reference) |
| `bm25_plus_unigram_tfidf` | sign-unigram TF-IDF cosine |
| `bm25_plus_bigram_tfidf` | sign unigram+bigram TF-IDF cosine (`eval_harness.add_bigrams`) |
| `bm25_plus_char_ngram` | character n-gram TF-IDF cosine, range **fixed at (4,6)** |

Fold structure, alpha grid, tie-breaking and seed are inherited unchanged from
`phase5_bm25_combiner` (composition-level folds over queries only, 12-value
alpha grid containing 0, ties to the smallest alpha, seed 20260722). Ranking
goes through `eval_harness.run_task_a`'s `precomputed_scores` path in every
arm and every universe — the one-ranking-implementation rule.

### Deliberate deviations, declared in advance

1. **Character n-gram range fixed at (4,6)** rather than fit per fold as the
   historical char arm did. Holding the arm fixed is the point of this run,
   and the range grid belongs to step 2's factorial. Consequence: the char arm
   here is **not comparable to the historical +0.1179** and is excluded from
   the reproduction assertion below.
2. **Legacy language-blind rendering is retained**, exactly as the historical
   runs used it. This is reproduction-only and is declared in the manifest as
   `LEGACY_LANGUAGE_BLIND_REPRODUCTION_ONLY`. It does not authorize a
   promoted scorer; word-aware language scope is step 2's business.

## 3. Checks asserted in code before any number is reported

- **C1, reproduction.** Under U1, `bm25_plus_unigram_tfidf` must reproduce
  **+0.0520** and `bm25_plus_bigram_tfidf` must reproduce **+0.1017** (held-out
  recall@1 delta vs BM25), each within ±0.0005. If either fails, the run is
  **VOID** and is reported as void. The numbers are not adjusted to match.
- **C2, no leakage from widening the index.** Cleanroom rule 2 places all
  witnesses of a composition on one side of the split, so a train-side
  fragment can never belong to a dev query's gold composition — widening the
  index can only add distractors. This is asserted, not assumed: the
  intersection of dev-query CTHs with train-only-fragment CTHs must be empty.
  A non-empty intersection voids U2 and U3.
- **C3, identity.** Row z-normalization must reproduce BM25's per-query
  records exactly in each universe (the existing combiner identity control),
  so that alpha = 0 provably recovers the baseline.

## 4. Statistics

For every arm, in every universe, against the BM25 reference of that same
universe:

- query-micro delta with paired query bootstrap (`phase5_bm25_combiner.compare`);
- **composition-cluster** and **composition-macro** deltas with cluster
  bootstrap (`phase5_unigram_tfidf_control._cluster_summary`), per correction
  5 of the review — one CTH contributes a large share of dev queries and
  query-level intervals understate cluster dependence.

The **decision statistic is the composition-cluster interval**, not the
query-micro interval.

## 5. Pre-registered decision rule

Primary statistic **Δ_survive** = held-out recall@1 delta of
`bm25_plus_bigram_tfidf` over `bm25`, in **U3**, composition-cluster CI.
Declared smallest worthwhile effect: **0.010** (the margin already declared
across this line).

| verdict | condition |
|---|---|
| `SURVIVES_DECLARED_UNIVERSE` | cluster CI lower bound > 0 **and** Δ_survive ≥ 0.010 |
| `COLLAPSES_UNDER_DECLARED_UNIVERSE` | cluster CI upper bound < 0.010 |
| `INCONCLUSIVE` | otherwise |

Applied through `lib/effect_decision.practical_increment_verdict`, so the
margin logic is the shared one and CI-includes-zero is not read as
equivalence.

**Secondary attributions, no decision weight** (they decompose the primary,
they do not test it):

- T1, statistics-universe effect = Δ(U2) − Δ(U1)
- T2, distractor effect = Δ(U3) − Δ(U2)

These are reported for every arm with cluster intervals, and are explicitly
descriptive: three universes measured on one query set do not license a
significance claim about the difference of two deltas.

## 6. What this run cannot establish

It cannot establish test-side transfer (protected, one-shot, not run), a
deployable absolute number, that character granularity or n-gram context is
the better representation (step 2's factorial), Task B or join-tier behaviour
(step 3), or that the legacy language-blind rendering is acceptable for a
promoted scorer. A `SURVIVES` verdict licenses proceeding to step 2 under the
declared universe. It does not license shipping anything.

## 7. Outputs

- `scripts/phase5_statistics_universe_control.py`
- `Phase4/phase4_out/p5_statistics_universe.json`
- `Phase4/phase4_out/p5_statistics_universe_per_query.jsonl`
- `Phase4/phase4_out/p5_statistics_universe_manifest.json`
- `reports/phase5_statistics_universe_results.md`
