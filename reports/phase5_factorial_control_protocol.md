# Factorial lexical-channel control — PROTOCOL

**Status: PRE-REGISTERED 2026-08-04, committed before the run.**
**Dev queries only; test is never loaded. Training-free; no gradients.**

Executes **step 2** of the required sequence in
`reports/phase5_classical_control_review.md`. Step 1
(`reports/phase5_statistics_universe_results.md`) is complete and reshapes the
question this step must ask.

## 1. The question, as step 1 left it

Step 1 refit all statistics over the declared labeled non-test universe and
widened the candidate index to 7,490 fragments. The gain survived
(`SURVIVES_DECLARED_UNIVERSE`, bigram arm +0.0601) but the three arms
**converged** to +0.0555 / +0.0601 / +0.0624 — a spread inside the declared
0.010 margin — and the paired sequence-context component fell from +0.0497 to
+0.0046, CI [−0.0146, +0.0236].

So the step-2 question is no longer "which representation is best". It is:

> **Does any richer lexical channel add a material increment over BM25 +
> unigram TF-IDF, once statistics are declared, the index is full, line
> boundaries are respected, and the ratified word-aware language scope is
> applied?**

Two things step 1 deliberately held fixed are released here, and both are
released as **measured factors rather than silent changes** — the same
discipline that made step 1 attributable.

## 2. Design — two crossed factors

### Factor R: rendering (3 levels)

A rendering is defined by **the segment within which an n-gram may form**.

| level | segments | language |
|---|---|---|
| `LEGACY` | one segment = the whole fragment's flat token list | language-blind |
| `BOUNDARY` | one segment per line | language-blind |
| `SCOPED` | one segment per line **admitted by `HITTITE_ONLY`** | word-aware, ratified |

`LEGACY` is step 1's rendering and the comparability anchor. Correction 4 of
the review observes that it strips every structural token, so an n-gram may
silently bridge a line break — and, where lines were dropped, bridge lines
that were never adjacent. `BOUNDARY` removes exactly that and nothing else.
`SCOPED` additionally applies `language_lookup_v2.hittite_only_projection`,
with the ratified `EXCLUDE_LINE` mixed-line policy: a line is admitted whole
or not at all. Dropping offending *words* and splicing the survivors would
manufacture adjacencies that never existed on the tablet, which is precisely
the failure the n-gram channels would then reward.

Line admission is taken from `EffectiveLanguageIndex.line_decision` and the
traversal from `hittite_tokenizer.iter_structured_attested`, which yields each
token's true `(line_index_in_doc, word_pos)` — the same single implementation
`lib/p4f_data.py` uses. No second traversal is written.

### Factor C: channel (BM25 reference + 5 added channels)

Each channel is a cosine similarity over TF-IDF, computed **per segment and
summed over a fragment's segments**, so no feature can cross a segment
boundary by construction.

| channel | features |
|---|---|
| `bm25` | reference; no added channel |
| `unigram_tfidf` | sign unigrams |
| `bigram_only_tfidf` | adjacent sign bigrams **only**, no unigrams |
| `unigram_plus_bigram_tfidf` | sign unigrams + adjacent bigrams (`eval_harness.add_bigrams`) |
| `char_within_sign` | character 4–6-grams, `analyzer='char_wb'` — cannot see across a sign |
| `char_across_sign` | character 4–6-grams, `analyzer='char'` — the historical arm |

`char_within_sign` vs `char_across_sign` is the direct test of the
philological story the review flagged as unsupported (correction 4): if the
signal were partially-preserved-sign matching, the within-sign channel should
carry it; if it is cross-sign sequence, only the across-sign channel can.

### Arms

- **Marginal**, 3 renderings × 5 channels = **15 arms**: `BM25 + C`, one weight
  fit per fold.
- **Conditional**, 3 renderings × 3 channels = **9 arms**: `BM25 + unigram + X`
  for X ∈ {`bigram_only_tfidf`, `char_within_sign`, `char_across_sign`}, with
  **both** weights fit jointly per fold. `unigram_plus_bigram_tfidf` is
  excluded from the conditional set because it contains the unigram channel.

Weight grids: the unigram weight uses the inherited 12-value `ALPHA_GRID`; the
second weight uses `[0.0, 0.1, 0.2, 0.4, 0.75, 1.0, 1.5]`, which spans the
range selected in step 1. **Both contain 0**, so each arm's family strictly
contains its own reference and an increment is attributable to the added
channel rather than to reparameterization. Ties resolve to the smallest
weights. Composition-level folds over queries only, seed 20260722, ranking via
`eval_harness.run_task_a`'s `precomputed_scores` path — all inherited unchanged.

## 3. Population — fixed in advance, before any retrieval number

Measured during design (data characterization, no retrieval run):
`HITTITE_ONLY` empties **15.07%** of lines and **14.25%** of content tokens,
and leaves **86 of 876** dev queries with no admitted content at all. Those
refusals are overwhelmingly genuine — 1,801 `OUT_OF_SCOPE_LANGUAGE` lines
against 611 `LINE_NOT_IN_LANGUAGE_DATASET` — and the fragments are recognizable
Akkadian/Sumerian material (the KUB 4.x bilinguals).

Comparing renderings therefore requires a population on which all three are
defined. Keeping 86 all-zero documents in the `SCOPED` arms would make the
rendering contrast largely a measure of *how many queries the scope destroys*,
not of how it changes the signal.

**Pre-registered population**: fragments with ≥4 content tokens under **all
three renderings** — expected **779 dev queries** and **6,722 candidates**.
Fixed and identical for every arm, so every comparison is paired.

**The excluded material is a reported finding, not a discard.** The count of
dev queries and candidates that the ratified language scope removes, and their
refusal reasons, are reported as the coverage cost of the scope. That Task A
has until now been scoring non-Hittite fragments is itself a result.

Because the population changes, `LEGACY` arms are **re-measured on it** rather
than compared against step 1's numbers across two different populations.

## 4. Checks asserted in code before any number is reported

- **C1, segmentation is inert for bag-of-token channels.** `LEGACY` and
  `BOUNDARY` differ only in segmentation, and BM25 and `unigram_tfidf` are
  bags of tokens. Their per-query records must be **identical** between the
  two renderings. A difference means the segmentation machinery is changing
  something it must not, and voids the run.
- **C2, identity control.** Row z-normalization must reproduce BM25's per-query
  records exactly, in each rendering.
- **C3, split purity.** Dev-query CTHs disjoint from train-index CTHs
  (inherited from step 1; re-asserted on the restricted population).
- **C4, no cross-segment features.** For a fragment with more than one
  segment, the `bigram_only` feature count must be strictly less than the
  flat-rendering count by exactly the number of segment joins. Asserted on a
  sample.

## 5. Statistics

Every arm reports query-micro delta with paired query bootstrap, and
**composition-cluster and composition-macro** deltas with cluster bootstrap.
The **decision statistic is the composition-cluster interval**, per correction
5 of the review.

## 6. Pre-registered decision rule

Primary: the three **conditional increments over `BM25 + unigram_tfidf` under
the `SCOPED` rendering**, each classified by
`lib/effect_decision.practical_increment_verdict` against the declared 0.010
margin using its composition-cluster interval.

| verdict | condition |
|---|---|
| `NO_CHANNEL_BEATS_UNIGRAM` | all three classify `BELOW_MARGIN` |
| `CHANNEL_ADDS` | at least one classifies as a material positive increment |
| `INCONCLUSIVE` | otherwise |

**Declared in advance:** `CHANNEL_ADDS` is reached across three simultaneous
comparisons and is therefore a multiple-comparison result. If it is reached,
the report must say so and must treat the channel as a candidate for
confirmation, not as an established effect.

Secondary, **no decision weight**, all descriptive:

- the rendering effect on each channel's marginal delta (`BOUNDARY` − `LEGACY`,
  `SCOPED` − `BOUNDARY`);
- `char_within_sign` vs `char_across_sign`, the partial-sign hypothesis;
- the coverage cost of the ratified language scope.

## 7. What this run cannot establish

Test-side transfer (protected, one-shot, not run); any deployable absolute
number; Task B or join-tier behaviour (step 3); anything about pretrained
models, whose increments were all measured under step 1's `U1` conditions and
remain bounded to them. A `NO_CHANNEL_BEATS_UNIGRAM` verdict would not prove
the channels are equivalent — it would bound their increments below the
declared margin in this setup, which is what the margin is for.

## 8. Outputs

- `scripts/phase5_factorial_control.py`
- `Phase4/phase4_out/p5_factorial_control.json`
- `Phase4/phase4_out/p5_factorial_control_per_query.jsonl`
- `Phase4/phase4_out/p5_factorial_control_manifest.json`
- `reports/phase5_factorial_control_results.md`
