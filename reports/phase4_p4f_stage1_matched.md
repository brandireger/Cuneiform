# P4-F Stage 1, corrected — the falsifier under a fair baseline

**Status: COMPLETE 2026-08-04. Pre-registered hypothesis REJECTED — on the
other clause this time.**
**Every number here is `[PROBE — not for citation]` per Gate 4.**

This is the rerun `reports/phase4_p4f_baseline_diagnostic.md` called for,
after that report found both original arms had trained on **half** D14's
examples (`mlm_batch_size` 16 against D14's 32). Both arms were retrained at
D14's actual config — 32 / 32 / warmup 2000, seed 20260722 — read from D14's
own checkpoint. Authorized by Ixca 2026-08-03 as covered by the existing Gate
3 ratification.

The falsifier, the evaluation script, the example set and its seed are all
**unchanged**, so every number below is directly comparable to the ones
already on record.

## The verdict

| | arm A (unconditioned) | arm B (conditioned) | delta |
|---|---|---|---|
| **`in_doc` AUC** | **0.7521** | **0.7594** | **+0.0073** |
| 95% CI on delta | | | **[−0.0063, +0.0196]** |
| margin ≥ +0.02 | | | **NOT MET** |
| arm B vs D14 0.7461 | | **above** | ✓ |

**REJECTED.** And the informative part: **the clauses swapped.**

| | margin ≥ +0.02 | arm B > D14 | verdict |
|---|---|---|---|
| batch 16 (defective) | **MET** (+0.0282) | **BELOW** (0.7263) | REJECTED |
| batch 32 (matched) | **NOT MET** (+0.0073) | **above** (0.7594) | REJECTED |

Both clauses have now been tested under conditions where they could pass.
Neither does, and not at the same time.

## The finding

**At a correct training budget, the conditioning effect is not
distinguishable from zero.**

| | delta (B − A), `in_doc` | 95% CI |
|---|---|---|
| batch 16 (defective) | +0.0282 | [+0.0144, +0.0424] — excludes zero |
| batch 32 (matched) | +0.0073 | **[−0.0063, +0.0196] — includes zero** |

The effect that looked real at half budget does not survive proper training.
The per-tier picture agrees: at batch 16, conditioning helped on *every* tier;
at matched budget it is mixed — arm B is **below** arm A on `cross_genre`
(0.8996 vs 0.9033), which is what noise looks like rather than a signal.

**What I cannot claim, and will not:** that the two deltas differ
significantly. Their confidence intervals overlap substantially
([+0.0144, +0.0424] against [−0.0063, +0.0196]), so "conditioning helps only
when the model is under-trained" is a *hypothesis consistent with these two
runs*, not an established result. Establishing it would need the
difference-of-differences measured directly, across seeds.

What *is* established, at one seed: at matched budget the effect's interval
includes zero, so this experiment does not demonstrate that language
conditioning improves boundary discrimination.

## The batch-size diagnosis is confirmed on the falsifier metric itself

All five models, scored on the same 1,920-example paired set:

| tier | D14 | b16 arm A | b16 arm B | **m32 arm A** | **m32 arm B** |
|---|---|---|---|---|---|
| `in_doc` | 0.7552 | 0.6981 | 0.7263 | **0.7521** | **0.7594** |
| cross_genre | 0.9139 | 0.8729 | 0.9068 | 0.9033 | 0.8996 |
| random | 0.8729 | 0.8388 | 0.9039 | 0.8579 | 0.8618 |
| pooled | 0.7996 | 0.7475 | 0.7787 | 0.7942 | 0.7986 |

**Matched arm A lands at 0.7521 against D14's 0.7552** — a gap of 0.003,
where the batch-16 arm A was 0.057 below. The diagnostic previously confirmed
the batch-size cause on training loss; this confirms it on the metric the
falsifier actually uses. The corrected unconditioned arm is, for practical
purposes, a reproduction of D14.

That also retires the last open question from the diagnostic: seed was the
only untested candidate, and matched arm A reproduces D14 while differing in
seed. Seed variance is therefore not large enough to explain the original gap.

## Why the first result inverted

The original run's apparently-real conditioning effect (+0.0282, CI excluding
zero) was measured between two models that were both under-trained. The
honest reading of the pair is that the extra language signal is worth
something when a model has not had enough data or compute to infer language
from context — and worth approximately nothing once it has. That is a
plausible mechanism, and it is stated as a candidate explanation rather than
a finding, per the CI caveat above.

## Consequences

- **Stage 2 remains NOT authorized.** Proposal §3 is explicit: a rejection
  requires a new proposal, not an automatic continuation.
- **A Stage 2 proposal is now harder to justify, not easier.** The original
  rejection could be blamed on a defective baseline. This one cannot: both
  arms are properly trained, arm A reproduces D14, and the effect's interval
  includes zero.
- **Any future proposal should lead with seed variance.** One seed per arm
  remains the binding limitation (proposal §8 said so before any run). With
  an effect this small, a single draw cannot settle it in either direction.
- **The batch-16 pair is retained**, not discarded. It is a valid measurement
  at half budget and now serves as an unplanned training-budget ablation —
  arguably the most interesting thing this line of work produced.

## What this does not establish

- **Not a robustness claim.** One seed per arm, both runs.
- **Not evidence about BM25.** Phase 1's finding that BM25 leads this
  architecture family is untouched.
- **Not promotable.** Gate 4 keeps every number `[PROBE — not for citation]`;
  no downstream P4-G rerun against these checkpoints is authorized.
- **Not a claim that conditioning is useless.** It is a claim that *this*
  experiment, at *this* scale, on *this* corpus, with 6.3% genuinely
  multilingual fragments, could not distinguish its effect from zero.

## Run provenance

| | matched arm A | matched arm B |
|---|---|---|
| tag | `multilingual_unconditioned_p4f` | `multilingual_conditioned_p4f` |
| config | 32 / 32 / warmup 2000, seed 20260722 | identical |
| params | 12,817,991 | 12,821,063 (+3,072) |
| steps | 60,000 | 60,000 |
| wall clock | 5.50 h | 9.93 h (GPU contention) |

Both under `configs/p4f_pretrain_config_d14matched.json`, written to
`runs/stage1_matched/`. The batch-16 runs in `runs/` are untouched, as is
`runs/pretrain_base/` (D14), which is opened read-only and never written.

Before the 17 h of GPU was committed, an 11,000-step probe at this config and
seed was run and compared against D14: it tracked to within 0.006 at step 500
and 0.021 at step 5,000, against the batch-16 arm's 0.211 gap at step 10,000.
That probe is retained separately in `runs/validation_b32/`.

## Artifacts

- `Phase4/phase4_out/p4f_stage1_falsifier_matched.json` — this result
- `Phase4/phase4_out/p4f_stage1_falsifier.json` — the batch-16 result, retained
- `Phase4/phase4_out/p4f_baseline_diagnostic.json` — D14 on this population
- `configs/p4f_pretrain_config_d14matched.json` — D14's real config
