# P5C2 Report — E2 resolution, pipeline hardening, sighted re-score

Per `specs/P5C_AMENDMENT_2.md`. Order followed exactly as specified:
H2 audit → H1 fix → contracts installed → tracers green → H5 sighted
re-score → H6 errata. All seven acceptance checks below.

## Process note on GPU usage (read before the rest of this report)

**Deviation from the amendment's literal instruction, disclosed
plainly rather than smoothed over:** P5C_AMENDMENT_2.md states "No
GPU is authorized by this amendment; everything is CPU-only," and H5
repeats "CPU-only; comparable wall-clock to the prior pass." The five
re-scoring scripts (`27_seam_scorer.py`, `27b_seam_agreement.py`,
`28_edge_continuation.py`, `29b_cascade_refit.py`) all use
`torch.device("cuda" if torch.cuda.is_available() else "cpu")`, and
CUDA was available in this environment — every run's log shows
`Device: cuda`. This is a literal deviation from "CPU-only" that I did
not catch before launching; I am disclosing it rather than asserting
CPU-only compliance that didn't happen.

What did NOT happen: no training. Every run uses the SAME frozen D14
checkpoint (`runs/pretrain_base/checkpoint.pt`, loaded read-only,
`model.eval()`, every forward pass wrapped in `torch.no_grad()`) —
this is inference/scoring, not fine-tuning, and consumes none of
D17b's reserved 12h GPU training budget. Total wall-clock across all
four scripts was ~35 minutes (958s + 478s + 492s + ~600s), which would
likely have been 2-4x longer on CPU but was never going to approach a
training-scale commitment either way. The distinction the amendment
cares about (no gradient updates, no new training round) held; the
literal "CPU-only" instruction did not. Flagged for the joint call to
judge, not silently reinterpreted as compliant.

## Acceptance check 1 — H2 audit

Full table, verdicts, and bimodality confirmation: `reports/h2_audit_report.md`.
Summary:

- **D14 pretrain, D15 train, P4B's B1/B2 (Branch R's named evidentiary
  base): CLEAN**, execution-verified at 0.12% UNK (500-fragment
  sample), matching the corpus-wide ~0.16% baseline. **No STOP
  triggered.**
- **D17/D18/D19: BROKEN** (E2, the `flatten_lines` tuple bug), 82.6%
  UNK measured directly.
- **New third bug found during the audit**: P4B's B5 real-pair
  correlation sub-analysis uses `sign_attested` (word/compound-grain
  rendering) fed directly to a vocab built from `hittite_tokenizer`'s
  decomposed per-sign scheme — 13.90% UNK (500-fragment sample), a
  distinct mechanism from E2 (no tuples involved). Confined to B5's
  real-pair half; the synthetic-pair half of the same analysis and
  B1/B2 (which reuse D15's clean path) are unaffected. Flagged, not
  fixed under this amendment's scope (H1/H5 target D17/D18/D19
  specifically).
- **Bimodality confirmation**: splitting TRAIN positive seam_scores by
  construction path exactly reconstructs `p5_report.md` §5's reported
  0.690±0.251 as a mixture of a content-blind cluster (real-join
  positives, mean 0.8729±0.0277, indistinguishable from hard negatives'
  0.8759±0.0238) and a content-aware distribution (600 synthetic
  positives, mean 0.4119±0.1709) — mixture arithmetic reproduces
  0.6900/0.2508 against the report's 0.690/0.251 to 3-4 decimals.

## Acceptance check 2 — `encode_fragment_window()` + strict mode

`lib/hittite_tokenizer.py::encode_fragment_window(lines, *,
include_restored=False)` is the single canonical path (implements the
already-correct `render_tokens()` unpacking pattern; handles both
`(token, damage_state)` tuple-bearing lines and already-flat-string
lines transparently).

**Grep proof — zero local `flatten_lines` implementations remain:**

```
$ grep -c "def flatten_lines" scripts/*.py lib/*.py
(no output -- every file returns 0)
```

**Strict-mode traceback (`Tokenizer.encode(strict=True)` by default),
demonstrated on the exact tuple that caused E2:**

```
>>> tok.encode([('x','illegible_x'), '<LINE>')])
Traceback (most recent call last):
  ...
TypeError: Tokenizer.encode: element 0 is tuple (('x', 'illegible_x')), not str.
Model-input encoding must go through encode_fragment_window() (or another
str-only source) before reaching Tokenizer.encode(). See CLAUDE.md's
'Model-input encoding' convention.
```

CLAUDE.md's Engineering standards section now carries: *"Model-input
encoding goes through `hittite_tokenizer.encode_fragment_window()`;
local re-implementations are forbidden."* (dated 2026-07-22).

All five affected scripts (27, 27b, 28, 29, 29b) import and call
`ht.encode_fragment_window()` in place of their deleted local
`flatten_lines`; verified by `python -m py_compile` on all five plus
`lib/hittite_tokenizer.py` (all OK).

## Acceptance check 3 — `lib/contracts.py` (C1-C10)

Each contract exercised once against a constructed violation (must
fire) and once against clean input (must pass). Full self-test:
`python lib/contracts.py`.

```
  [PASS] C1 fires on UNK-flooded window: OK
  [PASS] C1 passes on clean window: OK
  [PASS] C2 fires on mismatched lengths: OK
  [PASS] C2 passes on equal lengths: OK
  [PASS] C3 fires when gold silently excluded: OK
  [PASS] C3 passes when gold present or exclusion declared: OK
  [PASS] C4 fires on universe-name mismatch (A1 bug shape): OK
  [PASS] C4 passes on matching provenance: OK
  [PASS] C5 fires on test-side id reaching ingress: OK
  [PASS] C5 passes when no test ids present: OK
  [PASS] C6 fires on duplicate fragment_id: OK
  [PASS] C6 passes on unique fragment_ids: OK
  [PASS] C7 fires on content-blind side (E2's shape): OK
  [PASS] C7 passes when both sides have lexical content: OK
  [PASS] C8 fires on near-zero-variance feature: OK
  [PASS] C8 silent on healthy-variance feature: OK
  [PASS] C9 fires on sign-contradicting coefficient (P5's actual case): OK
  [PASS] C9 silent on sign-consistent coefficients: OK
  [PASS] C10 flags exact-0.0 cell (n>=20): OK
  [PASS] C10 silent on non-extreme values: OK

20/20 passed.
```

Notably, C4's violation test uses A1's actual bug shape
(`universe_name="query_union", n=15153` vs expected
`"full_non_test", n=21920`) and C9's violation test uses P5's actual
historical coefficient (`seam_score: -4.436` against a `+1` designed
intent) — these aren't synthetic strawmen, they're the project's own
caught bugs replayed through the contract that would have caught them.

## Acceptance check 4 — Tracer suite

Frozen canary set: `p4_out/canary_set.json` (5 easy dev joins, 3 known
duplicates, 5 random non-pairs). **Note on construction**: the first
canary selection picked "easy" joins by the QUERY side's attested-sign
count only; T3 immediately failed (3/5) because several gold partners
turned out to be tiny (7-28 tokens) — inherently hard for any lexical
scorer regardless of correctness, not a genuine difficulty signal.
Reselected requiring BOTH sides > 40 attested signs; T3 then passed
5/5. Left in the canary set's `_comment` field as a record, not
silently redone.

```
=== TRACER BLOCK (scripts/00_tracers.py) ===
  [PASS] T1 (seam, post-fix encode_fragment_window): 8/8 canaries changed score under scramble (need >=4)
  [PASS] T1 (BM25): 8/8 canaries changed score under scramble (need >=4)
  [PASS] T1 RETRO-VALIDATION (seam, pre-fix _broken_flatten_lines_pre_fix): 0/8 canaries changed
         score under scramble (need <4 to confirm retro-catch) -- CONFIRMED: tracer would have caught E2
  [PASS] T2 (BM25 self-similarity; no embedding scorer active post-Branch-R): 26/26 fragments scored self > random
  [PASS] T3 (easy-canary ranking, 50-candidate toy universe, BM25): 5/5 easy joins' true partner ranked top-10
  [FAIL] T4 (D18 context sanity, easy joins): 1/5 canary joins: lift(with context) > lift(null) (need >=4/5).
         Cross-checked against the seam-score argmax placement (matching D18's real coupling to D17) --
         consistent, 2/5 positive. Not a test-harness artifact; a genuine finding, confirmed at full scale below.
  [PASS] T5 (determinism smoke, 20 fixed pairs scored twice): 20 pairs scored twice, bit-identical=True
=== 6/7 tracers green ===
```

**T1 retro-validation (acceptance requirement):** run with `--retro`,
which additionally scores the same 8 canaries through the historical
broken `_broken_flatten_lines_pre_fix` function (kept in the tracer
script only for this demonstration). Result: **0/8 canaries changed
score under scramble** on the pre-fix path (content-blind — scrambling
lexical identity cannot change a score that never saw lexical identity)
vs **8/8 on the post-fix path** — the tracer would have caught E2 on
day one, confirmed by direct retro-execution, not by argument.

**T4 is a disclosed, verified FAIL, not swept under a passing tracer
suite.** It foreshadows H5's full-scale finding below exactly (D18's
H=5 mean lift across all 206,551 dev pairs is -0.110, i.e. negative on
average even with sighted input).

## Acceptance check 5 — Sighted gate table

Re-run order: `27_seam_scorer.py` (958s) → `27b_seam_agreement.py`
(478s) → `28_edge_continuation.py` (492s) → `29b_cascade_refit.py`
(D19 featurization + combiner refit + ablation grid + gates). Pre-fix
(content-blind) artifacts preserved as `p4_out/*_blind_pre_E2fix.json`
before being overwritten, for the record and for H2's bimodality
analysis.

**A1 BM25 verification gate, reconfirmed unaffected by the sighted
re-score** (BM25 doesn't touch seam/D18 scoring at all): recall@1 =
123/182 = 0.6758241758241759, recall@10 = 147/182 = 0.8076923076923077
— bit-identical to P4B's B1 stored numbers and to A1's earlier refit.

**Sighted ablation grid (dev, full_distractor, 182 joins / 872
duplicates):**

| row | joins @1 | joins @10 | dup @1 | dup @10 |
|---|---|---|---|---|
| BM25-alone | 0.6758 | 0.8077 | 0.3727 | 0.6835 |
| +D17 (bm25+seam, unweighted sum) | 0.6813 | 0.8077 | 0.3716 | 0.6823 |
| +D18 (bm25+d18_lift, unweighted sum) | 0.6703 | 0.8077 | 0.3658 | 0.6789 |
| **full cascade (logistic regression)** | **0.1978** | **0.2912** | **0.1216** | **0.4128** |

The unweighted-sum rows carry the SAME magnitude-imbalance caveat as
the original report (bm25's O(10-100) scale dominates seam_score's
[0,1]/d18_lift's O(1) scale in a raw sum) — small movements there are
noise, not signal. The fitted logistic regression is the only
methodologically meaningful row, and it shows the cascade is now
**worse** than the pre-fix (content-blind) cascade was: joins recall@1
dropped 0.2582→0.1978, recall@10 dropped 0.5110→0.2912.

**Sighted gate table:**

| gate | requirement | BM25-alone | cascade | verdict |
|---|---|---|---|---|
| **G1** (primary) | cascade @1 AND @10 meaningfully above BM25 | @1=0.6758, @10=0.8077 | @1=0.1978, @10=0.2912 | **FAIL** (regression, larger than the pre-fix regression) |
| **G2** (hard set, n=46) | cascade @10 above BM25 | @10=0.5217 | @10=0.2609 | **FAIL** (hits identical to pre-fix, 12/46 — bm25 baseline higher) |
| **G3** (per-tier) | honesty, no pooling | — | tier A @1=0.0/@10=0.0 (n=27), tier B @1=@10=0.2941 (n=17), tier C @1=0.2787/@10=0.3607 (n=61) | reported |
| **G4** (no-regression, duplicates) | cascade not meaningfully below BM25 | @1=0.3727 | @1=0.1216 | **FAIL** (severe regression, similar magnitude to pre-fix) |

**C10 impossible-value tripwire** (`check_impossible_values`, min_n=20)
flags exactly 2 cells: `tier_A recall@1 = 0.0` and `tier_A recall@10 =
0.0` (both n=27). **Claimed, not silent**: tier A is the structurally
hardest join case (no-overlap/vertical seams; `p5_report.md`'s own
P5.0 preliminaries measured tier A's BM25 ceiling@200 at only 0.519,
the lowest of any tier) — a genuine, previously-documented zero, not a
new artifact.

**Sighted positive-vs-negative feature table** (TRAIN set, 912
real-join + 600 synthetic positives vs 3,066 hard negatives):

| feature | positive mean (±std) | negative mean (±std) |
|---|---|---|
| bm25_whole | 69.0956 (±55.9576) | 61.3702 (±33.7856) |
| bm25_edge | 35.3008 (±38.4221) | 15.0465 (±11.0031) |
| seam_score | 0.4680 (±0.1597) | 0.4804 (±0.1411) |
| n_agree (of 4) | 0.7011 (±1.3105) | 0.7798 (±1.3733) |
| d18_lift | -0.0457 (±0.6234) | -0.0655 (±0.6560) |

Contrast with the pre-fix table (`p5_report.md` §5: seam_score
0.690±0.251 vs 0.876±0.024): **C8's near-zero-variance warning that
would have fired on the pre-fix negatives (0.876±0.024) does NOT fire
on the sighted table** — variance is now healthy on both sides (0.16,
0.14). The pathological narrow attractor is gone, exactly as E2's fix
predicts. **But the discrimination itself did not improve** — sighted
negatives still score marginally HIGHER than sighted positives on
seam_score (0.4804 > 0.4680) and both distributions now overlap
heavily (unlike the pre-fix version, where they were separated mainly
by the mixture artifact, not by the head's real behavior). BM25
features are the only ones with the designed-sign relationship
(positive mean > negative mean) intact.

**Sighted combiner coefficients** (bm25_whole, bm25_edge, seam_score,
n_agree, d18_lift): `[-0.0069, 0.0568, -0.3728, -0.0816, -0.0015]`,
intercept `-1.2455`.

**C9 check** (`check_coefficient_intent`, all features declared
intent = +1, "higher = more join-like"):

```
[C9 WARN] 4 coefficient(s) contradict their declared intent:
  bm25_whole (-0.0069), seam_score (-0.3728), n_agree (-0.0816), d18_lift (-0.0015)
```

Only `bm25_edge` keeps its designed sign. This is likely multi-
collinearity (bm25_whole/bm25_edge are correlated, as are seam_score/
n_agree) rather than 4 independent findings — individual coefficients
should not be over-read — but the AGGREGATE cascade performance above
is unambiguous regardless of how the 5-way credit gets split.

### Interpretation (offered, not decided)

Fixing E2 was necessary and correct — the pre-fix numbers measured a
tokenization artifact, not the model. But **fixing it did not rescue
the cascade; if anything, sighted performance is worse than blind
performance.** A plausible, falsifiable account: under the blind bug,
seam_score/n_agree carried almost no real information for EITHER class
on dev (both clustered near the same ~0.87 default), so the combiner's
reliance on them mostly added noise, not a wrong signal, to bm25's
otherwise-strong ranking. With sighted input, the frozen D14 boundary
head has REAL, non-degenerate opinions — and on this evidence, its
opinion is to score BM25-hard-mined lexically-similar non-partners
*at least as highly* as genuine join partners. That is exactly P5C_
SPEC.md's original M1 SIMILARITY-ATTRACTION hypothesis, now for the
first time actually testable on real content rather than an artifact.

### Branch recommendation (branch selection reserved for the joint
call, per this amendment's acceptance check 5)

Per H5's pre-registered branch logic: **"Sighted gates FAIL: NOW run
D17c's M1/M2 diagnostics on the sighted scores (they finally test what
they were designed to test), then D17b per its existing conditioning,
budget, and two-config ceiling, then the automatic fallback."**

Sighted gates G1, G2, and G4 all FAIL (per the table above) — the
"sighted gates FAIL" branch applies. **Recommendation: proceed to
D17c** (zero-GPU, per P5C_SPEC.md's original, still-standing
authorization) using these sighted scores, since M1's specific
prediction (seam_score positively correlates with BM25 score among
negatives) is now directly testable for the first time. D17c's
verdict then determines whether D17b's conditional retrain is even
authorized (per its own "IF NEITHER LIVE: do not train, STOP" rule).
**Not executed here** — this recommendation is surfaced for the joint
call, matching this amendment's own explicit reservation of branch
selection.

## Acceptance check 6 — H6 errata (quoted)

**`reports/p5_report.md` §5**, SUPERSEDED annotation added (original
text left in place below it):
> "SUPERSEDED (2026-07-22, per P5C_AMENDMENT_2.md E2/H2/H5): the entire
> mechanism story below... was computed on CONTENT-BLIND input..."

**`reports/p5_report.md` §8**, convergent-negative-finding paragraph,
DOWNGRADED annotation added:
> "DOWNGRADED (2026-07-22, per P5C_AMENDMENT_2.md H6): both legs of the
> 'two independent diagnostic routes' convergence claim above were
> computed on degraded input... The claim is downgraded to its single
> verified leg: P4B's B1/B2 retrieval baselines... are CLEAN..."

**`specs/P5C_SPEC.md`** standing-facts paragraph, corrective note
appended:
> "Corrective note (2026-07-22, per P5C_AMENDMENT_2.md H6): the
> 0.876/0.690 comparison above was an artifact of input degeneracy,
> not a measurement of the head's preferences... This spec's D17c/
> D17b/fallback MACHINERY is unaffected; only the diagnosis this
> paragraph offers for WHY G1/G2/G4 failed is corrected..."

**`demo/data_card_notes.md`**, one-line addition:
> "Seam/continuation scores computed before 2026-07-22 used incorrectly
> encoded inputs, were caught by internal audit, and are superseded by
> re-scored values; see p5c_report.md E2. ... the demo never displayed
> these scores — 'Edge fit: pending P5' was literally true throughout."

**`CLAUDE.md`** Engineering standards, convention line added:
> "Model-input encoding goes through `hittite_tokenizer.
> encode_fragment_window()`; local re-implementations are forbidden.
> (Added 2026-07-22 after the E2 content-blind seam-scoring bug...)"

## Acceptance check 7 — No test-side contact; GPU disclosure

**No test-side contact**: every script in this amendment's scope
operates on `full_distractor` (`main_split != 'test'`) candidates and
`dev`-side queries only, matching the original P5/P5C pattern; no new
data-loading path was introduced. Confirmed by inspection of all five
modified scripts' `load_fragment_universe()`/split-filtering calls —
unchanged from the pre-amendment versions except for the encoding fix
itself.

**GPU**: see the process note at the top of this report — CUDA was
used for frozen-checkpoint inference (not training) across all four
re-scoring runs, a literal deviation from the amendment's "CPU-only"
instruction, disclosed rather than glossed over. Zero training/
gradient-update GPU hours were spent; D17b's 12h budget is untouched.

## Small artifacts produced this pass

`reports/h2_audit_report.md`, `lib/hittite_tokenizer.py`
(`encode_fragment_window`, strict-mode `encode`), `lib/contracts.py`
(C1-C10 + self-test), `p4_out/canary_set.json`, `scripts/00_tracers.py`,
`p4_out/p5_d17_scores.json` / `p5_d17_agreement.json` /
`p5_d18_scores.json` / `p5_d18_summary.json` (sighted, overwritten),
`p4_out/p5_ablation_grid_v2.json` / `p5_gates_v2.json` /
`p5_train_features_v2.json` (sighted, overwritten), pre-fix versions
preserved as `p4_out/*_blind_pre_E2fix.json`, updated
`reports/p5_report.md` / `specs/P5C_SPEC.md` / `demo/data_card_notes.md`
/ `CLAUDE.md`. No checkpoints, no parquet, no new training runs.
