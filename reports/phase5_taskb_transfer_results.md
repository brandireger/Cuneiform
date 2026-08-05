# Task B relation retrieval, language scopes, and Task-A-frozen transfer

**Status: COMPLETE — four scopes, cross-fitted, plus the Task-A-frozen arm.
2026-08-04.**
Protocol: `reports/phase5_taskb_transfer_protocol.md`, pre-registered `318e153`,
amendments `3f334b9` and `2735e49` — all before the runs they govern.
Dev queries only; the protected test split is closed and was never loaded.
No representation learning or gradient training; two fusion weights per scope
fitted **out of fold**, and one arm using weights fitted on a different task
entirely.

## Provenance — why this file was rewritten once

An earlier version was **withdrawn in full**: it searched weights out of fold
but then discarded the held-out predictions, took modal weights across all
folds, and re-scored all of dev, so every query was scored under weights partly
chosen using its own fold. Those numbers were adaptive dev results, not
cross-fitted tests. They are **not reproduced here and not used as a comparison
target**. This note records that the correction happened; it does not invite a
before/after reading.

## Primary family — cross-fitted, `HITTITE_ONLY`

Contrast: `BM25 + unigram + bigram_only` over `BM25 + unigram`. Weights fitted
per fold on the pooled objective, applied **only to that fold's held-out
queries**, predictions concatenated; deltas, intervals, p-values, Holm
decisions and strata all computed on that concatenation.

| cell | n | clusters | r@1 unigram → +bigram | Δ | cluster CI | p | Holm thresh | reject H₀ | gained / lost |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|---:|
| joins | 171 | 54 | 0.5439 → 0.6550 | **+0.1111** | [+0.0602, +0.1768] | 0.0010 | 0.0167 | **yes** | +22 / −3 |
| pooled | 766 | 35 | 0.5013 → 0.5888 | **+0.0875** | [+0.0591, +0.1230] | 0.0010 | 0.0250 | **yes** | +106 / −39 |
| duplicates | 766 | 35 | 0.3799 → 0.4426 | **+0.0627** | [+0.0378, +0.1076] | 0.0070 | 0.0500 | **yes** | +93 / −45 |

Per-fold weights actually used:

| fold | α_u | (α_u, α_b) | held-out queries |
|---|---:|---:|---:|
| 0 | 1.0 | (0.40, 0.40) | 249 |
| 1 | 0.5 | (0.15, 1.00) | 133 |
| 2 | 0.75 | (0.15, 1.00) | 133 |
| 3 | 0.75 | (0.10, 0.75) | 132 |
| 4 | 0.5 | (0.00, 1.00) | 132 |

**C5** confirms weights are constant across cells and strata *within* each fold;
they differ across folds, as cross-fitting requires. The modal configuration
(α_u = 0.5, pair = (0.15, 1.0)) is retained as a deployment candidate and
**carries no dev performance claim** — no number above was computed from it.

## The load-bearing qualification: zero-overlap joins

| shared lines | n | clusters | r@1 unigram → +bigram | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| **0** | 34 | 18 | 0.2059 → 0.2353 | **+0.0294** | **[−0.0645, +0.1481]** |
| 1–2 | 43 | 19 | 0.4651 → 0.5814 | +0.1163 | [+0.0357, +0.2286] |
| 3–9 | 69 | 30 | 0.6957 → 0.8261 | +0.1304 | [+0.0541, +0.2154] |
| 10+ | 25 | 15 | 0.7200 → 0.8800 | +0.1600 | [+0.0385, +0.3203] |

Under the unrestricted control the zero-overlap cell is **−0.0278, CI [−0.0968,
0.0000]**. Indirect `(+)` joins agree: +0.0526, CI includes zero.

> The bigram channel improves duplicate-witness retrieval, and its help on
> physical joins **is concentrated where editor-aligned text is shared**. On
> joins with no shared lines — the case the fragment-as-matrix model exists to
> solve — there is no evidence it helps.

Shared-line count is **not a dose**: it is confounded with tier (0 shared lines
is exactly tier A here), with fragment length, and with other pair properties.

## Tier C, paired

Pair instances, each with its own exclusive renderings; full and exclusive on
**exactly the same instances and the same candidate universe** (asserted in
code); clustered by **physical join component**.

| `HITTITE_ONLY`, 51 instances → 102 query-instances, 23 clusters | r@1 unigram → +bigram | Δ | cluster CI | p |
|---|---:|---:|---:|---:|
| full rendering — **contaminated** | 0.3039 → 0.3824 | +0.0784 | [0.0000, +0.1875] | 0.109 |
| **overlap-exclusive** | **0.0392 → 0.0000** | −0.0392 | [−0.0938, 0.0000] | 0.123 |
| exclusive, **single-partner fragments only** (24 instances, 11 clusters) | 0.0000 → 0.0000 | 0.0000 | [0.0000, 0.0000] | 1.000 |

Removing shared editor-aligned lines collapses absolute recall@1 from ~0.38 to
**0.00–0.04** on the same instances against the same distractors, and the
single-partner sensitivity lands at exactly 0.0000 — so the collapse is not an
artifact of the multi-partner rendering problem the first version had.

**The bigram contribution *within* Tier C is unresolved**: neither delta clears
significance on 23 clusters. **Do not compare these absolutes to the tier-C row
in the strata table** — a stratum query may hit *any* of its partners, a pair
instance must hit the *specific* one. Different estimands.

## Language scopes

| scope | queries | index | relations | status |
|---|---:|---:|---:|---|
| `ALL_LANGUAGES_UNCONDITIONED` (ablation) | 876 | 7,490 | 43,008 | evaluable |
| `HITTITE_ONLY` | 779 | 6,722 | 40,176 | evaluable |
| `SAME_LANGUAGE_AS_QUERY` | 734 | 6,412 | 30,526 | evaluable |
| `CROSS_LANGUAGE_PARALLEL` | **0** | **0** | **0** | **NOT EVALUABLE** |

Cross-fitted deltas (pair arm over unigram arm):

| scope | joins | duplicates | pooled |
|---|---:|---:|---:|
| `HITTITE_ONLY` | +0.1111 [+0.0602, +0.1768] | +0.0627 [+0.0378, +0.1076] | +0.0875 [+0.0591, +0.1230] |
| `ALL_LANGUAGES_UNCONDITIONED` | +0.0824 [+0.0389, +0.1287] | +0.0393 [+0.0141, +0.0814] | +0.0566 [+0.0321, +0.0918] |
| `SAME_LANGUAGE_AS_QUERY` | +0.0867 [+0.0338, +0.1464] | +0.0457 [+0.0224, +0.0822] | +0.0637 [+0.0356, +0.0927] |

The effect is present under every evaluable scope. Between-scope differences
are **not** part of the primary family and carry no dedicated inference.

### `CROSS_LANGUAGE_PARALLEL` — a coverage result, and its ceiling

**Reachable-positive ceiling** (a positive counts as reachable only if the
target survives the different-language admission):

| cell | positives considered | reachable | ceiling |
|---|---:|---:|---:|
| joins | — | — | **0.0295** |
| duplicates | — | — | **0.0741** |
| pooled | — | — | 0.0739 |

At most **3–7%** of positives were ever reachable, and after requiring ≥4
admitted tokens on both endpoints, **zero queries remain scorable**. Without
the ceiling this would look like a scoring failure; it is an admission bound.

**Fragment-level cross-language parallel evidence is essentially unavailable in
this corpus under a strict different-language line admission.** That is a real
finding about the encoded evidence, not about the scorer.

**On what these positives are:** they are **different-language same-CTH
relations**. They are *not* independently annotated as actual textual
parallels — shared CTH membership plus a language difference is what the corpus
supports. Any future recall figure here must carry that caveat and its ceiling.

### `SAME_LANGUAGE_AS_QUERY` — the cost is my own fail-closed rule

It loses **12,482 relations, every one to `QUERY_LANGUAGE_UNRESOLVED`** — 4.4×
what `HITTITE_ONLY` loses. That is not line-level language evidence: it is
protocol §3.3, the rule I chose, which refuses any fragment whose lines resolve
to more than one language rather than assigning a majority label. 142 of 876
dev queries are refused outright on that basis.

The rule is defensible — assigning a majority language to a demonstrably
multilingual object is the fabrication `EXCLUDE_LINE` exists to prevent — but
its cost should be recorded as a **design choice**, not attributed to the
corpus.

### What `HITTITE_ONLY` costs, by cause

| cell | relations lost | endpoint refusal reasons |
|---|---:|---|
| joins | **7** | `OUT_OF_SCOPE_LANGUAGE` 9, `LINE_NOT_IN_LANGUAGE_DATASET` 4 |
| duplicates | **2,825** | `LINE_NOT_IN_LANGUAGE_DATASET` 1,693, `OUT_OF_SCOPE_LANGUAGE` 1,614 |
| pooled | 2,832 | `LINE_NOT_IN_LANGUAGE_DATASET` 1,697, `OUT_OF_SCOPE_LANGUAGE` 1,623 |

**Two causes that must stay separate.** `OUT_OF_SCOPE_LANGUAGE` is an
affirmative classification — the corpus records those lines as another
language, and excluding them is the scope doing its declared job.
`LINE_NOT_IN_LANGUAGE_DATASET` is a **coverage gap in our own derived Gate-2
dataset**, saying nothing about the tablet. For duplicates the two are nearly
equal, so **roughly half the duplicate evidence `HITTITE_ONLY` discards is lost
to our own pipeline's coverage** — a fixable engineering deficit, distinct from
the estimand choice.

### Absolute accuracy on the common population

658 queries scorable under all three evaluable scopes. Final-system (pair arm)
recall@1:

| cell | `HITTITE_ONLY` | `ALL_LANGUAGES` | `SAME_LANGUAGE` |
|---|---:|---:|---:|
| joins | 0.6733 | 0.6600 | **0.6759** |
| duplicates | **0.4284** | 0.4240 | 0.3889 |
| pooled | **0.5840** | 0.5760 | 0.5401 |

**No scope uniformly dominates.** `SAME_LANGUAGE_AS_QUERY` is best on joins,
`HITTITE_ONLY` on duplicates and pooled, the unrestricted ablation never best.
Differences on joins span 0.016. **No dedicated inference was pre-registered
for these and none is offered.** (Scored counts differ slightly — 145–150 joins,
648–651 duplicates — because a query with no reachable positive under a scope
is dropped by the retrieval runner.)

Language restriction remains an **evidence-policy and coverage choice buying a
named estimand**. Its measurable cost is coverage, not accuracy.

## Task-A-frozen arm

Task A's committed per-fold weights (step 2, `SCOPED` rendering, conditional
`bigram_only` arm) and **Task A's own CTH→fold mapping**, applied unchanged.
Nothing selected or retuned on Task B. Queries whose CTH had no Task A fold are
excluded and counted, never reassigned.

| scope | Task-A-frozen (pooled) | Task-B-fitted (pooled) | excluded |
|---|---:|---:|---:|
| `HITTITE_ONLY` | **+0.0888** [+0.0597, +0.1264] | +0.0875 | 0 |
| `ALL_LANGUAGES_UNCONDITIONED` | **+0.0712** [+0.0472, +0.1115] | +0.0566 | 10 |
| `SAME_LANGUAGE_AS_QUERY` | **+0.0770** [+0.0539, +0.1051] | +0.0637 | 10 |

**The Task A configuration works on Task B without any retuning**, matching or
beating the Task-B-fitted configuration in all three scopes.

**How strong this evidence is, honestly.** Under `HITTITE_ONLY` the two weight
sets differ **only in fold 3** — Task A chose (0.15, 1.0) where Task B chose
(0.10, 0.75) — so that row mostly shows *the two tasks independently selecting
nearly the same configuration*, which is a weaker claim than a distinct
configuration transferring. The informative rows are `ALL_LANGUAGES` and
`SAME_LANGUAGE`, where the weight sets genuinely differ and the frozen Task A
configuration still does better. Both arms also share the same corpus, index
and feature statistics; this is cross-**task** evidence, not cross-corpus.

With this arm in place, the word **transfer** is now usable for the specific
claim above — Task A's fitted configuration carries to Task B — and for nothing
broader.

## Bin-parent physical joins — descriptive

| `HITTITE_ONLY` | n | clusters | r@1 unigram → +bigram | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| bin-exception population | 504 | **198** | 0.5952 → 0.7302 | +0.1349 | [+0.1000, +0.1687] |

**Status `DESCRIPTIVE_NOT_CROSS_FITTED`.** External to weight fitting (these
fragments never enter any fold), but **not** cross-fitted and **not**
independent confirmation: same corpus construction, same index, same fitted
feature statistics as the dev cells. Its value is that it is where the join
evidence is — 198 independent join components against 54 in the labelled dev
cell. **C6** confirmed on every run that no bin fragment became a duplicate
positive, entered the non-bin candidate index, or appeared in the duplicates or
pooled cells.

## Corpus data-quality finding

Two `join_pairs.jsonl` rows give **both members the same siglum**, asserting a
fragment joins itself: `KUB 28.89+` (member 1 = KUB 48.20, twice) and
`KBo 22.130a+` (member 1 = KBo 22.130a, twice); both bin-parent and
discovery-side. Excluded and counted — `run_retrieval` excludes a query from its
own ranking, so a self-positive is **unretrievable by construction** and would
manufacture guaranteed misses. Worth reporting upstream to the TLHdig team.

## Checks

| check | result |
|---|---|
| **C1** same family **AND different parent_doc** | PASSED — 0 excluded; **364 same-family/same-parent join positives correctly kept** |
| C2 identity control, per scope | PASSED in all evaluable scopes |
| C3 split purity | PASSED |
| C4 joins/duplicates partition | PASSED |
| **C5** weights constant **within each fold** | PASSED in all evaluable scopes |
| C6 bin-exception prohibitions | PASSED |
| C7 Tier C paired, same universe, component-clustered | PASSED — asserted in code |

## Limits

1. **Dev-side characterization.** The design was developed adaptively across
   six pre-registered runs on this same dev material. The protected test split
   remains one-shot and closed.
2. **Few clusters.** 54 join components and 35 composition clusters carry the
   primary family; 23 carry Tier C.
3. **Geometry is not an independent stratum** — on this dev slice horizontal ≡
   tier C and vertical ≡ tiers A+B.
4. **Site has no contrast** — all dev join queries are Hattusa, so nothing here
   speaks to Hattusa→provincial generalization.
5. **`CROSS_LANGUAGE_PARALLEL` produced no scored result**, only a ceiling and
   a coverage account.
6. **Abstention** is reported as coverage, not as a rate: this setup has no
   calibrated abstention rule.

## Artifacts

- `reports/phase5_taskb_transfer_protocol.md` (`318e153`, `3f334b9`, `2735e49`)
- `scripts/phase5_taskb_transfer.py`, `tests/test_taskb_transfer.py`
- `Phase4/phase4_out/p5_taskb_transfer{,_per_query,_manifest}.json`
