# Task B relation retrieval, language scopes, and Task-A-frozen portability

**Status: AUTHORITATIVE. Four scopes, cross-fitted, plus the matching-scope
Task-A-frozen arm. 2026-08-04.**
Protocol: `reports/phase5_taskb_transfer_protocol.md`, pre-registered `318e153`,
amendments `3f334b9`, `2735e49`, `d1052d1` — each committed before the run it
governs. Dev queries only; the protected test split is closed and was never
loaded. No representation learning or gradient training; fusion weights fitted
**out of fold**, plus one arm using weights fitted on a different task.

## Provenance — three corrections behind this file

1. **Not cross-fitted.** The first run searched weights out of fold, then
   discarded the held-out predictions, took modal weights across all folds and
   re-scored all of dev. Withdrawn in full.
2. **Query-relative scopes selected populations under each fragment's own
   language**, not relative to the query language. This reported
   `CROSS_LANGUAGE_PARALLEL` as having **zero** evaluable queries while its own
   ceiling code found thousands of reachable targets, and it produced a
   `SAME_LANGUAGE_AS_QUERY` "12,482 relations lost to query refusal" figure
   that was an artifact. Both withdrawn.
3. **The Task-A-frozen arm used `SCOPED` weights for every scope**, and
   "matches or beats" compared *within-arm increments* rather than final
   systems. Both corrected below.

Superseded numbers are **not reproduced and not used as comparison targets**.

## Primary family — cross-fitted, `HITTITE_ONLY`

`BM25 + unigram + bigram_only` over `BM25 + unigram`. Weights fitted per fold
on the pooled objective, applied **only to that fold's held-out queries**,
predictions concatenated.

| cell | n | clusters | r@1 unigram → +bigram | Δ | cluster CI | p | Holm thresh | reject H₀ | +/− |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|---:|
| joins | 171 | 54 | 0.5439 → 0.6550 | **+0.1111** | [+0.0602, +0.1768] | 0.0010 | 0.0167 | **yes** | +22/−3 |
| pooled | 766 | 35 | 0.5013 → 0.5888 | **+0.0875** | [+0.0591, +0.1230] | 0.0010 | 0.0250 | **yes** | +106/−39 |
| duplicates | 766 | 35 | 0.3799 → 0.4426 | **+0.0627** | [+0.0378, +0.1076] | 0.0070 | 0.0500 | **yes** | +93/−45 |

Per-fold weights: fold 0 α_u 1.0 / (0.40, 0.40); fold 1 0.5 / (0.15, 1.00);
fold 2 0.75 / (0.15, 1.00); fold 3 0.75 / (0.10, 0.75); fold 4 0.5 / (0.00,
1.00). **C5** confirms weights are constant across cells and strata within each
fold and differ across folds, as cross-fitting requires. The modal
configuration is retained as a deployment candidate and **no reported number
was computed from it**.

**Unaffected by every correction above** — the three amendments touched the
query-relative scopes and the frozen arm only.

## The load-bearing qualification: zero-overlap joins

| shared lines | n | clusters | r@1 → | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| **0** | 34 | 18 | 0.2059 → 0.2353 | **+0.0294** | **[−0.0645, +0.1481]** |
| 1–2 | 43 | 19 | 0.4651 → 0.5814 | +0.1163 | [+0.0357, +0.2286] |
| 3–9 | 69 | 30 | 0.6957 → 0.8261 | +0.1304 | [+0.0541, +0.2154] |
| 10+ | 25 | 15 | 0.7200 → 0.8800 | +0.1600 | [+0.0385, +0.3203] |

Zero-overlap is **−0.0278, CI [−0.0968, 0.0000]** under the unrestricted
control; indirect `(+)` joins +0.0526, CI includes zero.

> The bigram channel improves duplicate-witness retrieval, and its help on
> physical joins **is concentrated where editor-aligned text is shared**. On
> joins with no shared lines — the case the fragment-as-matrix model exists to
> solve — there is no evidence it helps.

Shared-line count is **not a dose**: it is confounded with tier (0 shared lines
is exactly tier A here), with length, and with other pair properties.

## Tier C, paired

Pair instances with their own exclusive renderings; full and exclusive on the
**same instances and same candidate universe** (asserted in code); clustered by
**physical join component**.

| `HITTITE_ONLY`, 51 instances → 102 query-instances, 23 clusters | r@1 → | Δ | cluster CI | p |
|---|---:|---:|---:|---:|
| full rendering — **contaminated** | 0.3039 → 0.3824 | +0.0784 | [0.0000, +0.1875] | 0.109 |
| **overlap-exclusive** | **0.0392 → 0.0000** | −0.0392 | [−0.0938, 0.0000] | 0.123 |
| exclusive, single-partner only (24 instances, 11 clusters) | 0.0000 → 0.0000 | 0.0000 | [0.0000, 0.0000] | 1.000 |

Removing shared editor-aligned lines collapses absolute recall@1 from ~0.38 to
**0.00–0.04**; the single-partner sensitivity lands at exactly 0.0000, so the
collapse is not an artifact of multi-partner rendering. **The bigram
contribution *within* Tier C is unresolved** on 23 clusters. **Do not compare
these absolutes to the tier-C strata row** — a stratum query may hit *any*
partner, a pair instance must hit the *specific* one.

## Language scopes — all four evaluable

Cross-fitted deltas (pair arm over unigram arm):

| scope | joins | duplicates | pooled |
|---|---:|---:|---:|
| `HITTITE_ONLY` | +0.1111 [+0.0602, +0.1768] · 54 cl | +0.0627 [+0.0378, +0.1076] | +0.0875 [+0.0591, +0.1230] |
| `ALL_LANGUAGES_UNCONDITIONED` | +0.0824 [+0.0389, +0.1287] · 59 cl | +0.0393 [+0.0141, +0.0814] | +0.0566 [+0.0321, +0.0918] |
| `SAME_LANGUAGE_AS_QUERY` | +0.0897 [+0.0400, +0.1397] · 56 cl | +0.0664 [+0.0359, +0.1009] | +0.0858 [+0.0486, +0.1163] |
| `CROSS_LANGUAGE_PARALLEL` | n=7, 5 cl — **descriptive only** | +0.0049 [−0.0194, +0.0414] p=0.654 | +0.0049 [−0.0194, +0.0414] |

### Reachable-positive ceilings, conditional on query eligibility

| scope | joins | duplicates |
|---|---:|---:|
| `SAME_LANGUAGE_AS_QUERY` | **1.000** | **0.9726** |
| `CROSS_LANGUAGE_PARALLEL` | **0.0295** | **0.0741** |

Under same-language admission virtually every positive remains reachable. Under
cross-language admission at most **3–7%** ever were — so any recall figure
there is bounded by that, and a low number is an admission bound, not a scoring
failure.

**`CROSS_LANGUAGE_PARALLEL` is evaluable; the increment is INCONCLUSIVE.** 410
queries retain a reachable duplicate positive, and the bigram channel shows
**+0.0049, CI [−0.0194, +0.0414], p=0.654** — **no detected increment**. That
interval still permits both harm and a materially useful gain, so this is not
an absence of effect. Applying the shared margin rule
(`lib/effect_decision.practical_increment_verdict`, margin 0.010) the upper
endpoint +0.0414 exceeds the margin, so the verdict is **`INCONCLUSIVE`**, not
below-margin. Its joins cell has 7 queries across 5 clusters and is descriptive
only.

The defensible statement is therefore:

> Cross-language evidence has **low reachable-positive coverage** (ceiling
> 0.0295 joins / 0.0741 duplicates), and **within that restricted population
> the bigram increment is inconclusive.** The low ceiling is established;
> absence of effect is not.

**On what these positives are:** **different-language same-CTH relations**, not
independently annotated textual parallels. Shared CTH membership plus a
language difference is what the corpus supports.

**On the candidate universes:** the per-language counts below are **candidate
renderings with ≥4 tokens admitted as being in (or, for cross-language,
differing from) the query language** — not "fragments of language X". Parent
fragments may be multilingual or fragment-level unresolved, which is exactly
what the corrected candidate admission preserves.

| query language | same-language: queries / eligible / candidates | cross-language: queries / eligible / candidates |
|---|---:|---:|
| Hit | 649 / 658 / 6,722 | 344 / 658 / 1,349 |
| Akk | 40 / 42 / 386 | 32 / 42 / 7,109 |
| Hur | 24 / 24 / 566 | 24 / 24 / 7,216 |
| Hat | 7 / 7 / 244 | 7 / 7 / 7,318 |
| Luw | 3 / 3 / 109 | 3 / 3 / 7,405 |

### What `HITTITE_ONLY` costs, by cause

| cell | relations lost | endpoint refusal reasons |
|---|---:|---|
| joins | **7** | `OUT_OF_SCOPE_LANGUAGE` 9, `LINE_NOT_IN_LANGUAGE_DATASET` 4 |
| duplicates | **2,825** | `LINE_NOT_IN_LANGUAGE_DATASET` 1,693, `OUT_OF_SCOPE_LANGUAGE` 1,614 |

**Two causes that must stay separate.** `OUT_OF_SCOPE_LANGUAGE` is an
affirmative classification — the corpus records those lines as another
language. `LINE_NOT_IN_LANGUAGE_DATASET` is a **coverage gap in our own derived
Gate-2 dataset**, saying nothing about the tablet. They are nearly equal for
duplicates, so **roughly half the duplicate evidence `HITTITE_ONLY` discards is
lost to our own pipeline's coverage** — a fixable engineering deficit, distinct
from the estimand choice.

### Common population, intersected per cell

Over query IDs **actually scored** in each cell, across the three symmetric
scopes. `CROSS_LANGUAGE_PARALLEL` is excluded by §3.2: it is an asymmetric
assistance channel, and admitting it would collapse the intersection onto its
small population.

| cell | n | `HITTITE_ONLY` | `ALL_LANGUAGES` | `SAME_LANGUAGE` |
|---|---:|---:|---:|---:|
| joins | 150 | **0.6733** | 0.6600 | 0.6667 |
| duplicates | 649 | 0.4284 | 0.4253 | **0.4330** |
| pooled | 649 | 0.5840 | 0.5778 | **0.5871** |

**No scope uniformly dominates.** `HITTITE_ONLY` leads on joins,
`SAME_LANGUAGE_AS_QUERY` on duplicates and pooled, the unrestricted ablation
never. Spans are 0.013 / 0.008 / 0.009. **No dedicated inference was
pre-registered for these differences and none is offered.**

Language restriction remains an **evidence-policy and coverage choice buying a
named estimand**, not a performance improvement.

## Task-A-frozen arm — matching scope only

Task A's committed per-fold weights from the **matching** Step 2 rendering, with
Task A's own CTH→fold mapping, applied unchanged. Nothing selected or retuned
on Task B.

| Task B scope | Step 2 rendering | within-arm Δ | **final system vs Task-B-fitted** | cluster CI | p | n |
|---|---|---:|---:|---:|---:|---:|
| `HITTITE_ONLY` | `SCOPED` | +0.0888 | **+0.0026** | [−0.0024, +0.0104] | **0.422** | 766 |
| `ALL_LANGUAGES_UNCONDITIONED` | `BOUNDARY` | +0.0665 | **+0.0117** | [+0.0018, +0.0182] | 0.014 | 857 |
| `SAME_LANGUAGE_AS_QUERY` | — | — | **arm omitted** | | | |
| `CROSS_LANGUAGE_PARALLEL` | — | — | **arm omitted** | | | |

**There is no detected final-system difference on the primary scope, and
equivalence is NOT established.** +0.0026, CI [−0.0024, +0.0104], p=0.422 says
only that no difference was detected. **No equivalence margin or TOST was
pre-registered**, and even if the existing ±0.010 materiality margin were
reused post hoc, the interval's upper endpoint **+0.0104 lies just outside it**
— so the data do not support an equivalence claim under that margin either.
The earlier "matches or beats" reading came from comparing within-arm
increments, which a weaker baseline can inflate.

For `ALL_LANGUAGES_UNCONDITIONED`, **+0.0117 is a positive descriptive
difference only**: this secondary arm sits outside the corrected primary
family and carries no confirmatory claim.

The valid portability statement is narrower than either:

> **Task A's frozen configuration retains a positive within-arm benefit on
> Task B without retuning** (+0.0888 under `HITTITE_ONLY`). Its final accuracy
> is **close to** the Task-B-fitted configuration, but **their equivalence is
> not established.**

So what is shown is that **the Task-A-selected weights retain utility on Task
B** — not that the weights are task-independent, which would require an
equivalence test that was never designed. Neither query-relative scope has a
matching Step 2 arm, so no such claim exists for them at all.

## Bin-parent physical joins — descriptive

| `HITTITE_ONLY` | n | clusters | r@1 → | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| bin-exception population | 504 | **198** | 0.5952 → 0.7302 | +0.1349 | [+0.1000, +0.1687] |

**`DESCRIPTIVE_NOT_CROSS_FITTED`.** External to weight fitting, but not
cross-fitted and not independent confirmation: same corpus construction, index
and fitted feature statistics as the dev cells. Its value is that it is where
the join evidence is — 198 independent join components against 54 in the
labelled dev cell. **C6** confirmed all three prohibitions on every run.

## Corpus data-quality finding

Two `join_pairs.jsonl` rows give **both members the same siglum**, asserting a
fragment joins itself: `KUB 28.89+` and `KBo 22.130a+`, both bin-parent and
discovery-side. Excluded and counted — a self-positive is unretrievable by
construction and would manufacture guaranteed misses. Worth reporting upstream
to the TLHdig team.

## Checks

| check | result |
|---|---|
| **C1** same family **AND different parent_doc** | PASSED — 364 same-family/same-parent join positives correctly kept |
| C2 identity control, per scope | PASSED |
| C3 split purity | PASSED |
| C4 joins/duplicates partition | PASSED |
| **C5** weights constant within each fold | PASSED in all four scopes |
| C6 bin-exception prohibitions | PASSED |
| C7 Tier C paired, same universe, component-clustered | PASSED |

## Limits

1. **Dev-side characterization**, developed adaptively across nine
   pre-registered runs on this same material. The protected test split remains
   one-shot and closed.
2. **Few clusters** — 54 join components and 35 composition clusters carry the
   primary family; 23 carry Tier C; 5 carry the cross-language joins cell,
   which is why it is descriptive only.
3. **Geometry is not an independent stratum** (horizontal ≡ tier C on dev), and
   **site has no contrast** (all dev join queries are Hattusa), so nothing here
   speaks to Hattusa→provincial generalization.
4. Query-relative scopes do **not** carry Tier C, bin-exception or join-strata
   analyses; their join populations are too thin to support them.
5. **Abstention** is reported as coverage, not as a rate.

## Artifacts

- `reports/phase5_taskb_transfer_protocol.md` (`318e153`, `3f334b9`, `2735e49`, `d1052d1`)
- `scripts/phase5_taskb_transfer.py`, `tests/test_taskb_transfer.py` (35 tests)
- `Phase4/phase4_out/p5_taskb_transfer{,_per_query,_manifest}.json`
