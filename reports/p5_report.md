# P5 Report — Branch R: Retrieve-Deep + Seam-Local Rerank

Per specs/P5_RERANK_SPEC.md. All computation is analysis + one small
combiner fit (logistic regression, not GPU training) — the D14 encoder
stays FROZEN throughout D17/D18. **Bottom line up front: gates G1, G2,
and G4 all FAIL, and per the spec's own proceed-to-P6 rule ("If G1
fails, stop: architect check-in before any further build") this
report stops here for a joint decision — D17b (the one conditional
next step available) is NOT launched without that check-in.**

## 1. P5.0 — Stratification preliminaries

Tier distribution of the 182 dev joins: A=27, B=17, C=61, mixed=77
(a query touching pairs of more than one tier). Full per-tier B1/B3
tables: `p4_out/p5_b1_per_tier.json`, `p4_out/p5_b3_per_tier.json`.

**Hard set** (bottom quartile of BM25 score-to-true-partner, frozen
per spec, seed=20260722): threshold 45.12, **n=46/182**. Frozen list:
`p4_out/p5_hard_set.json`.

**Ceilings** (fraction whose true partner is in BM25 full_distractor
top-200):

| group | n | ceiling@200 |
|---|---|---|
| all | 182 | 0.896 |
| hard set | 46 | 0.696 |
| tier A | 27 | **0.519** |
| tier B | 17 | 0.765 |
| tier C | 61 | 0.984 |

Hard-set ceiling (0.696) clears the 0.5 flag threshold — **D16b stays
an ablation, not promoted to a requirement**, per the pre-registered
rule. Tier A is the structurally hardest case (matches CLAUDE.md's own
framing of tier A as the genuine "no-overlap" seam-continuation
problem) — worth flagging explicitly even though n=27 makes it
indicative only, per G3's honesty requirement.

## 2. D16/D16b — Candidate generation

**A real, pre-existing bug was found and fixed before it could
invalidate this whole phase**: `eval_harness.top_k_ranking`'s H1
family-exclusion logic, when naively applied to join queries, excluded
every query's own true partner (composite-doc siblings always share a
`parent_doc`, so `fragment_family()` always judged them "the same
family"). Confirmed against the already-*accepted* `results_p3_patched/`
artifacts: patched joins tier-A/B recall@1 read exactly **0.0** there
(vs the real unpatched 0.059/0.5) — a latent bug, not a genuine
regression. Fixed in `lib/eval_harness.py` (never exclude same-`parent_doc`
siblings; only exclude when parent_docs *differ* but map to the same
H1 family). `results_p3_patched/`/`h1_patch_report.md` are P3-phase
frozen artifacts and were **not** silently regenerated — flagged here
for a decision on whether/how to correct them.

BM25_sign, full_distractor, top-200, H1-corrected exclusions. D16b
(edge-window ablation, N∈{3,5}): union raises the ceiling from
163/182 (0.896) to 167/182 (0.918), **delta=0.022 ≥ 0.02 → PROMOTED**.
The join-query candidate set used by everything downstream is the
union (whole-fragment top-200 ∪ edge-window top-200, N=3).

## 3. D17 — Boundary-head reranking (frozen D14 head)

206,551 (query, candidate) pairs scored (872 unique queries: 182 join
+ 872 dup, full overlap). Offset search: 2 directions × 4 offsets
(0-3), "mean over aligned line-pairs at that offset" — averaged
boundary probability over every `<LINE>`/`<PAR>` position in the
constructed seam window, per pair, per offset; max over
(direction, offset) taken as the pair score, argmax recorded (the
demo/P7 placement). Runtime: ~447s (agreement addendum) + earlier
scoring pass.

## 4. D18 — Short-horizon edge-continuation

H ∈ {1, 3, 5}, hard-capped at 5 (confirmed: no H > 5 run). Mean lift
positive at every H (0.44 / 0.61 / 0.55) — the context DOES raise the
model's confidence in the true continuation on average, across the
full pair population (positives and BM25-distractor candidates mixed
together, since this ran over all D17-scored pairs, not separated by
true-positive vs distractor — see §5 for the actually decisive
positive-vs-negative comparison).

## 5. D19 — Cascade, ablation grid, and the key finding

> **SUPERSEDED (2026-07-22, per P5C_AMENDMENT_2.md E2/H2/H5):** the
> entire mechanism story below (§5's "the head conflates lexical
> similarity with genuine continuity because the curriculum never
> included BM25-hard-negatives") was computed on CONTENT-BLIND input —
> a per-script tokenization bug (`flatten_lines`, fixed via
> `hittite_tokenizer.encode_fragment_window()`) silently reduced ~83%
> of every scored seam window to `<UNK>`. The 0.876±0.024 vs
> 0.690±0.251 comparison below is real arithmetic but not a coherent
> single measurement of the head's preferences — `h2_audit_report.md`
> shows it exactly reconstructs as a mixture of a content-blind
> cluster (real-join positives + all negatives, indistinguishable at
> ~0.87-0.88) and a content-aware distribution (the 600 synthetic
> positives, which were correctly tokenized via a different code
> path). Original text below is left in place for the record. See
> `reports/p5c2_report.md`'s sighted gate table for the corrected
> measurement.

**Ablation grid (dev, full_distractor, all 182 joins):**

| row | recall@1 | recall@10 |
|---|---|---|
| BM25-alone | 0.665 | 0.802 |
| +D17 (bm25 + seam_score, unweighted sum) | 0.665 | 0.802 |
| +D18 (bm25 + d18_lift, unweighted sum) | 0.665 | 0.802 |
| **full cascade (logistic regression)** | **0.258** | **0.511** |

**Methodological caveat, stated plainly**: the "+D17"/"+D18" rows are
uninformative as constructed — `bm25_whole` scores range in the tens
to ~100+ while `seam_score` is bounded [0,1] and `d18_lift` is O(0.1-1),
so unweighted addition leaves bm25's much larger magnitude dominating
the sum entirely; the ranking is unchanged from BM25-alone by
construction, not because the added signal is inert. Only the fitted
logistic regression (which learns its own per-feature scale) is a
methodologically meaningful test of whether D17/D18 add value — and
that is the row that matters below.

**The full cascade actively hurts ranking, uniformly, everywhere it
was measured** — not "no improvement," but a real regression relative
to BM25-alone on every gate (see §6). Investigating why, rather than
treating it as a black box:

**Combiner coefficients** (bm25_whole, bm25_edge, seam_score, n_agree,
d18_lift): `[0.0043, 0.0377, -4.436, -1.858, -0.448]`, intercept
`9.375`. **`seam_score` and `n_agree` both carry large NEGATIVE
weights** — the logistic regression learned that a HIGH seam score
predicts the NEGATIVE class. This is not a training bug; it correctly
reflects the training data:

| feature | positive-pair mean (±std) | negative-pair mean (±std) |
|---|---|---|
| seam_score | 0.690 (±0.251) | **0.876 (±0.024)** |
| n_agree (of 4) | 2.588 (±1.853) | **3.998 (±0.065)** |
| d18_lift | 0.330 (±0.518) | 0.556 (±0.190) |

**The frozen D14 boundary head scores BM25-mined hard negatives
(lexically similar, non-partner fragments) HIGHER and far more
CONSISTENTLY (near-zero variance, 3.998/4 agreement) than it scores
real join partners.** This is the exact same failure mode P4B's B5
diagnosed for the (now-dropped) bi-encoder — the model conflates
lexical/topical similarity with genuine seam continuity — showing up
again here in the boundary-validity head specifically. It's a coherent
explanation, not a coincidence: D14's original negatives curriculum
(in_doc shuffle → cross_genre → random) never included "a different,
lexically-similar-but-wrong fragment" as a negative type, so the head
never learned to penalize exactly the case P5's hard-negative mining
constructs and BM25 reranking most needs to resist.

## 6. Gates (all at full_distractor, dev)

| gate | requirement | BM25-alone | cascade | verdict |
|---|---|---|---|---|
| **G1** (primary) | cascade @1 AND @10 meaningfully above BM25 | @1=0.665, @10=0.802 | @1=0.258, @10=0.511 | **FAIL** (regression, not just a miss) |
| **G2** (hard set, n=46) | cascade @10 above BM25 | @10=0.500 | @10=0.261 | **FAIL** |
| **G3** (per-tier, full cascade) | honesty, no pooling | — | tier A @10=0.037, tier B @10=0.294, tier C @10=0.607 | reported; tier A collapses hardest |
| **G4** (no-regression, duplicates) | cascade not meaningfully below BM25 | @1=0.391 | @1=0.116 | **FAIL** (severe regression) |

Per spec: **"If G1 fails, stop: architect check-in before any further
build."** All four gates fail. This report stops here.

## 7. D17b — NOT launched

D17b (fine-tune the boundary head on seam-local synthetic pairs) is
gated on "the frozen floor shows signal." §5's finding is genuinely
informative — it names a specific, plausible, fixable cause (D14's
negatives curriculum never covered "lexically-similar-but-wrong,"
exactly BM25-hard-negatives) rather than an unexplained failure. That
makes D17b a *reasonable candidate* — but it is a real ≤12h GPU
commitment, and the spec's own rule for a G1 failure is to stop for a
joint call, not to unilaterally spend more compute chasing a fix. Not
launched. Recommended as the most concrete next step (below), decision
reserved.

## 8. Consequential edits (done)

- `demo/data_card_notes.md`: added the third known-limitations line
  (ambiguous-duplicate training documents, verbatim per spec) and a
  new "Score columns" section retiring "Learned similarity" outright
  and keeping "Edge fit — pending P5" as pending (not flipped to
  active, since G1 failed).
- Paper note: P4B's B1 scale-degradation finding remains the headline
  negative result; P5's own finding (§5) is a second, related headline
  — dense/learned similarity signals repeatedly collapse toward
  "lexical similarity in disguise" on this corpus, at two different
  model components (D15's bi-encoder, D14's boundary head) via two
  independent diagnostic routes (P4B's B5 correlation study, P5's D19
  hard-negative comparison). That convergence is worth stating
  plainly in the paper, not just once per component.

  **DOWNGRADED (2026-07-22, per P5C_AMENDMENT_2.md H6):** both legs of
  the "two independent diagnostic routes" convergence claim above were
  computed on degraded input — P5's D19 comparison via E2's
  content-blind seam scoring (fixed, see H5's sighted re-score), and
  P4B's B5 real-pair correlation via a separate tokenization-scheme
  mismatch (`sign_attested` fed to a decomposed-scheme vocab, 13.9%
  UNK, found during H2's audit, not yet re-verified). The claim is
  downgraded to its **single verified leg**: P4B's B1/B2 retrieval
  baselines (dense_mean_pool/dense_line_max underperforming BM25 at
  full_distractor scale) are CLEAN — execution-verified at 0.12% UNK,
  reusing D15's own correctly-tokenized training path
  (`build_structured_sequence_attested`) — and stand on their own as
  the paper's negative result for dense retrieval. The "collapses
  toward lexical similarity, via two independent routes" framing is
  retracted until B5 and D19 are both re-verified on sighted input;
  restate as single-leg (D15/B1 only) until then. The E2 episode
  itself is a methods anecdote worth keeping: the diagnostic's own
  data requirements (per-token damage states, needed for D17c's M2)
  are what exposed the blind scorer — tooling honesty paid for itself.

## 9. Recommendation (Code Claude recommends; selection reserved)

Do not proceed to P6 as-is. Three live options, not decided here:

1. **Retrain D17b** with BM25-hard-negatives added as an explicit
   negative type in the boundary-head's fine-tuning curriculum
   (targets the diagnosed cause directly) — one time-boxed round
   (≤12h GPU), same gate re-applied afterward. Highest information
   value given §5's clean diagnosis, but not guaranteed to work (D15's
   analogous issue was NOT fixable by the equivalent move — P4B's B5
   found removing synthetic contamination from the bi-encoder only
   closed a small fraction of that gap).
2. **Fall back further than Branch R already did**: ship BM25-alone
   as the P5 retrieval+ranking stage with NO learned reranking
   component at all (D17/D18/D19 all written up as a second clean
   negative result, alongside D15's), and reconsider what a "P5
   contribution" means for the paper (ranking quality on the tiers
   where BM25 already works, per CLAUDE.md's "report more, claim
   less").
3. ~~Investigate D18 in isolation~~ **CHECKED, ruled out**: a
   bm25_whole + d18_lift-only combiner was fit on the same train data
   (cheap, done) — `d18_lift` ALSO gets a negative coefficient
   (-2.211) on its own. D18 shares D17's failure mode (negatives score
   higher on average, 0.556 vs 0.330 for positives — see §5's table);
   it is not merely being dragged down by D17 in the joint combiner.
   This narrows the real choice to options 1 or 2.

Small artifacts: `p5_report.md` (this file), `p4_out/p5_hard_set.json`,
`p4_out/p5_b1_per_tier.json`, `p4_out/p5_b3_per_tier.json`,
`p4_out/p5_d16b_report.json`, `p4_out/p5_d16_stamp.json`,
`p4_out/p5_d18_summary.json`, `p4_out/p5_ablation_grid.json`,
`p4_out/p5_gates.json`, `p4_out/p5_train_features.json`. No
checkpoints, no parquet, no new training runs.

## Addendum (2026-07-22) — Corrected-baseline gate table, per
specs/P5C_AMENDMENT_1.md A1/A2

**Reference-set caveat on the table above:** §5/§6's BM25 features
(whole-fragment and edge-window, N=3) were fit with IDF/avgdl computed
over `all_cand_ids_union` — the union of candidates appearing in ANY
of the 1,054 queries' D16/D16b lists (15,153 fragments) — rather than
the full non-test universe (21,920 fragments) that P4B's B1
measurement used as its reference. This was found during E1.3's
baseline reconciliation (`reports/p5c_report.md`): it explains 100% of
the small gap between P4B's B1 BM25-alone numbers (0.676/0.808,
3-decimal prose rounding of 123/182, 147/182) and this report's
original bm25_alone row (0.665/0.802). Per the architect's ratified
resolution (Option 1, P5C_AMENDMENT_1.md), all P5 BM25 features are
refit here over the full non-test universe — the corpus-statistic
convention now codified in CLAUDE.md's Engineering standards. The
D16/D16b candidate LISTS themselves are unchanged; only the BM25
scoring statistics were refit. Script: `scripts/29b_cascade_refit.py`.

**A1 verification gate:** the refit `bm25_alone` row on the 182 dev
joins at full_distractor reproduces **123/182 = 0.6758241758241759**
(recall@1) and **147/182 = 0.8076923076923077** (recall@10) — bit-
identical to P4B's B1 stored `full_distractor` numbers in
`p4_out/p4b_b1.json` (hits=123/147, n=182 both metrics). The "0.676 /
0.808" figures named in P5C_AMENDMENT_1.md's gate are P4B_report.md's
3-decimal prose rounding of these same exact values, not independently
-specified targets — **gate PASSES** (confirmed against the raw stored
hit counts, not the rounded prose figure).

**Corrected gate table (dev, full_distractor, refit BM25 features):**

| gate | requirement | BM25-alone (corrected) | cascade | verdict | stability vs original |
|---|---|---|---|---|---|
| **G1** (primary) | cascade @1 AND @10 meaningfully above BM25 | @1=0.6758, @10=0.8077 | @1=0.2582, @10=0.5110 | **FAIL** | **UNCHANGED** — cascade recall is bit-identical (47/182, 93/182 hits, same as original); the corrected, slightly HIGHER bm25 baseline makes the regression look marginally larger, not smaller |
| **G2** (hard set, n=46) | cascade @10 above BM25 | @10=0.5217 | @10=0.2609 | **FAIL** | **UNCHANGED** — cascade hits identical (12/46); bm25 baseline moved 0.500→0.5217 (23→24 hits), still far above cascade |
| **G3** (per-tier, full cascade) | honesty, no pooling | — | tier A @10=0.0370 (1/27), tier B @10=0.2941 (5/17), tier C @10=0.6066 (37/61) — all bit-identical to original; duplicates recall shifts marginally (101/872→96/872 @1) since duplicates' combiner scores also incorporate the corrected bm25 features | reported | descriptive only, no pass/fail to flip |
| **G4** (no-regression, duplicates) | cascade not meaningfully below BM25 | @1=0.3727 | @1=0.1101 | **FAIL** | **UNCHANGED** — both bm25 (0.391→0.373) and cascade (0.1158→0.1101) shift slightly downward under the corrected reference; the gap remains a severe, decisive regression either way |

**Verdict-stability statement:** all three gates carrying a pass/fail
verdict (G1, G2, G4) are **UNCHANGED** — FAIL under both the original
and the corrected baseline. G3 is descriptive-only and reports no
verdict to flip. Per P5C_AMENDMENT_1.md A2's pre-registered expectation
("all gate verdicts unchanged — a ~1-point baseline shift is noise
against a 40-point cascade regression"), this is exactly what was
found; **no STOP condition is triggered**. §5's diagnosis (the frozen
D14 boundary head scores BM25-hard-negatives higher and more
consistently than true join partners) stands unchanged, since it never
depended on the BM25 reference-set choice — `seam_score`/`n_agree`
are D14 forward-pass outputs, untouched by this refit. Full corrected
artifacts: `p4_out/p5_ablation_grid_v2.json`, `p4_out/p5_gates_v2.json`,
`p4_out/p5_train_features_v2.json`. Original v1 files retained
unmodified for the record.

Per P5C_AMENDMENT_1.md A4, this resolves the E1.3 stop condition; D17c
proceeds next per specs/P5C_SPEC.md, without further check-in.
