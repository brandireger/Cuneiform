# Phase 3 successor handoff

Prepared 2026-07-25 for the next maintainer of the Cuneiform/Takšan project,
continuing directly from `PHASE2_SUCCESSOR_HANDOFF.md`.

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
   `real_gaps_out/`) — the actual missing-text objective, built one verified
   step at a time (census → witness check → calibration application), now
   widened to the full CTH set the existing P2-E4 calibration covers. **Not
   yet wired into the demo UI** — it currently only produces JSON/Markdown
   reports, no packets, no browser-facing product.

Neither track has touched the frozen test split. No real-gap witness match,
editor-restoration agreement, or expert UI decision has been promoted to
corpus ground truth. No new model training occurred this phase.

All work described in this handoff, across both this session and the prior
reorganization session, is now committed (see "Commit history for this
phase" below) — there is no outstanding uncommitted state to resolve.

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
  (`demo/dm_out/`, `real_gaps_out/`) follow the same one-folder-per-phase
  convention but were not yet given a `Phase3/` top-level folder — worth
  deciding explicitly rather than defaulting either way.
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

### Real-gaps production pipeline (`scripts/`, `real_gaps_out/`)

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

   Full detail in `real_gaps_out/real_gap_calibration_report.md`.

This pipeline produces **no packets and no UI yet** — reports only. Wiring
it into a production-mode extension of the demo is the natural next step,
not yet started.

## What the successor must not do

Everything already listed in `PHASE2_SUCCESSOR_HANDOFF.md`'s equivalent
section still applies (test-side purity, no `cu`/morphology/editor-identity
as model input, no per-instance probability framing, no automatic truth
promotion). In addition, specific to this phase:

- Do not present the 28 demo packets as real damage, or reuse them as if
  they were real-gaps pipeline output — they are a deliberately-labeled
  training/calibration playground, a distinct product from the real-gaps
  pipeline.
- Do not borrow the same-line P2-E4 calibration for cross-line anchors, or
  the single-sign calibration for multi-sign real gaps — both need their
  own calibration pass; neither has one.
- Do not promote a real-gap witness match (or mismatch) against an editor's
  restoration to ground truth. It is corroborating or contradicting
  evidence only, exactly as `real_gap_calibration_report.md` states.
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

## Commit history for this phase

Everything above is committed as four logical commits on `master`, in this
order (oldest first):

| commit | summary |
|---|---|
| `1a24100` | Reorganize project into phase-scoped folders (Archive/, Phase1_pipeline/, Phase2/ — pure path moves and reference updates, no content change) |
| `7f32dbf` | Track `word_index_in_line` in the decomposed corpus cache (the alignment infrastructure both the demo export and the real-gaps pipeline depend on) |
| `dae199c` | Add training/calibration playground demo (library + workspace) |
| `f3bc201` | Build real-gaps production pipeline (census, witness check, calibration) |

This handoff document itself is committed separately, after the four above,
so its "what was completed" section describes an already-committed state.
Nothing from this phase or the prior reorganization session is outstanding
in the working tree as of this commit.

## Recommended order of work

1. Decide whether `demo/dm_out/` and `real_gaps_out/` should move under a
   new `Phase3/` folder per the project's own stated convention ("the next
   phase should get its own top-level phase folder") — not yet done.
2. **Multi-sign calibration**: build the P2-E6 analogue of
   `load_cth_fold_map()`/`rank_calibration` (no such fold structure exists
   yet for multi-sign contexts) so `real_gap_calibration.py` can cover
   multi-sign real gaps, not just single-sign.
3. **Cross-line calibration**: the 14,875 cross-line-anchored real gaps (in
   the 42-CTH scope) currently have descriptive coverage/agreement numbers
   only (`real_gap_witness_check_report.md`) and no calibrated rate at all.
   Needs its own calibration pass, not a borrowed same-line rate.
4. **Wire the real-gaps pipeline into the demo UI** as a production mode —
   the convergence point of both tracks, and the piece that would let a
   real restoration action actually re-score neighboring gaps (Ixca's
   original ask, explicitly not yet implemented).
5. Only after the above: revisit whether the chip/fragment/tablet
   content-to-location capability is worth scoping as its own initiative.
6. Draft paper and ALP workshop submission remain deferred, per Ixca's
   explicit instruction, until a mentor relationship exists.

## Verification and operating notes

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe lib\contracts.py
.\.venv\Scripts\ruff.exe check lib scripts tests demo
```

At this handoff: 88 repository tests pass. The three new `real_gap_*.py`
scripts and the `prepare_scope()` refactor were syntax-checked
(`ast.parse`) and re-run end-to-end after every change; step 2's own
default-scope numbers (25,559 gaps, 867 documents) were re-verified
unchanged after the refactor, confirming it is behavior-preserving for its
original caller. `ruff check` on `scripts/real_gap_*.py` and
`demo/dm1_missing_text_export.py` is clean (two trivial pre-existing
lint items — an unused import and an ambiguous variable name `l` — were
fixed in this handoff's own final pass).

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
4. `real_gaps_out/real_gap_census_report.md` →
   `real_gaps_out/real_gap_witness_check_report.md` →
   `real_gaps_out/real_gap_calibration_report.md`, in that order (each
   states plainly what it does not yet establish, and hands off to the
   next).
5. `specs/EXPERT_DECISION_CONTRACT.md` (still the governing contract for
   any packet either track produces).

The standing interpretation is unchanged from Phase 2: provide inspectable
possibilities to an expert where encoded evidence is informative, preserve
alternatives, and abstain everywhere else. This phase's addition is
narrower and procedural: keep the training playground and the real-gaps
production pipeline honestly separate until the second is actually ready to
replace the first's synthetic data with genuine damage.
