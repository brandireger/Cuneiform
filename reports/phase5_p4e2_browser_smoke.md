# Phase 5 — P4-E2 browser smoke test

**Status:** PASS after two bounded interface fixes, 2026-07-29.

This closes item 2 in `PHASE5_SUCCESSOR_HANDOFF.md`. The static workbench was
served from the repository over localhost and exercised in the Codex in-app
browser. No protected-test material was accessed. The one test judgment
existed only in browser memory: it was not downloaded, exported, ingested, or
written to the append-only annotation log.

## What passed

- The page rendered without clipping or broken layout at the browser's normal
  viewport.
- The canonical-record hash self-check reported `PASS`.
- The disclosure correctly identified the queue as a subset and every record
  as `NOT_CORPUS_TRUTH`.
- Cluster detail rendered surrounding lines, typed supporting and
  contradictory evidence, provenance, review actions, and abstention.
- Text and site filters narrowed the queue correctly; the mixed-language
  filter produced a valid empty state.
- The cross-language channel remained separate, required explicit opt-in,
  honored cancellation, and displayed its standing warning after enablement.
- A `WITHHOLD_JUDGMENT` interaction collected reviewer identity, declared
  role, and rationale, then changed the browser-only event count from 0 to 1
  and rendered `WITHHELD`.
- Reload discarded the browser-only event and restored `Export events (0)`.

## Defects found and fixed

1. The in-app browser rejects native `window.prompt()`. The original action
   flow therefore stopped before a reviewer could record any judgment. Native
   prompt, confirm, and alert calls were replaced with one in-page HTML
   `dialog` implementation.
2. The first dialog revision labelled the single-line field but not the
   multiline rationale field. Both controls now receive their accessible name
   from the shared `Response` label.

`tests/test_phase4_workbench_interface.py` now guards against reintroducing
unsupported native dialog calls, asserts the in-page dialog contract, and
pins export as an explicit local JSON download with no direct network or
ingest path.

## Deliberate bounds

- The smoke test did not download the JSON export. Browser-local event
  construction and event-count state were exercised; export-payload and ingest
  behavior remain covered by the existing Python tests.
- No human specialist assessed queue usefulness or workflow ergonomics.
- The placeholder-only and minimum-two-sign queue exclusions remain
  unratified. This test does not ratify them.
- The browser retained one console entry from the pre-fix failure at
  `2026-07-29T13:32:03.935Z`; the complete post-fix interaction added no new
  console error.

## Validation

```powershell
python -m unittest tests.test_phase4_workbench_interface  # 19 pass
python -m unittest discover -s tests                       # 215 pass
ruff check lib scripts tests demo                          # clean
python lib/contracts.py                                    # 20/20
python scripts/00_tracers.py                               # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check          # exit 0
git diff --check                                           # clean
```
