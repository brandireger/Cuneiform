# Combiner on Task B (joins / duplicates / pooled) — pre-registered protocol

**Status: PRE-REGISTERED 2026-08-04, written and committed BEFORE the run.**
Training-free; dev split only; test never loaded.

## Why

`reports/phase5_bm25_combiner_results.md` measured BM25 + frozen CANINE on
**Task A only**. Two reasons that is not where the question ends:

1. **A standing project decision requires it.** `AGENTS.md`: Task B positives
   are of two kinds, and the project must "ALWAYS evaluate and report
   joins-only, duplicates-only, and pooled — the full three-way matrix for
   every model." A combiner reported on Task A alone is not reported.
2. **Task B is where the shipping system lives and where the headroom is.**
   `P5_CLOSEOUT.md` records BM25-retrieve-deep as the shipping
   retrieval+ranking stage, with dev joins recall@1 0.6758 and **duplicates
   0.3727** — the weakest published retrieval number in the project.

The question: **does the Task A gain (+0.0462) transfer to pairwise
matching, and does it transfer differently to joins than to duplicates?**

Those two populations have different reasons to respond. A join partner is a
physically adjacent piece of the same tablet, so the shared signal is short,
local, and often damaged at the seam. A duplicate witness is a different copy
of the same composition, so the shared signal is long stretches of similar
wording. A character-level encoder has an obvious reason to help the second
and much less reason to help the first, and the design must let those two
answers differ rather than pooling them into one.

## Design

Same machinery, imported not reimplemented: dev fragments from
`phase5_ladder_screen.load_dev_fragments`, frozen CANINE embeddings, the
`phase5_bm25_combiner` fold assignment, α grid, and paired bootstrap.
Ranking goes through `eval_harness.run_retrieval`'s `precomputed_scores`
path — added for this, mirroring the parameter `run_task_a` already carries,
so self-exclusion and the H1 same-family exclusion stay the code BM25 goes
through.

- **Queries and candidate index**: the dev fragment set, matching the screen
  and the Task A combiner. Declared, not assumed: this is a *dev-only index*,
  so absolute numbers are not comparable to the published test-side
  `full_distractor` figures.
- **Positives**:
  - *joins* — join pairs whose members are both in the dev fragment set,
    from `eval_harness.build_join_positives`;
  - *duplicates* — `build_duplicate_positives(..., split="dev")`, real
    compositions only, join pairs removed;
  - *pooled* — the union, per the standing three-way rule.
- **Folds**: the same composition-level folds as the Task A combiner, so α is
  fit on queries from compositions disjoint from the ones it is applied to.

## Pre-registered reporting rule

> **All three cells are reported with their per-query paired bootstrap CI,
> whatever they say.** No cell may be omitted, and the pooled number may not
> stand in for a cell that disagrees with it.

Primary metric: held-out recall@1, paired per query against BM25 on the
identical query set, plus recall@10 (Task B's published numbers quote it and
it is the metric a reranking cascade actually consumes).

**No advance/withdraw decision attaches to this run.** It is a
characterisation of where the combiner helps, feeding the owed Gate-3
proposals. Declared in advance so no threshold can be chosen after seeing
which cell moved.

Stated expectation, recorded before the run so it can be wrong:
**duplicates should benefit more than joins.** If joins benefit more, that is
the interesting result and must not be smoothed over.

## Limitations carried forward

Dev-only index and dev-only queries; one seed; join query counts are small
(the published dev joins n=182 is against a different index, so this run's n
will differ and is reported, not assumed). Nothing here licenses a test-side
claim or authorizes training.
