# P4-F Stage 1 — language-conditioned pretraining: the falsifier verdict

**Status: COMPLETE 2026-08-03. Pre-registered hypothesis REJECTED.**
**Every number here is `[PROBE — not for citation]` per Gate 4, regardless of
outcome.**

> **SUPERSEDED 2026-08-04 — the corrected rerun is
> `reports/phase4_p4f_stage1_matched.md`; read it before citing anything
> here.** Both arms below trained on HALF D14's examples. At matched config
> the conditioning effect drops from +0.0282 to **+0.0073 with a CI that
> includes zero**, and the verdict is still REJECTED but on the OTHER clause
> (margin not met; arm B now clears D14). The numbers below remain valid as a
> half-budget measurement and are retained as a training-budget ablation.
>
> **SUPERSEDED IN ITS EXPLANATION, 2026-08-03 — read
> `reports/phase4_p4f_baseline_diagnostic.md` before citing anything below
> about D14.** The follow-up investigation found the cause of arm A's
> underperformance, and it is none of the three candidates this report
> lists: **both arms trained at `mlm_batch_size`/`boundary_batch_size` 16
> against D14's 32, so they saw exactly 50% of D14's examples.** That is a
> configuration defect in the Stage 0 integration, confirmed from D14's own
> checkpoint.
>
> The **arm A vs arm B comparison below is unaffected** — both arms ran under
> byte-identical config, so the +0.0282 conditioning effect stands. What is
> affected is the falsifier's second clause: "arm B must exceed D14's
> 0.7461" required a model trained on half the examples to beat one trained
> on twice as many. The REJECTED verdict stands as a matter of
> pre-registration, but its *explanation* is a config error in this session's
> integration, not a finding about language conditioning.

Authorized by `reports/phase4_p4f_gate3_proposal.md` (RATIFIED 2026-08-02),
which permits Stage 0 and the two named Stage 1 runs and nothing further.
Stage 2 remains unauthorized, and this rejection does not change that.

## The verdict, against the rule as written

Proposal §3 pre-registered two conditions, joined by `or` on the rejection
side: arm B must exceed arm A by **at least +0.02 `in_doc` AUC**, **and**
must exceed **D14's own historical `in_doc` AUC (0.7461)**. Failing either
rejects the hypothesis.

| | arm A (unconditioned) | arm B (conditioned) | delta |
|---|---|---|---|
| **`in_doc` AUC** | **0.6981** | **0.7263** | **+0.0282** |
| cross_genre AUC | 0.8729 | 0.9068 | +0.0339 |
| random AUC | 0.8388 | 0.9039 | +0.0651 |
| pooled AUC | 0.7475 | 0.7787 | +0.0312 |

- Margin condition: **MET** on the point estimate (+0.0282 ≥ +0.02).
- D14 condition: **NOT MET** — 0.7263 < 0.7461.
- **Therefore: REJECTED.**

Per §3, Stage 2 is not authorized by this result. Pursuing the remaining
charter comparisons requires a new proposal informed by what follows.

## What actually happened, stated precisely

**Conditioning helped, consistently and measurably.** Arm B beats arm A on
every negative tier and on the pooled metric. The paired bootstrap 95% CI on
the `in_doc` difference is **[+0.0144, +0.0424]**, which excludes zero: the
effect is real, not sampling noise.

Two honest qualifications on that same interval:

1. The CI's lower bound (+0.0144) sits **below** the +0.02 margin. We can be
   confident conditioning helps; we cannot be confident the effect is as
   large as +0.02. The point estimate clears the bar and the interval does
   not.
2. One seed per arm. Proposal §8 already said this in advance: a single seed
   is not a robustness claim, and nothing here is evidence about seed
   variance.

**What failed is the absolute bar, not the conditioning effect.** Arm A —
the control — lands **below D14 on every single tier** (in_doc 0.6981 vs
0.7461; cross_genre 0.8729 vs 0.9006; random 0.8388 vs 0.9473; pooled 0.7475
vs 0.7904). Arm B adds its ~+0.03 on top of that lower baseline and still
does not reach D14. D14 is simply the better-trained model here: at step
59,500 its dev mlm loss was 3.8778 and span-exact 0.2117, against arm B's
4.0728 and 0.1565.

This is reported as a finding, **not** as a reason to revisit the rule. The
falsifier was fixed before any run precisely so that a result like this one
could not be renegotiated after seeing it — the same discipline that kept
P2-E9's target-sensitivity sweep from being presented as a proposal.

## Why arm A underperforms D14 — candidate explanations, none confirmed

Recorded so a follow-up proposal starts from evidence rather than from
scratch. These are hypotheses; this session tested none of them.

- **Different training data.** D14 rendered language-blind, admitting every
  line. Both Stage 1 arms admit lines under `MULTILINGUAL_CONDITIONED`,
  which refused **7,610 lines not present in the Gate 2 language dataset**
  (2.1% of lines) plus 31 with unresolved lexical language. Less data is the
  most economical explanation for a uniformly weaker model, and it applies
  to arm A and arm B equally, so it does not touch the A-vs-B comparison.
- **Different seed.** 20260802 here vs D14's 20260722, one draw each.
- **Different dev pool.** The evaluation pool is the 883 dev fragments
  surviving the same admission rule, not D14's language-blind dev pool. The
  *protocol* is identical (see below); the *population* is not.

The third point is the one that most limits the D14 comparison, and it was
not foreseeable from the proposal text: the falsifier's second clause
compares arm B against a number computed on a different fragment population.

## Protocol fidelity — checked, not assumed

Proposal §3 required measurement "the same way `Archive/reports/
pretrain_report.md` §3 measured D14 (fresh pass, n≈1920, `in_doc` tier
specifically)". `scripts/phase4_p4f_stage1_eval.py` reproduces that
construction, and the check that it did so is exact rather than approximate:

> D14's report: `in_doc` tier, 938 positives + 711 negatives = **1,649** of
> **1,920** total.
> This evaluation: `in_doc` tier n = **1,649**, total n = **1,920**.

The tier composition matches to the example, under a different seed. The
`in_doc` AUC numbers are therefore comparable as *measurements*; the caveat
above is about the population they are measured on, not the method.

## Why the verdict was not read off the loss curve

Training-time evals run `n_batches=5` at batch 16 — at most ~80 boundary
examples each, of which `in_doc` is a fraction. Arm A's consecutive evals
read 0.830, 0.807, 0.802, 0.788, 0.799: a ~4-point spread with no trend,
**twice the size of the effect the falsifier is trying to detect**. Arm B's
final training eval read 0.8839, which would have suggested a far larger
gap than the 0.0282 that survives proper measurement.

Reading a verdict from those rows would have repeated the mistake this
project already made once, when a dev-only P2-E9 run manufactured a
12.8-point transfer gap on 55 spans that collapsed to 0.0 at scale
(`PHASE5_SUCCESSOR_HANDOFF.md`, trap 2).

The comparison is also **paired**: boundary examples are built by an RNG
that never consults a model, so both arms are scored on the byte-identical
example set and the bootstrap resamples examples while recomputing both
arms' AUCs per replicate. The interval is an interval on the difference, not
two independent intervals eyeballed for overlap.

## Run provenance

| | arm A | arm B |
|---|---|---|
| tag | `multilingual_unconditioned_p4f` | `multilingual_conditioned_p4f` |
| conditioning | off | on |
| params | 12,817,991 | 12,821,063 (+3,072) |
| steps | 60,000 | 60,000 |
| wall clock | 6.37 h | 2.98 h |

Both arms: seed 20260802, identical architecture, identical data (21,013
train+discovery fragments, 2,042,938 tokens, verified byte-identical shared
manifest blocks). The wall-clock difference is GPU contention from other
desktop processes, not a property of either arm — arm A ran overnight
against competing applications at times as slow as 0.19 steps/s, and both
arms ran at ~5.6 steps/s when the GPU was clear.

`runs/pretrain_base/` (D14) was never opened for writing; `--tag base` is
refused by the script.

### Tracer (proposal §9), run before either GPU run started

1. Language-embedding table not collapsed at init — PASS (worst pair cosine
   similarity 0.2932).
2. Conditioning measurably changes the forward pass — PASS (max abs
   hidden-state difference 1.2838 vs constant-language input).
3. Manifests differ exactly where expected — PASS on synthetic canaries
   **and** re-run against the two real manifests: shared block byte-identical
   across arms, arm block differing in exactly the five expected keys.

A known provenance wrinkle: arm A's manifest records git commit `884f790`
because the Stage 0 integration was committed (as `9415a4b`) after arm A
started. The working tree was identical in content at both points — the
commit recorded what was already on disk — but the recorded hash points at a
tree that does not contain the training script. Arm B's manifest records the
correct commit. Stated rather than patched: an artifact is not hand-edited
after the fact.

## What this does not establish

- **Not evidence about BM25.** Phase 1's finding that BM25 leads this
  architecture family decisively is untouched. Beating an unconditioned
  sibling is not beating the incumbent.
- **Not a robustness claim.** One seed per arm.
- **Not promotable.** Gate 4 keeps every number here at `[PROBE — not for
  citation]`, and no downstream P4-G rerun against these checkpoints is
  authorized.
- **Not a measurement of the multilingual population's ceiling.** Only 6.3%
  of training fragments (1,314 of 21,013) are genuinely multilingual, and
  80.6% of input positions carry a lexical language (Hit 72.0%, Hur 3.2%,
  Akk 3.0%). This bound was measured and recorded *before* the result, not
  fitted to it.

## Artifacts

- `scripts/phase4_p4f_pretrain.py` — the two runs
- `scripts/phase4_p4f_stage1_eval.py` — the falsifier measurement
- `Phase4/phase4_out/p4f_stage1_falsifier.json` — full result payload
- `runs/pretrain_multilingual_{unconditioned,conditioned}_p4f/` — checkpoints,
  loss curves, manifests (git-ignored, local only)

## Validation

```
python -m unittest discover -s tests      # 346 pass
ruff check lib scripts tests demo         # clean
python lib/contracts.py                   # 20/20
python scripts/phase4_p4f_conditioning_tracer.py   # 3/3
```
