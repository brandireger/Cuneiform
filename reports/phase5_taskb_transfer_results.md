# Task B transfer and language-scope comparison — results

> **WITHDRAWN 2026-08-04 — EVERY NUMBER BELOW IS SUPERSEDED. DO NOT QUOTE.**
> Ixca's review found the evaluation was not cross-fitted. Weights were
> searched out of fold, but the held-out predictions were then **discarded**,
> the modal weights across all five folds were taken, and all of dev was
> re-scored with them — so every query was scored under weights partly chosen
> using its own fold. The Holm rejections below are therefore **adaptive dev
> results, not cross-fitted tests**.
>
> The Tier C comparison is also withdrawn on two counts: full rendering
> (94 queries) and overlap-exclusive (42 scored queries) were computed on
> **different populations**, so the absolute drop was not a paired estimate;
> and exclusive renderings were keyed by fragment, so each of 32 fragments
> with several Tier C partners kept only the last partner's rendering — a
> partner-dependent quantity stored as a fragment-dependent one.
>
> A corrected run is in progress under the second protocol amendment. The
> findings most likely to survive, because they do not depend on the weight
> path, are the **zero-overlap qualification**, the **bin exception**, and the
> **self-join corpus finding**. Nothing here should be cited until the
> corrected results file replaces it.

**Status: WITHDRAWN, superseded by the corrected cross-fitted run.**
Protocol: `reports/phase5_taskb_transfer_protocol.md`, pre-registered at
`318e153`, amended and authorized at `3f334b9`, both **before** this run.
Dev queries only; the protected test split was never loaded. No representation
learning or gradient training; two fusion weights per scope were fitted out of
fold and then frozen.

Executes **step 3** of the required sequence in
`reports/phase5_classical_control_review.md`.

## Verdict on the declared primary family

The primary contrast is `BM25 + unigram + bigram_only` over
`BM25 + unigram`, in the three relation cells, under `HITTITE_ONLY`, on
composition/join-component cluster intervals, corrected by Holm–Bonferroni at
family-wise α = 0.05.

| cell | r@1 unigram → +bigram | Δ | cluster CI | p | Holm threshold | reject H₀ |
|---|---:|---:|---:|---:|---:|:--:|
| joins | 0.5556 → 0.6667 | **+0.1111** | [+0.0625, +0.1688] | 0.0010 | 0.0167 | **yes** |
| pooled | 0.5157 → 0.6031 | **+0.0875** | [+0.0591, +0.1277] | 0.0010 | 0.0250 | **yes** |
| duplicates | 0.3916 → 0.4543 | **+0.0627** | [+0.0370, +0.1131] | 0.0130 | 0.0500 | **yes** |

**All three cells reject, and this is the first time in this line that they
do.** Frozen CANINE reached significance in none of them; the step-2 character
and bigram results were Task A only. The effect replicates under the
unrestricted control (`ALL_LANGUAGES_UNCONDITIONED`: joins +0.1099, pooled
+0.0728, duplicates +0.0497, all p ≤ 0.007), so it is not an artifact of the
language scope.

Frozen weights, fitted once on the pooled objective and never re-tuned:
`HITTITE_ONLY` (α_u = 0.15, α_b = 1.0); `ALL_LANGUAGES_UNCONDITIONED`
(α_u = 0.0, α_b = 1.0). In both, the bigram channel carries the larger weight,
and under the unrestricted scope the fold fit set the unigram weight to **zero**
in the pair arm.

## The qualification that matters more than the verdict

**Amendment 3 was the right call, and it cuts against the joins headline.**

| Tier C, 51 usable dev pairs | r@1 unigram → +bigram | Δ | cluster CI | p |
|---|---:|---:|---:|---:|
| full rendering — **contaminated upper bound** | 0.7234 → 0.8617 | +0.1383 | [+0.0824, +0.1951] | — |
| **overlap-exclusive** | 0.1765 → 0.1569 | **−0.0238** | [−0.0769, 0.0000] | 0.514 |

Removing the shared editor-aligned lines drops absolute recall@1 from 0.86 to
**0.16**, and the bigram channel's contribution goes to nothing. Tier C is 94
of 171 join queries, so a majority of the joins cell rests on pairs where
retrieval is substantially the evaluation recovering the editor's own
alignment.

The shared-line stratum says the same thing continuously, and it is the
sharpest result in the run:

| shared lines | n | r@1 unigram → +bigram | Δ | cluster CI |
|---|---:|---:|---:|---:|
| **0** | 34 | 0.2059 → 0.2353 | **+0.0294** | **[−0.0645, +0.1481]** |
| 1–2 | 43 | 0.4651 → 0.5814 | +0.1163 | [+0.0357, +0.2286] |
| 3–9 | 69 | 0.7246 → 0.8551 | +0.1304 | [+0.0634, +0.2000] |
| 10+ | 25 | 0.7200 → 0.8800 | +0.1600 | [+0.0385, +0.3203] |

Under the unrestricted control the zero-overlap cell is **−0.0278, CI
[−0.0968, 0.0000]**. Indirect `(+)` joins — the designated long-gap stratum —
agree: +0.0526 CI [0.0000, +0.1878] under `HITTITE_ONLY` and exactly +0.0000
under the control, on absolute recall of 0.16–0.21.

**Therefore the defensible claim is narrower than the primary family alone
suggests:**

> The bigram channel transfers to duplicate-witness retrieval, and to physical
> joins **in proportion to how much text the two fragments already share**. On
> joins with no shared lines — the case the matrix model exists to solve — there
> is no evidence it helps.

That is not a failure of the channel; it is the evaluation finally being able
to tell the two situations apart, which it could not do before this amendment.

## Language scope: an estimand and coverage choice, on a common population

Cross-scope absolute numbers are otherwise measured on different query sets
(766 vs 865), so the protocol's common-population analysis is what makes them
comparable. Restricted to the queries **both** scopes can serve:

| cell | `HITTITE_ONLY` r@1 | `ALL_LANGUAGES` r@1 | Δ of the deltas |
|---|---:|---:|---|
| joins (n≈171) | 0.6667 | **0.6686** | HITTITE +0.1111, ALL +0.1105 |
| duplicates (n≈766) | 0.4543 | **0.4597** | HITTITE +0.0627, ALL +0.0519 |
| pooled (n≈766) | 0.6031 | **0.6091** | HITTITE +0.0875, ALL +0.0766 |

On identical queries the unrestricted scope is **equal or marginally better in
absolute accuracy in all three cells**, while `HITTITE_ONLY` shows the larger
*increment*. This is exactly the step-2 pattern: the scope weakens the
reference more than it weakens the system, so the increment rises while
accuracy does not.

What the restriction costs, reported as a first-class outcome:

| refused by `HITTITE_ONLY` | count |
|---|---:|
| dev queries | **97** of 876 |
| candidate documents | **768** of 7,490 |
| **positive relations** | **2,832** of 43,008 |

Refusal reasons across the labeled universe: `OUT_OF_SCOPE_LANGUAGE` 37,075
lines, `LINE_NOT_IN_LANGUAGE_DATASET` 7,610, `MIXED_LANGUAGE_LINE` 2,583,
`UNRESOLVED_LEXICAL_LANGUAGE` 31.

**Language restriction remains an evidence-policy and coverage choice buying a
named estimand — not a performance improvement.** Note also the declared
asymmetry: `ALL_LANGUAGES_UNCONDITIONED` is `is_ablation`, and
`language_lookup_v2._classify` short-circuits every filter for an ablation
scope, so it admits unresolved and conflated lines too. The contrast is
language *plus* unresolved-material admission, not language alone.

## The bin exception behaved, and it is where the join evidence is

| joins row | n queries | clusters | r@1 unigram → +bigram | Δ | cluster CI |
|---|---:|---:|---:|---:|---:|
| dev index only | 171 | 54 | 0.5556 → 0.6667 | +0.1111 | [+0.0625, +0.1688] |
| **+ bin-parent joins (§5.1)** | **675** | **252** | 0.5837 → 0.7111 | **+0.1274** | [+0.0969, +0.1595] |

Admitting bin-parent physical joins **quadruples** the join evidence (54 → 252
independent join components) and the effect holds and tightens. Check **C6**
confirmed all three prohibitions on every run: no bin fragment became a
duplicate positive in either role, entered the candidate index used by non-bin
queries, or appeared in the duplicates or pooled cells. The two rows are
reported separately and never averaged.

This is the clearest argument for the exception: most of the corpus's physical
join evidence sits under catalogue bins, and excluding it would have discarded
three quarters of the join components available for evaluation.

## Corpus data-quality finding

Two rows of `join_pairs.jsonl` give **both members the same siglum**, asserting
that a fragment joins itself: `KUB 28.89+` (member 1 = KUB 48.20, twice) and
`KBo 22.130a+` (member 1 = KBo 22.130a, twice). Both are bin-parent and
discovery-side, which is why they surface only through the §5.1 exception.

They are excluded from positives and counted. This is not cosmetic:
`run_retrieval` excludes a query from its own ranking, so a self-positive is
**unretrievable by construction** and would have manufactured guaranteed
misses. Worth reporting upstream to the TLHdig team alongside any other
findings.

## Other strata — descriptive only

Per the protocol, everything outside the primary family carries no confirmatory
claim. Read these as descriptive:

| stratifier | reading |
|---|---|
| **tier** | A +0.0294 CI [−0.0645, +0.1481] · B +0.1163 · C +0.1383 (contaminated) |
| **join_type** | direct +0.1325 · inferred_from_shared_lines +0.1014 · indirect +0.0526 CI includes 0 |
| **length** | long +0.1591 · medium +0.0597 · short +0.0625 — longer fragments carry more bigrams |
| **damage** | low +0.1277 · medium +0.0750 · high +0.1081 — no ordered pattern; intervals overlap |
| **geometry** | horizontal +0.1383 · vertical +0.0779 — **but see the confound below** |
| **site** | 171 of 171 dev join queries are Hattusa |
| **genre band** | 134 of 171 in band 600; other bands have 3–31 queries |

**Do not report geometry as an independent finding.** In this dev slice
horizontal n = 94 and tier C n = 94; vertical n = 77 = tier A 34 + tier B 43.
Geometry and tier are perfectly confounded here, so the geometry row is the
tier row wearing different labels.

**The site stratum is empty of contrast**: every dev join query is Hattusa, so
this run says nothing about the headline Hattusa→provincial generalization
experiment.

`join_type` has **four** values in the corpus, not the direct/indirect binary
the protocol's wording implies — `direct` 968, `inferred_from_shared_lines`
399, `indirect` 213, and one `None` across the full set. All are reported
rather than forced into two.

## Checks

| check | result |
|---|---|
| **C1** same family **AND different parent_doc** | **PASSED** — 0 positives excluded; **364 same-family/same-parent join positives correctly kept** |
| C2 identity control, per scope | PASSED in both |
| C3 split purity | PASSED |
| C4 joins/duplicates partition | PASSED — 0 overlapping pairs |
| C5 frozen weights | one (α_u, α_b) per scope across every cell and stratum |
| C6 bin exception prohibitions | PASSED — all three, both scopes |
| C7 Tier C overlap-exclusive | 92 considered → 41 `exclusive_untestable` → **51 usable**, all counted |

**C1 is the amendment, and the number vindicates it.** 364 join positive
endpoint-pairs share a family with the same parent; the protocol's first-draft
assertion would have flagged every one of them. That is the 2026-07-22
`top_k_ranking` bug — which drove joins tier-A/B recall@1 to 0.0 — reappearing
as a check instead of a defect.

## Limits, stated plainly

1. **Dev-side characterization, not confirmation.** The channel design was
   developed adaptively on this same dev material across four pre-registered
   runs that each reacted to the last. The protected test split remains
   one-shot and closed.
2. **Few clusters.** 54 join components and 35 composition clusters carry the
   primary family. The relation-aware intervals are correspondingly wide, and
   that is the honest width, not a defect of the bootstrap.
3. **Tier C overlap-exclusive rests on 42 scored queries across 23 clusters**,
   and **32 fragments appear in more than one Tier C pair**, where a
   per-fragment substitution retains only the last pair's exclusive set — a
   limitation inherited from `eval_harness.tier_c_exclusive_tokens`, now
   counted rather than silent.
4. **Not run.** The two query-relative scopes (`SAME_LANGUAGE_AS_QUERY`,
   `CROSS_LANGUAGE_PARALLEL`) are implemented but were deferred to a second
   pass. The **cross-task transfer arm** — Task-A-frozen weights applied to
   Task B — is specified in §2 and was **not implemented**; it remains owed.
5. **Abstention is reported as coverage, not as an abstention rate.** This
   retrieval setup has no calibrated abstention rule; inventing one here would
   have been a new estimand rather than a measurement. Candidate-set coverage,
   eligible candidate-set size, and refusal counts are reported instead.

## Artifacts

- `reports/phase5_taskb_transfer_protocol.md` (pre-registered `318e153`, amended `3f334b9`)
- `scripts/phase5_taskb_transfer.py`
- `tests/test_taskb_transfer.py`
- `Phase4/phase4_out/p5_taskb_transfer.json`
- `Phase4/phase4_out/p5_taskb_transfer_per_query.jsonl`
- `Phase4/phase4_out/p5_taskb_transfer_manifest.json`
