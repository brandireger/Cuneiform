# Phase 4 — workbench review queue

**Policy:** `contentful_sequence_length_v2` · contract `unresolved_evidence_contract` v1.1.0 · every record `NOT_CORPUS_TRUTH`.

A queue is a **view** over ratified artifacts. Nothing here modifies an occurrence, a cluster proposal, or an accepted hash, and exclusion from the queue is not a judgment that a cluster is uninteresting.

## What the queue shows, and what it does not

| channel | proposals | contentless | below min length | eligible | queued |
|---|---:|---:|---:|---:|---:|
| `SAME_LANGUAGE_AS_QUERY` | 4,566 | 148 | 1,523 | 2,895 | 60 |
| `CROSS_LANGUAGE_PARALLEL` | 1,278 | 42 | 538 | 698 | 60 |

## Language selection

No language selection was applied, so this queue spans every language. Because ranking is by sequence length and Hittite is ~89% of lexical tokens, an unrestricted queue is overwhelmingly Hittite; the browser's language filter narrows *this* queue and cannot reach material the queue never contained. Use `--language Akk` (repeatable, or comma-separated) to build a genuine single-language session.

Contentful clusters available per language, before any selection — the ceiling on what a single-language session could contain:

| channel | `<UNRESOLVED>` | `Akk` | `Hat` | `Hit` | `Hur` | `Luw` | `Pal` | `Sum` |
|---|---|---|---|---|---|---|---|---|
| `SAME_LANGUAGE_AS_QUERY` | 2 | 65 | 58 | 2,619 | 129 | 15 | 1 | 6 |
| `CROSS_LANGUAGE_PARALLEL` | 5 | 209 | 206 | 665 | 372 | 81 | 26 | 13 |

**A single-language session is a review surface, not a prediction surface.** No per-language calibration exists. Nothing in this project licenses transferring a rate fit on one language to another, and the sparser languages here (`Pal`, `Sum`, `Luw`) do not have the composition mass to support a leakage-safe calibration at all.

### Two exclusions, with different standing

**Contentless sequences — RATIFIED 2026-07-31.** A cluster whose shared sequence is nothing but placeholder characters (` !().=?_x}̣…〈〉`) groups occurrences by the absence of a reading. That gives an expert nothing to compare. Measured: with the rule off, **21 of the 60 visible same-language clusters and 16 of 60 cross-language** become runs of `x` and `_`, displacing that many real clusters out of view — and because ranking is length-descending, the top item would be twelve underscores. Same-language channel: 148 cluster(s) covering 132,129 occurrence(s).

The character set was **widened on ratification**, on the line that *the editor's apparatus is contentless but anything that could have been on the tablet is not*. Derived empirically: every distinct sequence containing no alphabetic character was enumerated and classified. Digits were deliberately **kept** — `10` occurs alone in 81 documents and `d 10` in 70, which is the Storm God with a damaged determinative. See `configs/p4e2_queue_policy.json`.

**Sequences shorter than 2 signs — UNRATIFIED, DEFERRED 2026-07-31.** Ranking an earlier draft by document count alone put the single signs `a` (3,542 documents), `i`, and `e` at the top, so the rule has a real target. But it is currently a **no-op**: rebuilding with `--min-sequence-length 1` grows the eligible pool from 2,897 to 4,441 and leaves the queue content hash byte-identical, because single-sign clusters can never reach a 60-cluster window under length-descending ranking. Same-language channel: 1,523 cluster(s) covering 74,864 occurrence(s).

Its rare tail is **not** noise: 468 of the 592 same-language single-sign clusters with ≤2 documents are plain sign readings, largely Sumerograms (`numun`, `kalam`, `géštug`, `ibila`, `gišgigir`). Whether those should be reviewed is deferred to the second queue, ranked by rarity rather than length, where the decision would actually have consequences.

Both remain **display policies**, not findings. Nothing excluded here is judged uninteresting, deleted, or altered; illegible runs and single signs remain in the extraction at their accepted hashes, and a future queue keyed on surrounding context rather than shared surface form would reach them.

### Sampling within a cluster

At most **12** members are rendered per cluster, beside the cluster's true `member_count`. The interface must present this as a sample; a reviewed cluster is never a fully-seen cluster.

At most **60** clusters per channel are exported, to bound the browser payload. The remainder is unqueued, not rejected.

## Payload

- `Phase4/phase4_out/workbench_ui_out/workbench_review_queue.js` — 1.96 MB
- content hash `3e4e66ea8d7796739901d379b8bb86cc1cb130c7b19226b7857f2a70ae432bee` (stable across rebuilds)
- file hash `6fff90bd4f1a1e68b0cbeeca70742cae7aaa994a29b9a341b6ab68e0f06bcde0` (moves with the clock; the records carry their own provenance)
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
