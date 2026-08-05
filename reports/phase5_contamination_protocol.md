# Contamination control by consistent sign relabeling — pre-registered protocol

> **POST-RUN CORRECTION 2026-08-04.** This historical protocol is preserved,
> but its “memorisation rejected” label was causally too broad. Survival can
> show that correct passage sequence is unnecessary for aggregate gain; it
> cannot exclude every memorised component. Do not alter the historical rule;
> use `reports/phase5_classical_control_review.md` for current interpretation.

**Status: PRE-REGISTERED 2026-08-04, written and committed BEFORE the run.**
Training-free; dev split only; test never loaded.

## The question

`reports/phase5_ladder_screen_results.md` recorded contamination as a live
concern and `reports/phase5_bm25_combiner_results.md` made it load-bearing:
there is now a positive result to explain (+0.0462 held-out Task A recall@1
from BM25 + frozen CANINE). TLHdig is openly licensed and on Zenodo, and
hethiter.net is on the open web; CANINE-s (multilingual Wikipedia) and XLM-R
(CommonCrawl) may have seen Hittite transliteration, or the corpus itself.

Enumerating CommonCrawl is not possible here, so the check must be
**behavioural**: does the gain depend on the specific surface forms of
Hittite, or on structural properties any similar text would have?

## The control

Apply a **bijective, character-length-preserving permutation** σ to the sign
vocabulary and re-render every dev fragment with σ applied. Signs are permuted
only within their own character-length class, so total sequence length — and
therefore truncation — is unchanged.

Why this separates the two explanations:

- **Structural/orthographic signal survives.** σ is a bijection applied
  consistently, so two fragments that shared the sign `ma` now share σ(`ma`).
  Every overlap, repetition and co-occurrence pattern is preserved exactly.
- **Memorised surface content does not survive.** The relabeled text is not
  Hittite. A model retrieving because it recognises an attested passage from
  pretraining has nothing left to recognise.

**Built-in correctness assertion: BM25 must be EXACTLY invariant.** Its
statistics (term frequency, document frequency, IDF, document length,
average document length) depend only on the multiset structure, which a
bijective relabeling preserves up to renaming. BM25's 865 per-query records
must be identical before and after. If they are not, the relabeling is not a
consistent bijection and every downstream number is void. This is asserted in
code, not inspected.

Vocabulary measured in advance: 1,339 signs over 161,020 dev occurrences.
Length classes hold 50 / 390 / 567 / 171 / 96 / 42 signs at lengths 1–6; only
5 signs (6 occurrences, lengths 9–13) sit in singleton classes and are
necessarily fixed points. The realised fraction of relabeled occurrences is
measured and reported, not assumed.

## Design

Five permutation seeds. For each: relabel, re-embed with frozen CANINE-s
(primary) and XLM-R (secondary), and re-fit the combiner using the **identical**
fold assignment, α grid, and decision machinery as
`reports/phase5_bm25_combiner_protocol.md` — the same script's functions, not
a second implementation.

Primary statistic: the **mean per-query held-out delta across the five
permutations**, with a paired bootstrap 95% CI over queries (1,000
replicates, seed 20260722).

**Retention** = mean relabeled delta ÷ **+0.0462** (the original CANINE delta,
fixed and already published in the results report — it is not re-estimated).

## Pre-registered decision rule

> - Retention **≥ 0.50** and the relabeled CI excludes zero →
>   **MEMORISATION REJECTED** as the explanation of the combiner gain.
> - Retention **≤ 0.20**, or the relabeled CI includes zero →
>   **MEMORISATION NOT EXCLUDED.**
> - Anything between → **INCONCLUSIVE**, reported as such, with no claim
>   either way.

## The test is deliberately one-sided, and the report must say so

**Survival is a clean result. Collapse is not.**

If the gain survives relabeling, memorisation is ruled out: there is nothing
Hittite left to have memorised, so whatever is working is structural.

If the gain collapses, that is **ambiguous between two innocent and one guilty
explanation**, and this protocol cannot separate them:

1. memorisation of TLHdig specifically (contamination — the concern);
2. legitimate transfer from Hittite or related transliterated material seen in
   pretraining, which is a *finding*, not a defect;
3. sensitivity to character-level statistics of real language in general
   (relabeled text is not natural in any language).

A collapse therefore triggers a follow-up, not a conclusion. It must never be
reported as "the model was contaminated."

## What this does not do

It does not prove TLHdig is absent from any pretraining corpus, does not
speak to the test split, and does not license any claim about fine-tuned
performance. It bounds one specific alternative explanation for one specific
measured gain.
