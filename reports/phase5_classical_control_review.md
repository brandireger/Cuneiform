# Expert review and correction — Phase 5 classical-control line

**Date: 2026-08-04. Status: corrective review adopted on the review branch.**

> **STEP 1 OF §"Required sequence before P6" IS DONE, AND IT SUPERSEDES
> CORRECTION 2 OF THIS REVIEW.** See
> `reports/phase5_statistics_universe_results.md` (pre-registered `b83c96e`).
> Refit over the declared labeled non-test universe with a full distractor
> index, the bigram arm survives at **+0.0601, composition-cluster CI
> [+0.0368, +0.0905]** — but the three arms converge to +0.0555 / +0.0601 /
> +0.0624, a spread inside the declared 0.010 margin, and the **+0.0497
> sequence-context component named in correction 2 falls to +0.0046, CI
> [−0.0146, +0.0236]**. The unigram TF-IDF component survives and grows
> slightly (+0.0555). Correction 2's *first* half stands; its second half does
> not. This review's executive judgment should now read "about +0.055–0.062 for
> adding a second lexical similarity score, with which score unresolved."
> Corrections 1 and 3–6, and the required sequence itself, are unaffected.
This file reviews `reports/phase5_classical_control_handoff.md` against its
protocols, result artifacts, implementation, `AGENTS.md`, `EXPERT_OPINION.md`,
`P5_CLOSEOUT.md`, and `PHASE5_SUCCESSOR_HANDOFF.md`.

The original measurements are retained. The corrections concern inference,
mechanism, governance, and the scope of the resulting decisions.

## Executive judgment

The classical signal is promising, but the former headline was too strong.
The defensible current statement is:

> In the current closed-world dev evaluation, combining BM25 with another
> lexical similarity measure improves Task A retrieval. A post-hoc
> decomposition attributes about +0.052 recall@1 to adding unigram TF-IDF
> scoring and a further +0.050 to the separately tuned sign-bigram arm. The
> combined bigram-arm effect survives composition-cluster analysis. It still
> requires a declared-universe refit, full-distractor evaluation, factorial
> confirmation, task/tier stratification, and a one-shot protected-test gate.

## Corrections to the inferential record

### 1. Non-significance is not equivalence

The original char and bigram protocols declared an added signal redundant
when its interval included zero. That rule is invalid for an equivalence
claim.

- CANINE increment over the char arm: −0.0046, CI [−0.0162, +0.0058]. Its
  upper endpoint is below the declared +0.010 useful margin, so the bounded
  current interpretation is **no material frozen CANINE increment at the
  +0.010 margin in this setup**, subject to composition-cluster confirmation.
- Character over bigram: +0.0162, CI [−0.0012, +0.0324]. The interval includes
  both zero and effects larger than +0.010. The result is **inconclusive**,
  not evidence that character granularity is unimportant.
- Task B CANINE strata are **inconclusive**, not negative transfer results.
  The pooled any-relation result is a distinct estimand and remains positive;
  it must be reported alongside, not substituted for, the individual cells.

`lib/effect_decision.py` now makes the margin logic explicit. The scripts save
both the historical preregistered verdict and the corrected interpretation.

### 2. The +0.10 was not all n-gram context

The original sequence omitted BM25 + unigram TF-IDF. The post-hoc audit finds
unigram TF-IDF fusion +0.0520 and the separately tuned bigram arm another
+0.0497 over it. See `reports/phase5_unigram_tfidf_control_results.md`.

The next confirmatory design must be factorial: BM25, unigram TF-IDF,
bigram-only TF-IDF, unigram+bigram TF-IDF, within-sign character n-grams, and
across-sign character n-grams, with all weights fitted inside grouped folds.

### 3. Relabeling does not exclude every memorised component

Retention 1.016 shows that correct Hittite passage sequence is not necessary
for aggregate gain. It does not prove the original gain contained no
memorised component because:

- replacement tokens remain real Hittite transliteration strings;
- alpha is refitted after each permutation;
- aggregate retention does not show that the same queries or score residuals
  survive; and
- a structural mechanism after permutation could replace a memorised
  mechanism in the original data.

The corrected label is
`CORRECT_HITTITE_PASSAGE_SEQUENCE_NOT_NECESSARY_FOR_AGGREGATE_GAIN`.
Required follow-up: fixed-alpha retention, per-query gain overlap, rank/score
correlation, and uncertainty over both composition clusters and permutation
seeds.

### 4. The fracture-face story is unsupported by the inputs

Character n-grams see Latin-character substrings of editorial
transliteration, not clay, glyph fragments, fracture geometry, or a split
cuneiform sign. The historical loader also strips every structural token,
including line boundaries, so bigrams can cross artificial line joins.

Do not explain the join gain as matching half-preserved glyphs. Plausible
textual mechanisms include formulaic wording, repeated sign sequences,
transliteration substrings, and word/line serialization artifacts. Required
controls from `EXPERT_OPINION.md` include token scramble, line-order scramble,
boundary-respecting n-grams, formula-only passages, same-parent wrong members,
and candidate-ID permutation.

### 5. The resampling unit must match the claim

One CTH contributes 255/876 fragments and the five largest contribute 56%.
Query-level bootstrap intervals therefore understate cluster dependence.
The new audit saves composition summaries and cluster intervals. All promoted
results must report query-micro, composition-macro, and object/composition-
cluster uncertainty. Join analyses should cluster by physical joined object
or connected join component where appropriate.

### 6. Frozen mean pooling does not close pretrained adaptation

The evidence bounds a frozen, generic mean-pooled encoder in this retrieval
setup. It does not falsify fine-tuned CANINE, task-specific pooling, late
interaction, restoration, or span infilling. Not writing a Gate-3 proposal is
a defensible priority decision while the specialist session is blocked; it
must not be described as a scientific closure of pretrained models.

## Governance corrections

- New retrieval scores are registered as `MODEL_DERIVED`.
- The post-hoc audit emits a manifest and per-query artifact.
- The historical loader is declared
  `LEGACY_LANGUAGE_BLIND_REPRODUCTION_ONLY`; that declaration reproduces an
  old analysis and does not authorize a new production scorer.
- The char, bigram, Task B, and relabeling historical runs still need rebuilt
  manifests if they are promoted. The existing BM25+CANINE manifest also
  needs `frozen_pretrained_similarity_score`, a non-empty dataset hash, and
  `discovery_assisted` rather than a policy that omits model-derived input.

## Required sequence before P6

1. Fit statistics over the declared full non-test reference universe while
   keeping the labeled evaluation index and unlabeled discovery pool distinct.
2. Run the factorial unigram/bigram/character control under explicit,
   word-aware language scopes and boundary-preserving renderings.
3. Evaluate full-distractor Task A and the complete Task B matrix, stratified
   by direct/indirect join, join tier, shared-line count, damage, length,
   language, genre, and site.
4. Report candidate-set coverage/size, recall@k, MRR, composition macro,
   calibration, selective risk, and abstention. Recall@1 remains diagnostic.
5. Have a specialist inspect gained and lost cases blind to method where
   practical; persist typed support, contradiction, and dependence evidence.
6. Freeze one final configuration and analysis plan before the one-shot P6
   run. No further method selection may use protected-test output.

The first real specialist session remains the highest-value product and paper
gate. These corrections improve the retrieval evidence without displacing
that work.
