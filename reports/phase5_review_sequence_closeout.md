# Corrective-review sequence — closeout for steps 1–3

**Date: 2026-08-04. Status: steps 1, 2 and 3 complete. Steps 4–6 open.**

This closes the required sequence in
`reports/phase5_classical_control_review.md`. Every run was pre-registered
before it ran, dev-side only; the protected test split was never loaded.

## What was asked, and what came back

| step | question | verdict |
|---|---|---|
| 1 | Does the classical gain survive a declared statistics universe and a full distractor index? | **`SURVIVES`** — but 41% smaller, and its stated mechanism was wrong |
| 2 | Does any richer lexical channel beat BM25 + unigram TF-IDF? | **`CHANNEL_ADDS`** — and step 1's mechanism claim was a parameterization artifact |
| 3 | Does it hold on Task B, across language scopes, with frozen Task A weights? | **All three relation cells reject H₀**, with one large qualification |

## The claim set that survives

1. **A separately weighted sign-bigram channel materially improves retrieval.**
   Task A: +0.0940 conditional increment over `BM25 + unigram` under the
   ratified word-aware scope. Task B, cross-fitted, `HITTITE_ONLY`: joins
   **+0.1111** [+0.0602, +0.1768], pooled **+0.0875** [+0.0591, +0.1230],
   duplicates **+0.0627** [+0.0378, +0.1076] — all three reject under
   Holm–Bonferroni at family-wise α = 0.05.
2. **The join gain is concentrated where editor-aligned text is shared.** At
   zero shared lines the increment is **+0.0294, CI [−0.0645, +0.1481]**
   (−0.0278 under the unrestricted control). **On joins with no shared lines —
   the case the fragment-as-matrix model exists to solve — there is no evidence
   it helps.** Shared-line count is confounded with tier and length, so this is
   not a dose–response relationship.
3. **Tier C retrieval is largely the editor's own alignment read back.** On
   identical pair instances against the same candidate universe, removing
   shared lines collapses absolute recall@1 from ~0.38 to **0.00–0.04**; the
   single-partner sensitivity is exactly 0.0000. The bigram contribution
   *within* Tier C is unresolved on 23 clusters.
4. **Cross-line n-grams were costing accuracy.** Forbidding bigrams that bridge
   a line break is worth **+0.0287**, and is a genuine accuracy gain.
5. **The within-sign transliteration proxy is rejected.** `char_within_sign`
   contributes exactly 0.0000 (weight 0 in all five folds). This tests a
   Latin-transliteration proxy, **not** physical partial-glyph evidence, which
   TLHdig does not encode.
6. **Language restriction is an evidence-policy and coverage choice**, not a
   performance improvement. On a per-cell common population no scope uniformly
   dominates (spans 0.008–0.013), and no inference is offered for those
   differences.
7. **`HITTITE_ONLY` costs almost exclusively duplicate evidence**: 2,825 of
   2,832 lost relations are duplicates, 7 are joins. Roughly half that
   duplicate loss is `LINE_NOT_IN_LANGUAGE_DATASET` — a coverage gap in our own
   Gate-2 dataset, not an affirmative non-Hittite classification. **Keep those
   two causes separate.**
8. **Bin-parent physical joins are where the join evidence is** — 198
   independent join components against 54 in the labelled dev cell.
   `DESCRIPTIVE_NOT_CROSS_FITTED`: external to weight fitting, but sharing
   corpus construction, index and feature statistics.
9. **Task A's frozen configuration retains utility on Task B without
   retuning** (+0.0888 within-arm). Final accuracy is close to the
   Task-B-fitted configuration, **but equivalence is not established** — no
   equivalence margin or TOST was pre-registered, and the interval's upper
   endpoint (+0.0104) lies just outside the ±0.010 materiality margin.
10. **Cross-language parallel evidence has low reachable coverage** — ceiling
    0.0295 joins / 0.0741 duplicates — and **within that restricted population
    the increment is inconclusive**, not absent.
11. **Corpus data-quality finding for the TLHdig team:** two
    `join_pairs.jsonl` rows give both members the same siglum, asserting a
    fragment joins itself (`KUB 28.89+`, `KBo 22.130a+`).

## What was withdrawn along the way, and why

Every one of these was a real error caught in review, not a narrowing.

| withdrawn claim | why it was wrong |
|---|---|
| "Sequence context adds ~+0.005; the arms converge" (step 1) | Artifact of merging two feature families into one L2-normalized vector. Separately weighted, the same family gives +0.0431. |
| "The bigram gain is worth ~+0.10" | Fit on 876 dev fragments with a dev-only index. Under the declared universe: +0.0601. |
| "`HITTITE_ONLY` improves the system" | The increment rose only because the reference weakened faster; final recall **fell** −0.0131. |
| "Task A scored non-Hittite fragments as Hittite" | Overclaim. Historical Task A was **language-unrestricted despite being described as Hittite retrieval** — a task-definition gap, not contamination. |
| "The partial-sign story is dead" | Too broad. Only the **within-sign Latin-transliteration proxy** was tested. |
| Step 3's first Holm rejections | **Not cross-fitted.** Weights were searched out of fold, then the held-out predictions discarded and all of dev re-scored with modal weights. |
| "`CROSS_LANGUAGE_PARALLEL` is not evaluable" | Population selected under each fragment's *own* language. Corrected: 410 queries are evaluable. |
| "`SAME_LANGUAGE_AS_QUERY` loses 12,482 relations to query refusal" | Same defect on the candidate side. Its true reachability ceiling is 1.000 joins / 0.973 duplicates. |
| "Task-A-frozen matches or beats the fitted configuration" | Compared within-arm increments, which a weaker baseline inflates. Final-system difference is +0.0026, p=0.422. |
| "Cross-language is null" / "the configurations are equivalent" | **Non-significance is not equivalence.** Both are `INCONCLUSIVE`. |

## Methodological traps, so a successor does not re-enter them

1. **Searching weights out of fold is not cross-fitting.** If you then discard
   the held-out predictions and re-score everything with modal weights, every
   query is scored under weights partly chosen using its own fold.
2. **Non-significance is never equivalence.** This was correction 1 of the
   review that opened this line, and it was re-made three more times in prose
   before being guarded mechanically. `lib/effect_decision` now emits the
   verdict; `DECISION_MARGIN` is encoded, not left to the writeup.
3. **Parameterization is a factor.** Two feature families sharing one TF-IDF
   vector is not a factorial, and a contrast between such arms measures neither
   family's marginal value.
4. **Population selection must match the estimand.** A query-relative scope
   needs query-language-relative selection on *both* sides. Selecting either
   side by the fragment's own language silently changes the question.
5. **Frozen-weight transfer needs the matching scope.** Applying a
   Hittite-scoped configuration to an unrestricted scope is cross-task *plus*
   cross-scope portability, a different claim.
6. **Compare final systems, not increments.** A larger increment can come from
   a weaker baseline.
7. **The resampling unit must match the relation** — physical join component
   for joins, composition for duplicates. Getting this wrong reported 12
   clusters where the objects supply 56.
8. **A paired comparison needs the same population *and* the same candidate
   universe.** Full-vs-exclusive Tier C on different populations is not a
   paired estimate.
9. **Check that a stratifier actually varies.** `build_join_positives` drops
   `n_shared_lines`, so the shared-line stratum silently reported a constant.
10. **The family-exclusion predicate is `same family AND different
    parent_doc`.** Asserting that positives never share a family flags every
    composite join pair — the 2026-07-22 bug that drove joins tier-A/B to 0.0.
11. **Measure before believing a bug.** The crash from a degenerate self-join
    pair was a corpus finding, not a coding accident.

## What is open

Steps **4–6** of the review's sequence:

4. A specialist inspects gained and lost cases **blind to method**, with typed
   support, contradiction and dependence evidence persisted.
5. Freeze **one** final configuration and analysis plan.
6. The one-shot P6 run against the protected test split.

**The binding blocker is the first specialist session**, which no further
retrieval work substitutes for. The deployment-candidate configuration exists
(`HITTITE_ONLY`, α_u = 0.5, pair = (0.15, 1.0)) and carries **no** dev
performance claim.

## Artifacts

| step | protocol | results |
|---|---|---|
| 1 | `phase5_statistics_universe_protocol.md` | `phase5_statistics_universe_results.md` |
| 2 | `phase5_factorial_control_protocol.md` | `phase5_factorial_control_results.md` |
| 3 | `phase5_taskb_transfer_protocol.md` (+3 amendments) | `phase5_taskb_transfer_results.md` |

Scripts: `phase5_statistics_universe_control.py`,
`phase5_statistics_universe_posthoc.py`, `phase5_factorial_control.py`,
`phase5_taskb_transfer.py`. Tests: `test_statistics_universe_control.py`,
`test_factorial_control.py`, `test_taskb_transfer.py`.
