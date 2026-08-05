# Unigram TF-IDF decomposition control

**Status: REVIEWER-REQUESTED POST-HOC DECOMPOSITION, 2026-08-04.**
**This is not a preregistration and must never be described as one.** The
reviewer had already run a read-only diagnostic and knew that unigram TF-IDF
recovered material gain before this file was written. The purpose of this
artifact is reproducibility and correction of the causal account, not a new
confirmatory claim.

## Question

The classical-control handoff attributes roughly +0.10 Task A recall@1 to
"n-gram context." That conclusion omitted a necessary control: BM25 combined
with TF-IDF cosine over the **same unigram sign tokens**. BM25 and TF-IDF
weight and normalize the same terms differently, so an ensemble can improve
without adding sequence context.

This audit decomposes the already-observed sign-bigram arm into:

1. BM25 + unigram TF-IDF versus BM25;
2. BM25 + unigram+bigram TF-IDF versus BM25; and
3. the separately cross-fitted bigram arm versus the separately cross-fitted
   unigram arm.

The third comparison is a useful paired decomposition diagnostic, not a
formal conditional-increment test: the two arms tune their mixing weights
separately. A future confirmatory design should use a factorial nested model
with unigram-only and bigram-only channels.

## Frozen reproduction design

- Reuse the historical dev-only fragment loader, candidate index, fold
  assignment, alpha grid, Task A ranking, and paired records.
- Preserve the historical statistics-universe deviation: vocabulary and IDF
  are fit on 876 dev fragments. This is necessary to decompose the published
  number exactly, but it remains prohibited for a promoted/deployed result.
- Save per-query records and composition summaries, which the original Phase
  5 artifacts omitted.
- Report both query-micro and composition-macro deltas and a
  composition-cluster bootstrap interval.
- Emit a feature-use manifest under `discovery_assisted`; BM25 and TF-IDF
  scores are `MODEL_DERIVED`.
- Declare the old loader's language behavior explicitly as
  `LEGACY_LANGUAGE_BLIND_REPRODUCTION_ONLY`. It is not an approved language
  scope for new production scoring.

## Interpretation limits

This audit can show that the original mechanism attribution was incomplete.
It cannot validate full-corpus scale, the protected test split, physical-join
utility, character granularity, or deployment. No thresholded advance or
withdraw verdict attaches to it.
