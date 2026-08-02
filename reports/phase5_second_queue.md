# Phase 4/5 — the second queue

**Status: DONE 2026-08-02.** Closes handoff item 4 (data/export layer only
— see "What is deliberately not done" below). Two populations named across
three prior reports were structurally unreachable through the first queue
(`scripts/phase4_workbench_review_export.py`):

- `reports/phase4_p4e2_expert_interface.md`, open decision 3: **~13,900
  ungrouped occurrences** whose sequence is unique, so the first queue's
  exact-sequence clustering never forms a cluster from them at all.
- `reports/phase5_p4e2_queue_policy_ratification.md`: **468–599 rare
  single-sign clusters** (same-language, ≤2 documents) that exist as real
  clusters but can never reach a 60-cluster window under length-descending
  ranking, "the same build the P4-E2 report already anticipates."

Both are now data artifacts: `scripts/phase4_unresolved_clustering.py
--local-context` (a new clustering channel) and
`scripts/phase4_workbench_second_queue_export.py` (a new, separate export —
never a mode on the first).

## Why a separate script, not a mode on the first queue

`workbench_review_queue.js`'s `channels_logical_sha256` is a pinned
invariant elsewhere in this project (PHASE5_SUCCESSOR_HANDOFF.md: "if it
moves without a deliberate policy change, something altered what a
specialist sees"). The new export **imports** the first export's helpers
(`load_proposals`, `sequence_is_contentless`, `distinct_document_count`,
`build_line_index`, the ratified `CONTENTLESS_CHARS` set) rather than
duplicating them, but writes to its own path and never opens
`workbench_review_queue.js` for writing. Verified, not assumed: `git diff`
on the first queue's three output files is empty after every run in this
session.

## RARE_BY_RARITY

Reads the exact same candidate file the first queue's `SAME_LANGUAGE_AS_QUERY`
channel reads (`unresolved_similarity_candidates.jsonl`) — no reclustering,
no new hash for anything the first queue depends on. Only the ranking
differs: ascending `distinct_document_count`, then ascending member count
(both dimensions biased toward *less* evidence, the literal opposite of the
first queue's `rank_key`).

**A real bug found and fixed before shipping this.** The first pass at this
channel put punctuation-leading tokens (`'i`, `:a`, `_bu`, `(traces)`) across
the entire visible top of the queue. This is precisely the mistake
`reports/phase5_p4e2_queue_policy_ratification.md` already named once: "I
first eyeballed the rare single-sign tail and reported it as editorial
apparatus. That was wrong — I was reading an alphabetically sorted sample."
The cause here was structural, not a sampling accident: thousands of
clusters tie on `(distinct_document_count=1, member_count=2)` — the minimum
possible values — and the original tiebreak, `cluster_id`, inherits
`build_clusters()`'s own `sorted(buckets.items(), key=lambda item:
str(item[0]))` ordering, which is effectively alphabetical by sequence.
Fixed with a SHA-256-of-`(seed, cluster_id)` tiebreak (`tiebreak()`) —
deterministic and reproducible across reruns, but with no relationship to
sequence content, so it cannot reintroduce the bias. Measured before and
after on the top 60: punctuation-leading sequences went from effectively all
of the visible top-10 to 8 of 60 (13%), consistent with the ratified
finding that the rare tail is "79.1% plain sign readings." (Python's
built-in `hash()` was deliberately not used — it is randomized per process
unless `PYTHONHASHSEED` is pinned, which `reports/phase5_deferred_issues_sweep.md`
already flagged as a live, unresolved source of nondeterminism elsewhere in
this repo. A rebuild must produce the same queue every time.)

## LOCAL_CONTEXT_PARALLEL

A genuinely new clustering channel, not a re-ranking. Groups the ~13,900
occurrences with no same-language sequence peer by their immediate flanking
attested tokens instead of by their own content — the second of two channel
types `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` already names ("exact or
normalized sign sequence" vs. "local left/right textual context"); only the
first had been built before this.

**Window size was measured, not guessed.** Each occurrence already carries
6 tokens of left/right context (`CONTEXT_TOKENS` in
`phase4_unresolved_extraction.py`); the question was how many of those
tokens two occurrences must share on each side to count as the same
environment.

| window (tokens/side) | occurrences joining a cluster | clusters formed |
|---:|---:|---:|
| 1 | 4,089 of 13,901 (29.4%) | 1,240 |
| 2 | 73 (0.5%) | 35 |
| 3 | 8 | 4 |
| 4 | 4 | 2 |
| 6 | 2 | 1 |

Window=1 is the only viable choice among these — Hittite scribal formulae
are short enough that requiring two full flanking tokens on each side is not
"more precise," it is "empty." Both sides are required to match (not a
one-sided match): loosening to one side would recover more material at real
cost to precision, and the yield at window=1 with both sides required
(4,089 of 13,901) was already judged sufficient without loosening further.

**Contentless filtering applies to the context key, not the member's own
content** — the member's own content is inherently damaged/unresolved by
definition (that is why it is in the workbench at all), so testing *it* for
contentlessness would exclude the entire channel. Testing the *flanking*
context instead is the direct analogue of the first queue's rule. Measured
before deciding to apply it: without the filter, the largest clusters by
member count were `x`/`x` (133 members, 126 documents) and similar
damage-flanked-by-damage pairs — a "parallel" that is itself illegible tells
an expert nothing. 283 of 1,240 clusters (32% of members) carry a
contentless left or right key; excluded using the same ratified
`CONTENTLESS_CHARS` set imported from `phase4_workbench_review_export.py`,
not a new character-set decision.

**Ranked by descending document count** — the opposite bias from
`RARE_BY_RARITY`, and deliberately so: this channel's value is a
well-supported *slot* (many independent scribes landing on the identical
immediate environment), not rare content. The two channels solve different
problems and are not meant to agree on what "good" looks like.

## What is deliberately not done

- **No UI.** This closes the data/export layer named in the three source
  reports. `demo/workbench_unresolved_prototype.html` is a substantial,
  separately browser-verified interface
  (`reports/phase5_browser_verification.md`); wiring `window
  .WORKBENCH_SECOND_QUEUE` into it (or a new page) is presentation-layer
  work that needs its own review, not something to fold silently into a
  backend build.
- **`--language` selection and a cross-language variant** are not
  implemented for this queue. Both are straightforward extensions of the
  first queue's existing machinery (which this script already imports from)
  if wanted later; not built now because neither population this queue was
  scoped to close needed them.
- **Queue size (60/channel) is inherited, not re-ratified.** The first
  queue's own P4-E2 report already flags this as open
  ("`Queue size`... If the intent is broad coverage rather than depth, this
  should rise"). This queue reuses the same provisional default rather than
  deciding it twice.
- **The deferred `minimum_sequence_length` rule is not applied here.**
  `RARE_BY_RARITY` exists specifically to admit what that rule's
  length-descending sibling suppresses; `LOCAL_CONTEXT_PARALLEL` clusters
  carry no single "cluster sequence" for the rule to test in the first
  place. Neither is a ratification of the rule one way or the other — it
  stays `UNRATIFIED_DEFERRED` in `configs/p4e2_queue_policy.json`, unchanged.

## Validation

```
python -m unittest discover -s tests      # 312 pass (was 291; 21 new:
                                           # clustering + ranking/tiebreak/
                                           # contentless regression tests)
ruff check lib scripts tests demo         # clean
python scripts/phase4_unresolved_clustering.py               # unchanged
                                                               # output
                                                               # (verified
                                                               # byte-for-
                                                               # byte modulo
                                                               # provenance)
python scripts/phase4_unresolved_clustering.py --local-context
python scripts/phase4_workbench_second_queue_export.py
git diff --stat Phase4/phase4_out/workbench_ui_out/workbench_review_queue*  # empty
```
