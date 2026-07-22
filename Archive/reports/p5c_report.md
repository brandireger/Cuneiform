# P5C Report — E1 Bookkeeping + Amendment 1 (A1-A4 complete; D17c proceeds)

Per specs/P5C_SPEC.md, amended by specs/P5C_AMENDMENT_1.md. **E1.3's
baseline reconciliation did not fully explain the P4B→P5 delta with the
two named candidate effects — a third, unnamed effect (BM25 IDF/avgdl
fit over a query-derived reference set) accounted for the entire gap.
Per the spec's own instruction, that stopped this report before D17c.
The architect (P5C_AMENDMENT_1.md, ratified 2026-07-22) selected OPTION
1 (full-universe refit); A1-A3 below are now complete and A4 (D17c)
proceeds per the amendment's explicit "no further check-in" authorization.**

## E1.1/E1.2 — Erratum & v2 tables (complete)

- `results_p3_patched_v2/` regenerated with the corrected H1 logic.
  Joins tier-A/B recall@1 now reproduces the real unpatched baseline
  exactly (bm25_sign: 0.0588/0.5, matching `results/` to 4 decimal
  places) — confirms the fix.
- `results_p3_patched/` (v1) marked SUPERSEDED (`SUPERSEDED.md`), kept
  for the record, not deleted.
- Erratum paragraph appended to `reports/h1_patch_report.md`: what the
  bug was, which numbers it affected (v1 patched joins tier-A/B/C-full,
  all read exactly 0.0), which it did NOT affect (unpatched `results/`
  baseline incl. the 0.059 number-to-beat; duplicates task; Task A),
  date, and the fix's provenance (uncommitted at write time, on top of
  git `703fa46ee3e7b06114d3675b2e99ab28bbea47fd`).

## E1.3 — Baseline reconciliation: INCOMPLETE, stopping here

**Target delta:** P4B's B1 full_distractor BM25 recall@1/@10 =
**0.676 / 0.808** → P5's D19 `bm25_alone` gate row = **0.665 / 0.802**.

Measured the decomposition directly (not assumed), by rebuilding each
step from the same underlying data and re-scoring the 182 dev-join
queries at each stage:

| step | change applied | recall@1 | recall@10 |
|---|---|---|---|
| 1 | P4B replica (full non-test universe as both candidates AND BM25 IDF reference, no family exclusion) | 0.676 | 0.808 |
| 2 | + H1-fixed family exclusion (same full-universe candidates/IDF) | 0.676 | 0.808 (unchanged) |
| 3 | + restrict RANKING to each query's own D16(b) candidate list (union whole+edge-window top-200), but score with the SAME full-universe-fit BM25 values | 0.676 | 0.808 (unchanged) |
| 4 | + refit BM25's IDF/avgdl over the SMALLER reference set D19 actually used (`all_cand_ids_union`, the union of candidates that appear in ANY of the 1,054 queries' lists — 15,153 fragments, vs the full 21,920) | **0.665** | **0.802** |

**Neither of the two effects the spec pre-named — (a) the H1 fix, (b)
the union-candidate-set restriction — moves the number AT ALL** (steps
2 and 3 are bit-identical to step 1). **100% of the observed delta
comes from a THIRD, previously-unidentified effect: `scripts/
29_cascade.py`'s BM25 feature was fit with IDF/avgdl computed over a
smaller, query-candidate-union-derived reference corpus (15,153
fragments) rather than the full non-test universe (21,920) P4B's B1
used.** Step 4 reproduces D19's actual reported bm25_alone numbers
(0.6648/0.8022) to 4 decimals, confirming this is exactly the
mechanism, not a further unexplained residual.

This is not a correctness bug in the sense of "wrong code" — BM25 IDF
fit over "the candidate universe this cascade ever actually considers"
is a defensible choice on its own terms. But it is a REAL, previously
undocumented methodological inconsistency between P4B's and P5's BM25
baselines that the pre-registered two-factor decomposition did not
anticipate, and per the spec's own rule this is exactly the situation
that requires stopping rather than silently reporting a "fully
explained" delta that isn't.

## What this means for D17c / next steps (RESOLVED — see "Resolution —
P5C_AMENDMENT_1.md" section below; kept verbatim for the record of
what was presented at the time)

Two live options were presented for the joint call rather than picked
unilaterally (Option 1 was subsequently selected — see resolution
below):

1. **Refit all P5 BM25 features (whole-fragment AND edge-window) over
   the FULL non-test universe** (matching P4B's reference exactly),
   re-run D16/D19's BM25-alone row, and treat THAT as the corrected
   baseline going into D17c/D17b. This costs one BM25 re-fit (cheap,
   no GPU) but means D19's already-fitted combiner and gate numbers
   from `p5_report.md` are on a baseline that will shift again once
   reconciled — small in magnitude (0.011/0.006 recall points) but it
   should be settled before D17c's diagnostics are read as final.
2. **Keep the smaller reference set as a documented, intentional
   choice** (BM25 over "the actual candidate pool," not the
   theoretical full universe) and simply RESTATE P4B's baseline
   alongside a footnote explaining the now-understood 0.011/0.006-point
   gap, rather than re-fitting anything. Cheaper, but leaves two
   "BM25-alone" numbers in the project's own record that don't match
   for a fully-understood-but-not-unified reason.

Given the gap is small (1.1 / 0.6 recall points) and fully explained
(not a residual mystery), either choice is defensible — this is a
judgment call about methodological consistency, not a correctness
emergency, but per the spec's own explicit stop-and-flag instruction it
is surfaced here rather than resolved silently.

## Resolution — P5C_AMENDMENT_1.md (ratified 2026-07-22, Option 1 selected)

The architect selected full-universe refit: "a corpus statistic must be
a property of the corpus, fixed independently of the evaluation
queries; a query-derived reference is evaluation-dependent
preprocessing, the same family of contamination this project polices
everywhere else." Four actions (A1-A4) were specified; all four are now
complete.

### A1 — Refit (complete)

All P5 BM25 features (whole-fragment and edge-window, N=3) refit with
IDF/avgdl computed over the full non-test universe (21,920 fragments —
confirmed via `frags[frags["main_split"] != "test"]`, matching P4B's B1
reference exactly). Candidate lists (`p4_out/p5_candidates_whole.json`,
D16/D16b union top-200) unchanged — only the scoring statistics
refit. Script: `scripts/29b_cascade_refit.py`.

**Verification gate result:** the refit `bm25_alone` row on the 182 dev
joins reproduces **recall@1 = 123/182 = 0.6758241758241759**, **recall@10
= 147/182 = 0.8076923076923077** — bit-identical to P4B's B1 stored
`full_distractor` numbers in `p4_out/p4b_b1.json` (hits=123/147,
n=182). **GATE PASSES.** (Note: the amendment's gate text names
"0.676 / 0.808 to 4 decimals" — those are `p4b_report.md`'s 3-decimal
prose rounding of these same 123/182 and 147/182 hit counts, not
independently-specified targets; verification was performed against
the raw stored hits/n in `p4b_b1.json`, which is the authoritative
reference, and matches exactly.)

### A2 — Gate-table re-emission (complete)

D19 ablation grid and G1-G4 gates re-run over the corrected features,
same frozen combiner protocol (logistic regression refit on TRAIN with
corrected feature values, no new features/search). Emitted as an
ADDENDUM section in `reports/p5_report.md` ("Addendum (2026-07-22) —
Corrected-baseline gate table"), original table left in place above it.

**Verdict-stability statement:** all three gates carrying a pass/fail
verdict are **UNCHANGED**:
- **G1 (primary): FAIL → FAIL.** Cascade recall bit-identical (47/182,
  93/182 hits); corrected bm25 baseline is slightly higher, making the
  regression look marginally larger, not smaller.
- **G2 (hard set): FAIL → FAIL.** Cascade hits identical (12/46); bm25
  baseline moved 23→24/46, still far above cascade.
- **G4 (no-regression, duplicates): FAIL → FAIL.** Both bm25 (0.391→
  0.373) and cascade (0.1158→0.1101) shift slightly downward; the gap
  remains a severe, decisive regression either way.
- G3 is descriptive-only (no pass/fail verdict to flip); its per-tier
  join numbers are bit-identical across v1/v2, duplicates shift
  marginally (101/872→96/872 @1) since duplicates' cascade scores also
  incorporate the corrected bm25 features.

**No verdict flipped — the pre-registered expectation ("a ~1-point
baseline shift is noise against a 40-point cascade regression") held
exactly. No STOP condition triggered.** §5's core diagnosis (the frozen
D14 boundary head scores BM25-hard-negatives higher and more
consistently than true join partners) is untouched by this refit, since
`seam_score`/`n_agree` are D14 forward-pass outputs independent of the
BM25 reference-set choice.

Corrected artifacts: `p4_out/p5_ablation_grid_v2.json`,
`p4_out/p5_gates_v2.json`, `p4_out/p5_train_features_v2.json`. Original
v1 files retained unmodified for the record.

### A3 — Convention codified (complete)

Appended to `CLAUDE.md`'s "Engineering standards" section:

> Corpus statistics (BM25 IDF/avgdl, calibration distributions,
> vocabulary counts, damage-rate profiles) are fit over the DECLARED
> universe for their phase (typically the full non-test universe),
> never over query-derived subsets. Any deviation is a documented
> decision, not a default. (Added 2026-07-22 after the E1.3
> reconciliation; see p5c_report.md.)

### A4 — Proceed to D17c

A1 verified, A2 emitted with no verdict flip — per the amendment's
explicit authorization, D17c proceeds next per specs/P5C_SPEC.md
unchanged, without further check-in. D17c's M1 correlations will use
the corrected (full-universe) BM25 scores throughout.

## E2 — NEW FINDING, STOP before D17c (found while preparing D17c,
2026-07-22): seam-scoring pipeline is content-blind (`flatten_lines`
tuple bug)

**While reconstructing seam windows for D17c's M2 damage-stat analysis
(which requires per-token damage state at the scored argmax placement),
direct inspection of the actual token stream fed to the frozen D14
encoder turned up a second, independent, and more consequential bug
than A1's BM25 reference-set issue — found and verified empirically,
not assumed, before writing it up.**

**The bug.** `fracture_engine.get_fragment_tokens()` returns each
line as `(idx, [(token, damage_state), ...])` — a list of 2-tuples,
by design (damage state travels with the token for downstream use).
Every one of the four D17/D18/D19 scoring scripts —
`scripts/27_seam_scorer.py`, `27b_seam_agreement.py`,
`28_edge_continuation.py`, `29_cascade.py` (and this session's
`29b_cascade_refit.py`, inherited verbatim since it was copied from
`29_cascade.py`) — defines its own local `flatten_lines()` that does
`flat.extend(toks)` directly on this list, WITHOUT unpacking the
tuples (`27_seam_scorer.py`'s version even takes an unused `tok`
parameter, a vestige suggesting extraction was once intended and
dropped). The resulting flat sequence is a mix of `(token, state)`
tuples and bare `"<LINE>"` strings. When passed to
`Tokenizer.encode()` (`self.vocab.get(t, self.unk_id)` per token), NO
tuple ever matches a string vocabulary key — every real content
position silently resolves to `<UNK>` (id=1). Only the explicitly-
appended `"<LINE>"`/`"<PAR>"` structural markers survive as real
vocabulary ids.

**Verified, not assumed:**
- Direct reproduction on a real fragment (`KBo 49.259`): `flat[:10]`
  = `[('x','illegible_x'), '<LINE>', ('x','illegible_x'), ...]`;
  `tok.encode(flat[:10])` = `[1, 4, 1, 1, 4, ...]` (1=`<UNK>`,
  4=`<LINE>`) — every content tuple maps to `<UNK>`.
- Quantified over 90 sampled real (query, candidate) seam windows
  drawn from `p4_out/p5_d17_scores.json`: **82.6% of all tokens in
  the scored 64-token window are `<UNK>`** — the remaining ~17.4% is
  entirely `<LINE>` separators, zero lexical content.
- This is a genuine oversight, not an intentional design: the SAME
  codebase does the unpacking correctly elsewhere —
  `fracture_engine.render_tokens()` (used for the 600 synthetic
  train pairs): `flat.extend(t for t, st in toks)`; and
  `29_cascade.py`'s own `build_edge_window_tokens()` (used for the
  BM25 edge-window feature, unaffected by this bug):
  `if t not in ht.SPECIALS and st != "restored": toks.append(t)`.
  Only the real-fragment path into the seam-scoring `flatten_lines()`
  fails to extract `t` before flattening.

**What this does NOT affect (checked directly, not assumed):**
- **D14's own pretraining is clean.** `scripts/19_pretrain.py` builds
  its training sequences via `hittite_tokenizer.
  build_structured_sequence_attested()`, which correctly does
  `seq.extend(t for t, st in toks if st != RESTORED)`. **The frozen
  D14 checkpoint itself saw real, correctly-tokenized content during
  training — it does not need retraining.** This bug is confined to
  how the (correctly-trained) frozen model is QUERIED at scoring
  time, in the four D17/D18/D19 scripts.
- **BM25 features (A1's refit) are unaffected** — `bm25_whole`/
  `bm25_edge` are computed from `frags_lookup["sign_attested"]` JSON
  strings and `build_edge_window_tokens()`, an entirely separate,
  correctly-implemented code path.
- **The 600 synthetic train pairs are correctly tokenized** (via
  `render_tokens()`), so roughly 600 of the train combiner's 1,512
  positives carry real seam signal; the other ~916 real-join
  positives and ALL ~3,066 hard negatives do not.

**What this means for D17c and for the entire D17/D18/D19 narrative
in `p5_report.md`.** D17c's M1/M2 tests are built on the premise that
`seam_score` reflects the model's genuine (mis-directed) sensitivity
to lexical similarity (M1) or fluency/damage (M2). If ~83% of every
scored window is `<UNK>`, `seam_score`/`n_agree`/`d18_lift` cannot be
carrying the kind of content-based signal either mechanism presumes —
at most they reflect coarse STRUCTURAL proxies (line count, token-
count-per-line, position of `<LINE>` markers within the fixed
64-token window), not lexical or damage content per se. This also
recasts `p5_report.md` §5's explanation ("the head conflates lexical
similarity with genuine continuity because the curriculum never
included BM25-hard-negatives as a type") as UNVERIFIED and possibly
wrong as a causal account — the near-zero-variance clustering of
negatives at seam_score≈0.876±0.024 is at least as consistent with
"the model defaults to a narrow structural prior when given content-
free input" as with a curriculum gap. The combiner's negative
weights on `seam_score`/`n_agree` are real (correctly fit on the
data as given), but the DATA itself may be near-meaningless as a test
of the intended mechanisms.

**Two options, not decided here (mirrors the E1.3 stop):**

1. **Fix `flatten_lines` in all four affected scripts** (extract `t`
   from each `(t, st)` tuple before flattening, matching
   `render_tokens()`/`build_edge_window_tokens()`'s already-correct
   pattern), **re-run D17 (`27_seam_scorer.py`, `27b_seam_agreement.py`),
   D18 (`28_edge_continuation.py`), and D19's train-side featurization
   + combiner fit (`29_cascade.py`/`29b_cascade_refit.py`) against the
   SAME frozen D14 checkpoint** — no GPU retrain required, since D14
   itself is clean; this is a CPU-only re-scoring pass (206,551 dev
   pairs + ~4,600 train pairs, similar wall-clock to the runs already
   completed this session). THEN run D17c's M1/M2 diagnostics on the
   corrected scores, so the diagnostic tests what it was designed to
   test. This is the technically correct move given the frozen
   checkpoint is intact and the fix is well-understood and cheap.
2. **Run D17c on the current (content-blind) scores anyway**,
   documenting this caveat prominently, treating M1/M2's verdicts as
   provisional/likely-uninformative given the input they're computed
   over. Cheaper (zero re-scoring), but risks handing D17b a
   diagnosis built on structural noise rather than the intended
   mechanism test — exactly the kind of silently-degraded diagnostic
   this project's cleanroom discipline exists to prevent.

Given the frozen checkpoint's integrity and the fix's low cost/high
clarity, option 1 is the stronger technical choice — but per this
project's established practice (E1.3), the decision is surfaced here
rather than made unilaterally, since it changes the D17c timeline and
re-opens numbers already written into `p5_report.md`'s §5 narrative.

## Status

E1 and the P5C_AMENDMENT_1.md resolution (A1-A4) are complete and
correct as far as they go. **A NEW stop condition (E2, above) was
found while preparing D17c and blocks D17c until resolved** — this is
a different, independent issue from anything P5C_AMENDMENT_1.md
addressed, so its "proceed to D17c without further check-in"
authorization (scoped to the BM25 reference-set question) does not
cover it. D17c has NOT been run. D17b, D19 re-run, and the automatic
fallback clause remain pending. No test-side contact occurred anywhere
in this pass (confirmed: `full_distractor` throughout is defined as
`main_split != 'test'`).
