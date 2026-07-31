# Phase 5 successor handoff — cross-line calibration applied; expert surfaces made usable

**Handoff date:** 2026-07-28
**Refreshed:** 2026-07-31 (both expert prototypes browser-verified)
**Prior refresh:** 2026-07-30 (workbench readability + single-language
sessions; empty-middle measured and resolved by display treatment)
**Repository state:** P4-D/E ratified; **P4-E2 expert interface, P4-G rerun,
the full cross-line calibration line (P2-E8 → E9 → E10), production real-gap
scope widening, and the 2026-07-30 expert-surface work complete.** Cross-line
single-sign is applied across its applicable P2-E9 composition scope.
Cross-line multi-sign is measured and deliberately **not** applied.
Protected-test access and GPU training remain unauthorized; Gate 3 is
untouched.

Read `AGENTS.md` first — it remains the design authority.

## Start here

`reports/phase2_p2e9_ratification.md` records the two decisions Ixca made on
2026-07-28 and what they cost. Then, in order:

- `reports/phase4_p4g_rerun.md` — why every prior coverage number moved
- `reports/phase2_p2e10_cross_line_multisign.md` — read the **conclusion**
- `reports/phase5_empty_middle_census.md` — the measurement, and why filtering
  was the wrong instinct
- `reports/phase5_empty_middle_display_treatment.md` — what was adopted
- `reports/phase5_workbench_readability_and_language_selection.md`
- `reports/phase4_p4e2_expert_interface.md`
- `reports/phase5_browser_verification.md` — both prototypes rendered and
  checked; read its "deliberate bounds"
- `reports/phase5_p4e2_browser_smoke.md` — the earlier, narrower workbench
  check that this supersedes

Older `PHASE4_SUCCESSOR_HANDOFF.md` "Next work" text is a historical record,
not the current queue. `README.md`, `PHASE4_CHARTER.md`, `Phase4/README.md`,
and the corresponding Claude authority text were reconciled on 2026-07-30 so
they point here rather than reviving already-completed work.

## Work completed

**2026-07-28 session**

| work | outcome |
|---|---|
| CI staleness guard | `p4d_stamp_stale_reports.py --check` runs in CI, two-sided invariant |
| **P4-G rerun** | all ten artifacts recomputed under P4-D; decision 5 closed |
| **P4-E2** | expert interface browser-smoke-tested; native dialogs replaced |
| **P2-E8** | cross-line recoverability census |
| **P2-E9** | cross-line per-rank calibration; **applied in production** |
| **P2-E10** | cross-line multi-sign calibration; **deliberately not applied** |
| real-gap scope | union of applicable P2-E4/P2-E9 CTHs; **288 CTHs / 6,145 docs** |

**2026-07-30 session**

| work | outcome |
|---|---|
| workbench readability | actions grouped by what the click records; mandated disclosures moved behind progressive disclosure, never deleted; damage-state overlay + legend |
| `--language` on the review export | single-language review sessions are reachable for the first time |
| **empty-middle census** | 109 of 577 accepted cross-line gaps (18.9%); filtering measured and rejected |
| **empty-middle display treatment** | option 2 adopted and implemented across the contract, both adapters, and the Takšan page |

Neither 2026-07-30 change moved a ratified number. The default review queue's
`channels_logical_sha256` is unchanged, and real-gap counts are unchanged at
703/41 same-line and 46,118/577 cross-line.

**2026-07-31 session**

| work | outcome |
|---|---|
| **browser verification** | both prototypes rendered and checked in Chrome; `data-damage` selectors apply, and no percentage appears beside an empty middle |
| **P4-E2 queue policy** | contentless exclusion **ratified** and widened; minimum-length **deferred**; policy versioned to `v2` |

First recorded browser check for `demo/taksan_missing_text_prototype.html`.
Human visual check against a checklist, not an automated capture — see the
report's deliberate bounds.

The queue's visible content hash is unchanged by the ratification
(`3e4e66ea…`); the widening removes 26 apparatus clusters that were already
below the display cut.

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

## Ratified decisions

**2026-07-28** (`reports/phase2_p2e9_ratification.md`)

1. **`LAYOUT_AGNOSTIC`** is the cross-line witness-admission rule. Line
   division is scribal layout, not textual structure. `STRICT` is retained as
   a declared ablation — it yields 3.3x less held-out mass *and* transfers
   worse (2.3 vs 0.0 pts), which is only demonstrable because it was kept.
2. **Cross-line calibration target 0.75**, separate from same-line's 0.90.
   Recorded in `configs/p2e9_cross_line_calibration.json` with who ratified it
   and why; `require_calibration_target()` refuses any value not marked
   `RATIFIED`.

**2026-07-30** (`reports/phase5_empty_middle_display_treatment.md`)

3. **The empty middle is treated at the display layer, not filtered.** It
   keeps its rank and witness support — that is the ranking P2-E4/P2-E9 were
   fit over — but is rendered as typed contradictory evidence rather than a
   candidate reading, and its rank-level group rate is withheld because that
   rate's estimand is agreement with the true attested middle, which this
   option cannot be.

**2026-07-31** (`reports/phase5_p4e2_queue_policy_ratification.md`,
`configs/p4e2_queue_policy.json`)

4. **The contentless-sequence exclusion is ratified**, with its character set
   widened on the line *the editor's apparatus is contentless; anything that
   could have been on the tablet is not*. Digits are deliberately kept — `10`
   alone is in 81 documents and `d 10` in 70, the Storm God with a damaged
   determinative. Safety invariant: no sequence carrying a sign value can be
   caught, since the only letter in the set is the illegible placeholder `x`.
5. **The minimum-sequence-length rule is NOT ratified**, and is deferred to
   the second queue. Consumers must present it as such and must not extend
   the contentless ratification to it. `require`-style fail-closed loading is
   in `phase4_workbench_review_export.load_queue_policy()`.

## Traps hit, so you don't

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
   `e`. Queue policy `contentful_sequence_length_v2` handles both.
6. **Verbose UI text is often contractual, not sloppy.** The "not a
   probability" and "absence of a recorded objection" lines exist because
   standing display rules require them. Collapsing a required statement is a
   presentation change; deleting one is a contract breach; in a diff of a
   900-line HTML file the two look identical. Ordering tests now pin which
   statements must stay outside their disclosures.
7. **A "bug" in the output may be a finding wearing the wrong label.** The
   empty middle looked like noise. Measured, 41 of 109 cases are the system
   automatically catching an editorial restoration that the witness tradition
   contradicts — a headline deliverable, not a defect. Measure before fixing.
8. **Homoglyphs fail silently and survive code review.** The corpus uses
   U+2329/U+232A angle brackets; U+3008/U+3009 are visually identical CJK
   characters occurring in it zero times. The first draft of the queue-policy
   tests pasted the wrong pair — the rule looked right and caught nothing.
   Character sets that gate what a specialist sees are now pinned **by
   codepoint** in tests, not by appearance.
9. **Two rules presented as a pair may not be comparable.** The P4-E2 queue
   exclusions had been bundled since they were written. Measured separately,
   one turned out load-bearing (removing it costs 35% of visible slots) and
   the other a no-op (the queue hash is byte-identical either way). They got
   different answers. Measure each rule against what a specialist actually
   sees before bundling a decision.
10. **Check which key an artifact actually stores its options under.** The
   first empty-middle count read `candidate_set.alternatives` and reported 5;
   P2-E6 stores `tie_complete_alternatives`, and the real figure was 10,
   including one at rank 1 on 19 families.

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
- **A single-language review queue is a review surface, not a prediction
  surface.** No per-language calibration exists for any language. `Pal` (3
  real compositions), `Sum`, and `Luw` cannot support a leakage-safe one at
  all; whether `Hur`/`Akk`/`Hat` can is a separate, separately gated question,
  and each would need its own ratified target.

## Open, in the order I would take them

1. ~~**Browser-verify two prototypes.**~~ **DONE 2026-07-31**
   (`reports/phase5_browser_verification.md`). Ixca rendered both pages in
   Chrome over a local `http.server` and confirmed every checklist item. The
   two highest-risk items passed: the workbench's `data-damage` attribute
   selectors actually apply, and **no percentage appears beside an empty
   middle** in Takšan — the defect the whole treatment exists to remove. This
   was the Takšan page's first ever recorded browser check.

   Not covered, and still open: **no export was downloaded and no ingest was
   exercised** (those remain covered by Python tests only), and **no automated
   regression capture exists** — the string-level tests pin that the required
   wording and hooks are present, but they cannot observe a CSS selector
   matching nothing, which is exactly the failure class that made the manual
   check necessary. A future markup change can still break rendering silently.

2. ~~**Ratify the two P4-E2 queue exclusions.**~~ **DECIDED 2026-07-31**
   (`reports/phase5_p4e2_queue_policy_ratification.md`,
   `configs/p4e2_queue_policy.json`). They were presented as a pair since
   P4-E2; measuring them separately showed they are not comparable, so they
   got different answers.
   - **Contentless exclusion: RATIFIED**, character set widened on the line
     *the editor's apparatus is contentless, anything that could have been on
     the tablet is not*. It is load-bearing: with the rule off, 21 of the 60
     visible same-language slots become runs of `x` and `_`, and the top item
     is twelve underscores. Digits were deliberately kept — `10` alone is in
     81 documents and `d 10` in 70, the Storm God with a damaged
     determinative.
   - **Minimum length 2: UNRATIFIED, DEFERRED** to the second queue. It is a
     no-op — rebuilding with 1 leaves the queue content hash byte-identical,
     because ranking already suppresses single-sign clusters. And its rare
     tail is not noise: 468 of 592 are plain sign readings, largely
     Sumerograms. Ratifying it would assert something the data contradicts;
     rejecting it would change nothing. The real question belongs to item 4.

   Queue policy is now `contentful_sequence_length_v2`; the export reads its
   rules from the record and fails closed without it, and per-rule status is
   shown on screen.

3. **Review the empty-middle branch wording as copy.** The four branch texts
   in `lib/expert_decision_contract.py` are the sentences a Hittitologist will
   actually read. They were written from the encoded evidence and reviewed as
   logic, not as philological prose.

4. **The second queue: rare single signs and ungrouped occurrences.** This is
   where the deferred minimum-length decision actually has consequences.
   Two populations are unreachable through a cluster-first queue ranked by
   sequence length:
   - **468 rare single-sign clusters** (same-language, ≤2 documents, 79.1% of
     that tail) — largely Sumerograms: `numun`, `kalam`, `géštug`, `ereš`,
     `naga`, `ḫabrud`, `gišnú`, `giškim`, `ibila`, `gišgigir`, `iku`, `i₇`.
     Ranking by **rarity** rather than length would surface them.
   - **~13,900 ungrouped occurrences** whose sequence is unique, so they are
     in no cluster at all — arguably the most interesting material, and the
     P4-E2 report already flagged that a queue keyed on surrounding context
     rather than shared surface form would be a separate build.

   Settle `minimum_sequence_length` together with this, not before it.

5. **Two scope questions surfaced by the empty-middle work**, deliberately not
   settled as side effects of a display change:
   - **`…` indeterminate lacunae are counted as single-sign gaps** — 2,725 of
     46,118 cross-line eligible, 35,221 restored ellipsis tokens corpus-wide.
     A `…` means "an unknown amount is missing", not one sign, so these
     arguably do not belong in a single-sign population at all.
   - **`AT 454` is filed under CTH 577** and reads as a Hittite oracle report,
     but `AT` is CLAUDE.md's Alalakh siglum with exactly one document. Check
     the site-prefix table; it bears on the Hattusa→provincial generalization
     experiment.

6. **First real specialist session.** It must run
   `scripts/phase4_workbench_backup.py` before and after, exercise an actual
   browser JSON download and the verifying ingest path, and remain
   quarantined. The 2026-07-29 test event never left browser memory. Queue
   size, the separate queue needed for roughly 13,900 ungrouped occurrences,
   and shared-versus-per-reviewer logs are real follow-up decisions but do not
   authorize automatic truth promotion.

7. **Gate 3 proposal.** Training is still unauthorized. A proposal must name
   the hypothesis, falsifier, config, sampling policy, time/GPU budget,
   conditioned-versus-unconditioned tracer, and new paths that cannot
   overwrite frozen D14. Only after ratification may P4-F training and its
   required comparisons begin.

8. **Later product/evaluation gates.** The real-gap pipeline and Takšan
   playground are not yet one production expert mode — this is where a cover
   page, a search front door, and a language mode selector carrying
   per-language evidence state belong; they span both prototypes and should
   follow item 2, not precede it. Protected-test/P6 runs remain one-shot and
   separately unauthorized. P7 candidate export, expert verification, and
   paper drafting come only after their standing human gates. The full
   model-ladder commitment must either be completed or explicitly amended
   before final publication claims.

Cross-line multi-sign is **not** an open implementation item: P2-E10 is a
completed negative result, and leaving it unapplied is the ratified
evidence-bounded behavior. The empty middle is **not** an open item either:
option 2 is adopted and implemented; only the copy review (item 3) remains.

## Optional contract question

`expert_decision_contract.CONTRACT_VERSION` stays **1.1.0**. The empty-middle
additions are additive, and the schema now refuses to emit an unannotated
empty option, so the producer side is safe. But a renderer written against
1.1.0 that ignores the new `display` block would draw an empty candidate —
the exact defect. If the block should be a hard *renderer* requirement rather
than a producer-side invariant, that is a version bump needing ratification.

## Validation at handoff

```powershell
python -m unittest discover -s tests      # 274 pass
ruff check lib scripts tests demo         # clean
python lib/contracts.py                   # 20/20
python scripts/00_tracers.py              # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check   # exit 0
git diff --check                          # clean
```

The tracer suite passing after this much change is the reassurance worth
having: the plumbing that caught E2 is still live, and every rerun script
re-ran its own C1 encoding assertion on the way through.

**Both prototypes were browser-verified on 2026-07-31**
(`reports/phase5_browser_verification.md`) — a human visual check against a
supplied checklist, not an automated capture, since no browser automation tool
was available. What that check could not cover is recorded there and in open
item 1: no export/ingest was exercised, and no automated regression capture
exists for rendering.
