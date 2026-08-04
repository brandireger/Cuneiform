# Task B relation retrieval and language-scope comparison — results

**Status: COMPLETE for the two fixed scopes. Cross-fitted. 2026-08-04.**
Protocol: `reports/phase5_taskb_transfer_protocol.md`, pre-registered `318e153`,
first amendment `3f334b9`, **second amendment `2735e49`** — all before this run.
Dev queries only; the protected test split is closed and was never loaded.
No representation learning or gradient training; two fusion weights per scope
were fitted **out of fold** by grid search.

**The word "transfer" is deliberately withheld from every claim below.** The
system evaluated here is fitted to Task B. Whether Task A's configuration
carries over is a different question, answered only by the Task-A-frozen arm
(protocol §2), which has not yet been run.

## Provenance — why this file was rewritten

An earlier version of this run was **withdrawn in full**. It searched weights
out of fold but then discarded the held-out predictions, took the modal weights
across all five folds, and re-scored all of dev with them, so every query was
scored under weights partly chosen using its own fold. Those numbers were
adaptive dev results, not cross-fitted tests, and they are **not reproduced
here or used as a comparison target**. The correction changed results, in one
scope materially. This section exists to record that the correction happened,
not to invite a before/after reading.

## Primary family — cross-fitted

Contrast: `BM25 + unigram + bigram_only` over `BM25 + unigram`. Weights fitted
per fold on the pooled objective and applied **only to that fold's held-out
queries**; predictions concatenated across folds; deltas, intervals, p-values
and Holm decisions all computed on that concatenation. Scope `HITTITE_ONLY`.

| cell | n | clusters | r@1 unigram → +bigram | Δ | cluster CI | p | Holm thresh | reject H₀ | gained / lost |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|---:|
| joins | 171 | 54 | 0.5439 → 0.6550 | **+0.1111** | [+0.0602, +0.1768] | 0.0010 | 0.0167 | **yes** | +22 / −3 |
| pooled | 766 | 35 | 0.5013 → 0.5888 | **+0.0875** | [+0.0591, +0.1230] | 0.0010 | 0.0250 | **yes** | +106 / −39 |
| duplicates | 766 | 35 | 0.3799 → 0.4426 | **+0.0627** | [+0.0378, +0.1076] | 0.0070 | 0.0500 | **yes** | +93 / −45 |

Per-fold weights actually used (α_u for the unigram arm; (α_u, α_b) for the
pair arm), with the held-out queries each was applied to:

| fold | α_u | (α_u, α_b) | held-out queries |
|---|---:|---:|---:|
| 0 | 1.0 | (0.40, 0.40) | 249 |
| 1 | 0.5 | (0.15, 1.00) | 133 |
| 2 | 0.75 | (0.15, 1.00) | 133 |
| 3 | 0.75 | (0.10, 0.75) | 132 |
| 4 | 0.5 | (0.00, 1.00) | 132 |

Weights differ across folds, as cross-fitting requires; **C5** confirms they are
constant across cells and strata *within* each fold. A modal configuration
(α_u = 0.5, pair = (0.15, 1.0)) is retained as a deployment candidate and
**carries no dev performance claim** — no number in this table was computed
from it.

Depth metrics for the pair arm move with recall@1: joins r@5 0.6901 → 0.7661,
r@100 0.8304 → 0.8772, MRR 0.6075 → 0.7090; duplicates r@5 0.6292 → 0.7428,
r@100 0.9086 → 0.9543, MRR 0.4946 → 0.5788.

Under the unrestricted control (`ALL_LANGUAGES_UNCONDITIONED`) the same three
cells give joins +0.0824 CI [+0.0389, +0.1287], pooled +0.0566 CI [+0.0321,
+0.0918], duplicates +0.0393 CI [+0.0141, +0.0814]. The effect is **robust to**
that scope — overlapping evidence on largely the same queries, **not**
independent replication.

## The qualification: where the join gain lives

**Zero-overlap joins show no evidence of gain.** This is the load-bearing
qualification, and unlike the Tier C comparison it rests on the primary cells'
own cross-fitted predictions.

| shared lines | n | clusters | r@1 unigram → +bigram | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| **0** | 34 | 18 | 0.2059 → 0.2353 | **+0.0294** | **[−0.0645, +0.1481]** |
| 1–2 | 43 | 19 | 0.4651 → 0.5814 | +0.1163 | [+0.0357, +0.2286] |
| 3–9 | 69 | 30 | 0.6957 → 0.8261 | +0.1304 | [+0.0541, +0.2154] |
| 10+ | 25 | 15 | 0.7200 → 0.8800 | +0.1600 | [+0.0385, +0.3203] |

Under the unrestricted control the zero-overlap cell is **−0.0278, CI [−0.0968,
0.0000]**. Indirect `(+)` joins agree: +0.0526, CI [0.0000, +0.1878], on
absolute recall of 0.16–0.21.

So the supportable statement is:

> The bigram channel improves duplicate-witness retrieval, and its help on
> physical joins **is concentrated where editor-aligned text is shared**. On
> joins with no shared lines — the case the fragment-as-matrix model exists to
> solve — there is no evidence it helps.

**Shared-line count is not a dose.** It is confounded with tier (0 shared lines
is exactly tier A here), with fragment length, and with other pair properties.
The monotone-looking column is a description of which pairs are easy, not a
dose–response relationship.

## Tier C, paired

Now evaluated as **pair instances**: each pair carries its own exclusive
renderings for both members, full and exclusive are computed on **exactly the
same instances and the same candidate universe** (identical index membership;
every fragment except the pair's own two identical in content — asserted in
code), and instances are clustered by **physical join component**.

| `HITTITE_ONLY`, 51 pair instances → 102 query-instances, 23 clusters | r@1 unigram → +bigram | Δ | cluster CI | p |
|---|---:|---:|---:|---:|
| full rendering — **contaminated** | 0.3039 → 0.3824 | +0.0784 | [0.0000, +0.1875] | 0.109 |
| **overlap-exclusive** | **0.0392 → 0.0000** | −0.0392 | [−0.0938, 0.0000] | 0.123 |
| overlap-exclusive, **single-partner fragments only** (24 instances, 11 clusters) | 0.0000 → 0.0000 | 0.0000 | [0.0000, 0.0000] | 1.000 |

**What this now supports, and what it does not.** Removing the shared
editor-aligned lines collapses absolute recall@1 from ~0.38 to **0.00–0.04** on
the same instances against the same distractors. The single-partner sensitivity
analysis lands at exactly 0.0000 for both arms, so the collapse is not an
artifact of the multi-partner rendering problem that the first version had.

The **bigram contribution** within Tier C is *not* resolved: neither the full
(p=0.109) nor the exclusive (p=0.123) delta clears significance on 23 clusters.
This population is too small to say whether the channel helps there.

**Do not compare these absolute numbers to the tier-C row in the strata table.**
They are different estimands: a stratum query counts a hit against *any* of its
join partners, whereas a pair instance requires the *specific* partner. The
0.3824 above and the 0.8404 in the strata table are not the same measurement.

Tier C accounting: 92 pairs considered, 41 `exclusive_untestable`, 0 lost to
missing reconstruction, 0 empty-exclusive, **51 usable**, of which 12 involve
only single-partner fragments.

## Language scope: what restriction costs, by cause

`HITTITE_ONLY` refuses 97 dev queries, 768 candidate documents, and 2,832
positive relations. **Broken down by cell, that loss is almost entirely
duplicates:**

| cell | relations lost | endpoint refusal reasons |
|---|---:|---|
| joins | **7** | `OUT_OF_SCOPE_LANGUAGE` 9, `LINE_NOT_IN_LANGUAGE_DATASET` 4 |
| duplicates | **2,825** | `LINE_NOT_IN_LANGUAGE_DATASET` 1,693, `OUT_OF_SCOPE_LANGUAGE` 1,614 |
| pooled | 2,832 | `LINE_NOT_IN_LANGUAGE_DATASET` 1,697, `OUT_OF_SCOPE_LANGUAGE` 1,623 |

(Endpoint counts exceed relation counts because both endpoints of a relation
can be refused.)

**Two distinct causes, which must not be merged:**

- **`OUT_OF_SCOPE_LANGUAGE`** is an affirmative classification: the corpus
  records these lines as a language other than Hittite. Excluding them is the
  scope doing its declared job.
- **`LINE_NOT_IN_LANGUAGE_DATASET`** is a **coverage gap in our own derived
  Gate-2 dataset**, not a statement about the tablet. These lines are not
  known to be non-Hittite; they are unresolved by our pipeline.

For duplicates the two are nearly equal (1,693 vs 1,614), so **roughly half the
duplicate evidence that `HITTITE_ONLY` discards is discarded because our
language dataset does not cover it**, not because the material is
non-Hittite. That is a fixable engineering deficit, and it is a different
finding from the estimand choice.

On the common population, absolute recall@1 under the unrestricted scope is
equal or marginally higher in all three cells (joins 0.6395 vs 0.6550 — here
`HITTITE_ONLY` is higher; duplicates 0.4429 vs 0.4426; pooled 0.5857 vs
0.5888), while the deltas differ in the other direction. Language restriction
remains an **evidence-policy and coverage choice buying a named estimand**, not
a performance improvement.

## Bin-parent physical joins — descriptive

| `HITTITE_ONLY` | n | clusters | r@1 unigram → +bigram | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| bin-exception population | 504 | **198** | 0.5952 → 0.7302 | +0.1349 | [+0.1000, +0.1687] |

**Status: `DESCRIPTIVE_NOT_CROSS_FITTED`.** These fragments never enter any
fold's weight fit, so the deployment-candidate configuration is *external to
weight fitting* for them. That is **not** cross-fitting and **not** independent
confirmation: they share the same corpus construction, the same index, and the
same fitted feature statistics as the dev cells. Read it as a descriptive
readout on a population the weights did not see.

Its value is that it is where the join evidence actually is: 198 independent
join components against 54 in the labelled dev cell. Check **C6** confirmed on
every run that no bin fragment became a duplicate positive in either role,
entered the candidate index used by non-bin queries, or appeared in the
duplicates or pooled cells.

## Corpus data-quality finding

Two `join_pairs.jsonl` rows give **both members the same siglum**, asserting a
fragment joins itself: `KUB 28.89+` (member 1 = KUB 48.20, twice) and
`KBo 22.130a+` (member 1 = KBo 22.130a, twice). Both are bin-parent and
discovery-side. Excluded and counted — `run_retrieval` excludes a query from
its own ranking, so a self-positive is **unretrievable by construction** and
would manufacture guaranteed misses. Worth reporting upstream to the TLHdig
team.

## Checks

| check | result |
|---|---|
| **C1** same family **AND different parent_doc** | PASSED — 0 positives excluded; **364 same-family/same-parent join positives correctly kept** |
| C2 identity control, per scope | PASSED in both |
| C3 split purity | PASSED |
| C4 joins/duplicates partition | PASSED |
| **C5** weights constant **within each fold** | PASSED in both scopes; weights differ across folds by construction |
| C6 bin-exception prohibitions | PASSED — all three, both scopes |
| C7 Tier C paired, same universe, component-clustered | PASSED — asserted in code |

## Limits

1. **Dev-side characterization.** The design was developed adaptively across
   five pre-registered runs on this same dev material. The protected test split
   remains one-shot and closed.
2. **Few clusters.** 54 join components and 35 composition clusters carry the
   primary family; 23–26 clusters carry Tier C. The intervals are wide because
   the evidence is.
3. **Geometry must not be read as an independent stratum** — on this dev slice
   horizontal ≡ tier C and vertical ≡ tiers A+B.
4. **Site has no contrast** — all 171 dev join queries are Hattusa, so nothing
   here speaks to Hattusa→provincial generalization.
5. **Not yet run:** `SAME_LANGUAGE_AS_QUERY`, `CROSS_LANGUAGE_PARALLEL`, and
   the **Task-A-frozen arm**. Until the last of these exists, no claim in this
   file may be described as cross-task transfer.
6. **Abstention** is reported as coverage, not as a rate: this retrieval setup
   has no calibrated abstention rule, and inventing one would be a new estimand
   rather than a measurement.

## Artifacts

- `reports/phase5_taskb_transfer_protocol.md` (`318e153`, amended `3f334b9`, `2735e49`)
- `scripts/phase5_taskb_transfer.py`, `tests/test_taskb_transfer.py`
- `Phase4/phase4_out/p5_taskb_transfer{,_per_query,_manifest}.json`
