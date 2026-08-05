# Model-ladder amendment — rungs 3, 4 and 6 withdrawn from publication scope

> **CORRECTIVE REVIEW 2026-08-04.** The classical controls support a resource
> decision not to prioritize a retrieval Gate-3 proposal before the specialist
> session. They do not scientifically close pretrained adaptation or
> non-retrieval tasks. Relabeling shows that correct passage sequence is not
> necessary for aggregate gain; it does not exclude every memorised component.
> See `reports/phase5_classical_control_review.md`.

**Status: RATIFIED by Ixca 2026-08-04 — then PARTIALLY OVERTURNED the same
day by its own reinstatement mechanism. Read
`reports/phase5_ladder_screen_results.md` before citing anything here.**

> **What changed.** Ixca was uncomfortable that this amendment dismissed
> three untested candidates on the evidence of two failures of a different
> architecture family, and commissioned a training-free screen. Two of the
> three cleared its pre-registered bar:
>
> | rung | model | frozen recall@1 | vs BM25 0.6312 | outcome |
> |---|---|---|---|---|
> | 4 | CANINE-s | 0.3711 | 58.8% | **REINSTATED (screened in)** |
> | 6 | XLM-R | 0.3225 | 51.1% | **REINSTATED (screened in)** |
> | 6 | mT5-small | 0.2717 | 43.0% | withdrawal CONFIRMED |
> | 3 | ByT5-small | 0.2462 | 39.0% | withdrawal CONFIRMED |
>
> **Rung 3's withdrawal is now better supported than when written** — it
> rests on measurement rather than on an inductive leap. **Rungs 4 and 6 are
> reinstated to the extent of CANINE and XLM-R respectively** and each owes a
> Gate-3-style proposal before any training. Rung 6's two models split: XLM-R
> in, mT5 out.
>
> The claim-limits below are revised accordingly and are restated in the
> results report. The reasoning about *why* the amendment was made stands;
> its conclusion for two of three rungs did not survive measurement.
>
> **Second follow-up, same day** (`reports/phase5_bm25_combiner_results.md`):
> a pre-registered combiner test found the screen's oracle headroom is ~51%
> realizable — BM25 + frozen CANINE reaches held-out dev recall@1 0.6775 vs
> BM25's 0.6312, **+0.0462, 95% CI [+0.0254, +0.0682]**, with no training at
> all. That adds one claim the paper may now make and removes none; see the
> "may claim" list below.
>
> **Historical third follow-up, same day — corrected by the expert review.**
> `reports/phase5_char_ngram_control_results.md`: a classical character
> n-gram TF-IDF beats the frozen CANINE combiner 2.55× on Task A and is
> significant in every Task B cell where CANINE reached none. The former
> reading treated I = −0.0046, CI [−0.0162, +0.0058] as “adds nothing” and
> called rungs 4 and 6 answered. Current correction: the interval bounds a
> frozen +0.010 increment in this setup, but fine-tuned adaptation and
> non-retrieval tasks remain untested. The original inductive leap was still
> not acceptable.

`AGENTS.md` commits to a six-rung model ladder, "run in this order; every rung
reported," and `PHASE5_SUCCESSOR_HANDOFF.md` item 8 requires that commitment
to be "either completed or explicitly amended before final publication
claims." This is that amendment. It is the *explicit* branch, taken
deliberately, not the commitment quietly lapsing.

## What was run, and what was not

| rung | status | result |
|---|---|---|
| 1. BM25 / TF-IDF over sign n-grams | **RUN** | Task A test-side recall@1 **0.7831** (`bm25_sign`) / **0.8184** (`bm25_lemma`); dev joins recall@1 0.6758, recall@10 0.8077 |
| 2. Naive Bayes / MaxEnt (Tyndall replication) | **RUN** | MaxEnt all-token: approx-scale **0.390**, full-scale **0.164** (published 2012 figure: 0.67) |
| 3. ByT5 (small→base) | **NOT RUN — withdrawn** | — |
| 4. CANINE | **NOT RUN — withdrawn** | — |
| 5. From-scratch sign-level transformer | **RUN** | D14 (`in_doc` AUC 0.7461); P4-F arms at two budgets |
| 6. XLM-R / mT5 | **NOT RUN — withdrawn** | — |

## The decision

**Rungs 3, 4 and 6 are withdrawn from the current publication scope.** They
are not deleted from the design: a future proposal may reinstate any of them,
and the ladder text in `AGENTS.md` retains them as withdrawn rather than
removing them, so the original commitment stays legible.

## Evidence basis

Two independent neural attempts have now been measured against the classical
baseline, and neither displaced it:

1. **Phase 1 (D14/D15).** `P5_CLOSEOUT.md` records that BM25 beats the
   dense/boundary system decisively at every scale, that the D14 boundary
   head "does not discriminate true join partners from BM25-mined
   lexically-similar non-partners on real content" (0.468 vs 0.480, heavily
   overlapping), and that tier-A joins are "not solved, or approached, by
   anything built."
2. **P4-F Stage 1 (2026-08-02→04).** Language conditioning on the same
   architecture produced an effect of **+0.0073 `in_doc` AUC, 95% CI
   [−0.0063, +0.0196]** — indistinguishable from zero at a correct training
   budget (`reports/phase4_p4f_stage1_matched.md`).

A third data point cuts the other way and is worth stating, because it
weakens rather than strengthens the case for more neural rungs: **rung 2, the
classical Tyndall replication, also failed** — MaxEnt reached 0.390 at
approximate scale against the published 0.67. The ladder's cheap classical
rung underperformed its own published baseline, while BM25 substantially beat
both. Whatever is limiting performance here is not obviously "insufficiently
modern representation learning."

The compute budget is a single consumer GPU (`AGENTS.md`: "if a design
exceeds it, redesign"). ByT5-base at 580M parameters does not fit 12 GB for
full fine-tuning; ByT5-small would require a new evidence-registered
byte-level encoding path, because `encode_fragment_window()` — mandatory per
`AGENTS.md` — is sign-level by construction and a per-script bypass is the
exact shape of the E2 defect.

## What this forecloses — the limitation to state in the paper

This is the cost, and it must be stated plainly wherever the research
question is answered:

> The project's stated research question asks whether **modern representation
> learning** improves over classical methods. With rungs 3, 4 and 6
> withdrawn, that question is answered **only for the architecture family
> actually tested** — a from-scratch sign-level transformer with masked-span
> and boundary objectives, plus a contrastive bi-encoder over it. **No
> pretrained byte-level model (ByT5, CANINE) and no multilingual subword
> model (XLM-R, mT5) was evaluated.**

Specifically, the paper may **not** claim:

- that BM25 beats *neural methods* in general on this task;
- that transfer from large pretrained multilingual models does not help
  fragmentary Hittite;
- any comparison to Yavasan & Gordin's T5-lineage results as a *measured*
  contrast — only as related work.

It **may** claim, and should:

- that BM25 beats the domain-native from-scratch architecture family tested
  here, decisively and at every scale;
- that language conditioning of that architecture produced no measurable
  gain at matched training budget;
- that a classical MaxEnt replication underperformed its own published
  figure at both scales;
- that these are negative results reported in full, including the two
  pretraining runs whose falsifier was pre-registered and failed;
- **(added 2026-08-04, from the combiner test)** that a *frozen*, un-fine-tuned
  pretrained character-level encoder (CANINE-s) adds measurable signal to
  BM25 on the dev split — held-out Task A recall@1 0.6775 vs 0.6312, +0.0462,
  95% CI [+0.0254, +0.0682] — provided the claim carries its three
  qualifications: 32 of 865 queries regress, the effect requires a fitted
  down-weight (unfitted equal-weight fusion is 7–8 points worse than BM25
  alone), and it is dev-side only against a 0.6312 reference that is not the
  published test-side 0.7831;
- **(corrected 2026-08-04, from the contamination and classical controls)**
  that correct Hittite passage sequence is not necessary for the relabeled
  aggregate gain (retention 1.016); that a classical lexical ensemble is
  stronger in this dev setup; and that the CI for frozen CANINE's increment
  over the char arm has an upper endpoint below the declared +0.010 useful
  margin. Do **not** claim that relabeling excludes every memorised component,
  that pretrained adaptation is closed, or that the full +0.10 classical gain
  comes from n-gram context. The post-hoc decomposition attributes +0.052 to
  unigram TF-IDF fusion and a further +0.050 to the separately tuned bigram
  arm. All are dev-side exploratory results.

## Why now, and why not later

The binding constraint on the paper is not a missing model. It is the **first
specialist session** (handoff item 6), which no amount of GPU removes and on
which P7's headline deliverable — an expert-verified candidate list — depends
entirely. Running ByT5 before that session would spend 2–4 engineering
sessions plus 6–12 GPU hours to answer a question that is not blocking, while
the actual blocker stays untouched.

The scientific centre of the project — evidence-bounded reconstruction with
calibrated abstention — is complete and does not depend on any withdrawn
rung: same-line calibration at 0.90, cross-line at 0.75 under the ratified
`LAYOUT_AGNOSTIC` rule, P2-E10's negative result on cross-line multi-sign,
and the empty-middle display treatment.

## Reinstatement

Any withdrawn rung may be reinstated by a Gate-3-style proposal naming a
hypothesis, a pre-registered falsifier, a config, a GPU budget, and
checkpoint paths that cannot collide with frozen runs. If one is, ByT5-small
pointed at span-infilling is the recommended candidate: it is the direct
lineage comparison to Yavasan & Gordin, and D14's own span-infill numbers
(exact-match 0.413 at length 1, collapsing to ~0 by length 6) give a
ready-made head-to-head.

## Standing prerequisites carried forward

Recorded in `PHASE5_SUCCESSOR_HANDOFF.md` for whenever training resumes:
bf16 autocast and `torch.compile` on all arms from step 0 (approved
2026-08-03; safe now that no fp32 baseline is being matched), plus the two
numerically inert micro-fixes. And the process lessons from P4-F: read a
frozen baseline's config from its **checkpoint**, not from a script's
`DEFAULT_CONFIG`; verify sampler fidelity against the original; pair the
comparison; and never read a verdict off a training curve.
