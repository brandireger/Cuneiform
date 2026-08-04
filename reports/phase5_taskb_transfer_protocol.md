# Task B transfer and language-scope comparison — PROTOCOL

**Status: PRE-REGISTERED 2026-08-04, committed before the run.**
**Authorized by Ixca 2026-08-04 with a written specification; this protocol
implements that specification and records where it makes a judgement call.**
**Dev queries only; test is never loaded. Training-free; no gradients.**

Executes **step 3** of the required sequence in
`reports/phase5_classical_control_review.md`. Steps 1 and 2 are complete
(`reports/phase5_statistics_universe_results.md`,
`reports/phase5_factorial_control_results.md`).

## 0. Framing — what this run is and is not

This is **dev-side transfer characterization, not independent confirmation.**
The channel design being carried into Task B was developed adaptively on this
same dev material, across three pre-registered runs that each reacted to the
last. A Task B result here inherits that adaptivity. Independent confirmation
requires the protected test split, which remains one-shot and separately gated.

Second framing constraint, carried from step 2 and load-bearing for how the
scope comparison must be read: **language restriction is an evidence-policy and
coverage choice with a named estimand, not a performance improvement.** On Task
A, `HITTITE_ONLY` raised the conditional increment while *lowering* absolute
recall@1 by −0.0131. Scope comparisons below are therefore reported as
estimand-and-coverage trade-offs, never as accuracy rankings.

## 1. Arms

| arm | added channels | weights |
|---|---|---|
| `bm25` | — | none |
| `bm25_unigram` | sign-unigram TF-IDF | α_u fitted |
| `bm25_unigram_bigram` | + adjacent sign **bigram-only** TF-IDF | (α_u, α_b) fitted **jointly** |

Bigrams carry their **own fitted weight**. The merged `unigram+bigram` channel
is **retired from the primary design** and appears only as a declared
historical control, because step 2 showed a merged vector's contrast is
indistinguishable from zero (+0.00261, cluster CI [−0.0192, +0.0192]) while the
same feature family separately weighted is not (+0.0431, CI [+0.0096,
+0.0821]).

**Primary contrast: `bm25_unigram_bigram` over `bm25_unigram`** — not over
BM25. Channels are computed per segment and summed per fragment, so no feature
crosses a line boundary; all renderings below are boundary-respecting.
Machinery (`channel_similarity`, `_segment_docs`, folds, grids, cluster
bootstrap) is imported from `phase5_factorial_control` and
`phase5_bm25_combiner`, never reimplemented.

## 2. Weight fitting — fit once, then freeze

Sparsity in the joins cell makes per-stratum fitting both unstable and
circular. Therefore, **per scope**:

1. Fit (α_u, α_b) **once**, on the **pooled** relation objective, over
   composition-level fit folds (recall@1, the inherited 12-value `ALPHA_GRID`
   for α_u and `[0.0, 0.1, 0.2, 0.4, 0.75, 1.0, 1.5]` for α_b, both containing
   0, ties to the smallest).
2. **Freeze** them.
3. Evaluate joins-only, duplicates-only, pooled, and **every** stratum with the
   frozen weights.

No weight is ever tuned on a result stratum. A stratum's number is a readout of
a system fitted elsewhere.

**Cross-task transfer is a separate, secondary arm**, reported apart and never
mixed with the above: the Task-A weights selected in step 2 under the matching
scope, applied unchanged to Task B. It answers "do Task A weights transfer?"
and nothing else.

## 3. Language scopes — compared, never assumed

`SCOPED`-only is prohibited by the authorizing specification. Compared scopes,
all boundary-respecting:

| scope | role |
|---|---|
| `HITTITE_ONLY` | ratified word-aware scope; **primary** |
| `ALL_LANGUAGES_UNCONDITIONED` | unrestricted control; **ablation-labeled** |
| `SAME_LANGUAGE_AS_QUERY` | query-relative scope |
| `CROSS_LANGUAGE_PARALLEL` | **separate assistance channel**, see §3.2 |

### 3.1 A declared asymmetry in the control

`ALL_LANGUAGES_UNCONDITIONED` is `is_ablation` in the contract, and
`language_lookup_v2._classify` short-circuits **every** filter for an ablation
scope. It therefore admits not only other languages but also lines that are
unresolved, mixed, or archive-stem-conflated, which the other scopes refuse.
The difference between it and `HITTITE_ONLY` is consequently **not purely
language** — it is language *plus* admission of unresolved material. This is
the P4-F Stage 1 trap (handoff "Traps hit", item 11) and is declared here in
advance so it is not later read as a clean language contrast. Refusal reasons
are reported by category so the two components stay separable.

### 3.2 Why `CROSS_LANGUAGE_PARALLEL` is a channel, not a rendering

Under that scope a line is admitted only if its language **differs** from the
query's, so a monolingual Hittite query rendered under it would be empty. It
cannot render the query side. It is therefore applied to the **candidate side
only**: the query is rendered under its own resolved language, and the index
admits only lines in a different language. That is an assistance channel over
cross-language parallel evidence, reported on its own, outside the primary
family and outside the common population.

### 3.3 Resolving a query's language, fail-closed

Query-relative scopes need a query language. Rule, fixed in advance: a
fragment's language is the **unique** resolved language across its lines; a
fragment whose lines resolve to more than one language is **refused** as
`QUERY_LANGUAGE_UNRESOLVED` and counted, never assigned a majority label.
Assigning a majority would invent a single-language identity for a
demonstrably multilingual object — the same fabrication `EXCLUDE_LINE` exists
to prevent.

## 4. Population and coverage — refusal is an outcome, not a filter

Step 2 intersected renderings to a common population. That is **wrong here**,
because it would hide precisely the coverage effect this run must measure.

- **Base population**: fragments with ≥4 content tokens under
  `ALL_LANGUAGES_UNCONDITIONED` (the most permissive scope), full labeled
  non-test universe, `main_split ∈ {train, dev}`, bins excluded from the
  labeled index as `main_split='discovery'`. Full-scale distractors; no
  dev-only index.
- **Per scope**, report as first-class outcomes:
  - queries that become unscorable,
  - candidate documents that become unscorable,
  - **positive relations lost because either endpoint became unscorable**,
  broken down by refusal reason.
- A **common-population sensitivity analysis** across the three symmetric
  scopes is reported additionally, so both readings are visible.

Every denominator is reconciled explicitly in the results, in the form step 2
adopted: raw → eligible → actually scored, with the exclusions named.

## 5. The mandatory three-way matrix, and stratification

Joins-only, duplicates-only, and pooled are reported for **every** arm, scope
and stratum. Pooled is a distinct estimand and never substitutes for a cell.

Positives come from `eval_harness.build_join_positives` and
`build_duplicate_positives` unchanged. **Bin rule, unchanged and load-bearing:
bin documents never become duplicate positives or negatives** (a bin fragment
is unlabeled, not negative), **but a physical join remains valid even when its
parent CTH is a bin** — `parent_is_bin` pairs are reported both included and
excluded.

Join strata: `join_type` (**direct `+` vs indirect `(+)`**), `tier` (A/B/C),
**tier-A / no-overlap** (`n_shared_lines == 0`), shared-line count band, damage
rate, fragment length band, resolved language, genre band, site, and
`parent_is_bin`. Duplicate strata: the applicable subset (damage, length,
language, genre band, site).

Two honest labels on the stratifiers: **`genre_band` is `cth // 100`**, a
coarse catalogue-century proxy and not a philological genre; and **`site`**
comes from the P2.5 provenance patch, with the standing caution that `AT` is a
single-document siglum.

## 6. Inference

**Resampling unit must match the relation**, per correction 5 of the review —
query rows are not independent:

| cell | bootstrap cluster |
|---|---|
| joins | **connected component of the physical join graph** |
| duplicates | composition / witness family (CTH) |
| pooled | composition (CTH); join components nest inside |

**One primary inferential family, declared now**: the primary contrast
(§1) in the **three relation cells** (joins, duplicates, pooled) under the
**primary scope** `HITTITE_ONLY` — three tests. Multiplicity correction:
**Holm–Bonferroni at family-wise α = 0.05**, applied to those three and only
those three.

**Everything else is descriptive**: all other scopes, all strata, the
cross-task transfer arm, and the assistance channel. They are reported with
intervals but carry no confirmatory claim unless separately corrected, and the
results must say so wherever they are quoted.

Metrics: **recall@1/5/10/100, MRR, candidate-set coverage, abstention rate, and
eligible candidate-set size**, for every cell.

## 7. Checks asserted in code before any number is reported

- **C1, same-family exclusion identity.** `eval_harness.build_family_map`'s H1
  exclusion must be active, and it is asserted that **no positive relation has
  both endpoints in one family** — such a pair would be silently unscorable
  rather than merely excluded. Counts reported. This check exists because the
  family-exclusion path previously exposed a real Task B defect.
- **C2, identity control.** Row z-normalization reproduces BM25's per-query
  records exactly, per scope.
- **C3, split purity.** Dev-query CTHs disjoint from train-index CTHs.
- **C4, joins/duplicates are a partition.** No pair appears in both positive
  sets (`build_duplicate_positives` excludes join pairs; asserted, not assumed).
- **C5, frozen weights are frozen.** The (α_u, α_b) recorded for a scope is
  byte-identical across all three cells and all strata for that scope.

## 8. What this run cannot establish

Test-side transfer; any deployable number; any claim about pretrained models;
and any assertion that one language scope is "better" — the scope comparison
reports an estimand-and-coverage trade-off, and step 2 already showed the
scope that maximizes a conditional increment is not the one that maximizes
absolute accuracy.

## 9. Outputs

- `scripts/phase5_taskb_transfer.py`
- `Phase4/phase4_out/p5_taskb_transfer.json`
- `Phase4/phase4_out/p5_taskb_transfer_per_query.jsonl`
- `Phase4/phase4_out/p5_taskb_transfer_manifest.json`
- `reports/phase5_taskb_transfer_results.md`
