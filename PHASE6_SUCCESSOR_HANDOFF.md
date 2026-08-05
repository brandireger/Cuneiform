# Phase 6 successor handoff — the retrieval line is closed; the specialist session is the blocker

**Handoff date:** 2026-08-04
**Branch merged to `master`:** `codex/phase5-classical-control-review`
**Protected test split: CLOSED. GPU training: unauthorized. Gate 3 Stage 2:
unauthorized.**

Read `AGENTS.md` (or `CLAUDE.md` — they are the same document for two agents,
**and they drift**; diff them before trusting either) first. It remains the
design authority.

## Start here, in this order

1. `reports/phase5_review_sequence_closeout.md` — **the one document that
   matters.** The complete arc of the corrective review's steps 1–3: what
   stands, what was withdrawn and why, and eleven methodological traps.
2. `reports/phase5_classical_control_review.md` — the corrective review that
   set the sequence. Its steps 4–6 are what remains.
3. `reports/phase5_taskb_transfer_results.md` — the authoritative Task B
   result, with three amendments recorded in its protocol.
4. `PHASE5_SUCCESSOR_HANDOFF.md` — still current for everything *before* this
   line of work (workbench, cross-line calibration, Gate 3, expert surfaces).

## Repository state at handoff

```powershell
python -m unittest discover -s tests -q          # 421 pass
ruff check lib scripts tests demo                # clean
python lib/contracts.py                          # 20/20
python scripts/00_tracers.py                     # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check # exit 0
git diff --check                                 # clean
```

The 62 remaining ruff errors under `Archive/` are the frozen Phase 1 snapshot
and must not be rewritten.

## What this line established

The full claim set is in the closeout. The three that should shape what comes
next:

- **A separately weighted sign-bigram channel materially improves retrieval**
  on both tasks — Task B cross-fitted, all three relation cells reject under
  Holm–Bonferroni.
- **It does not help the case the project exists to solve.** On joins with no
  shared lines the increment is **+0.0294, CI [−0.0645, +0.1481]**. Tier C
  retrieval is largely the editor's alignment read back: strip the shared lines
  and absolute recall@1 collapses from ~0.38 to 0.00–0.04.
- **Language restriction is an evidence-policy and coverage choice**, not an
  accuracy gain, and roughly half of what `HITTITE_ONLY` discards is lost to a
  coverage gap in our own Gate-2 dataset rather than to an affirmative
  non-Hittite classification.

## Open, in the order I would take them

1. **The first specialist session. This is the blocker, and no further
   retrieval work substitutes for it.** Review step 5 requires a specialist to
   inspect gained and lost cases **blind to method**. Everything needed exists:
   `scripts/phase4_workbench_backup.py` before and after,
   `scripts/phase4_workbench_review_export.py`,
   `demo/workbench_unresolved_prototype.html`, and
   `scripts/phase4_workbench_ingest_events.py` as the only supported ingest
   path. Still never exercised end-to-end: an actual browser JSON download and
   the verifying ingest.

2. **Freeze one configuration and analysis plan** (review step 5). The
   deployment candidate is `HITTITE_ONLY`, α_u = 0.5, pair = (0.15, 1.0). It
   **carries no dev performance claim** — every reported number is cross-fitted
   and none was computed from it. Freezing means committing the configuration,
   the metric set, and the analysis plan *before* any protected-test access.

3. **The one-shot P6 run** (review step 6). Separately gated. No method
   selection may use protected-test output.

4. **Cheap and unclaimed:** the Gate-2 coverage deficit. `LINE_NOT_IN_LANGUAGE_DATASET`
   accounts for ~1,693 of the duplicate-relation endpoints `HITTITE_ONLY`
   refuses. That is our own pipeline's gap, not the corpus's, and closing it
   would recover duplicate evidence without any modelling change.

5. **Owed but not urgent:** re-measure frozen CANINE's increment at full scale.
   Its retirement was measured over the char arm in the dev-fit/dev-index
   universe now known to be the most generous one to that comparator. Needs no
   training — frozen embeddings for 7,490 fragments.

## Standing constraints added by this line

- **Never quote +0.10 for the classical gain.** Under the declared universe it
  is ~+0.06, and the bigram channel's conditional increment is what to cite.
- **Never describe a non-significant result as null, absent, or equivalent.**
  `lib/effect_decision.practical_increment_verdict` emits the verdict and
  `DECISION_MARGIN` is encoded in the Task B script; use them rather than
  prose. `paired_final_system` carries `equivalence_established: False` by
  construction.
- **Never pool cross-line and same-line rates** (inherited), and never pool
  a stratum estimand with a pair-instance estimand — a stratum query may hit
  *any* partner, a pair instance must hit the *specific* one.
- **Geometry is not an independent stratum** on dev (horizontal ≡ tier C), and
  **site has no contrast** (all dev join queries are Hattusa), so nothing in
  this line speaks to Hattusa→provincial generalization.
- **Bin documents** never become duplicate positives or ordinary negatives; the
  physical-join exception is confined to the joins-only cell and asserted by
  check C6.
- **"Transfer"** may be used only for the specific claim that Task A's frozen
  configuration retains utility on Task B without retuning.

## Traps hit this session

The full list of eleven is in the closeout. The three most expensive:

1. **Searching weights out of fold is not cross-fitting** if you then discard
   the held-out predictions and re-score with modal weights. This invalidated a
   complete set of Holm rejections.
2. **Population selection must match the estimand.** Selecting a query-relative
   scope's population by each fragment's *own* language produced both a false
   "not evaluable" verdict and a false 12,482-relation loss figure.
3. **Non-significance is not equivalence** — re-made three times in prose
   after being corrected once. Now guarded mechanically, which is the only
   reason it will not recur.

## Community obligation created

Two `join_pairs.jsonl` rows assert that a fragment joins itself (`KUB 28.89+`,
`KBo 22.130a+`, both bin-parent and discovery-side). Worth reporting to the
TLHdig team alongside any other findings, per the standing outreach decision
that approaches them **with evidence in hand**.
