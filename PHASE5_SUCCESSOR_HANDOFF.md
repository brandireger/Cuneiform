# Phase 5 successor handoff — cross-line calibration applied; expert surfaces made usable

**Handoff date:** 2026-07-28
**Refreshed:** 2026-08-03 (session 4 — open items 3, 4 and 7 are CLOSED.
The copy review and the second queue shipped 2026-08-02; **Gate 3 was
ratified 2026-08-02 and its Stage 1 ran to completion 2026-08-03 with the
pre-registered hypothesis REJECTED** — see item 7 and
`reports/phase4_p4f_stage1.md`. Stage 2 remains unauthorized. The remaining
open items are 1's uncovered residue, 4's UI/policy residue, 6, and 8.)
**Prior refresh:** 2026-08-01 (session 3 — the session-2 commit-state gap below is
now closed: PR #6 is merged to `origin/master`; the lacuna split-estimand
rerun is implemented, verified against a from-scratch rebuild of the full
derived-data chain, and committed on `agent/phase5-lacuna-split-estimand`.)
**Prior refresh:** 2026-07-31 (session 2 — Phase 5 branch merged to local
`master`; item 5a lacuna scope ratified as split estimand; contract version
closed at 1.1.0; `AT 454` resolved.)
**Prior refresh:** 2026-07-31 (both expert prototypes browser-verified; P4-E2
queue policy ratified and versioned to `v2`)
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

**Where this work lives.** PR #6 (`agent/phase5-real-gap-scope`) is merged
into `origin/master`. The two session-2 artifacts that previously existed only
in an ephemeral session container — `specs/EXPERT_DECISION_CONTRACT.md`'s
deferred-bump note and `reports/phase5_lacuna_scope_decision.md` — are
reproduced from the original session output and committed, along with item
5a's implementation (the `real_gap_calibration.py` split-estimand rerun and
its test), on branch `agent/phase5-lacuna-split-estimand`. **Session-3 note
worth keeping:** none of the raw corpus, derived parquet, or Phase 4
language-layer artifacts this rerun depends on are checked into git (by
design — see `README.md`'s Corpus setup section). Verifying the rerun required
downloading the pinned TLHdig 0.2.0-beta zip from Zenodo (MD5-checked against
the pin) and rebuilding the entire chain from `Archive/scripts/01_inventory.py`
through `10_resplit.py`, then `lib/decompose_corpus.py`,
`scripts/line_lang_rebuild.py`, `scripts/phase4_language_layers_v2.py`, and
`scripts/phase4_multilingual_token_dataset.py` — in that order, since each
depends on the previous. `splits.json`/`.parquet` is seed-derived (seed
20260721) and frozen/constitutional; the rebuild reproduced it exactly rather
than re-rolling it. The rebuild's fidelity was confirmed two ways: the
*unmodified* `real_gap_calibration.py` reproduced the already-committed
46,118/577 figures exactly, including a byte-identical
`language_dataset_file_sha256`; and `scripts/line_lang_rebuild.py`'s own
manifest step currently throws (`EvidencePolicyError`: registered class
`EDITORIAL_TRANSCRIPTION` for `line_lang` isn't permitted by the
`artifact_strict` policy the script requests) — a real, pre-existing latent
bug unrelated to this work, harmless here only because the parquet write
happens before that crash and nothing downstream hashes the stale manifest.
Worth a follow-up, not fixed in this pass.

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

**2026-07-31 (session 2)** — three decisions, one memo, one spec note.

6. **Indeterminate lacunae (`…`) — split estimand** (item 5a; recorded in
   `reports/phase5_lacuna_scope_decision.md`). The 2,725 `…` tokens inside the
   cross-line single-sign eligible set (5.9% of 46,118) mean "unknown amount
   missing," not one sign. Rather than filter them (drops the denominator) or
   keep them silently (inflates it), single-sign coverage is **reported on two
   denominators** — full eligible (46,118) and ellipsis-excluded (43,393) —
   with the gap disclosed. No positions leave calibration; no accepted count or
   ratified rate changes. **Implemented and verified 2026-08-01:**
   `scripts/real_gap_calibration.py` was rerun against a from-scratch,
   MD5-verified rebuild of the full derived-data chain (nothing was locally
   cached) and reproduces 43,393/46,118 exactly, with
   `tests/test_real_gap_calibration_scope.py` pinning the new
   `exclude_indeterminate_lacunae()` function.
7. **CONTRACT_VERSION stays 1.1.0; the hard-renderer requirement is a deferred
   major bump** (spec note appended to `specs/EXPERT_DECISION_CONTRACT.md`
   §Versioning). The empty-middle `display` block is a producer-side invariant
   — the schema refuses to emit an unannotated empty option — so the only
   renderer that exists cannot draw a blank candidate. Making honoring `display`
   a *compliance* requirement is deferred until a second renderer exists (the
   unified front door). This closes the former "Optional contract question."
8. **`AT 454` is not mis-assigned by any active mechanism** (item 5b). The
   `AT = Alalakh` siglum→site association exists **only as CLAUDE.md prose**
   marked "verify against inventory"; it is **not wired into any site-prefix
   mapping** in `lib`/`scripts`/`configs`. `AT 454` appears only as a witness
   siglum in join-candidate sets, never as an anchor carrying auto-assigned
   provenance, so nothing feeds it into the Hattusa→provincial experiment
   today. **Standing note for the future:** if a site-prefix table is ever
   *implemented*, `AT` must be excluded or hand-verified — it is a
   single-document siglum. No code change now.

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
10. **A training-time eval is not a measurement.** P4-F Stage 1's evals run
   ~80 boundary examples and swing ~4 AUC points with no trend — twice the
   +0.02 effect the falsifier had to detect. Arm B's last one read 0.8839
   against the 0.7263 that survived a proper n=1,920 paired pass. Never read
   a verdict off a loss curve; build the evaluation the falsifier named, and
   pair the arms on one shared, model-independent example set so the interval
   is on the *difference*.

11. **An ablation scope can silently hand one arm more data.** Giving P4-F's
   unconditioned arm the ratified `ALL_LANGUAGES_UNCONDITIONED` scope looks
   like the obviously correct label, and would have broken the experiment:
   `language_lookup_v2._classify` short-circuits every filter for an ablation
   scope, admitting the unresolved and conflated lines the conditioned arm
   must refuse. Data admission and conditioning are separate concepts and are
   now separate manifest fields.

12. **Check which key an artifact actually stores its options under.** The
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

- **Never trade numerical comparability for wall clock while a frozen
  baseline is in the comparison.** Training throughput work is APPROVED by
  Ixca (2026-08-03) for the **next** training experiment, and was
  deliberately NOT applied to the P4-F Stage 1 matched rerun.

  Apply on all arms from step 0, once no fp32 baseline is being matched:
  **bf16 autocast** (neither `19_pretrain.py` nor
  `scripts/phase4_p4f_pretrain.py` uses any mixed precision; ~1.5-2x on this
  Ampere card) and **`torch.compile`** (~1.2-1.8x at 12.8M params). Two
  numerically inert micro-fixes are worth folding in at the same time:
  `sample_boundary_batch` rebuilds a 21,013-entry `by_genre` index every step
  over a pool that never changes (~1%), and the per-step CSV write opens and
  closes the file 60,000 times per run (~1-2%).

  Why not on the matched rerun: D14 was trained fp32, and precision changes
  would have reintroduced exactly the confound the rerun exists to remove --
  as well as breaking the arm-A-vs-arm-B comparison, since arm A was already
  running. See `reports/phase4_p4f_baseline_diagnostic.md`.

  Throughput facts worth not re-deriving (RTX 3060 12GB, shared with the
  desktop): batch 32 runs ~3.03 steps/s on a clear GPU and ~1.89 under
  contention; batch 16 reached 5.7 steps/s clear. Contention from ordinary
  desktop applications swung throughput by up to 17x across one overnight
  run, so quote rates measured on a clear GPU and say so. `loss_curve.csv`'s
  `elapsed_s` RESETS on every resume -- sum the segments; reading the last
  row as total wall clock understates D14's 8.8h as 4.6h.

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

3. ~~**Review the empty-middle branch wording as copy.**~~ **DONE 2026-08-02**
   (`reports/phase5_empty_middle_copy_review.md`).

4. ~~**The second queue: rare single signs and ungrouped occurrences.**~~
   **DONE 2026-08-02, data/export layer only** (`reports/phase5_second_queue.md`,
   `scripts/phase4_workbench_second_queue_export.py`). `RARE_BY_RARITY` ranks
   by ascending document count — the literal opposite of the first queue's
   rank key — and `LOCAL_CONTEXT_PARALLEL` is a genuinely new channel keyed on
   flanking attested context rather than own content, joining 4,089 of the
   13,901 ungrouped occurrences at the measured window=1 (window=2 joins 73).
   A separate script, never a mode on the first queue: that queue's
   `channels_logical_sha256` is a pinned invariant and is verified untouched
   after every run.

   **Still open from this item:** no UI (wiring `window.WORKBENCH_SECOND_QUEUE`
   into a page is presentation work needing its own review), no `--language`
   variant, queue size 60/channel inherited rather than re-ratified, and
   `minimum_sequence_length` still `UNRATIFIED_DEFERRED` — `RARE_BY_RARITY`
   exists precisely to admit what its length-descending sibling suppresses,
   so neither building it nor ranking by rarity ratified that rule either way.

5. **Two scope questions surfaced by the empty-middle work** — **both resolved
   2026-07-31 (session 2).**
   - ~~**`…` indeterminate lacunae counted as single-sign gaps.**~~
     **RATIFIED: split estimand** (`reports/phase5_lacuna_scope_decision.md`).
     Single-sign coverage is reported on two denominators — full eligible
     (46,118) and ellipsis-excluded (43,393) — with the gap disclosed; nothing
     is filtered from calibration. **Implemented and verified 2026-08-01:**
     `scripts/real_gap_calibration.py` reruns to exactly 43,393/46,118, pinned
     by `tests/test_real_gap_calibration_scope.py`.
   - ~~**`AT 454` filed under CTH 577.**~~ **RESOLVED: non-issue.** The
     `AT = Alalakh` association is CLAUDE.md prose only, not wired into any
     active site-prefix mapping; `AT 454` is never an anchor with auto-assigned
     provenance, so nothing feeds it into the generalization experiment today.
     Standing note: exclude/hand-verify `AT` if a site-prefix table is ever
     implemented (single-document siglum).

6. **First real specialist session.** It must run
   `scripts/phase4_workbench_backup.py` before and after, exercise an actual
   browser JSON download and the verifying ingest path, and remain
   quarantined. The 2026-07-29 test event never left browser memory. Queue
   size, the separate queue needed for roughly 13,900 ungrouped occurrences,
   and shared-versus-per-reviewer logs are real follow-up decisions but do not
   authorize automatic truth promotion.

7. ~~**Gate 3 proposal.**~~ **RATIFIED 2026-08-02; Stage 1 RUN, REJECTED, AND
   RERUN AFTER A BASELINE DEFECT -- REJECTED AGAIN 2026-08-04** (`reports/phase4_p4f_gate3_proposal.md`,
   `reports/phase4_p4f_stage1.md`).

   Ratification authorized Stage 0 and the two named runs only. Both reached
   60,000 steps. `in_doc` AUC: arm A **0.6981**, arm B **0.7263**, delta
   **+0.0282**, paired bootstrap 95% CI **[+0.0144, +0.0424]**. The +0.02
   margin is met on the point estimate; the clause requiring arm B to exceed
   **D14's 0.7461** is not, and either failure rejects. **Stage 2 is NOT
   authorized** and needs a new proposal.

   Read the report before writing that proposal, because the verdict and the
   effect point different ways: **conditioning helped on every tier** and the
   CI excludes zero, but the CI's lower bound is below the margin, and **arm A
   — the control — is below D14 on every tier**, so arm B adds a real ~+0.03
   to a baseline that already could not reach the bar. Three candidate causes
   are recorded and none were tested: `MULTILINGUAL_CONDITIONED` admission
   refuses 7,610 lines D14 trained on (2.1%), a different seed, and a D14
   reference number computed on a different fragment population. The rule was
   deliberately not relitigated after the data came in.

   **CORRECTED RERUN, 2026-08-04** (`reports/phase4_p4f_stage1_matched.md`).
   Both arms retrained at D14's real config. `in_doc`: arm A 0.7521, arm B
   0.7594, delta **+0.0073, CI [-0.0063, +0.0196] -- includes zero**. Verdict
   still REJECTED, but the clauses swapped: margin NOT met, D14 clause now
   PASSED. **At a correct training budget the conditioning effect cannot be
   distinguished from zero.** Matched arm A (0.7521) reproduces D14 (0.7552),
   confirming the batch-size diagnosis on the falsifier's own metric and
   retiring seed as an explanation for the original gap. Stage 2 is now
   harder to justify, not easier; a future proposal should lead with seed
   variance.

8. **Later product/evaluation gates.** The real-gap pipeline and Takšan
   playground are not yet one production expert mode — this is where a cover
   page, a search front door, and a language mode selector carrying
   per-language evidence state belong; they span both prototypes and should
   follow the first specialist session (item 6), not precede it — the point of
   that session is to learn what the front door needs to do. Ixca raised all
   three on 2026-07-30 and they are deliberately parked, not forgotten.
   Protected-test/P6 runs remain one-shot and
   separately unauthorized. P7 candidate export, expert verification, and
   paper drafting come only after their standing human gates. The full
   model-ladder commitment must either be completed or explicitly amended
   before final publication claims.

Cross-line multi-sign is **not** an open implementation item: P2-E10 is a
completed negative result, and leaving it unapplied is the ratified
evidence-bounded behavior. The empty middle is **not** an open item either:
option 2 is adopted and implemented; only the copy review (item 3) remains.

## Contract question — DECIDED

`expert_decision_contract.CONTRACT_VERSION` stays **1.1.0**; making `display` a
hard renderer requirement is a **deferred major bump** (see Ratified decisions
item 7, and the note appended to `specs/EXPERT_DECISION_CONTRACT.md`
§Versioning). No longer open.

## Validation at handoff

```powershell
python -m unittest discover -s tests      # 289 pass
ruff check lib scripts tests demo         # clean
python lib/contracts.py                   # 20/20
python scripts/00_tracers.py              # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check   # exit 0
git diff --check                          # clean
```

To rebuild the review queue under the ratified `v2` policy:

```powershell
python scripts/phase4_workbench_review_export.py
# optional single-language session, e.g.:
python scripts/phase4_workbench_review_export.py --language Akk
```

The visible queue's `channels_logical_sha256` must stay `3e4e66ea…`. If it
moves without a deliberate policy change, something altered what a specialist
sees. `git_commit` and `payload_sha256` **do** move on every rebuild by design
— they record provenance, not content — so a rebuild dirties those three
tracked artifacts without meaning anything changed. Check the logical hash, not
`git status`.

The tracer suite passing after this much change is the reassurance worth
having: the plumbing that caught E2 is still live, and every rerun script
re-ran its own C1 encoding assertion on the way through.

**Both prototypes were browser-verified on 2026-07-31**
(`reports/phase5_browser_verification.md`) — a human visual check against a
supplied checklist, not an automated capture, since no browser automation tool
was available. What that check could not cover is recorded there and in open
item 1: no export/ingest was exercised, and no automated regression capture
exists for rendering.
