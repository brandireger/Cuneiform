# Factorial lexical-channel control — results

**Status: COMPLETE, PRE-REGISTERED, 2026-08-04.**
Protocol: `reports/phase5_factorial_control_protocol.md`, committed at
`318e153` **before** this run. Dev queries only; test never loaded;
training-free; nothing deployed.

Executes **step 2** of the required sequence in
`reports/phase5_classical_control_review.md`.

## Verdict

**`CHANNEL_ADDS`.** Under the ratified word-aware `SCOPED` rendering, two of
the three richer channels add a material increment over `BM25 + unigram
TF-IDF`, judged on composition-cluster intervals against the declared 0.010
margin:

| conditional increment over BM25 + unigram | delta | cluster CI | verdict |
|---|---:|---:|---|
| **`bigram_only_tfidf`** | **+0.0940** | [+0.0641, +0.1497] | MATERIAL |
| `char_across_sign` | +0.0470 | [+0.0295, +0.0729] | MATERIAL |
| `char_within_sign` | −0.0065 | [−0.0170, −0.0011] | BELOW MARGIN |

As the protocol required in advance, this is three simultaneous comparisons
and `CHANNEL_ADDS` is therefore a candidate for confirmation rather than an
established effect. The bigram cell's lower bound (+0.0641) is far enough from
zero to survive any obvious multiplicity adjustment; `char_across_sign`'s
(+0.0295) is closer and should be treated as the weaker of the two.

## This corrects step 1's headline, and the correction is attributable

Step 1 (`reports/phase5_statistics_universe_results.md`) concluded that the
three classical arms converge at full scale and that the sequence-context
component collapses to **+0.0046, CI [−0.0146, +0.0236]**. That measurement is
reproduced here exactly — and it turns out to have been a property of **how the
channel was parameterized**, not of the data.

Under `LEGACY` (step 1's own rendering), on this population:

| step 1 arm, reproduced | this run |
|---|---:|
| BM25 + unigram TF-IDF | +0.0574 (step 1: +0.0555) |
| BM25 + unigram**+**bigram TF-IDF | **+0.0601** (step 1: +0.0601) |
| BM25 + char n-gram | +0.0601 (step 1: +0.0624) |

The merged arm reproduces step 1 to four decimals. Step 1's convergence finding
is real and is confirmed. But its *interpretation* was wrong, because
`unigram+bigram TF-IDF` puts both feature types into **one L2-normalized vector
at a fixed relative weight**, and the unigram mass — which `BM25 + unigram`
already has — dominates it. So step 1's contrast asked "what does adding bigram
mass to an already-present unigram vector buy?", and the honest answer to that
question is +0.0046.

Give the bigrams **their own channel and their own fitted weight** — the
`bigram-only` cell the review explicitly named as required — and the same
comparison, same universe, same rendering, same population, reads **+0.0431**.

**So the review was right to demand a factorial, and step 1's reading of its
own numbers was wrong.** Had the line stopped at step 1, the project would have
concluded that sign-sequence context is worth ~+0.005 and dropped it. It is
worth roughly twenty times that.

## The decomposition, one declared factor at a time

Conditional increment of a bigram channel over `BM25 + unigram TF-IDF`:

| change | increment | what moved |
|---|---:|---|
| step 1's merged parameterization, `LEGACY` | +0.0046 | — |
| bigrams get their own weight, `LEGACY` | **+0.0431** | parameterization |
| line boundaries respected, `BOUNDARY` | **+0.0718** | rendering |
| ratified `HITTITE_ONLY` applied, `SCOPED` | **+0.0940** | language scope |

Each step is attributable precisely because rendering and channel were varied
as declared, crossed factors rather than changed together.

**Correction 4 of the review is vindicated.** It objected that the historical
loader strips structural tokens, so an n-gram may silently bridge a line break
— and, where lines were dropped, bridge lines that were never adjacent. Those
cross-line bigrams were not neutral noise: forbidding them is worth **+0.0287**
of conditional increment (+0.0431 → +0.0718), and it raises the marginal
bigram-only arm from +0.1044 to +0.1266. The fabricated adjacencies were
actively costing accuracy.

Applying the ratified language scope adds a further +0.0222.

## The partial-sign story is dead

The review flagged as unsupported the philological reading that character
n-grams help at fracture seams because they match partially preserved signs.
This run tests it directly: if that story were true, `char_within_sign`
(`analyzer='char_wb'`, which cannot see across a sign) should carry the signal.

It carries nothing. Under `LEGACY` and `BOUNDARY` its conditional increment is
**exactly 0.0000, CI [0.0000, 0.0000]** — the joint fit selected weight 0 in
all five folds, which is the pre-registered identity property working as
designed: the family contains its reference, and the fit correctly declined to
use the channel at all. Under `SCOPED` it is −0.0065, CI [−0.0170, −0.0011];
in two folds a nonzero weight was selected on the fit set and lost on held-out,
which is mild weight overfitting and is reported rather than smoothed away.

Meanwhile `char_across_sign` — the historical arm — does contribute (+0.0470),
but **only half of what sign bigrams contribute** (+0.0940), and its marginal
arm is beaten by bigram-only in every rendering. The character channel is
therefore a *cruder proxy for the same cross-sign sequence signal*, not a
different kind of evidence. Character granularity was never the point; it was a
worse way of seeing context.

## Full marginal results

Held-out Task A recall@1 delta over the BM25 reference of the same rendering,
on 779 dev queries against 6,722 candidates.

| channel | LEGACY | BOUNDARY | SCOPED |
|---|---:|---:|---:|
| BM25 absolute | 0.4034 | 0.4034 | 0.3943 |
| `unigram_tfidf` | +0.0574 | +0.0574 | +0.0313 |
| `bigram_only_tfidf` | +0.1044 | +0.1266 | **+0.1332** |
| `unigram_plus_bigram_tfidf` | +0.0601 | +0.0888 | +0.1018 |
| `char_within_sign` | +0.0104 | +0.0104 | −0.0104 |
| `char_across_sign` | +0.0601 | +0.1005 | +0.0836 |

Two things in this table are worth not skimming past.

**Merging dilutes.** `bigram_only` beats `unigram_plus_bigram` in every
rendering, by +0.044 / +0.038 / +0.031. Whenever two feature families share one
TF-IDF vector, the more numerous family wins the L2 budget. This is the
mechanism behind step 1's mistaken reading, stated as a general caution.

**The language scope helps bigrams and hurts unigrams.** `HITTITE_ONLY` moves
the unigram channel from +0.0574 to +0.0313 and `char_across_sign` from +0.1005
to +0.0836, while moving `bigram_only` up from +0.1266 to +0.1332, and BM25's
own absolute score down from 0.4034 to 0.3943. An untested hypothesis on file:
logograms and Akkadograms shared across compositions are strong *unigram* cues
and some of them sit on lines the scope refuses, so scoping costs bag-of-token
matching what it gains in cleaner sequence. **Not measured. Do not report as a
finding.**

## Checks

| check | result |
|---|---|
| C1 segmentation inert for bag-of-token channels | **PASSED** — BM25 and unigram TF-IDF per-query records identical between `LEGACY` and `BOUNDARY` |
| C2 identity control (z-normalized BM25 ≡ BM25) | **PASSED** in all three renderings |
| C3 split purity (dev-query CTHs vs train-index CTHs) | **PASSED** — 379 train vs 48 dev compositions, disjoint |
| C4 cross-segment features removed exactly | **PASSED** on 200 multi-segment fragments |

**C1 earned its place.** The first implementation failed it by up to 0.136
cosine: vectorizing per segment had silently moved document frequency from a
per-fragment to a per-line estimate, so the rendering factor would have been
changing feature adjacency *and* the IDF universe at once, and no result would
have been attributable to either. The fix — count per segment, weight per
fragment — is in `channel_similarity` and pinned by
`tests/test_factorial_control.py`. This was caught before the run, by a check
written into the protocol before the code.

## The coverage cost of the ratified language scope

Reported as a finding, not a discard. `HITTITE_ONLY` refuses **29,361 of
194,791 lines (15.07%)**:

| refusal reason | lines |
|---|---:|
| `OUT_OF_SCOPE_LANGUAGE` | 22,343 |
| `LINE_NOT_IN_LANGUAGE_DATASET` | 4,868 |
| `MIXED_LANGUAGE_LINE` | 2,129 |
| `UNRESOLVED_LEXICAL_LANGUAGE` | 21 |

**104 of 883 dev fragments (11.8%)** and 887 of 7,609 labeled fragments fall
below the four-content-token floor under at least one rendering and are outside
this run's population. The refusals are overwhelmingly genuine rather than
coverage gaps — `OUT_OF_SCOPE_LANGUAGE` outnumbers `LINE_NOT_IN_LANGUAGE_DATASET`
4.6 to 1 — and the excluded fragments are recognizable Akkadian/Sumerian
material such as the KUB 4.x bilinguals.

**That Task A has been scoring non-Hittite fragments as though they were
Hittite, throughout this project's history, is itself a result**, and it is
independent of everything else here. The `main_split` machinery never asked
what language a fragment was in.

## What this does and does not license

**Licenses:** step 3 (Task B and join-tier stratification), which should now
carry a `bigram_only` channel under the `SCOPED` rendering rather than the
merged arm this line has been reporting; and it makes the choice of shipping
feature a real question again, at ~+0.09–0.13 rather than the ~+0.005 step 1
implied.

**Does not license:** any test-side or deployed number (protected, one-shot,
not run); any Task B claim (every Task B cell in this line was measured under
the merged parameterization *and* the flat rendering, both now known to
understate a bigram channel); any claim about pretrained models, whose
increments were all measured against comparators that have now moved twice.

**A standing caution this run establishes:** two feature families in one
TF-IDF vector is not a factorial, and a contrast between such arms does not
measure the marginal value of either family. Step 1 made that mistake in good
faith and its stated conclusion was wrong because of it.

## Artifacts

- `reports/phase5_factorial_control_protocol.md` (pre-registered, `318e153`)
- `scripts/phase5_factorial_control.py`
- `tests/test_factorial_control.py`
- `Phase4/phase4_out/p5_factorial_control.json`
- `Phase4/phase4_out/p5_factorial_control_per_query.jsonl`
- `Phase4/phase4_out/p5_factorial_control_manifest.json`
