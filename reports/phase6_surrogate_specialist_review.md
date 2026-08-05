# Phase 6 blinded surrogate review — provisional findings

**Status:** completed AI-assisted methodological and transliteration-evidence
review; **not specialist validation**. 2026-08-04. Protected test remained
closed.

## Outcome

The blinded review supports a narrow claim: the separately weighted sign-bigram
channel often retrieves a more textually defensible candidate than the unigram
system in cases where it changes a miss to a benchmark hit. It does **not**
support the physical-join interpretation, and it exposed that the benchmark
cell historically called `duplicates` is actually a same-CTH proxy rather than
an annotated duplicate/parallel task.

The correct paper-safe description is:

> Blinded AI-assisted error analysis found that sign bigrams often improve
> inspectable textual affinity, especially through coherent multi-sign runs.
> The available encoded evidence did not permit physical-join adjudication,
> and the same-CTH benchmark does not validate duplicate or parallel discovery.

The first session with a trained Hittite specialist remains required. This
review prepares that session and permits provisional drafting; it does not
replace it.

## A post-reveal label correction

The locked packet called one task `duplicate_parallel_retrieval`, and the
sealed reveal used the field name `editorial_relation_positive`. Those names
overstated the implemented truth set. Inspection of
`eval_harness.build_duplicate_positives` established that the cell contains
**all same-CTH fragment pairs, excluding physical joins and catch-all bins**.
It does not use an annotated duplicate/parallel relation.

This changes the interpretation, not the recorded retrieval numbers:

- `joins`: benchmark positives are editor-encoded physical partners;
- historical `duplicates`: benchmark positives are same-CTH, non-join pairs;
- `pooled`: union of those two operational truth sets.

Accordingly, this report calls the second cell **same-CTH affinity**. The
analysis code now emits `benchmark_positive` and
`SAME_CTH_NON_JOIN_BENCHMARK_PROXY`. The original locked reveal remains in git
history so the correction is auditable; the analyzer handles its legacy field
name without promoting it to editorial truth.

This is a substantive validity limitation. The reported +0.0627 does not by
itself establish better duplicate-witness retrieval. A true duplicate/parallel
claim requires relation-specific expert labels or a separately justified
operational definition.

## Procedure

The protocol was committed before packet generation. The exporter recomputed
the cross-fitted `HITTITE_ONLY` predictions and required exact agreement with
all 1,874 saved correctness bits. It then selected a deterministic,
non-prevalence-weighted diagnostic sample:

| cell | gained | lost | total |
|---|---:|---:|---:|
| same-CTH affinity | 6 | 6 | 12 |
| physical joins | 5 | 3 (all available) | 8 |
| total | 11 | 9 | 20 |

The reviewer saw attested-only signs grouped by line, the active language
scope, and the task label. Candidate identity was randomized. Hidden fields
included methods, scores, ranks, outcomes, CTH, sigla, and benchmark labels.
The twenty annotations were committed at `b85f2e3` before reveal content was
inspected.

The reviewer is an AI surrogate, not a Hittitologist. Judgments concern only
whether the visible transliteration gives inspectable textual support. No
judgment establishes grammar, restoration, duplicate status, or physical fit.

## Blinded preferences after reveal

| sampling stratum | expanded | unigram | both | neither |
|---|---:|---:|---:|---:|
| same-CTH gained | 5 | 0 | 1 | 0 |
| same-CTH lost | 0 | 4 | 0 | 2 |
| join gained | 4 | 0 | 1 | 0 |
| join lost | 1 | 2 | 0 | 0 |

These are deliberately balanced case counts, not estimates of prevalence or
accuracy. The result is nevertheless useful as a manipulation check: the
quantitative gains usually corresponded to a qualitative difference visible
without method identity. Among gained cases, expanded candidates received
`STRONG` textual support in 7/11 and `MODERATE` support in 4/11. Direct
preference went to the expanded candidate in 9/11; both candidates remained
plausible in 2/11.

Across all non-abstaining choices, the selected set contained a benchmark
positive in 17/18 cases. For single-candidate choices the figure was 15/16.
These are agreement counts against two different truth constructions—not
expert accuracy. The same-CTH proxy must not be called duplicate truth, and an
editor-encoded join is not independent physical re-adjudication.

## What the gains appear to use

The most persuasive expanded candidates showed coherent runs across multiple
lines, not merely shared token inventory. Examples include:

- `SR002`, `SR005`, and `SR006`: dense, long sign runs in a relatively short
  candidate beat diffuse matches in a far longer candidate;
- `SR014`, `SR016`, and `SR017`: multiple exact or near-exact lines strongly
  identify textual relationship;
- `SR003` and `SR004`: the expanded candidate is preferable, but the query is
  too short for more than a moderate judgment.

Five of six same-CTH gained cases were rated `HIGH` for
formulaicity/ambiguity. Thus the channel may be doing exactly what the
quantitative controls imply—capturing local sign sequence—without that
sequence necessarily identifying a duplicate witness. A system intended for
discovery needs a formula-aware explanation, candidate-length controls, and an
explicit distinction between composition affinity and passage-level parallel.

## Why the join claim remains unsupported

All 8 join cases received
`INSUFFICIENT_ENCODED_EVIDENCE`. This is not a vote against their catalogued
joins. It states that attested transliteration alone cannot adjudicate clay
fit, fracture geometry, paleography, or spatial placement.

The gained join cases often had exact lines at matching encoded positions.
That makes the textual relation easy to inspect but intensifies the known
confound: the system can read back editor-aligned shared material. It is
consistent with the population result that the join gain disappears on the
zero-shared-line stratum and with the Tier C collapse after aligned lines are
removed.

`SR020` is the most informative counterexample. Blinded, the expanded
candidate was judged textually stronger: it had more distributed overlap and
more exact lines. After reveal it was **not** the editor-encoded physical
partner; the unigram candidate was. This is not necessarily a bad textual
retrieval—it may be a strong same-composition or formulaic relation—but it is a
join-ranking failure. It directly demonstrates why textual affinity and
physical joining require separate heads, evidence types, and abstention.

## Cases that should lead the real specialist session

1. **`SR020` — highest priority.** Decide what relation, if any, the strong
   non-join candidate bears to the query, and why it outranks the physical
   partner textually.
2. **`SR015` and `SR001` — unresolved candidate competition.** Both candidates
   were textually plausible. Identify diagnostic versus merely formulaic
   sequences.
3. **`SR007` and `SR012` — benchmark hit rejected by the surrogate.** Determine
   whether same-CTH membership supplies any real duplicate/parallel evidence
   when the attested overlap is only two-sign material.
4. **`SR003` and `SR004` — short-query gains.** Assess whether two or three
   local runs are philologically meaningful or accidental.
5. **`SR013`, `SR014`, `SR016`, `SR017`, and `SR019` — aligned-line joins.**
   Separate text shared because of editorial alignment from evidence a
   specialist would independently use for physical placement.

The specialist should receive the blind packet first, with method and
benchmark reveal withheld until their judgments are persisted. They should
also be allowed to request catalog images or editions in a second pass; that
second modality must be recorded separately from the transcription-only pass.

## Product implications

The current retrieval channel is useful as a **textual-affinity candidate
generator**. It is not yet a physical-join system and it is not validated as a
duplicate detector. A robust product should:

- expose why a candidate was retrieved, including distinct matching runs,
  their line locations, and whether they repeat elsewhere in the corpus;
- normalize explanations for candidate length and formula frequency;
- label same-CTH affinity, passage parallelism, duplicate witness, and
  physical join as different hypotheses;
- abstain on physical joining unless independent structural or physical
  evidence is available;
- preserve `other / unsupported` and contradictory evidence;
- collect specialist decisions as provenance-bearing annotations, never as
  automatically promoted corpus truth.

## Limits

- The sample is small, balanced by outcome, and selected from development
  data. No confidence interval or population claim is licensed.
- The reviewer is not a Hittite specialist and did not adjudicate morphology,
  syntax, translation, or tablet condition.
- Only attested transliteration and line grouping were visible. Physical and
  bibliographic modalities were intentionally absent.
- Formulaicity ratings are qualitative and should be replaced or supplemented
  by corpus-frequency summaries in the expert UI.
- The protected test split was not loaded.

## Reproducible artifacts

- protocol: `reports/phase6_surrogate_specialist_protocol.md`
- exporter: `scripts/phase6_surrogate_review_export.py`
- locked blind packet: `Phase4/phase4_out/phase6_surrogate_review_blind.json`
- locked annotations: `Phase4/phase4_out/phase6_surrogate_review_annotations.json`
- sealed historical reveal: `Phase4/phase4_out/phase6_surrogate_review_reveal.json`
- descriptive analyzer: `scripts/phase6_surrogate_review_analyze.py`
- analysis: `Phase4/phase4_out/phase6_surrogate_review_analysis.json`

