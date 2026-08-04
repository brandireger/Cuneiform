# Sign-bigram control — pre-registered protocol

> **POST-RUN CORRECTION 2026-08-04.** This historical protocol incorrectly
> treated CI-includes-zero as evidence that character granularity was
> unimportant. CI [-0.0012, +0.0324] is inconclusive at the +0.010 margin. The
> historical rule remains visible; current interpretation is governed by
> `reports/phase5_classical_control_review.md`.

**Status: PRE-REGISTERED 2026-08-04, written and committed BEFORE the run.**
Training-free; dev split only; test never loaded.

## Why — a hole in my own headline

`reports/phase5_char_ngram_control_results.md` reports that BM25 + character
n-gram TF-IDF beats BM25 by +0.1179 on Task A and clears zero in every Task B
cell, and concludes that the useful signal is *character-level*.

That conclusion is not yet earned. There is a cheaper explanation I have not
excluded: the gain may come from **n-gram context of any kind**, not from
character granularity specifically. Whole-sign **bigrams** would supply
context too, and if they recover the same gain then "character n-gram" is
partly a rediscovery of something the project already had.

The project already had it, unrun: `eval_harness.add_bigrams()` and
`13_bm25.py`'s `use_bigrams` flag both exist, but P3 only ever reported
`bm25_sign`, `bm25_lemma`, and `tfidf_cosine_sign`. **No bigram variant was
ever measured.** This closes that gap and tests my own claim against the
obvious alternative.

## Design

Identical machinery to the character n-gram control — same loader, same
composition-level folds, same α grid, same paired bootstrap, same
`run_task_a` path. The only new signal is:

- **sign-bigram TF-IDF**: `add_bigrams()` over each fragment's sign tokens
  (unigrams + adjacent-pair tokens), TF-IDF, cosine similarity.

Arms, mirroring the structure used to retire CANINE:

1. **BM25 + sign-bigram** vs BM25 alone → `R_bigram`.
2. **BM25 + sign-bigram + char n-gram** vs **BM25 + sign-bigram** →
   `I_char`, the increment of character granularity over token n-grams.

## Pre-registered decision rule

> - **`I_char`'s 95% CI includes zero → CHARACTER GRANULARITY IS NOT THE
>   POINT.** The finding must be restated as "n-gram context helps," sign
>   bigrams are the simpler implementation, and the character framing in the
>   char n-gram report must be corrected.
> - **`I_char`'s CI excludes zero and `I_char` ≥ +0.010 → CHARACTER
>   GRANULARITY EARNS ITS KEEP** beyond token n-grams, and the reported
>   conclusion stands as written.
> - Otherwise → **INCONCLUSIVE**, reported as such.

Secondary, reported regardless: `R_bigram`, and its ratio to the character
n-gram's +0.1179.

## Why this matters for the write-up

Whichever way it falls, the handoff and any second opinion need it. If sign
bigrams do the work, the recommendation to Ixca changes from "add a character
n-gram feature" to "add a bigram feature," which is simpler, cheaper, and
already half-implemented in the repo. Discovering that after a reviewer asks
would be worse than discovering it now.

## Limitations

Dev only, dev-only index, one seed, one fold assignment. Task A only; the
Task B picture would need its own run if this changes the recommendation.
