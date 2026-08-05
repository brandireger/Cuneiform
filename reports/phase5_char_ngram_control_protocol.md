# Classical character n-gram control — pre-registered protocol

> **POST-RUN CORRECTION 2026-08-04.** This historical protocol incorrectly
> treated CI-includes-zero as redundancy. The script now preserves that
> historical verdict separately and applies the declared +0.010 margin to the
> CI upper bound for the current interpretation. See
> `reports/phase5_classical_control_review.md`.

**Status: PRE-REGISTERED 2026-08-04, written and committed BEFORE the run.**
Training-free; no pretrained weights; dev split only; test never loaded.

## Why this is now the decisive experiment

`reports/phase5_contamination_results.md` established that the combiner's
+0.0462 **survives destroying the Hittite language entirely** — retention
1.016 across five sign-vocabulary permutations. Whatever CANINE contributes
is therefore *not* knowledge of Hittite. It is generic character-sequence
similarity.

If that is right, a classical character n-gram model should recover the same
gain: no pretrained weights, no GPU, no contamination question, no rung.

## Two questions, the second decisive

**(a) Recovery.** Does BM25 + char-n-gram TF-IDF reach CANINE's +0.0462?

**(b) Increment — PRIMARY.** Does CANINE add anything *beyond* the classical
control? Measured as BM25 + char-n-gram + CANINE against BM25 + char-n-gram.

(b) is what decides whether either owed Gate-3 proposal is worth writing. (a)
alone could not: two methods can produce similar aggregate gains on different
queries.

## Design

Same machinery throughout, imported not reimplemented — the screen's fragment
loader, the Task A combiner's composition-level folds, α grid, `run_task_a`
path and paired bootstrap.

- **Candidate signal**: `TfidfVectorizer(analyzer="char")` over the same
  rendered fragment text CANINE was given, cosine similarity. `analyzer="char"`
  rather than `"char_wb"` deliberately: n-grams must span the spaces between
  signs, since cross-sign sequence is exactly the fuzzy-matching signal at
  issue.
- **n-gram range** is fitted like α, inside folds, from the declared grid
  `{(2,3), (2,4), (3,5), (4,6)}`. Declared now so the range cannot be chosen
  after seeing which one wins.
- **Combination**: `z(bm25) + α·z(char)`, and for (b) `z(bm25) + α₁·z(char) +
  α₂·z(canine)`, α from the existing pre-registered grid, ties to the
  smallest.
- Fit-set statistics: the TF-IDF vocabulary is fit over the dev fragment set,
  matching how BM25's statistics are fit in this harness. Noted as a known
  deviation from a fully held-out index, identical in kind to the one already
  declared for the Task A combiner.

## Pre-registered decision rule

Let `R = ` held-out recall@1 delta of BM25 + char-n-gram over BM25 alone, and
`I = ` held-out recall@1 delta of BM25 + char-n-gram + CANINE over BM25 +
char-n-gram.

> - **`I`'s 95% CI includes zero → CANINE IS REDUNDANT.** A classical
>   character model captures everything the pretrained encoder was adding.
>   Recommendation: withdraw rungs 4 and 6 again — this time on direct
>   evidence rather than an inductive leap — and report the char n-gram
>   result as the finding.
> - **`I`'s CI excludes zero and `I` ≥ +0.010 → CANINE ADDS SOMETHING
>   CLASSICAL METHODS DO NOT.** The owed proposals stay justified and must
>   quote `I`, not +0.0462, as their expected headroom.
> - Otherwise → **INCONCLUSIVE**, reported as such.

Secondary, reported regardless: `R`, and retention `R / 0.0462`.

## What a redundancy verdict would and would not mean

It **would** mean the pretrained-model line of inquiry is answered for this
task, cheaply and on direct measurement — a genuinely useful negative result,
and a better one than the original amendment's inductive dismissal.

It would **not** mean pretrained models are useless for Hittite generally, nor
would it speak to span-infilling, restoration, or any task other than the
retrieval measured here. It also would not retract the Task A combiner
result; it would reattribute it.

## Limitations

Dev only, one seed, one fold assignment. Task A only — the Task B picture is
already weak for the combiner
(`reports/phase5_combiner_taskb_results.md`) and is not re-measured here.
Nothing authorizes training.
