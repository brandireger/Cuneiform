# Classical character n-gram control — results

**Status: COMPLETE 2026-08-04. Verdict CANINE_REDUNDANT.**
**A classical n-gram model beats every pretrained candidate, on
every task cell, with no GPU and no pretrained weights.**
`[PROBE — not for citation]`; dev split only, test never loaded.

> **CORRECTION 2026-08-04, from `reports/phase5_bigram_control_results.md`.**
> This report concluded the useful signal is **character-level**. That
> conclusion was overstated and its design could not support it. A sign-bigram
> control run afterwards recovers **86.3%** of the gain (+0.1017 of +0.1179),
> and character granularity's increment over it is **+0.0162, 95% CI
> [−0.0012, +0.0324] — includes zero**.
>
> **Every measurement below stands.** What changes is the explanation: what
> helps is **n-gram context beyond single signs**, not character granularity
> specifically. Sign bigrams and character n-grams are near-substitutes.
> Read "character n-gram" below as "an n-gram context feature, of which this
> is one of two near-equivalent implementations."

Executes `reports/phase5_char_ngram_control_protocol.md` (PRE-REGISTERED,
committed as `2580d85` before the run). Training-free.

## Task A — the pre-registered rule

| arm | held-out recall@1 | Δ vs BM25 | 95% CI | +gained / −lost |
|---|---|---|---|---|
| BM25 alone | 0.6312 | — | — | — |
| BM25 + **frozen CANINE** | 0.6775 | +0.0462 | [+0.0254, +0.0682] | +72 / −32 |
| **BM25 + char n-gram TF-IDF** | **0.7491** | **+0.1179** | [+0.0913, +0.1445] | **+125 / −23** |
| BM25 + char n-gram + CANINE | 0.7445 | +0.1133 | — | — |

- **(a) Recovery**: `R = +0.1179`, retention vs CANINE **2.55×**. The
  classical control does not merely recover the pretrained model's gain — it
  is two and a half times larger, with a far better gain/loss ratio
  (125:23 against 72:32).
- **(b) Increment — PRIMARY**: `I = −0.0046`, 95% CI **[−0.0162, +0.0058]**.
  **Includes zero, point estimate negative.**

**Verdict by the pre-registered rule: CANINE_REDUNDANT.** Adding a frozen
pretrained character encoder on top of character n-grams contributes
nothing — nine queries gained, thirteen lost.

`(4, 6)` was selected in **all five folds**, and α_char at 0.75 in four of
five. This is not a fragile configuration.

## Task B — and here it is not close

Run through the same protocol as the CANINE Task B measurement
(`reports/phase5_combiner_taskb_results.md`), with `(4,6)` fixed rather than
refitted, so this tests transfer of a settled configuration rather than a
second search.

| cell | n | metric | BM25 | + char n-gram | Δ | 95% CI | CANINE Δ (same cell) |
|---|---|---|---|---|---|---|---|
| **joins** | 182 | recall@1 | 0.5604 | **0.6703** | **+0.1099** | [+0.0604, +0.1648] | +0.0165 *(ns)* |
| | | recall@10 | 0.7747 | 0.8626 | +0.0879 | [+0.0495, +0.1319] | +0.0055 *(ns)* |
| **duplicates** | 865 | recall@1 | 0.5642 | **0.6520** | **+0.0879** | [+0.0601, +0.1156] | +0.0197 *(ns)* |
| | | recall@10 | 0.8821 | 0.9179 | +0.0358 | [+0.0231, +0.0509] | +0.0127 *(ns)* |
| **pooled** | 865 | recall@1 | 0.6821 | **0.7919** | **+0.1098** | [+0.0844, +0.1353] | +0.0266 |
| | | recall@10 | 0.9017 | 0.9341 | +0.0324 | [+0.0197, +0.0462] | +0.0116 *(ns)* |

**Every cell, every metric, CI excluding zero.** Where the CANINE combiner
failed to reach significance in either individual cell, the classical control
delivers 5–7× the effect and clears zero everywhere. Joins gain +22 against
−2 losses.

## My pre-registered expectation was wrong, in an informative way

The Task B protocol recorded, before any run: *"duplicates should benefit
more than joins"*, reasoning that a character model has more to work with in
long stretches of similar wording than at a damaged seam.

**Joins benefit more** (+0.1099 vs +0.0879), and the fitted weights say the
same thing loudly: α = **2.0** for joins against 0.75 for duplicates — the
join cell wants the character signal weighted nearly three times as heavily.

The reasoning was backwards, and the correction is philologically sensible.
A join seam is exactly where signs are *partially* preserved — half-broken
glyphs, truncated words, a sign split across the fracture. Whole-token BM25
scores those as misses; character n-grams match the surviving fragment of the
sign. The classical model helps most precisely where the tablet is broken,
which is the project's subject matter.

*(Caveat added after the bigram control: this partial-sign story is a
plausible reading of the joins result, not a demonstrated mechanism. Sign
bigrams — which cannot match a partial sign — recover 86% of the Task A gain,
so context alone explains most of it. The Task B joins cell has not been rerun
with bigrams, which is the measurement that would actually separate the two.)*

## What this settles, and what it costs

**Rungs 4 and 6 are answered on direct evidence.** The ladder's position on
them has now moved three times, and it is worth being explicit that this is
the third:

1. **Withdrawn** by the amendment (2026-08-04), on an inductive leap from two
   failures of a different architecture family.
2. **Reinstated** by the screen, which measured them and found the leap
   wrong.
3. **Answered now**: the gain they were reinstated for is real, is not
   memorisation, is not linguistic, and is captured better by a classical
   method that adds nothing when they are stacked on top of it.

Each move followed evidence, and the third is the best supported: it rests on
a direct head-to-head with a control that did not exist in steps 1 or 2. The
recommendation is that **neither owed Gate-3 proposal be written on retrieval
grounds** — not because pretrained models were dismissed, but because they
were measured against the right control and lost.

**The pretrained-model excursion was not wasted.** It produced the
contamination control, and it produced the observation — from the relabeling
result — that the useful signal was character-level and not linguistic. That
observation is what motivated this experiment. Nobody would have run a char
n-gram control had CANINE simply failed the screen.

## A real improvement to the shipping system — with a gate in front of it

`P5_CLOSEOUT.md` records BM25-retrieve-deep as the shipping retrieval stage.
On dev, adding a character n-gram feature to it is worth **+0.1179 Task A
recall@1** and **+0.088 to +0.110 across all three Task B cells**, for
essentially zero compute.

**This is a recommendation to Ixca, not a change already made.** Nothing in
the shipping path has been modified. Before it could be:

- **It must be validated test-side**, and test-side runs are one-shot and
  separately unauthorized (P6). Every number here is dev-only.
- **The statistics universe must be fixed first.** `AGENTS.md` requires
  corpus statistics to be fit over the declared universe for their phase,
  "never over query-derived subsets." This run fits the TF-IDF vocabulary
  over the 876 dev fragments — a query-derived subset. **The BM25 reference
  in this harness is fit the same way**, so the comparison between arms is
  fair and the deltas stand; but an absolute deployed number must refit over
  the declared non-test universe. This is a known, shared deviation, recorded
  rather than discovered later.

## Limitations

- Dev only, dev-only candidate index, one seed, one fold assignment. Absolute
  numbers are not comparable to published test-side figures.
- `min_df=2` and `analyzer="char"` are fixed implementation choices, not
  fitted and not pre-registered as swept; only `ngram_range` and α were
  fitted, within folds.
- The Task B run fixes `(4,6)` from Task A rather than refitting it. That is
  deliberate — it tests transfer of a settled configuration — but it means
  Task B's ngram range was not itself validated on Task B.
- This says nothing about span-infilling, restoration, or any task other than
  the retrieval measured here. It does not retract the CANINE result; it
  reattributes it.

## Artifacts

- `scripts/phase5_char_ngram_control.py`
- `scripts/phase5_combiner_taskb.py --signal char`
- `Phase4/phase4_out/p5_char_ngram_control.json`
- `Phase4/phase4_out/p5_combiner_taskb_char.json`
