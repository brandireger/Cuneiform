# Combiner on Task B — results

> **CORRECTIVE REVIEW 2026-08-04.** “Does not transfer” below is too
> categorical. The join and duplicate intervals are inconclusive and permit
> practically meaningful positive effects. The pooled any-relation result is
> a distinct positive estimand that must be reported alongside, not used as a
> substitute for, the two individual cells. See
> `reports/phase5_classical_control_review.md`.

**Status: COMPLETE 2026-08-04. Individual Task B strata are inconclusive;
pooled any-relation retrieval improves.** `[PROBE — not for citation]`; dev split only, dev-only
candidate index, test never loaded.

Executes `reports/phase5_combiner_taskb_protocol.md` (PRE-REGISTERED, committed
as `5b67048` before the run). Training-free.

## The three-way matrix, as the standing rule requires

BM25 + frozen CANINE, α fit per composition-level fold, paired per query
against BM25 on the identical query set.

| cell | n | metric | BM25 | combiner | Δ | 95% CI | CI excl. 0 | +gained / −lost |
|---|---|---|---|---|---|---|---|---|
| **joins** | 182 | recall@1 | 0.5604 | 0.5769 | +0.0165 | [−0.0165, +0.0495] | **no** | +7 / −4 |
| | | recall@10 | 0.7747 | 0.7802 | +0.0055 | [−0.0165, +0.0330] | no | +3 / −2 |
| **duplicates** | 865 | recall@1 | 0.5642 | 0.5838 | +0.0197 | [−0.0023, +0.0416] | **no** | +58 / −41 |
| | | recall@10 | 0.8821 | 0.8948 | +0.0127 | [+0.0000, +0.0254] | no (lower bound = 0) | +21 / −10 |
| **pooled** | 865 | recall@1 | 0.6821 | 0.7087 | +0.0266 | [+0.0058, +0.0486] | **yes** | +59 / −36 |
| | | recall@10 | 0.9017 | 0.9133 | +0.0116 | [−0.0012, +0.0254] | no | +21 / −11 |

Positives: 182 join pairs, 42,826 duplicate pairs, over 876 dev fragments.

## What this says

**The individual Task B effects are unresolved.** On Task A the combiner
gained +0.0462 with a CI clear of zero. On Task B, joins +0.0165 and
duplicates +0.0197 have intervals spanning zero but also permitting
practically meaningful positive effects. The evidence is weaker than Task A;
it is not evidence of equivalence or no transfer.

**The one significant cell is pooled — and that is exactly the cell the
standing rule exists to stop us reporting alone.** `AGENTS.md` requires the
full three-way matrix precisely because a pooled number can look like a
result that neither constituent supports. Pooled reaches +0.0266 with a CI
excluding zero, but nothing new appears there: its positive set is the union
of the other two, so it combines two same-signed effects over the larger
query set. Note also that pooled recall@**10** does *not* exclude zero
(+0.0116, [−0.0012, +0.0254]), so even the pooled cell is significant on only
one of its two metrics. **The honest headline is the two cells, not the
pool.** No mechanism beyond aggregation has been tested here, and none is
claimed.

**My pre-registered expectation is unconfirmed.** I predicted duplicates
would benefit more than joins, on the reasoning that a character-level
encoder has more to work with in long stretches of similar wording than at a
damaged seam. The direction is right (+0.0197 vs +0.0165) and the magnitude
of the difference is meaningless. The prediction was recorded so it could be
wrong; what actually happened is that it was untestable at this sample size.

## Why Task A and Task B might differ — a hypothesis, not a result

Task A ranks **53 compositions**, scored by their best-matching fragment.
Task B ranks **876 individual fragments**. Aggregating to composition level
gives a weak per-fragment signal several chances to surface: the combiner
only has to lift *one* witness of the right composition above the others.
That aggregation is absent in Task B, where the specific correct partner must
itself be lifted.

If that is what is happening, the combiner's value is real but concentrated
in coarse-grained retrieval rather than in the pairwise matching the shipping
system does. **This is untested** and would need a fragment-level Task A
diagnostic to confirm.

## Numbers here are NOT comparable to the published ones

Stated in the protocol in advance and worth repeating, because the deltas
look flattering against the published figures and are not measuring the same
thing:

| | published (P5_CLOSEOUT, dev) | here |
|---|---|---|
| joins recall@1 | 0.6758 | 0.5604 |
| duplicates recall@1 | 0.3727 | 0.5642 |

The published figures use a different index and query set; this run uses a
**dev-only candidate index of 876 fragments**. Duplicates are far easier here
(0.5642 vs 0.3727) because there are three orders of magnitude fewer
distractors. That also means **this setup may compress exactly the headroom
the combiner would exploit** at full-corpus scale — a plausible reason the
Task B effect is small here that this run cannot rule in or out.

## Method notes and limitations

- Ranking goes through `eval_harness.run_retrieval`'s new `precomputed_scores`
  path, so self-exclusion and the H1 same-family exclusion are the same code
  BM25 goes through. Verified both ways in `tests/test_phase4_p4f_pretrain.py`:
  handed BM25's own matrix, that path reproduces the BM25 path exactly, and a
  misshapen matrix fails closed.
- **The joins cell is small and its fit is noisy.** 182 queries across five
  folds is ~36 per fold, and the selected α reflects it: `[0.75, 0.05, 0.75,
  0.75, 0.75]` — fold 1 fell back to near-BM25. Duplicates and pooled were
  stable (`[0.5, 1.0, 0.4, 0.5, 0.5]`).
- The combiner is not free here either: 41 duplicate queries and 4 join
  queries regress at recall@1.
- One seed, one fold assignment, dev only. No test-side claim, no
  authorization to train.

## Consequence for the owed Gate-3 proposals

Narrower than the Task A result alone suggested. A rung-4 proposal must now
say **which task** it expects to improve, and cannot cite +0.0462 as though
it were a general retrieval gain — on pairwise matching, the same combiner
delivers roughly half that, with intervals including zero in both reported
cells.
