# Phase 3 successor handoff

Prepared 2026-07-25 for the next maintainer of the Cuneiform/Takšan project,
continuing directly from `PHASE2_SUCCESSOR_HANDOFF.md`.

**Successor Gate 2 note (2026-07-25):** `PHASE4_CHARTER.md` governs the next
phase after a word-level language review showed that the line-only
containment fix below is not the final multilingual design. Gate 2 has passed
and authorizes language-aware API and workbench implementation. Test access
and GPU training remain unauthorized.

## Executive status

Phase 2 closed with a mandate: "build a small expert UI prototype against
`specs/EXPERT_DECISION_CONTRACT.md`." That prototype now exists, but working
with it surfaced a distinction Ixca made explicit and that now organizes all
of this phase's work:

> The 28 P2-E4/P2-E6 packets are **training/calibration data** — signs
> artificially hidden from attested text for evaluation. They are not real
> damage. A trained Hittitologist's actual working session is choosing a
> real tablet and filling **real** gaps (`restored`/`illegible_x` spans the
> corpus already encodes). Those are two different products, not one.

Two tracks exist as a result, at different levels of completion:

1. **Training/calibration playground** (`demo/`) — complete as a UI shell.
   Library landing page, per-tablet workspace, restored shelf, option cards
   with witness-support vs. calibrated-track-record separated, and search —
   all built and headless-Chrome-verified against the 28 real (but
   synthetic-gap) packets.
2. **Real-gaps production pipeline** (`scripts/real_gap_*.py`,
   `Phase3/real_gaps_out/`) — the actual missing-text objective, built one
   verified step at a time (census → witness check → single-sign
   calibration → **multi-sign calibration**, added in this update). Single-
   sign calibration is widened to the full CTH set P2-E4 covers; multi-sign
   calibration now covers the analogous P2-E6-fold CTH set. **Not yet wired
   into the demo UI** — it currently only produces JSON/Markdown reports, no
   packets, no browser-facing product.

Neither track has touched the frozen test split. No real-gap witness match,
editor-restoration agreement, or expert UI decision has been promoted to
corpus ground truth. No new model training occurred this phase.

**Update (2026-07-25, continued session):** two more items from this
handoff's own "Recommended order of work" are now done: (1) `demo/dm_out`
and `real_gaps_out` were moved under a new `Phase3/` top-level folder, per
the project's stated one-folder-per-phase convention (item 1 below), and
(2) multi-sign real-gap calibration was built as the P2-E6 analogue of
step 3's P2-E4 reuse (item 2 below). Both are detailed in their own
subsections further down and are fully committed — no outstanding
uncommitted state.

**Update (2026-07-25, third continuation — multilingual-layer
contamination fix):** Ixca asked whether the project accounted for the
corpus's multilingual layers (Akkadian, Sumerian, Hattic, Luwian, Palaic,
Hurrian alongside Hittite). Investigation found it did not, in
implementation, despite CLAUDE.md naming the layers explicitly since
Phase 1: the per-line `lg` signal was captured in P2's `corpus.parquet`
but never propagated into P4's `decomposed_corpus.parquet`, so the
tokenizer, every P2-E script, and the real-gap pipeline (including this
same session's own multi-sign calibration) treated every line as Hittite
regardless of actual language. This was ratified, fixed, and integrated
end-to-end this session — see its own major section below,
"Multilingual-layer contamination fix," for the full account. Short
version: a new ratified `line_lang_canonical` field now exists and is
wired into the shared anchor-index construction every P2-E/real-gap
script uses; every affected script was rerun and its frozen numbers
updated; the one piece NOT changed is the tokenizer's own vocabulary
(reverted after it broke the pretrained P4 checkpoint — retraining is a
multi-hour job, deliberately deferred).

## Why this phase happened

Phase 2's handoff named the expert UI as the next product task and assumed
the P2-E4/P2-E6 evaluation packets were a reasonable stand-in for "real
gaps" to build it against. Iterative hands-on testing by Ixca surfaced UI
bugs (exact gap alignment, multi-word duplication, a dropdown disconnected
from restoration mode, `.fp-gap-target` visually indistinguishable from a
candidate) that were fixed in turn — see `demo/missing_text_prototype_report.md`
Revisions 1–4 for the full sequence.

Fixing those bugs led to the harder realization: the packets themselves are
synthetic (real signs hidden for evaluation), not authentic damage. Ixca's
own reframing (verbatim, Revision 5) split the product into a library +
playground (buildable immediately, no new pipeline needed) and a real-gaps
production pipeline (needs its own witness-matching work against genuinely
damaged spans). Both are now real, and the second is mid-build.

## What was completed

### Reorganization (carried over from the previous session, now committed)

- `Archive/` now holds the frozen Phase 1 snapshot plus
  `Archive/superseded_docs/` for absorbed root docs.
- Live outputs split by phase folder: `Phase1_pipeline/{p2_out,p3_out,p4_out}/`,
  `Phase2/{phase2_out,corpus_audit_out}/`. This handoff's own new outputs
  now also follow that convention: `demo/dm_out/` and `real_gaps_out/` were
  moved to `Phase3/{demo_out,real_gaps_out}/` in this update (see "This
  session's additions" below) — the folder-naming question this handoff
  originally left open is resolved.
- `lib/decompose_corpus.py` gained `word_index_in_line` tracking (verified
  against `Archive/scripts/02_parse.py`), needed for exact gap-to-source
  alignment in both the demo export and the real-gaps pipeline.

### Training/calibration playground (`demo/`)

- `demo/dm1_missing_text_export.py` — exports the 28 real P2-E4/P2-E6
  packets (16 single-sign, 12 multi-sign; 24 present-candidates, 4 abstain)
  across 18 distinct tablets into browser-ready JS, via
  `lib/expert_decision_contract.py`'s existing `adapt_p2e4_packet()`/
  `adapt_p2e6_packet()` — no new adaptation logic, hidden evaluation gold
  stays stripped. Cleanroom-checked: every packet's fragment resolves to
  `dev` in `splits.parquet`; the export hard-aborts on any other split.
- `demo/taksan_missing_text_prototype.html` — single-file app (vanilla JS,
  inline CSS, zero network calls):
  - **Library landing page** (new default view): all 18 tablets as cards
    (docID, CTH + German title, site, line/gap counts), searchable by
    docID/CTH/site/packet_id, organized into Restored shelf / In progress /
    Not started (computed from recorded decisions, never guessed).
  - **Workspace**: per-tablet gap-filling UI, correctly scoped to that
    tablet's own packets only (previously listed all 28 globally — fixed).
  - Option cards separate **witness support** (evidence — how many
    independent witnesses proposed this reading) from **track record**
    (calibration — this rank's historical group-audit rate, with Wilson CI
    and sample size), after Ixca flagged the two were being conflated in a
    way that read as contradictory ("witnesses ~95%, actual sign ~4%").
  - A persistent **"TRAINING PLAYGROUND — CALIBRATION DATA"** header badge
    and library intro paragraph state plainly that gaps here are
    artificially hidden attested signs, not real damage — so this UI cannot
    be mistaken for the production tool.
  - Restored shelf is **organizational only** — moving a tablet there is an
    explicit human click, never automatic, and does not (cannot yet) trigger
    the "algorithm re-scores the restoration" behavior Ixca originally
    asked for; that needs the real-gaps pipeline's witness index to treat a
    filled gap as new context for neighboring gaps, which does not exist.
  - All of the above independently verified in headless Chrome (see report
    Revisions 3–7 for the specific verification transcripts); Python suite
    stayed green throughout (88 tests).
- `demo/missing_text_prototype_report.md` — cumulative, 7 revisions, the
  full bug-fix and reframing history. Read this before touching the HTML.

### Real-gaps production pipeline (`scripts/`, `Phase3/real_gaps_out/`)

Built one step at a time per Ixca's explicit instruction ("let's take this a
step at a time, and evaluate the changes and results"), each step verified
against real numbers before moving on:

1. **`real_gap_census.py`** — structural count only. Train+dev, non-bin
   documents; a "real gap" is a contiguous run of `restored`/`illegible_x`
   tokens in the decomposed sign stream. Found 181,051 real-gap runs across
   6,767 documents. No witness lookup yet.
2. **`real_gap_witness_check.py`** — reuses P2-E4/P2-E6's own witness-index
   machinery (`build_anchor_index`/`independent_proposals`), applied to
   genuinely damaged spans instead of synthetic masks. Two extensions built
   on top:
   - **Cross-line anchor extension**: when a line runs out of attested
     context on one side, walks to the next line the *same witness fragment*
     actually preserves, capped at 3 lines per side (Ixca's call, after
     seeing the uncapped tail run to 39 lines) — raised same-line-only
     anchor coverage from 7.7% to 75.7% of gaps in its 5-CTH default scope,
     with same-line and cross-line results always reported separately, never
     pooled (cross-line has no calibration of its own).
   - **Edge-loss cross-reference** (`edges.parquet`): separates "this
     witness retains at least one original tablet surface, so the damage is
     interior" from "every side is already a break" — answering Ixca's own
     question about whether heavily-damaged fragments belong to the
     join-training objective or the missing-text objective. In its 5-CTH
     default scope: 17,684 gaps sit in pure-edge-material fragments, 7,875
     in fragments with at least one preserved surface.
   - `prepare_scope()` now takes an **explicit CTH list** (refactored this
     session) rather than picking one itself, so callers can scope
     independently — this is what made the calibration-widening below
     possible without touching this script's own default report.
3. **`real_gap_calibration.py`** — applies the already-frozen P2-E4 5-fold
   `rank_calibration` tables (same numbers the demo displays) to real gaps.
   No recalibration; pure reuse. **This session's change**: rescoped from
   step 2's unrelated "top gap count" CTH list (which only overlapped the
   calibration folds at CTH 627) to the full **42 CTHs** the 5 folds
   actually cover, via the `prepare_scope()` refactor above:

   | | before (CTH 627 only) | after (42 CTHs) |
   |---|---|---|
   | documents in scope | 867 | 749 |
   | eligible real gaps (same-line, single-sign) | 171 | **1,010** |
   | selector-accepted | 24 | **44** |
   | restored spans matching a ranked witness alt | 23 | **41** |
   | contradicted by rank-1 | 1 | 3 |
   | no usable rate | 0 | 0 |

   Full detail in `Phase3/real_gaps_out/real_gap_calibration_report.md`.

This pipeline produces **no packets and no UI yet** — reports only. Wiring
it into a production-mode extension of the demo is the natural next step,
not yet started.

### This session's additions (2026-07-25, continued)

1. **Phase3/ folder move.** `demo/dm_out/` → `Phase3/demo_out/`,
   `real_gaps_out/` → `Phase3/real_gaps_out/`. Every path reference updated
   (the three `real_gap_*.py` scripts' `OUT_DIR`, the three `demo/dm*.py`
   export scripts, `demo/taksan_missing_text_prototype.html`'s `<script
   src>` tags, README's live/archive map table). All three real-gap scripts
   and the demo export were re-run after the move and produced byte-for-byte
   identical counts to before (181,051 gap runs / 6,767 docs; 25,559 gaps /
   867 docs; 1,010 eligible / 44 selector-accepted; 28 packets / 18
   fragments) — a pure relocation, confirmed non-regressive. The demo HTML
   was also re-verified in headless Chrome from its new relative path: all
   18 library cards render correctly from the relocated JS data files.
2. **Multi-sign real-gap calibration** (`scripts/real_gap_multisign_calibration.py`,
   `Phase3/real_gaps_out/real_gap_multisign_calibration.json` +
   `_report.md`) — the P2-E6 analogue of step 3's P2-E4 reuse, closing
   recommended-order item 2 from this handoff's first version. This is
   **not** a drop-in reuse of step 3's approach: P2-E6's fold structure
   calibrates a different estimand than P2-E4's. P2-E4 gives a per-rank
   rate ("rank R is historically correct X% of the time"); P2-E6 gives a
   **set-inclusion rate** keyed by `(mask_length, adaptive_anchor_length)`
   — "does the tie-complete displayed candidate set contain the true
   attested span," where `adaptive_anchor_length` is chosen per-gap by
   trying the longest anchor (3 signs, then 2, then 1) with any
   independent-witness support before abstaining, exactly replicating
   `p2e6_multisign_horizon.build_adaptive_records`'s own selection rule.
   - `real_gap_witness_check.compute_anchor_key_crossline` was generalized
     to take `anchor_length` and `max_lines_crossed_per_side` as parameters
     (defaults unchanged, re-verified behavior-preserving for existing
     callers) so the new script could resolve anchor keys at lengths 1, 2,
     and 3, same-line only (`max_lines_crossed_per_side=0`) — cross-line
     multi-sign gaps are out of scope here for the same reason cross-line
     single-sign gaps were out of scope in step 3: P2-E6's own folds were
     fit entirely on synthetic within-line masks, so there is no cross-line
     rate to borrow.
   - Scoped to the same 42 CTHs step 3 uses (P2-E4 and P2-E6 both fold over
     the same dev CTH universe, so their `evaluation_cth` unions coincide),
     749 documents.
   - Of **9,022** real multi-sign gaps found in that scope, **1,338** are
     eligible (a same-line 1-sign anchor exists on both sides — the base
     population before trying longer anchors), **989** get a presented
     candidate set (74%; anchor length 1 sufficed for 834, length 2 for
     106, length 3 for 49), **349** abstain entirely.
   - Of **835** presented `restored` spans checked: **356** have the
     editor's reading included in the calibrated candidate set (a
     historical set-inclusion rate applies, e.g. 57.6% for the
     mask=2/anchor=2 group, n=8,578), **479** do not (reported against the
     same group rate — never as "the editor is wrong"), **0** have no
     usable rate for their group.
   - Full detail in `Phase3/real_gaps_out/real_gap_multisign_calibration_report.md`.

## Multilingual-layer contamination fix (2026-07-25, third continuation)

Prompted by Ixca asking directly whether the project accounted for the
corpus's known multilingual layers. It did not, in implementation, though
CLAUDE.md had named the layers ("Hittite, Akkadian, Sumerian, Hattic,
Cuneiform Luwian, Palaic, Hurrian... do not silently discard non-Hittite
layers") since Phase 1.

### What was found

- The per-line `lg` XML attribute is captured in P2's `corpus.parquet`
  (`line_lang` column) but was never propagated into P4's
  `decomposed_corpus.parquet` — the token-level cache every downstream
  script reads. `hittite_tokenizer.py`'s vocab builder, every P2-E
  script, and every `real_gap_*.py` script (including this same
  session's own multi-sign calibration) treated every line as Hittite
  regardless of actual language.
- ~10.5% of corpus word-rows are non-Hittite-tagged (Akkadian, Hurrian,
  Hattic, Luwian, Sumerian, Palaic).
- A drafted-but-unratified spec already existed for exactly this problem
  (`specs/LINE_LANG_MIGRATION.md`), flagging that the raw `line_lang`
  values have real data-quality defects (a small number of malformed
  entries with leftover XML fragments) — never carried out.

### What was done (all steps of `specs/LINE_LANG_MIGRATION.md`, now
marked RATIFIED AND IMPLEMENTED in that spec)

1. **Step A audit** (`scripts/line_lang_audit.py`,
   `migrations/line_lang_v1/audit_report.md`) — independently re-walked
   the raw XML (bypassing the frozen `02_parse.py` entirely), restricted
   to train/dev/discovery (test-side `line_lang` values were never read,
   not merely excluded from the report). Found one confirmed
   parser-side defect (`KBo 53.44`, all 8 lines tagged `Hur` in source
   but recorded `Hit` in `corpus.parquet`) and one confirmed source-XML
   defect (`KUB 43.50+`, a malformed `lg` value verified present
   verbatim in the parsed attribute dictionary — an initial plain-text
   grep had wrongly suggested otherwise; the correction is recorded
   in-report, not silently dropped).
2. **Step B ratification** (Ixca, 2026-07-25): 7-code canonical
   vocabulary (`Hit, Akk, Sum, Hat, Hur, Luw, Pal`), `Hattian -> Hat`
   mapped as the same language under two spellings, `Lu`/`5f_`/`ign`
   quarantined as `unrecognized` pending further review rather than
   guessed at.
3. **Step C rebuild** (`scripts/line_lang_rebuild.py`) — applied the
   ratified rule mechanically to every document, all splits (test
   included, but never printed/sampled/ranked), writing
   `migrations/line_lang_v1/line_lang_canonical.parquet` (regenerable,
   gitignored like every other `.parquet` in this repo).
4. **Step D verification** — all 10 acceptance checks from the spec
   passed (`migrations/line_lang_v1/verification_report.md`), including
   a determinism check (two clean runs, byte-identical logical tables).
5. **Propagation**: `lib/line_lang_lookup.py` is the new shared reader
   (fails toward EXCLUSION — an unconfirmed line's language is treated
   as non-Hittite, never guessed in). Wired into:
   - `hittite_tokenizer.py`'s `build_structured_sequence`/
     `_attested`/`build_vocab` (optional `line_lang_lookup` param; a
     non-Hittite line's `<LINE>` position slot is preserved, only its
     token CONTENT is excluded — no downstream position-numbering code
     needed to change).
   - `p2e_witness_recoverability.render_fragments` (same convention),
     now the single shared choke point for anchor-index construction —
     wired into all 8 call sites (7 external callers plus its own
     `main()`, which was missed on the first pass and caught because
     its rerun showed suspiciously byte-identical numbers).
6. **Tokenizer vocab: rebuilt, then reverted.**
   `scripts/rebuild_tokenizer_hittite_only.py` regenerated
   `configs/tokenizer.json` under the Hittite-only filter (vocab
   2,374 → 1,957) — the first regeneration since Phase 1 closeout
   (confirmed via grep: nothing in the live tree called `build_vocab()`
   before this). This broke the mandatory base-tracer gate
   (`scripts/00_tracers.py`) because `runs/pretrain_base/checkpoint.pt`
   — a real, completed 60,000-step P4 pretraining run — has an
   embedding matrix sized to the old vocab. Retraining is a multi-hour
   job. Per Ixca's explicit call, **`configs/tokenizer.json` was
   reverted to the original Phase 1 vocab**; the rebuild script and its
   report (`configs/tokenizer_report_line_lang_v1.md`) are kept as
   ready-to-use infrastructure for whenever retraining is scheduled.
7. **Reran everything downstream of the anchor-index filter**: all of
   P2-E2 through P2-E7, all four `real_gap_*.py` scripts, and the demo
   export. Every rerun verified against `git diff` (all these outputs
   are git-tracked) and committed with its before/after numbers in the
   commit message. Notable movement: P2-E4's rank-1 calibrated agreement
   89.97% → 88.79%; P2-E6's maximum displayed-set size at 5 signs
   shrank from 237 to 85 options (non-Hittite content had been inflating
   candidate-set noise); the real-gap calibration scripts'
   calibration-covered CTH count moved 42 → 39 documents as the P2-E4/
   P2-E6 fold composition shifted; the demo now shows 19 distinct
   tablets (was 18).

### What is explicitly still open

- **The real-gap pipeline's QUERY side is not language-filtered.** Which
  line a candidate real gap sits on is still not checked against
  `line_lang_canonical` before the gap is counted/queried. Lower
  severity than the (now-fixed) witness/proposal side — querying a
  Hittite-only anchor index with a non-Hittite anchor key fails safe (no
  coverage, abstain) rather than returning a wrong answer — but
  `real_gap_census.py`'s gap counts are not yet language-stratified.
  Flagged, not silently expanded into.
- **The tokenizer vocabulary is still the Phase 1, language-blind one.**
  Rebuilding it Hittite-only requires first retraining
  `runs/pretrain_base/checkpoint.pt` (multi-hour job) or accepting a
  vocab/checkpoint mismatch — a dedicated future session's decision, not
  made here.
- **Evidence-class reclassification of `line_lang_canonical`** was resolved
  by Phase 4 Gate 0 as `EDITORIAL_TRANSCRIPTION`, consistent with the official
  HPM language-marking semantics. See `configs/evidence_registry.yaml` and
  `reports/phase4_gate0_ratification.md`.

## What the successor must not do

Everything already listed in `PHASE2_SUCCESSOR_HANDOFF.md`'s equivalent
section still applies (test-side purity, no `cu`/morphology/editor-identity
as model input, no per-instance probability framing, no automatic truth
promotion). In addition, specific to this phase:

- Do not present the 28 demo packets as real damage, or reuse them as if
  they were real-gaps pipeline output — they are a deliberately-labeled
  training/calibration playground, a distinct product from the real-gaps
  pipeline.
- Do not borrow the same-line P2-E4/P2-E6 calibration for cross-line
  anchors (single- or multi-sign) — cross-line still has no calibration
  pass of its own; nothing changed on this front this session.
- Do not conflate P2-E4's per-rank calibration with P2-E6's set-inclusion
  calibration, or apply one file's rate to the other's gap population —
  `real_gap_calibration.py` (single-sign, per-rank) and
  `real_gap_multisign_calibration.py` (multi-sign, set-inclusion) are
  reused from structurally different source estimands and are not
  interchangeable.
- Do not promote a real-gap witness match (or mismatch) against an editor's
  restoration to ground truth. It is corroborating or contradicting
  evidence only, exactly as `real_gap_calibration_report.md` and
  `real_gap_multisign_calibration_report.md` state.
- Do not treat the "restored shelf" as re-scoring anything yet — it is
  organizational bookkeeping until the real-gaps pipeline is wired in.
- Do not pivot to the content→location / chip-placement capability (Ixca's
  own tablet/fragment/chip-by-edge-count taxonomy, and whether a chip's
  textual context alone can place it in a fragment or tablet) without
  Ixca's explicit go-ahead — Ixca considered this and chose to continue the
  existing real-gaps plan instead ("since it's already in the plan, that's
  fine, let's proceed as you suggested"). It's a real, separately-scoped
  future initiative, not folded into the current pipeline.
- Do not start the draft paper or ALP workshop submission — both are
  explicitly deferred by Ixca until after a mentor is in hand ("the draft
  paper will happen just before i meet them... the workshop will wait for
  mentor sign-off").
- Do not re-derive `line_lang_canonical` from `Phase1_pipeline/p2_out/
  corpus.parquet`'s own `line_lang` column anywhere. That column is the
  unratified, data-quality-flagged source; `lib/line_lang_lookup.py`
  reading `migrations/line_lang_v1/line_lang_canonical.parquet` is the
  single ratified source of truth.
- Do not assume `configs/tokenizer.json` is language-filtered. It is
  still the original Phase 1 vocab (reverted after breaking the
  pretrained checkpoint) — only the anchor-index/witness-matching layer
  is Hittite-only-filtered. Don't conflate the two when reasoning about
  why a token is or isn't in-vocab.
- Do not rebuild the tokenizer vocab Hittite-only again without either
  retraining `runs/pretrain_base/checkpoint.pt` first or explicitly
  accepting/documenting the resulting checkpoint mismatch — this was
  tried this session and reverted for exactly that reason.
- Do not treat real_gap_census.py's gap counts as language-stratified —
  the query side (which line a gap sits on) still isn't checked against
  `line_lang_canonical`, per the "explicitly still open" list above.

## Commit history for this phase

Everything above is committed as sixteen logical commits on `master`, in
this order (oldest first):

| commit | summary |
|---|---|
| `1a24100` | Reorganize project into phase-scoped folders (Archive/, Phase1_pipeline/, Phase2/ — pure path moves and reference updates, no content change) |
| `7f32dbf` | Track `word_index_in_line` in the decomposed corpus cache (the alignment infrastructure both the demo export and the real-gaps pipeline depend on) |
| `dae199c` | Add training/calibration playground demo (library + workspace) |
| `f3bc201` | Build real-gaps production pipeline (census, witness check, calibration) |
| `bf123cf` | Add Phase 3 successor handoff (this document's first version) |
| `946cc64` | Move Phase 3 output folders under Phase3/, generalize anchor-key builder |
| `0faf03a` | Add multi-sign real-gap calibration (P2-E6 analogue) |
| `3b9f9f2` | Update Phase 3 handoff for Phase3/ folder move + multi-sign calibration |
| `7afdeb3` | Add line_lang migration Step A non-test audit (read-only) |
| `35b3eb2` | Ratify and rebuild line_lang canonical field (migration Steps C/D) |
| `905c320` | Add line_lang_lookup module; rebuild tokenizer vocab Hittite-only |
| `aecdddb` | Revert tokenizer vocab; fix missed render_fragments call site |
| `47c9d44` | Filter render_fragments (shared anchor-index construction) to Hittite-only |
| `6c017ea` | Rerun P2-E2 through P2-E7 under the Hittite-only anchor-index filter |
| `9d3a7de` | Rerun real_gap_witness_check/calibration/multisign_calibration |
| `f796318` | Refresh demo export against the rebuilt P2-E4/P2-E6 packets |

This handoff document's own update commit follows the above, so its
"what was completed" sections describe an already-committed state.
Nothing from this phase is outstanding in the working tree as of this
commit.

## Recommended order of work

1. ~~Decide whether `demo/dm_out/` and `real_gaps_out/` should move under a
   new `Phase3/` folder~~ — **done** (`946cc64`): both now live under
   `Phase3/{demo_out,real_gaps_out}/`.
2. ~~**Multi-sign calibration**: build the P2-E6 analogue of
   `load_cth_fold_map()`/`rank_calibration`~~ — **done** (`0faf03a`):
   `scripts/real_gap_multisign_calibration.py` applies P2-E6's
   set-inclusion fold calibration to multi-sign real gaps.
3. **Cross-line calibration**: the 14,875 cross-line-anchored single-sign
   real gaps, and the (not yet separately counted) cross-line multi-sign
   gaps, currently have descriptive coverage/agreement numbers only
   (`real_gap_witness_check_report.md`) and no calibrated rate at all.
   Needs its own calibration pass — for both single- and multi-sign gaps —
   not a borrowed same-line rate from either P2-E4 or P2-E6.
4. **Wire the real-gaps pipeline into the demo UI** as a production mode —
   the convergence point of both tracks, and the piece that would let a
   real restoration action actually re-score neighboring gaps (Ixca's
   original ask, explicitly not yet implemented). With both same-line
   calibration passes (single- and multi-sign) now in hand, this is the
   most natural next substantial step.
5. **Language-filter the real-gap query side**: extend
   `real_gap_census.py`/`real_gap_witness_check.py` to check a gap's own
   line against `line_lang_canonical` before counting/querying it — the
   "explicitly still open" gap from this session's multilingual-layer
   fix. Lower urgency than items 3-4 (fails safe today) but should not
   be left indefinitely.
6. **Retrain `runs/pretrain_base/checkpoint.pt` under the Hittite-only
   vocab**, then rerun `scripts/rebuild_tokenizer_hittite_only.py` for
   real this time — a multi-hour job, deliberately deferred this
   session. Until this happens, `configs/tokenizer.json` remains the
   original Phase 1, language-blind vocab (only the anchor-index/
   witness-matching layer is currently Hittite-only-filtered).
7. Only after the above: revisit whether the chip/fragment/tablet
   content-to-location capability is worth scoping as its own initiative.
8. Draft paper and ALP workshop submission remain deferred, per Ixca's
   explicit instruction, until a mentor relationship exists.

## Verification and operating notes

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe lib\contracts.py
.\.venv\Scripts\ruff.exe check lib scripts tests demo
```

At this handoff: 88 repository tests pass (unchanged by the multilingual-
layer fix — no new unit tests were added; `scripts/line_lang_audit.py`/
`line_lang_rebuild.py` were verified manually, including a two-clean-runs
determinism check, matching the existing convention for `real_gap_*.py`).
The four `real_gap_*.py` scripts, the `prepare_scope()` refactor, and the
`compute_anchor_key_crossline` parameterization were all re-run end-to-end
after every change; step 2's own default-scope numbers (25,559 gaps, 867
documents) were re-verified unchanged after both refactors, confirming
each is behavior-preserving for its original caller. Every P2-E script and
every `real_gap_*.py` script was subsequently rerun again under the
language filter (see the "Multilingual-layer contamination fix" section
above for the full before/after numbers) — `git diff` against each
git-tracked output/report is the audit trail, not a separate snapshot.
`ruff check` on `lib scripts tests demo` is clean throughout.

The demo (`demo/taksan_missing_text_prototype.html`) has no automated test
suite of its own; all verification so far is manual headless-Chrome
transcripts recorded in `demo/missing_text_prototype_report.md`. It has
never been reviewed by an actual Hittite specialist — per
`PHASE2_CLOSEOUT.md`'s own framing, that question can only be answered by
putting it in front of one.

## Fast reading path

1. `PHASE2_SUCCESSOR_HANDOFF.md` (prior state).
2. This handoff.
3. `demo/missing_text_prototype_report.md` (all 7 revisions — the demo's
   full bug history and the library/playground reframing).
4. `Phase3/real_gaps_out/real_gap_census_report.md` →
   `Phase3/real_gaps_out/real_gap_witness_check_report.md` →
   `Phase3/real_gaps_out/real_gap_calibration_report.md` →
   `Phase3/real_gaps_out/real_gap_multisign_calibration_report.md`, in that
   order (each states plainly what it does not yet establish, and hands
   off to the next).
5. `specs/EXPERT_DECISION_CONTRACT.md` (still the governing contract for
   any packet either track produces).
6. `specs/LINE_LANG_MIGRATION.md` (now RATIFIED AND IMPLEMENTED) →
   `migrations/line_lang_v1/audit_report.md` →
   `migrations/line_lang_v1/rebuild_report.md` →
   `migrations/line_lang_v1/verification_report.md`, in that order, for
   the multilingual-layer contamination fix's full account.

The standing interpretation is unchanged from Phase 2: provide inspectable
possibilities to an expert where encoded evidence is informative, preserve
alternatives, and abstain everywhere else. This phase's addition is
narrower and procedural: keep the training playground and the real-gaps
production pipeline honestly separate until the second is actually ready to
replace the first's synthetic data with genuine damage.
