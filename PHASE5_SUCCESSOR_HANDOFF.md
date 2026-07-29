# Phase 5 successor handoff — cross-line calibration built, applied, and bounded

**Handoff date:** 2026-07-28
**Repository state:** P4-D/E ratified; **P4-E2 expert interface, P4-G rerun,
the full cross-line calibration line (P2-E8 → E9 → E10), and production
real-gap scope widening complete.** Cross-line single-sign is applied across
its applicable P2-E9 composition scope. Cross-line multi-sign is measured and
deliberately **not** applied. Protected-test access and GPU training remain
unauthorized; Gate 3 is untouched.

Read `AGENTS.md` first — it remains the design authority.

## Start here

`reports/phase2_p2e9_ratification.md` records the two decisions Ixca made on
2026-07-28 and what they cost. Then, in order:

- `reports/phase4_p4g_rerun.md` — why every prior coverage number moved
- `reports/phase2_p2e10_cross_line_multisign.md` — read the **conclusion**
- `reports/phase4_p4e2_expert_interface.md`

## What this session did

| work | outcome |
|---|---|
| CI staleness guard | `p4d_stamp_stale_reports.py --check` runs in CI, two-sided invariant |
| **P4-G rerun** | all ten artifacts recomputed under P4-D; decision 5 closed |
| **P4-E2** | expert interface for the workbench (never opened in a browser) |
| **P2-E8** | cross-line recoverability census |
| **P2-E9** | cross-line per-rank calibration; **applied in production** |
| **P2-E10** | cross-line multi-sign calibration; **deliberately not applied** |
| real-gap scope | union of applicable P2-E4/P2-E9 CTHs; **288 CTHs / 6,145 docs** |

## The through-line, and the one number that matters

Cross-line anchors are **89.9% of anchored real gaps** and had no calibration
at all. Borrowing same-line rates for them would have overstated the evidence
by ~5x. The whole line of work above exists to replace that borrowing with a
measurement.

Where it landed:

- **Single-sign cross-line works.** Held-out rank-1 agreement **77.5%** on
  8,208 spans across 279 compositions, clearing the ratified 0.75 target with
  a **0.0-point** transfer gap. The first application found 61 accepted
  cross-line gaps because it inherited P2-E4's 38-CTH scope. Production now
  uses the union of the applicable P2-E4 and P2-E9 sets: same-line remains
  **703 eligible / 41 accepted**; cross-line is **46,118 eligible / 577
  accepted**.
- **Multi-sign cross-line does not.** Set inclusion **13.8%** at two signs
  falling to **6.7%** at five. The calibration is sound (0.0 transfer gap on
  235k–377k held-out spans); what it establishes is that the channel does not
  work. **Do not wire P2-E10 into `real_gap_multisign_calibration.py`** — a
  calibrated 8% set-inclusion rate is honest but not decision-support.

## Ratified this session (`reports/phase2_p2e9_ratification.md`)

1. **`LAYOUT_AGNOSTIC`** is the cross-line witness-admission rule. Line
   division is scribal layout, not textual structure. `STRICT` is retained as
   a declared ablation — it yields 3.3x less held-out mass *and* transfers
   worse (2.3 vs 0.0 pts), which is only demonstrable because it was kept.
2. **Cross-line calibration target 0.75**, separate from same-line's 0.90.
   Recorded in `configs/p2e9_cross_line_calibration.json` with who ratified it
   and why; `require_calibration_target()` refuses any value not marked
   `RATIFIED`.

## Traps this session hit, so you don't

1. **A calibration-set rate is not a held-out rate, and they have different
   jobs.** The rate ATTACHED to a gap must be `calibration_set` — fit on
   compositions disjoint from that gap's own. `held_out` is the *quality*
   claim and is measured on exactly those compositions, so attaching it
   per-gap is circular. Both scripts now name these roles in their payloads.
   This nearly shipped the wrong way round.
2. **A small sample can manufacture a transfer gap.** The dev-only P2-E9 run
   showed a 12.8-point optimism gap on 55 held-out spans (per-fold accepts
   45/5/1/4). Widening to the governed non-test universe collapsed it to 0.0.
   The gap was the sample, not the evidence.
3. **Widening the universe is safe *here* for a specific reason** worth not
   re-deriving: this calibration consumes no model. It counts independent
   witness families in an anchor index, so train compositions cannot leak
   anything a model was fit on. Folds stay composition-level; bins stay out;
   test exclusion is asserted, not assumed.
4. **Regenerating a report can strip a caveat that is still true.** The
   P4-G rerun removed the census's note, which was a *scope disclosure*
   (deliberately language-blind), not a staleness claim. The CI guard caught
   it within minutes of being wired in. The census stays stamped.
5. **Clustering is Zipfian and it only bites with a human in front of it.**
   The largest workbench cluster has 95,530 members whose whole sequence is
   `x`; ranking by document count instead surfaces the single signs `a`, `i`,
   `e`. Queue policy `contentful_sequence_length_v1` handles both.

## Standing constraints (unchanged)

Everything in `PHASE4_SUCCESSOR_HANDOFF.md`'s equivalent section still
applies: workbench category vocabulary, `LEXICAL_UNKNOWN` reserved for expert
assertion, backup before/after every expert session, logical-not-file hashes,
never read `cu`, Gate 3 closed. Additionally:

- **Never pool cross-line and same-line rates**, or substitute one for the
  other. Different populations (~5x apart in gold inclusion), different
  ratified targets (0.75 vs 0.90).
- **Do not use a second ranking implementation.** `p2e9.merged_ranking` is
  what was calibrated and what production applies. A parallel implementation
  is how E2 happened.

## Open, in the order I would take them

1. ~~**Widen the real-gap scope.**~~ **DONE 2026-07-28.** The top-5 figure was
   the descriptive witness-check slice, while production was actually
   restricted by P2-E4's 38-CTH scope. The application now uses the union of
   38 same-line and 279 cross-line CTH sets (288 distinct); see
   `reports/phase5_real_gap_scope_widening.md`.
2. **Open the expert interface in a browser.** It has never been run. Field
   contract, hash vector, and every Python path are verified; rendering is
   not. Treat the first run as a smoke test.
3. **Ratify the two P4-E2 queue exclusions** (placeholder-only sequences;
   sequences under 2 signs). They decide what a specialist is shown.
4. **The empty-middle observation.** A rank-1 proposal can be the *empty*
   middle — witnesses attesting both anchors adjacent with nothing between.
   For a one-sign gap that is disagreement with the query's structure, not a
   reading. It arises identically in the same-line path; filtering it is a
   scoring change needing its own justification.
5. **Gate 3** still requires a full proposal.

## Validation at handoff

```powershell
python -m unittest discover -s tests      # 211 pass
ruff check lib scripts tests demo         # clean
python lib/contracts.py                   # 20/20
python scripts/00_tracers.py              # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check   # exit 0
```

The tracer suite passing after this much change is the reassurance worth
having: the plumbing that caught E2 is still live, and every rerun script
re-ran its own C1 encoding assertion on the way through.
