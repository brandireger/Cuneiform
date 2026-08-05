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
already has — dominates it.

The parameterization sensitivity, measured on this population under `LEGACY`:

| contrast, same universe / rendering / population | delta | cluster CI |
|---|---:|---:|
| merged `unigram+bigram` **minus** `unigram` | **+0.00261** | [−0.0192, +0.0192] |
| separately weighted `bigram_only` over `unigram` | **+0.0431** | [+0.0096, +0.0821] |

The merged contrast is indistinguishable from zero; the separately weighted one
is not. **The two parameterizations of the same feature family give different
answers, and that is the finding** — deliberately stated as a pair of measured
effects rather than as a ratio, since dividing by an estimate whose interval
spans zero produces an unstable multiplier that would misrepresent the
evidence.

**So the review was right to demand a factorial with a `bigram-only` cell.**
Had the line stopped at step 1, the project would have concluded that
sign-sequence context contributes nothing measurable and dropped it.

## The decomposition, one declared factor at a time

Conditional increment of a bigram channel over `BM25 + unigram TF-IDF`:

| change | increment | what moved |
|---|---:|---|
| step 1's merged parameterization, `LEGACY` | +0.00261 | — |
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
actively costing accuracy. **This row is a genuine accuracy gain** — the
`BOUNDARY` reference is identical to `LEGACY`'s (C1), so the increment and the
absolute system move together, 0.5039 → 0.5326.

### The last row is NOT an accuracy gain, and must not be read as one

Applying `HITTITE_ONLY` raises the *conditional increment* from +0.0718 to
+0.0940. It does so because **the reference weakens faster than the system
does**:

| rendering | BM25 | BM25 + unigram | final: + `bigram_only` | increment |
|---|---:|---:|---:|---:|
| `BOUNDARY` | 0.4034 | 0.4608 | **0.5326** | +0.0718 |
| `SCOPED` | 0.3943 | 0.4256 | **0.5196** | +0.0940 |

Final held-out recall@1 **falls by −0.0131** under the scope. Every component
of the scoped system is absolutely worse; the increment grows only because its
baseline fell further.

The defensible reading is that **language restriction is an evidence-policy and
coverage choice, not a performance improvement**. It buys a named, auditable
estimand — retrieval over material the corpus resolves as Hittite — and it
costs accuracy and coverage. Which is the right trade is a scientific and
product decision, not something this measurement settles.

## The within-sign transliteration proxy is rejected

The review flagged as unsupported the philological reading that character
n-grams help at fracture seams because they match partially preserved signs.
This run tests **one operationalization** of it: if the signal lived inside
sign readings, `char_within_sign` (`analyzer='char_wb'`, which cannot see
across a sign) should carry it.

**Scope of this test, stated first.** `char_within_sign` sees substrings of
**Latin transliteration** of sign readings. It is a proxy for within-sign
evidence, not a test of physical partial-glyph evidence — broken wedges,
surviving sign fragments, paleographic traces. TLHdig does not encode that
modality at all (and 3D break geometry is explicitly out of scope for this
project). So what is rejected here is **the within-sign transliteration
proxy**, not the philological hypothesis about clay.

It carries nothing. Under `LEGACY` and `BOUNDARY` its conditional increment is
**exactly 0.0000, CI [0.0000, 0.0000]** — the joint fit selected weight 0 in
all five folds, which is the pre-registered identity property working as
designed: the family contains its reference, and the fit correctly declined to
use the channel at all. Under `SCOPED` it is −0.0065, CI [−0.0170, −0.0011];
in two folds a nonzero weight was selected on the fit set and lost on held-out,
which is mild weight overfitting and is reported rather than smoothed away.

Meanwhile `char_across_sign` — the historical arm — does contribute (+0.0470),
but **only half of what sign bigrams contribute** (+0.0940), and its marginal
arm is beaten by bigram-only in every rendering. Within the transliteration
signal this project actually has, the character channel is therefore a *cruder
proxy for the same cross-sign sequence evidence*, not a different kind of
evidence. Character granularity was never the point; it was a worse way of
seeing context.

## Full marginal results

Held-out Task A recall@1 delta over the BM25 reference of the same rendering,
on **766 scored dev queries** (of 779 in the population) against 6,722
candidates.

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

The refusals are overwhelmingly language decisions rather than coverage gaps —
`OUT_OF_SCOPE_LANGUAGE` outnumbers `LINE_NOT_IN_LANGUAGE_DATASET` 4.6 to 1 —
and the fragments they empty are recognizable Akkadian/Sumerian material such
as the KUB 4.x bilinguals.

### Denominator reconciliation

Every dev-side number in this report rests on this chain, stated in full:

| stage | n | what removes the difference |
|---|---:|---|
| dev fragments in the labeled universe | **883** | — |
| pass the ≥4-content-token floor under **all three** renderings | **779** | 104 fragments; overwhelmingly emptied by `HITTITE_ONLY` |
| **actually scored** | **766** | 13 **single-witness** queries |

The final 13 are the only fragment of their CTH in this population, so after
`run_task_a`'s leave-one-out exclusion of the query's own `parent_doc` there is
no eligible same-composition candidate. The harness excludes them and counts
them (`n_excluded_single_witness`) rather than scoring them as silent failures.
They are: KBo 1.28, KUB 27.42, UBT 11, KUB 28.83, VBoT 68, DAAM 2.9, KUB 43.38,
KUB 36.108, KUB 31.141, KUB 18.12+, KUB 23.102, KBo 8.66, KUB 21.39.

### What the language finding actually is

The defensible statement is that **historical Task A was language-unrestricted
despite being described as Hittite fragment retrieval**. The evaluation ranked
and scored fragments without reference to what language the corpus records them
in, and `main_split` never asked.

That is a **task-definition** problem, not evidence of contamination.
Multilingual material is legitimate evidence in this corpus — Akkadian and
Sumerian witnesses stand in real relations to Hittite compositions, and the
project's own standing rule is not to silently discard non-Hittite layers. What
was missing was a *declared* scope, so that the estimand being measured was
named. It now can be, and step 3 measures scopes against each other rather than
assuming one.

## What this does and does not license

**Licenses:** step 3 (Task B and join-tier stratification), which should now
carry a separately weighted `bigram_only` channel rather than the merged arm
this line has been reporting, and which must **compare language scopes against
each other rather than adopt one** — this run establishes that scope choice
moves absolute accuracy, so running scoped-only would confound the estimand
with the measurement.

**A framing constraint on everything above.** The factorial design was
developed adaptively on this same dev material, across three pre-registered
runs that each reacted to the last. These are dev-side characterization
results, not independent confirmation, and the eventual protected-test run
remains one-shot and separately gated.

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
