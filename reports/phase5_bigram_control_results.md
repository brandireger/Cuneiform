# Sign-bigram control — results

**Status: COMPLETE 2026-08-04. Verdict CHARACTER_GRANULARITY_NOT_THE_POINT.**
**The gain is about n-gram CONTEXT, not character granularity. My own
conclusion in the char n-gram report was overstated and is corrected there.**
`[PROBE — not for citation]`; dev split only, test never loaded.

Executes `reports/phase5_bigram_control_protocol.md` (PRE-REGISTERED,
committed as `4b74171` before the run). Training-free.

## Result

| arm | held-out recall@1 | Δ vs BM25 | 95% CI |
|---|---|---|---|
| BM25 alone | 0.6312 | — | — |
| **BM25 + sign-bigram TF-IDF** | **0.7329** | **+0.1017** | [+0.0774, +0.1272] |
| BM25 + char n-gram (4,6) | 0.7491 | +0.1179 | [+0.0913, +0.1445] |

**Sign bigrams recover 86.3% of the character n-gram gain**, using a function
(`eval_harness.add_bigrams`) that has been in the repo since P3 and was never
measured.

Primary statistic — the increment of character granularity:

> **`I_char` = +0.0162, 95% CI [−0.0012, +0.0324]** — **includes zero.**

By the pre-registered rule: **CHARACTER_GRANULARITY_NOT_THE_POINT.**

## An important subtlety in how that increment was measured

The two-parameter fit was free to mix both signals. In **all five folds it
set α_bigram to 0.0** and kept only the character signal. So arm 2 did not
measure "char *on top of* bigram" — it measured **char *instead of* bigram**,
because no mixture beat the character signal alone on the fit folds.

The honest statement is therefore: **sign bigrams and character n-grams are
near-substitutes.** They capture substantially the same thing. Character
n-grams are slightly better, by +0.0162, and that margin is not
distinguishable from zero at this sample size.

## Correction to the char n-gram report

`reports/phase5_char_ngram_control_results.md` concluded the useful signal is
"character-level." **That framing is wrong and has been corrected there.** The
measured facts are unchanged — BM25 + char n-gram really does reach +0.1179
on Task A and clear zero in all three Task B cells — but the *explanation*
was not established. What is established:

- **n-gram context beyond single signs is what helps** (+0.10 to +0.12);
- character granularity specifically buys at most a further +0.0162, with a
  CI including zero;
- the simplest sufficient implementation is sign bigrams, which the project
  already has.

I caught this myself, before handing the work over, by asking what a reviewer
would ask first. It should have been the control run *alongside* the char
n-gram test rather than after it — the char n-gram report drew a mechanistic
conclusion its design could not support.

## What this does NOT change

- **CANINE is still redundant.** It added nothing over char n-grams
  (I = −0.0046, CI [−0.0162, +0.0058]), and char n-grams are the stronger of
  the two classical signals. The recommendation against writing the owed
  Gate-3 proposals on retrieval grounds stands.
- **Not directly measured, and worth stating**: whether CANINE adds anything
  over *sign bigrams* specifically. Since bigrams are slightly weaker than
  char n-grams, transitivity is suggestive but not proof. If the shipping
  recommendation becomes bigrams, that gap should be closed.
- The Task B result stands as measured for char n-grams; **the equivalent
  Task B run for sign bigrams has not been done** and is the obvious next
  step if bigrams become the recommendation.

## Revised recommendation to Ixca

The improvement worth having is a **token n-gram context feature added to
BM25**, on dev worth roughly **+0.10 recall@1 on Task A**. Two
implementations are within noise of each other:

- **sign bigrams** — simpler, already half-implemented (`add_bigrams`,
  `13_bm25.py`'s unused `use_bigrams` flag), interpretable in sign terms;
- **character n-grams (4,6)** — marginally better, and the more plausible
  choice on damaged text, since it can match a partially preserved sign that
  a whole-sign bigram scores as a miss. The Task B joins result (+0.1099,
  α = 2.0) is consistent with that but does not isolate it.

All the same gates apply: dev-only measurement, test-side validation is
one-shot and unauthorized, and the statistics-universe deviation must be
fixed before any deployed number.

## Limitations

Dev only, dev-only index, one seed, one fold assignment, Task A only.
`min_df` and the TF-IDF configuration were fixed, not swept.

## Artifacts

- `scripts/phase5_bigram_control.py`
- `Phase4/phase4_out/p5_bigram_control.json`
