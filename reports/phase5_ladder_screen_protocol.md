# Withdrawn-rung screening protocol — PRE-REGISTRATION

**Status: AWAITING RATIFICATION (Ixca). Nothing has been run.**

`reports/phase5_model_ladder_amendment.md` withdrew rungs 3 (ByT5), 4
(CANINE) and 6 (XLM-R/mT5) from publication scope. Its evidence base is two
failures of a **from-scratch, 12.8M-parameter, sign-level** architecture. The
withdrawn rungs differ in the one respect that matters most — they bring
**transfer from large-scale pretraining** — so the amendment rests on an
inductive step that nothing has measured.

Evidence points the other way too, and the amendment underweights it:
**Yavasan & Gordin published T5-lineage results on this same corpus** at the
target venue. That is direct reason to think a T5-family model does something
useful with Hittite transliteration.

This protocol closes that gap cheaply, and it is the evidence-gathering the
amendment's own reinstatement clause anticipates. It does not revert the
amendment; either outcome improves it.

## The question

**Does any withdrawn rung's pretrained representation carry usable signal for
Hittite transliteration — enough to justify the full rung?**

## What is deliberately NOT done: a short fine-tune

The obvious screen — train each candidate briefly and compare — is the exact
mistake this project made twice in the last three days. The batch-16 P4-F
arms looked meaningfully worse than D14 for reasons unrelated to the
hypothesis (half the training budget), and the ~80-example training evals
read 0.8839 against a true 0.7263. An under-trained ByT5 would look bad for
reasons having nothing to do with its potential, and we would wrongly feel
vindicated.

**Every stage below is training-free.** There is no training budget to
confound, so the screen cannot repeat that error.

## Stage 1 — tokenization fertility (CPU, minutes)

For each candidate tokenizer, over the non-test corpus rendering:

- tokens emitted per sign-level token (fertility ratio);
- fraction of corpus signs that survive as a single token vs. shatter;
- unknown/byte-fallback rate;
- resulting sequence lengths against each model's position limit.

Purpose: a candidate whose tokenizer shatters `ḫa-at-tu-ša` into
near-noise is structurally unsuited regardless of pretraining, and that can
be established for the cost of a CPU minute. **Diagnostic only — Stage 1
cannot advance or eliminate a candidate on its own**, it only characterises
what Stage 2 is measuring.

## Stage 2 — frozen-embedding Task A probe (GPU inference, <1h total)

**No fine-tuning. Pretrained weights, forward pass only.**

- Embed each dev fragment by mean-pooling the encoder's final hidden states
  (ByT5: encoder only; CANINE: encoder; XLM-R/mT5: encoder, mean-pool over
  non-pad positions).
- Rank compositions by cosine similarity using **`eval_harness.run_task_a`**,
  the existing leave-one-out protocol — parent-doc and docID-family
  exclusions, best-scoring-fragment-per-composition ranking, single-witness
  exclusions, all unchanged. `run_task_a` will gain an additive
  `precomputed_scores` parameter so a cosine matrix can be supplied; the
  ranking and exclusion logic is NOT reimplemented (AGENTS.md's standing rule,
  and the direct cause of the E2 defect).
- Report recall@1, recall@5, MRR, and the chance level.

### The reference is computed in the same run, not quoted

The published BM25 Task A recall@1 of **0.7831 is test-side** and therefore
unusable here — test stays untouched (cleanroom rule 1), and this project has
already been bitten once this week by comparing across populations (the D14
0.7461 clause). **BM25 will be run on the identical dev-side query set, in
the same execution, and its recall@1 pinned as `R_bm25` BEFORE any candidate
is embedded.**

Absolute numbers from this screen are therefore **not** comparable to the
published test-side figures. Only the within-run comparison is meaningful.

## Pre-registered decision rule

Fixed now, before any candidate is scored:

| outcome | rule |
|---|---|
| **ADVANCE** to a full Gate-3 proposal | frozen recall@1 **≥ 0.50 × `R_bm25`** |
| **CONFIRMED WITHDRAWN** | frozen recall@1 **< 0.50 × `R_bm25`** |

**Why the bar is deliberately generous.** A frozen probe is *biased against*
the candidates: models that would shine after fine-tuning can look mediocre
with frozen features. A weak result is therefore weaker evidence than a
strong result is — the asymmetry is real, and it is stated here rather than
discovered afterwards. Half of BM25's dev performance, with no fine-tuning at
all, is a low bar on purpose. A candidate clearing it would very likely beat
that bar comfortably once trained.

`R_bm25` is pinned from the BM25 run before candidates are touched, so fixing
the rule as a ratio does not constitute peeking.

## Candidates

| rung | model | params |
|---|---|---|
| 3 | `google/byt5-small` | ~300M |
| 4 | `google/canine-s` | ~132M |
| 6 | `xlm-roberta-base` | ~270M |
| 6 | `google/mt5-small` | ~300M |

## What this does NOT establish

- **A negative result here does not prove a candidate would fail
  fine-tuned.** See the asymmetry above. It establishes that the pretrained
  representation carries little usable signal *without adaptation*, which is
  the honest and limited claim.
- **A positive result is not a result.** It advances the rung to a proposal;
  it is not a measurement of that rung's performance and may not be cited as
  one.
- **Contamination is a live risk if a candidate scores well.** TLHdig is
  openly licensed and on Zenodo; web-crawled pretraining corpora may contain
  it. A strong frozen score could reflect memorisation rather than
  representation. This must be investigated before any published claim, and
  is flagged now so a good result is not taken at face value.
- Everything here is `[PROBE — not for citation]`.

## Evidence policy and gating

- **No training.** Gate 3 gates GPU *training*; this is inference on
  downloaded weights. If the ratifier reads it otherwise, it stops here.
- **Dev split only.** Test is never loaded. `lib/contracts.assert_no_test`
  applies as everywhere else.
- **External pretrained weights introduce MODEL_DERIVED knowledge from
  outside the corpus.** These artifacts are screening diagnostics that never
  reach an expert-facing prediction, and are quarantined as such. Any future
  use in a prediction path requires registration under
  `configs/evidence_registry.yaml`.
- **Dependencies stay quarantined.** `transformers` and model downloads
  (~2–3 GB) go in a separate `requirements-screen.txt`, not the pinned
  `requirements.txt`, until a rung is actually reinstated.

## Budget

| stage | cost |
|---|---|
| engineering | ~1 session |
| Stage 1 | CPU, minutes |
| Stage 2 | GPU inference, <1h total for all four models (dev pool is ~880 fragments) |
| downloads | ~2–3 GB, one-off |

Against 2–4 engineering sessions plus 6–12 GPU hours for a *single* full
rung. The screen is roughly an order of magnitude cheaper than the decision
it informs.

## What ratification authorizes

Stages 1 and 2 as described, and nothing further. A candidate that ADVANCES
gets a **separate Gate-3-style proposal** — hypothesis, pre-registered
falsifier, config, budget, non-colliding checkpoint paths — which is a
distinct ratification. Advancing is not authorization to train.
