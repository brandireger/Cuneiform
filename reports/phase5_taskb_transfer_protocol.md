# Task B transfer and language-scope comparison — PROTOCOL

**Status: PRE-REGISTERED 2026-08-04, committed before the run.**
**Authorization: Ixca issued a written specification on 2026-08-04 and, on
reviewing the first draft of this protocol, granted authorization
*conditional on four amendments* — C1's exclusion predicate, an explicit
physical-join bin exception, overlap-exclusive Tier C evaluation, and the
genre label. This revision implements all four. Authorization is effective
from the commit of this revision; the first draft was NOT authorized to run.**
**Dev queries only; the protected test split is closed and is never loaded.**
**No representation learning or gradient training; fusion weights are fitted
out of fold.**

> **SECOND AMENDMENT, 2026-08-04, after Ixca reviewed the first results.** The
> first implementation searched weights out of fold but then **discarded the
> held-out predictions**, took the modal weights across all five folds, and
> re-scored all of dev with them — so every query was scored under weights
> partly chosen using its own fold. The reported Holm rejections were adaptive
> dev results, not cross-fitted tests. **Every number from that run is
> withdrawn.** §2 and §6 below are amended to require genuine cross-fitting;
> §5.2 is amended to evaluate Tier C as pair instances, because the first
> version compared full and exclusive renderings on different populations and
> made a partner-dependent rendering fragment-dependent; and §4 is amended to
> break lost relations down by cell and endpoint refusal reason.

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

Third, on what "no training" means here: **no representation learning and no
gradient training occur.** Two fusion weights per scope are fitted, by grid
search, **out of fold** on composition-level folds. That is a fitted quantity
and is described as one; it is not the same as an untuned system.

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

1. **For each fold f**, fit (α_u, α_b) on the **pooled** relation objective
   using the other folds only (recall@1, the inherited 12-value `ALPHA_GRID`
   for α_u and `[0.0, 0.1, 0.2, 0.4, 0.75, 1.0, 1.5]` for α_b, both containing
   0, ties to the smallest).
2. **Freeze those weights within fold f** and use them, unchanged, for every
   relation cell and every stratum, to score **fold f's held-out queries only**.
3. **Concatenate the held-out predictions across folds.** Deltas, clustered
   intervals, p-values, Holm decisions and strata are all computed on that
   concatenation.

**No held-out prediction may be produced by weights selected with that query's
own fold.** A modal or all-dev configuration may be retained as a deployment
candidate, but it **receives no dev performance claim** and no reported number
is computed from it — except for the bin-exception population, which never
enters any fit and for which that configuration is therefore out-of-sample by
construction (§5.1).

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
  non-test universe, `main_split ∈ {train, dev}`. Full-scale distractors; no
  dev-only index.
- **Bins**: `main_split='discovery'` documents are excluded from this base
  population, with **one narrow, explicitly defined exception** for members of
  bin-parent composite documents that appear in a join pair. That exception is
  specified in **§5.1**, is confined to the joins-only cell, and is asserted in
  code by check **C6**. Nothing else about the discovery pool changes: it
  remains inference-only material and never supplies duplicate positives or
  ordinary negatives.
- **Per scope**, report as first-class outcomes:
  - queries that become unscorable,
  - candidate documents that become unscorable,
  - **positive relations lost because either endpoint became unscorable**,
    broken down **by relation cell** (joins / duplicates / pooled) **and** by
    the refusal reason of the endpoint that became unscorable. A single
    aggregate count is not sufficient: losing join evidence and losing
    duplicate evidence are different costs.
- A **common-population sensitivity analysis** across the three symmetric
  scopes is reported additionally, so both readings are visible.

Every denominator is reconciled explicitly in the results, in the form step 2
adopted: raw → eligible → actually scored, with the exclusions named.

## 5. The mandatory three-way matrix, and stratification

Joins-only, duplicates-only, and pooled are reported for **every** arm, scope
and stratum. Pooled is a distinct estimand and never substitutes for a cell.

Positives come from `eval_harness.build_join_positives` and
`build_duplicate_positives` unchanged.

### 5.1 The physical-join bin exception, stated explicitly

The first draft was internally inconsistent: §4 excluded every
`main_split='discovery'` document while §5 promised included/excluded results
for bin-parent joins. Those cannot both hold. The exception is therefore
defined here in full, and it is narrow.

**Why an exception exists at all.** A bin CTH is a catalogue shelf, not a
composition. Bin membership makes a document's *composition label* unusable,
which is why bin fragments are barred from duplicate supervision. It says
nothing about whether two fragments physically join: the fit is a property of
the clay, and the editor's `+` notation records it. `CLAUDE.md` states this
directly — a composite join document whose parent CTH is a bin still yields a
valid join pair, tagged `parent_is_bin=True` and reported both ways.

**Exactly what the exception admits:**

| population | status |
|---|---|
| Members of a composite doc with `parent_is_bin=True` **that appear in a join pair** | admitted as **queries and candidates, in the joins-only cell only** |
| All other `main_split='discovery'` documents | **excluded entirely**, as in §4 — they remain the discovery pool |

**Split assignment.** These documents carry no `main_split` and are not given
one. They are evaluated as a **declared separate stratum**, `bin_parent_joins`,
reported alongside the dev cells and never merged into them. The leakage unit
is the `parent_doc`: all members of one composite document are one physical
object and cannot be split across sides. There is no composition-level split to
violate, because the bin CTH is not a supervision label for anything — which is
the entire reason these documents were binned.

**Three prohibitions, asserted in code (C6):**

1. A bin-exception fragment **never enters `build_duplicate_positives`**, in
   either role. (`build_duplicate_positives` already filters `~is_bin`; this is
   asserted rather than assumed.)
2. A bin-exception fragment **never appears in the candidate index used by
   non-bin queries**, so it cannot become an ordinary negative for the dev
   cells. The joins-only cell is therefore computed twice — once on the dev
   index, once on the dev index augmented with bin-exception fragments — and
   the two are reported as separate rows, never averaged.
3. A bin-exception fragment **never enters the duplicates or pooled cells** in
   any role.

Under this definition "reported both included and excluded" means the
joins-only cell appears with and without the `bin_parent_joins` stratum, with
its own denominators, and nothing about the duplicates or pooled estimands
changes between the two.

Join strata: `join_type` (**direct `+` vs indirect `(+)`**), `tier` (A/B/C),
**tier-A / no-overlap** (`n_shared_lines == 0`), shared-line count band, damage
rate, fragment length band, resolved language, genre band, site, and
`parent_is_bin`. Duplicate strata: the applicable subset (damage, length,
language, genre band, site).

### 5.2 Tier C must be evaluated on overlap-exclusive content

Tier-C pairs share editor-aligned lines. Retrieving a partner that literally
contains the same lines as the query is not a retrieval result; it is the
evaluation reading the editor's alignment back to itself.

**The reported Tier C number is therefore the overlap-exclusive one.** Each
member is re-rendered using **only its lines exclusive of the pair's shared
overlap**, via a dev-side generalization of
`eval_harness.tier_c_exclusive_tokens` — which is currently hardcoded to
`test_side` and to the flat `render_fragment`. The generalization keeps its
logic (exclusive line sets from `unjoin_reconstructed.jsonl`'s `member_lines` /
`shared_with`) and changes two things only: the side predicate becomes dev, and
the restricted line set is rendered through this run's
segmented, scope-aware path — `iter_structured_attested` already accepts an
explicit line list, so no second rendering implementation is introduced.

- Pairs whose exclusive content is empty on either side are **not silently
  dropped**: they are counted and reported as `exclusive_untestable`, which is
  already a field on `join_pairs.jsonl`.
- Ordinary full-rendering Tier C results are still computed, but are reported
  **only as a clearly labeled contaminated upper bound**, never as the Tier C
  result and never pooled into an overall joins number without the label.

**Amended: Tier C is evaluated as PAIR INSTANCES.** The first version compared
a full-rendering number computed on 94 Tier C queries against an exclusive
number computed on 42 scored queries — different populations, so the absolute
drop between them was not a paired estimate. It also keyed exclusive
renderings by `fragment_id`, so a fragment with several Tier C partners kept
only the last partner's exclusive set: a rendering that is genuinely
*partner*-dependent, stored as though it were *fragment*-dependent. 32 dev
fragments are in that position. Therefore:

1. Each **pair** is its own instance and carries its own exclusive renderings
   for both members, so nothing is overwritten.
2. **Full and exclusive are computed on exactly the same pair instances**, so
   the drop between them is paired.
3. A **sensitivity analysis restricted to fragments belonging to exactly one
   Tier C pair** is reported alongside.

Until those three hold, the zero-overlap stratum — not the Tier C
comparison — is the load-bearing qualification of the joins result.

### 5.3 Honest labels on two stratifiers

**`genre_band`** is `eval_harness.load_fragment_universe`'s
`(cth // 100) * 100` — floor of the CTH number to a multiple of 100, so CTH 433
falls in band 400. It is a **coarse numeric CTH catalogue band**. It is not a
philological genre, and it is not a "century" of anything: CTH numbers are
catalogue positions, not dates. Any stratum finding on it is a finding about
catalogue neighbourhoods.

**`site`** comes from the P2.5 provenance patch, with the standing caution that
`AT` is a single-document siglum and must be hand-verified rather than trusted
as a site label.

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
  exclusion must be active, and it is asserted that **no positive relation
  satisfies the actual exclusion predicate**, which is
  **same family AND different `parent_doc`** (`eval_harness.top_k_ranking`,
  the `candidate_families[i] == query_family and cand_parent != query_parent`
  branch).

  **It must NOT be asserted that no positive's endpoints share a family.**
  Composite join members share a parent and therefore a family *by
  construction* — `fragment_family()` strips the `::N` suffix — so that
  stronger assertion would flag every valid join pair. This is not
  hypothetical: the 2026-07-22 bugfix recorded in `top_k_ranking`'s docstring
  is exactly this error in the implementation, and it drove joins tier-A/B
  recall@1 to 0.0 against a real 0.059/0.5. The predicate's `and cand_parent
  != query_parent` clause is what keeps a join query's true partner rankable,
  and C1 exists to protect that clause, not to contradict it.

  Counts of genuinely excluded candidates are reported via `_exclusion_log`.
- **C2, identity control.** Row z-normalization reproduces BM25's per-query
  records exactly, per scope.
- **C3, split purity.** Dev-query CTHs disjoint from train-index CTHs.
- **C4, joins/duplicates are a partition.** No pair appears in both positive
  sets (`build_duplicate_positives` excludes join pairs; asserted, not assumed).
- **C5, frozen weights are frozen WITHIN EACH FOLD.** The (α_u, α_b) used in
  fold *f* is identical across all three cells and all strata for that fold.
  Weights are **expected to differ across folds** — that is what cross-fitting
  means, and asserting a single global weight would re-introduce exactly the
  defect this check now exists to catch.
- **C6, the bin exception stays in its lane.** No bin-exception fragment
  appears in any duplicate positive, in the duplicates or pooled cells, or in
  the candidate index used by non-bin queries (§5.1's three prohibitions,
  each asserted separately).
- **C7, Tier C is overlap-exclusive.** Every reported Tier C pair has non-empty
  exclusive content on both sides, and the count of `exclusive_untestable`
  pairs is reported rather than absorbed. The contaminated full-rendering
  variant is present in the output only under a key that names it as such.

## 8. What this run cannot establish

Test-side transfer; any deployable number; any claim about pretrained models;
and any assertion that one language scope is "better" — the scope comparison
reports an estimand-and-coverage trade-off, and step 2 already showed the
scope that maximizes a conditional increment is not the one that maximizes
absolute accuracy.

## 9. Outputs

- `scripts/phase5_taskb_transfer.py`
- a dev-side, segmentation-aware generalization of
  `eval_harness.tier_c_exclusive_tokens` (§5.2), added beside the original
  rather than mutating a frozen P3-phase helper
- `Phase4/phase4_out/p5_taskb_transfer.json`
- `Phase4/phase4_out/p5_taskb_transfer_per_query.jsonl`
- `Phase4/phase4_out/p5_taskb_transfer_manifest.json`
- `reports/phase5_taskb_transfer_results.md`
