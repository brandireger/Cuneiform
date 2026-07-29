# Phase 4 — workbench review queue

**Policy:** `contentful_sequence_length_v1` · contract `unresolved_evidence_contract` v1.1.0 · every record `NOT_CORPUS_TRUTH`.

A queue is a **view** over ratified artifacts. Nothing here modifies an occurrence, a cluster proposal, or an accepted hash, and exclusion from the queue is not a judgment that a cluster is uninteresting.

## What the queue shows, and what it does not

| channel | proposals | contentless | below min length | eligible | queued |
|---|---:|---:|---:|---:|---:|
| `SAME_LANGUAGE_AS_QUERY` | 4,566 | 125 | 1,544 | 2,897 | 60 |
| `CROSS_LANGUAGE_PARALLEL` | 1,278 | 38 | 542 | 698 | 60 |

### Two exclusions, both awaiting ratification

**Contentless sequences.** A cluster whose shared sequence is nothing but placeholder characters (` ()._x` — the illegible `x`, the indeterminate filler `_`, editorial parentheses) groups occurrences by the absence of a reading. That gives an expert nothing to compare, and it is what produces the 95,530-member proposal that would otherwise open the interface. Same-language channel: 125 cluster(s) covering 131,963 occurrence(s).

**Sequences shorter than 2 signs.** Ranking an earlier draft of this queue by document count alone put the single signs `a` (3,542 documents), `i`, and `e` at the top. A damaged common sign appears everywhere; shared-sequence evidence gets its force from specificity, not from recurrence alone. This is the second Zipfian floor, one level up from `x`. Same-language channel: 1,544 cluster(s) covering 75,018 occurrence(s).

Both are **display policies**, not findings. Nothing excluded here is judged uninteresting, deleted, or altered; illegible runs and single signs remain in the extraction, and a future queue keyed on surrounding context rather than shared surface form would reach them. The pair needs Ixca's ratification before the queue is used for real expert labor, because they decide what a specialist is shown.

### Sampling within a cluster

At most **12** members are rendered per cluster, beside the cluster's true `member_count`. The interface must present this as a sample; a reviewed cluster is never a fully-seen cluster.

At most **60** clusters per channel are exported, to bound the browser payload. The remainder is unqueued, not rejected.

## Payload

- `Phase4/phase4_out/workbench_ui_out/workbench_review_queue.js` — 1.96 MB
- content hash `3e4e66ea8d7796739901d379b8bb86cc1cb130c7b19226b7857f2a70ae432bee` (stable across rebuilds)
- file hash `bf48d9dbc9e24b23ba94926c0a7c2786b0ca7cc7da6ac1ea68567cb578edf236` (moves with the clock; the records carry their own provenance)
- Whole canonical records travel with the queue, so the browser hashes the same bytes that are on disk; a display object would bind an expert's judgment to something unverifiable.

## Source artifacts (unmodified)

- `occurrences_logical_sha256`: `fd387b97a9aeb1cb9b7e9a89f3b20f8b015ef50af524695cec6567b64b191f47`
- `contract_version`: `1.1.0`
- `SAME_LANGUAGE_AS_QUERY_candidates_logical_sha256`: `33c3cff9985a4ee26716515d3b764b2b1f812328a93ca0ffa195dce711f3c21b`
- `CROSS_LANGUAGE_PARALLEL_candidates_logical_sha256`: `573ed092f8dcbf2300119eb12e9b03f33e70c79232ddeac8a2bc3b48c5c98f51`

## Standing display rules for any interface built on this queue

1. Same-language is the default channel; cross-language is shown only as a visibly enabled alternative.
2. No count or member total may be presented as a probability.
3. Contradictory evidence attached to a proposal is always rendered.
4. Withhold judgment is always available.
5. The screen states that the queue is a subset, with these counts.
