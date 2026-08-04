# Statistics-universe and full-distractor control — results

**Status: COMPLETE, PRE-REGISTERED, 2026-08-04.**

> **THIS REPORT'S CENTRAL INTERPRETATION IS WRONG AND IS CORRECTED BY STEP 2**
> (`reports/phase5_factorial_control_results.md`, pre-registered `318e153`).
> Every measurement below reproduces exactly. But the conclusion drawn from
> them — that sequence context adds only +0.0046 and the arms converge — is an
> artifact of **how the channel was parameterized**, not a property of the
> data. `unigram+bigram TF-IDF` merges both feature families into one
> L2-normalized vector, where the unigram mass that `BM25 + unigram` already
> carries dominates. On the factorial population the merged contrast reads
> **+0.00261, cluster CI [−0.0192, +0.0192]** — indistinguishable from zero —
> while a separately weighted bigram channel, same reference, same universe and
> rendering, reads **+0.0431, cluster CI [+0.0096, +0.0821]**. Two
> parameterizations of one feature family, two different answers. The
> convergence finding below is confirmed *for merged arms under the flat
> rendering* and dissolves outside those conditions.
> **Do not cite "context adds ~+0.005"**, and do not express the correction as
> a ratio — the denominator's interval spans zero, so any multiplier is
> unstable. What stands from this report: the declared-universe and
> full-distractor effects (T1 and T2), the reproduction check, and the caution
> that dev-fitted statistics flatter n-gram arms.
Protocol: `reports/phase5_statistics_universe_protocol.md`, committed at
`b83c96e` **before** this run. Dev queries only; test never loaded;
training-free; nothing deployed.

Executes step 1 of the required sequence in
`reports/phase5_classical_control_review.md`, and answers self-doubts 6.1 and
6.2 of `reports/phase5_classical_control_handoff.md`.

## Verdict

**`SURVIVES_DECLARED_UNIVERSE`.** The sign-bigram arm's held-out Task A
recall@1 gain over BM25, fit and evaluated over the declared labeled non-test
universe with a full distractor index, is **+0.0601, composition-cluster CI
[+0.0368, +0.0905]** (composition-macro +0.0482, cluster CI [+0.0029,
+0.0901]). The lower bound clears zero and the point estimate clears the
declared 0.010 margin.

**But the headline shrinks by 41%, and the mechanism claim does not survive at
all.** Both threats the protocol separated turned out to be real, and a third
finding — not anticipated by the protocol — is the most consequential.

## Checks

| check | result |
|---|---|
| C1 reproduction (U1 must recover +0.0520 and +0.1017) | **PASSED**, to 4 decimal places (observed 0.052023 and 0.101734; absolute difference ≤ 3.5e-05) |
| C2 no composition overlap between dev queries and train index | **PASSED**: 437 train compositions disjoint from 53 dev query compositions |
| C3 identity control (z-normalized BM25 ≡ BM25) | **PASSED** in all three universes |

C1 matters more than a formality. The run scores queries against a candidate
pool they are not a subset of, which needed a rectangular runner the previous
scripts did not have; exact reproduction of both published deltas is the
evidence that the new runner is the old one plus a wider index, not a second
implementation with its own behaviour. It delegates to
`eval_harness.run_task_a`'s precomputed path, and
`tests/test_statistics_universe_control.py` pins that it agrees with
`phase5_bm25_combiner.run_subset` exactly when the pools coincide.

## The three universes

Query set identical throughout: 876 dev fragments, real compositions only.
Labeled non-test universe: **7,490 fragments** (6,614 train + 876 dev),
490 compositions. Bins excluded as `main_split='discovery'`.

| universe | candidates | candidate compositions | BM25 recall@1 |
|---|---:|---:|---:|
| U1 dev-fit, dev index | 876 | 53 | 0.6312 |
| U2 full-fit, dev index | 876 | 53 | 0.6370 |
| U3 full-fit, full index | 7,490 | 490 | **0.3965** |

Held-out recall@1 delta over the BM25 reference **of the same universe**:

| arm | U1 | U2 | U3 | U3 cluster CI |
|---|---:|---:|---:|---:|
| BM25 + unigram TF-IDF | +0.0520 | +0.0439 | **+0.0555** | [+0.0389, +0.0820] |
| BM25 + sign unigram+bigram TF-IDF | +0.1017 | +0.0855 | **+0.0601** | [+0.0368, +0.0905] |
| BM25 + char n-gram (4,6) | +0.1179 | +0.0994 | **+0.0624** | [+0.0400, +0.1004] |

### T1 — the statistics universe (handoff 6.1)

The self-doubt was correct in direction and in ordering. Refitting BM25 IDF/avgdl
and the TF-IDF vocabularies over 7,490 documents instead of 876, with the
candidate pool held at 876, costs:

| arm | T1 = Δ(U2) − Δ(U1) |
|---|---:|
| unigram TF-IDF | **−0.0081** |
| sign bigram | **−0.0162** |
| char n-gram | **−0.0185** |

The n-gram arms lose roughly **twice** what the unigram arm loses. That is
exactly the asymmetry §6.1 hypothesised: larger, sparser n-gram vocabularies
benefit more from an optimistically small IDF fitting set than BM25 over
unigrams does. The deviation was not neutral, and "both arms share the
deviation so the deltas are fair" was too generous.

Note also that BM25's own absolute score *improves* slightly under
full-universe statistics (0.6312 → 0.6370). The n-gram arms did not merely
fail to improve — they gave back ground while the baseline gained.

### T2 — the distractor pool (handoff 6.2)

§6.2 said "I have no principled prediction and would like one." The measurement
gives one, and it splits by arm:

| arm | T2 = Δ(U3) − Δ(U2) |
|---|---:|
| unigram TF-IDF | **+0.0116** |
| sign bigram | **−0.0254** |
| char n-gram | **−0.0370** |

Both of the hypotheses offered in §6.2 are true, of different arms. With 8.5×
the candidates and 9.2× the compositions, the unigram arm's advantage **grows**
— a second scoring rule over the same tokens discriminates more when there is
more to discriminate. The n-gram arms' advantage **shrinks**, and the
character arm shrinks most: more candidates mean more chances for spurious
n-gram overlap, and the finer the granularity the more spurious matches there
are to find.

## The finding the protocol did not anticipate: the arms converge

At U3 the three arms sit at **+0.0555 / +0.0601 / +0.0624** — a total spread of
0.0069, *inside* the 0.010 margin declared for this whole line of work. The
ordering that drove months of interpretation survives, but the separation does
not.

A post-hoc paired contrast makes this precise
(`scripts/phase5_statistics_universe_posthoc.py`, **not pre-registered**,
descriptive only, computed from the per-query artifact the pre-registered run
wrote):

| paired contrast | U1 | U2 | U3 | U3 cluster CI |
|---|---:|---:|---:|---:|
| bigram arm vs unigram arm | **+0.0497** | +0.0416 | **+0.0046** | [−0.0146, +0.0236] |
| char arm vs bigram arm | +0.0162 | +0.0139 | +0.0023 | [−0.0085, +0.0201] |
| char arm vs unigram arm | +0.0659 | +0.0555 | +0.0069 | [−0.0074, +0.0317] |

The U1 column reproduces the corrective review's +0.0497 exactly.

**This overturns correction 2 of the corrective review.** That correction
decomposed the ~+0.10 into +0.0520 of unigram TF-IDF complementarity plus a
further +0.0497 of sequence context. The first component survives the declared
universe and grows slightly (+0.0555). **The second component does not: it
falls from +0.0497 to +0.0046, with an interval containing zero.** Under the
review's own corrected logic this is `INCONCLUSIVE` rather than zero — the
upper bound +0.0236 still exceeds the 0.010 margin — but it is emphatically not
+0.05, and no writeup may continue to attribute half the gain to n-gram
context.

The defensible statement is now:

> Under the declared non-test statistics universe with a full labeled
> distractor index, adding a **second lexical similarity score** to BM25 is
> worth about **+0.055 to +0.062** held-out Task A recall@1. **Which** second
> score — sign unigrams, sign bigrams, or character 4–6-grams — is not
> resolved by this evidence; the three are separated by less than the declared
> materiality margin, and every pairwise contrast between them has an interval
> containing zero.

Char-over-bigram was `INCONCLUSIVE` at U1 and remains `INCONCLUSIVE` at U3, now
at a quarter the size. The question is still open and is now smaller than it
looked.

## Secondary observation: the mixing weight destabilises

At U1 the bigram and char arms selected α = 0.75 in all five folds. At U3 they
select 0.4–1.5 and 0.3–1.0 respectively, while the unigram arm stays tight
(0.75–1.0). The load-bearing mixing weight recorded in
`reports/phase5_bm25_combiner_results.md` is less determined once the index is
realistic — one more reason the n-gram arms' apparent stability was partly an
artifact of the small setup.

## What this does and does not license

**Licenses:** proceeding to step 2 (the factorial control) — and requires it to
be run at U3 scale from the start, since the whole question it was designed to
answer ("unigram vs bigram vs character") is the question that collapsed here.

**Does not license:** any claim of +0.10; any test-side or deployed number
(protected, one-shot, not run); any conclusion about Task B or join tiers
(step 3 — the review's Task B cells were all measured under U1 conditions and
are now known to be measured in the universe that most inflates n-gram arms);
any acceptance of the legacy language-blind rendering for a promoted scorer,
which was deliberately held fixed here so the universe was the only moving
part.

**Two prior conclusions are now bounded more narrowly than their reports say.**
Frozen CANINE's increment (−0.0046, CI [−0.0162, +0.0058]) was measured *over
the char arm under U1*. That comparator has moved, and the char arm's own
advantage over the cheapest classical arm has largely evaporated at scale, so
the CANINE measurement is bounded to a setup now known to be the most generous
one to its comparator. Re-measuring it at U3 is feasible (frozen embeddings for
7,490 fragments, no training) but is outside this protocol and was not done.
Likewise, the shipping-stage suggestion in the handoff — "adding a
unigram+bigram lexical arm is worth ~+0.10 on this dev setup" — must be
restated as **~+0.06**, and still carries its three unmet preconditions.

## Artifacts

- `reports/phase5_statistics_universe_protocol.md` (pre-registered, `b83c96e`)
- `scripts/phase5_statistics_universe_control.py`
- `scripts/phase5_statistics_universe_posthoc.py` *(post-hoc, descriptive)*
- `tests/test_statistics_universe_control.py`
- `Phase4/phase4_out/p5_statistics_universe.json`
- `Phase4/phase4_out/p5_statistics_universe_per_query.jsonl`
- `Phase4/phase4_out/p5_statistics_universe_manifest.json`
- `Phase4/phase4_out/p5_statistics_universe_posthoc.json`
