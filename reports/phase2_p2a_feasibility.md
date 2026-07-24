# Phase 2 P2-A feasibility probe

**[PROBE — not for citation]**

## Question

Does TLHdig/P2 encode a true within-line seam and offset that can serve as the target for P2-A's handed-over-truth localization test?

## What I did

Inspected 184 `dev` relation rows, of which 182 mapped to the canonical fragment universe. The probe decoded no transliteration, `cu`, restoration, test-side join payload, or model output. Budget: 2 hours; elapsed: 0.5 seconds.

## What I found

- [PROBE] 92 / 182 mapped pairs have an editor-derived, consistent row-alignment offset because their member line sets share at least one parent-document row.
- [PROBE] 22 / 182 mapped pairs identify only which member's row range comes first; they do not identify a row offset.
- [PROBE] 32 / 182 mapped pairs have interleaved ranges without a shared row and therefore supply neither a unique row offset nor simple ordering.
- [PROBE] 36 / 182 mapped pairs have shared rows but more than one positional row delta, so they do not supply one consistent offset.
- [PROBE] 2 dev relation rows were excluded because one or both fragment IDs are absent from the canonical edge universe.
- [PROBE] 4 pair records disagree with the line-set intersection count.
- [PROBE] 1 relation row was excluded before payload decoding because its parent `doc_id` has conflicting frozen split assignments.
- [PROBE] 0 pairs encode a member-specific within-line sign span or fracture column. Shared `{€N+M}` rows are represented as one fused parent line assigned to both members, not as separate left/right halves.

| tier | pairs | identifiable row offset | ordering only | interleaved | inconsistent offset |
|---|---:|---:|---:|---:|---:|
| A | 54 | 0 | 22 | 32 | 0 |
| B | 31 | 27 | 0 | 0 | 4 |
| C | 97 | 65 | 0 | 0 | 32 |

## What it rules in / rules out

The corpus supports a row-alignment probe for the subset with shared rows. It does **not** support the P2-A test as worded—scoring a true within-line seam against wrong seam offsets—because the target seam column is absent. The existing D17 `offset` skips whole leading rows of a candidate; it is not an editor-supplied fracture-column label and must not be relabeled as ground truth.

No scoring occurred, so a tracer block is not applicable.

## Cost

0.5 seconds elapsed against a 2-hour budget.

## Falsifier

This conclusion would be wrong if a source field not materialized in `edges.parquet` or the metadata-only join records encodes separate per-member within-line spans or an explicit fracture column.
