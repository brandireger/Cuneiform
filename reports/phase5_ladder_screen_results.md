# Withdrawn-rung screen — results

> **CORRECTIVE REVIEW 2026-08-04.** Later follow-ups in this historical report
> overstate closure. The current bounded result concerns frozen mean-pooled
> retrieval only; it does not close fine-tuned adaptation, task-specific
> pooling, restoration, or span infilling. See
> `reports/phase5_classical_control_review.md`.

**Status: COMPLETE 2026-08-04. Two of the three withdrawn rungs clear the
pre-registered bar. The ladder amendment's inductive step was wrong.**
**Everything here is `[PROBE — not for citation]`.**

Executes `reports/phase5_ladder_screen_protocol.md` (RATIFIED 2026-08-04).
Training-free throughout: Stage 1 is tokenizer statistics, Stage 2 is a
forward pass over frozen pretrained weights. Dev split only; test never
loaded.

## The verdict, by the rule as pre-registered

`R_bm25` was pinned on the dev query set **before any candidate was
embedded**: recall@1 **0.6312** (recall@5 0.8578, MRR 0.7336, n=865, 11
single-witness compositions excluded). The ADVANCE threshold is therefore
0.50 × 0.6312 = **0.3156**.

| rung | model | recall@1 | 95% CI | recall@5 | MRR | % of BM25 | verdict |
|---|---|---|---|---|---|---|---|
| 4 | `google/canine-s` | **0.3711** | [0.340, 0.405] | 0.6994 | 0.5209 | 58.8% | **ADVANCE** |
| 6 | `xlm-roberta-base` | **0.3225** | [0.294, 0.354] | 0.6971 | 0.4857 | 51.1% | **ADVANCE** |
| 6 | `google/mt5-small` | 0.2717 | [0.240, 0.301] | 0.6486 | 0.4386 | 43.0% | CONFIRMED WITHDRAWN |
| 3 | `google/byt5-small` | 0.2462 | [0.218, 0.275] | 0.5908 | 0.4020 | 39.0% | CONFIRMED WITHDRAWN |

Chance recall@1 is **0.0189** (53 dev compositions). Every candidate is 13–20×
chance, so **none of these representations is signal-free** — the bar is
pragmatic (half of BM25), not a test of whether signal exists. That
distinction matters for how the withdrawn two are described.

## What this overturns

Ixca's discomfort with the amendment was correct, and the amendment's
inductive step does not survive contact with measurement. It withdrew three
rungs on the evidence of two failures of a *from-scratch, 12.8M-parameter,
sign-level* architecture. Two of the three carry enough signal, **with no
fine-tuning at all**, to clear a bar set at half of BM25's performance.

Two specific predictions in the record were wrong, and are worth naming
because they were stated confidently:

- **ByT5 was the recommended candidate** — "the one I'd pick," on the
  strength of AGENTS.md calling it the "primary neural candidate" and its T5
  lineage matching Yavasan & Gordin. It scored **lowest of the four** and is
  confirmed withdrawn.
- **CANINE was dismissed as adding least.** It scored **highest**, and is the
  only candidate whose confidence interval sits entirely above the threshold.

The lesson is narrow and worth keeping: architectural family reputation and
venue lineage predicted this ranking backwards. The cheap screen was worth
running precisely because the priors were wrong.

## Honest qualifications

**XLM-R's margin is thin.** Its CI is [0.294, 0.354] against a 0.3156
threshold — the interval straddles the bar. The pre-registered rule uses the
point estimate and it advances; that rule is not being revised after the
fact. But XLM-R's advance is materially less secure than CANINE's, whose
entire interval clears, and a Gate-3 proposal should say so.

**The frozen probe is biased against all candidates**, as the protocol stated
in advance. These numbers are a floor, not an estimate of fine-tuned
performance. That cuts both ways: it strengthens the two ADVANCE verdicts and
weakens the two withdrawals, which is why the withdrawn pair is described
above as "did not clear a pragmatic bar" rather than "carries no signal."

**Contamination is now a live concern**, exactly as pre-registered. TLHdig is
openly licensed and hosted on Zenodo; CANINE-s (multilingual Wikipedia) and
XLM-R (CommonCrawl) were trained on web-scale text that may include Hittite
transliteration from hethiter.net or the corpus itself. A strong frozen score
could reflect memorisation rather than representation. **This must be
resolved before any published claim** and is a required section of any Gate-3
proposal.

**Truncation was modest** after Stage 1's finding was acted on: 5.0% (CANINE),
11.1% (XLM-R), 15.4% (ByT5), 5.1% (mT5) at each model's native limit. A
uniform 512 cap would have truncated ~30% of ByT5 and CANINE; the limits were
raised **before any candidate was scored**, not after.

## Stage 1 — tokenization fertility (diagnostic only)

| model | fertility vs sign-level | mean len | p95 | >512 | UNK |
|---|---|---|---|---|---|
| `google/byt5-small` | 3.43× | 630 | — | 29.9% | 0 |
| `google/canine-s` | 3.08× | 565 | — | 26.4% | 0 |
| `xlm-roberta-base` | 1.33× | 244 | — | 11.1% | **8,429** |
| `google/mt5-small` | 1.53× | 281 | — | 13.5% | 334 |

Stage 1 could not advance or eliminate anything, and it is as well it
couldn't: **XLM-R emits 8,429 UNK tokens on Hittite transliteration and still
advanced.** Read on its own, that figure would have condemned the rung whose
representation turned out second-best. A structural-plausibility diagnostic is
not a performance predictor.

## Method notes

- **The reference was computed, not quoted.** The published BM25 Task A
  recall@1 of 0.7831 is *test-side* and unusable here. BM25 ran on the
  identical dev query set in the same execution. Dev has only 53 compositions
  against a larger test-side set, and BM25 scores *lower* here (0.6312) —
  absolute numbers from this screen are not comparable to published ones, and
  only the within-run comparison is meaningful.
- **One ranking implementation.** Candidates were scored through
  `eval_harness.run_task_a`'s new `precomputed_scores` path, so leave-one-out
  exclusions, best-fragment-per-composition ranking and single-witness
  handling are literally the same code BM25 goes through. Verified: handed
  BM25's own score matrix, that path reproduces the BM25 path's per-query
  records and aggregate exactly.
- Embeddings are mean-pooled final encoder hidden states over non-pad
  positions; ranking is cosine similarity.

## Addendum — do the advancing candidates add anything BM25 lacks?

**Not part of the pre-registered rule.** Written and run AFTER seeing the
verdicts, so it revises nothing; its purpose is to inform the Gate-3
proposals an ADVANCE requires. Same dev query set, same `run_task_a`
protocol.

CANINE and XLM-R are character- and subword-level. The most parsimonious
explanation for a frozen embedding retrieving compositions well is that it
captures *orthographic* similarity — which is what BM25 already does
lexically, and better. If a candidate is right exactly where BM25 is right,
it re-derives BM25's signal and a rung buys nothing.

| | CANINE-s | XLM-R |
|---|---|---|
| both correct | 243 | 225 |
| **only the candidate correct** | **78** | **54** |
| only BM25 correct | 303 | 321 |
| neither | 241 | 265 |
| of the candidate's correct answers, share BM25 also gets | **75.7%** | **80.6%** |
| oracle union recall@1 | **0.7214** | 0.6936 |
| oracle gain over BM25 (0.6312) | **+0.0902** | +0.0624 |

**Both readings are true and neither should be dropped.** The candidates are
largely *redundant* — three-quarters or more of what they get right, BM25
already had. But they are not *wholly* redundant: CANINE is right on 78
queries (9.0% of the set) where BM25 fails, and a perfect combiner would
reach 0.7214 against BM25's 0.6312.

That reframes what a rung is for. The interesting hypothesis is **not**
"a pretrained model beats BM25" — on this evidence it plainly does not, at
0.37 against 0.63. It is "**does BM25 + candidate beat BM25 alone?**", which
is a narrower, cheaper and more falsifiable question, and it matches Phase 1's
own conclusion that BM25-retrieve-deep is the shipping system and the real
question is what can be added to it.

Two cautions on the oracle figure. It is an **upper bound** assuming a
perfect per-query selector; a real combiner recovers only a fraction. And
~28–31% of queries (241 / 265) are missed by both, a hard core neither signal
reaches.

> **FOLLOW-UP, 2026-08-04 — the fraction is now measured.**
> `reports/phase5_bm25_combiner_results.md` fits a real combiner under a
> pre-registered rule: held-out recall@1 **0.6775 vs 0.6312, +0.0462, 95% CI
> [+0.0254, +0.0682]**, i.e. **51.2% of the +0.0902 oracle**, with frozen
> weights and no training. It also found that unfitted equal-weight rank
> fusion is 7–8 points *worse* than BM25 alone — the candidate helps only as
> a down-weighted tie-breaker — and that 32 queries regress. Read that report
> before writing either owed proposal; it changes what they must ask.
>
> **HISTORICAL SECOND FOLLOW-UP, 2026-08-04 — inference corrected later.**
> `reports/phase5_char_ngram_control_results.md`: a classical character
> n-gram TF-IDF reaches **+0.1179 on Task A (2.55× CANINE)** and is
> significant in **every Task B cell**, where CANINE reached none — and
> CANINE adds **nothing** on top of it (I = −0.0046, CI [−0.0162, +0.0058]).
> Historical verdict **CANINE_REDUNDANT**. Corrected review: the CI bounds a
> frozen increment of +0.010 in this setup but does not close fine-tuned
> adaptation or non-retrieval tasks. The recommendation not to prioritize a
> proposal before the specialist session is a resource decision. This screen was still worth
> running: it is what produced the candidates whose relabeling behaviour
> revealed the signal was character-level rather than linguistic, which is
> what motivated the classical control.

## What happens next — and what does NOT

**Advancing is not authorization to train.** Per the protocol, each ADVANCE
requires its own Gate-3-style proposal: hypothesis, pre-registered falsifier,
config, budget, and non-colliding checkpoint paths. Two are now owed, for
rung 4 (CANINE) and rung 6 (XLM-R). Neither has been written and no training
has been started.

On the addendum's evidence, those proposals should test **combination with
BM25, not replacement of it**, and should lead with CANINE — it has the
higher score, the only CI clearing the threshold outright, the larger
complementary set (78 queries), and the larger oracle headroom (+0.090).
A resolved contamination check is a prerequisite for both.

**`reports/phase5_model_ladder_amendment.md` must be revised.** Its withdrawal
of rungs 4 and 6 is contradicted by direct measurement; its withdrawal of rung
3 (ByT5) is now *better* supported than before, resting on evidence rather
than on an inductive leap. The paper's claim-limits change accordingly.

**mT5 and ByT5 stay withdrawn**, now on direct evidence. Note that rung 6 is
"XLM-R / mT5" as a single ladder entry and the two split: XLM-R advances,
mT5 does not. The rung is reinstated in respect of XLM-R only.

## Artifacts

- `scripts/phase5_ladder_screen.py`
- `Phase4/phase4_out/p5_ladder_screen.json`
- `scripts/phase5_ladder_screen_complementarity.py` (addendum, below)
- `Phase4/phase4_out/p5_ladder_screen_complementarity.json`
