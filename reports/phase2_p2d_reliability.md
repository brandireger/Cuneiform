# Phase 2 P2-D ground-truth reliability audit

**[PROBE — not for citation]**

## Question

Does TLHdig record different evidential bases for dev join labels, and is the frozen 46-query BM25 hard set enriched for weaker bases?

## What I did

Audited all 182 canonical dev relation pairs (182 query fragments) using only `join_type`, `declared_adjacent`, technical IDs, and the frozen hard-set list. The split gate ran before JSON decoding; no transliteration, restoration, `cu`, model score, or test-side payload was read. Seed 20260723; paths: `p2_out/join_pairs.jsonl`, `p2_out/splits.parquet`, `p2_out/edges.parquet`, and `p4_out/p5_hard_set.json`.

## What I found

| recorded basis | dev pairs | interpretation |
|---|---:|---|
| direct `+` | 104 | editor-declared direct physical join notation; not independently reverified here |
| indirect `(+)` | 17 | same object, not a direct physical fit; attributed on textual/content grounds |
| inferred from shared-line tags | 60 | parser-derived relation between non-adjacent members co-occurring in editor-supplied line tags |
| unsupported/unknown | 1 | field combination does not support a stronger classification |

- [PROBE] 77 / 182 pairs (42.3%) are indirect or shared-line-inferred rather than direct `+` pairs.
- [PROBE] At the frozen query unit, 17 / 46 hard queries (37.0%) touch a weaker-basis relation versus 76 / 136 non-hard queries (55.9%). The hard set is not enriched; the observed odds ratio is 0.463 (one-sided enrichment p=0.992; two-sided p=0.028).
- [PROBE] Query rows are dependent within composite parents. A parent-level robustness view changes direction but remains inconclusive: 12 / 26 hard-associated parents versus 13 / 33 other parents (odds ratio 1.319, two-sided p=0.791).
- [PROBE] No source field in the governed relation artifacts marks a join as `proposed` or supplies a certainty grade. That requested category is unavailable, not zero.
- [PROBE] 2 dev relation rows lack one or both canonical fragment mappings; 1 ambiguous-parent row was quarantined before payload decoding.

## What it rules in / rules out

The dev gold is heterogeneous: a substantial share is indirect or algorithmically expanded from editorial shared-line attribution, so future physical-join reporting must keep these bases separate. This probe does **not** support the hypothesis that the BM25 hard set is hard because it contains more weak editorial claims. It also cannot measure absolute correctness or certainty: direct `+` is a notation class, not an independent physical re-fit audit.

No content scoring occurred, so the tracer block is not applicable.

## Cost

0.4 seconds elapsed against a 2-hour budget.

## Falsifier

This conclusion would be wrong if a TLHdig field not materialized in the governed relation artifacts records proposal/certainty status and is systematically concentrated in the hard set.
