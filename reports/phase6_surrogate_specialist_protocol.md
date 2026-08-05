# Phase 6 blinded surrogate specialist review — protocol

**Status:** PRE-REGISTERED BEFORE PACKET GENERATION OR CASE INSPECTION.
**Date:** 2026-08-04.
**Protected test:** CLOSED and never loaded.

## Purpose and status

This review prepares a mentor-facing paper draft and a later session with a
trained Hittite specialist. The reviewer is an AI acting as a **methodological
and transliteration-evidence surrogate**, not as a Hittitologist. Its judgments
must never be described as expert validation, philological adjudication, or
corpus truth.

The review can assess whether the encoded, attested-only transliteration gives
inspectable support for a retrieved textual relation. It cannot establish a
physical join, evaluate clay geometry or paleography, or authoritatively judge
Hittite grammar and restoration.

Paper-safe label:

> blinded AI-assisted error analysis used to develop the review protocol and
> prioritize cases for subsequent specialist adjudication.

## Evidence boundary

Reviewer-visible evidence uses the `transcription_assisted` profile:

- epigraphically attested sign tokens grouped by encoded line;
- line indices and the active `HITTITE_ONLY` scope;
- task label (`duplicate/parallel retrieval` or `physical-join retrieval`).

The packet excludes restorations, morphology, `cu`, CTH, site, publication
sigla, relation labels, scores, ranks, method names, correctness, and model
outputs. Fragment identifiers are replaced by case-local aliases.

Editorial relation labels and model-derived predictions may be used only to
construct balanced sampling strata and the sealed reveal map. They are not
review evidence.

## Sampling

Deterministic seed: `20260804`.

The sample is diagnostic, deliberately balanced, and **not prevalence
weighted**:

- duplicate retrieval: 6 gained and 6 lost queries;
- join retrieval: 5 gained and all 3 lost queries.

Selection prefers distinct composition clusters and avoids repeating a query.
If a requested cell cannot be filled, the exporter records the shortfall and
does not silently substitute another outcome.

For each query, the top candidate from the unigram ensemble and the top
candidate from the expanded bigram ensemble are shown as anonymous candidates
`A` and `B`; their order is randomized per case. The exporter must reproduce
the persisted held-out correctness records exactly before emitting a packet.

## Locked rubric

The surrogate reviewer records, before opening the reveal map:

1. **Preferred candidate:** `A`, `B`, `BOTH`, `NEITHER`, or `UNRESOLVED`.
2. **Textual relation support for each candidate:** `STRONG`, `MODERATE`,
   `WEAK`, or `NONE`.
3. **Formulaicity/ambiguity:** `LOW`, `MEDIUM`, or `HIGH`.
4. **Editorial-dependence risk:** `LOW`, `MEDIUM`, or `HIGH`.
5. **Contradictory evidence:** free-text, including line-order conflict,
   language mismatch, insufficient overlap, or competing formulaic matches.
6. **Evidence independence:** whether support comes from several distinct
   lines/sign runs or one repeated/shared sequence.
7. **Physical-join judgment for join cases:** `TEXTUALLY_COMPATIBLE`,
   `TEXTUALLY_CONTRADICTED`, or `INSUFFICIENT_ENCODED_EVIDENCE`.
8. **Specialist priority:** `HIGH`, `MEDIUM`, or `LOW`.
9. **Rationale:** concise evidence-bounded explanation.

For physical joins, textual compatibility is never promoted to an asserted
join. With no physical modality, `INSUFFICIENT_ENCODED_EVIDENCE` is expected
whenever the transliteration cannot discriminate adjacency from duplicate,
formula, or same-composition affinity.

## Reveal and analysis

Annotations are written to a separate locked file before the reveal map is
read. After reveal, analysis reports:

- preference for the expanded versus unigram candidate by gained/lost stratum;
- agreement with the corpus relation label, clearly named as editorial truth;
- abstention and `NEITHER` rates;
- dependence on exact/shared lines or formulaic evidence;
- cases whose quantitative gain is not qualitatively persuasive;
- cases where the weaker-ranked method produced the more defensible candidate;
- a prioritized queue for real specialist adjudication.

No inferential p-value or population estimate is computed from this balanced
sample. The review is qualitative and hypothesis-generating.

## Outputs

- `scripts/phase6_surrogate_review_export.py`
- `Phase4/phase4_out/phase6_surrogate_review_blind.json`
- `Phase4/phase4_out/phase6_surrogate_review_reveal.json`
- `Phase4/phase4_out/phase6_surrogate_review_manifest.json`
- `Phase4/phase4_out/phase6_surrogate_review_annotations.json`
- `reports/phase6_surrogate_specialist_review.md`
- mentor-paper draft material, clearly labeled provisional

