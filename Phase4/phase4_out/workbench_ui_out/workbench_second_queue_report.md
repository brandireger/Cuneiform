# Phase 4/5 — the second workbench queue

**Policy:** `contentful_sequence_length_v2` (contentless-sequence exclusion reused; minimum-sequence-length NOT applied here, see below) · contract `unresolved_evidence_contract` v1.1.0 · every record `NOT_CORPUS_TRUTH`.

A separate queue from `workbench_review_queue.js`, covering two populations that queue's length-first ranking and exact-sequence clustering structurally cannot reach. See `reports/phase5_second_queue.md` for the full design writeup and the measurements behind every choice below.

## Channels

| channel | proposals | contentless excluded | eligible | queued |
|---|---:|---:|---:|---:|
| `RARE_BY_RARITY` | 4,566 | 148 | 4,418 | 60 |
| `LOCAL_CONTEXT_PARALLEL` | 1,240 | 283 | 957 | 60 |

### `RARE_BY_RARITY`

Same candidate pool as the first queue's `SAME_LANGUAGE_AS_QUERY` channel (`unresolved_similarity_candidates.jsonl`), re-ranked by ascending distinct-document-count instead of descending sequence length. Nothing is reclustered and no hash the first queue depends on is touched. Ranked by rarity, most of the top of this queue is single-sign material, largely Sumerograms — the population named in `reports/phase5_p4e2_queue_policy_ratification.md`.

### `LOCAL_CONTEXT_PARALLEL`

A genuinely new clustering channel (`scripts/phase4_unresolved_clustering.py --local-context`): occurrences with no same-language sequence peer, grouped instead by the single immediately-adjacent attested token on each side. Measured before choosing the window (`reports/phase5_second_queue.md`): requiring two full tokens collapses the yield from 4,089 occurrences to 73. Ranked by descending distinct-document-count — the opposite bias from `RARE_BY_RARITY`, because this channel's value is a well-supported SLOT, not a rare CONTENT.

## What this queue does not do

- The deferred `minimum_sequence_length` rule from `configs/p4e2_queue_policy.json` is **not applied** in either channel here — `RARE_BY_RARITY` exists specifically to admit what that rule's sibling (length-descending ranking) suppresses, and `LOCAL_CONTEXT_PARALLEL` clusters carry no single "cluster sequence" for the rule to test.
- `--language` selection and a `CROSS_LANGUAGE_PARALLEL`-style channel are not implemented for this queue. Both are straightforward extensions of the first queue's existing machinery if wanted; not built here because neither was named in the two populations this queue was scoped to close.
- **Queue size (60/channel) is inherited, not re-ratified.** The first queue's own P4-E2 report flags this as still open; this queue did not resolve it, only reused the same provisional default.

## Payload

- `Phase4/phase4_out/workbench_ui_out/workbench_second_queue.js` — 3.10 MB
- content hash `571bb93bec2942de00cd5a1ca9239a9b6250705baa46c813c6e4deae74319dd3` (stable across rebuilds)
- file hash `1523f1b883a5c257ff1565ff2eb7c38e17c7ba5c2a11633927d7819f159bb9a5` (moves with the clock; the records carry their own provenance)

## Source artifacts (unmodified)

- `occurrences_logical_sha256`: `fd387b97a9aeb1cb9b7e9a89f3b20f8b015ef50af524695cec6567b64b191f47`
- `contract_version`: `1.1.0`
- `SAME_LANGUAGE_AS_QUERY_candidates_logical_sha256`: `33c3cff9985a4ee26716515d3b764b2b1f812328a93ca0ffa195dce711f3c21b`
- `LOCAL_CONTEXT_PARALLEL_candidates_logical_sha256`: `96779e1a91c2edb5342303890e592bd7a29bc93e9e47774941f16c7a63172a67`

## Standing display rules for any interface built on this queue

1. No count or member total may be presented as a probability.
2. Contradictory evidence attached to a proposal is always rendered.
3. Withhold judgment is always available.
4. The screen states that the queue is a subset, with these counts.
5. This queue and the first queue are separate views; a specialist session should say which one produced a given judgment.
