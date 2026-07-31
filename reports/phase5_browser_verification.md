# Phase 5 — browser verification of both expert prototypes

**Status:** PASS, 2026-07-31. Closes open item 1 in
`PHASE5_SUCCESSOR_HANDOFF.md`.

**Verified by:** Ixca, manually, in Chrome against a local `http.server` on
`127.0.0.1:8765` serving the repository root. **This was a human visual
check against a supplied checklist, not an automated capture** — no browser
automation tool was available in the session. There are no retained
screenshots, no DOM dumps, and no recorded console transcript; the evidence is
Ixca's confirmation that every checklist item below behaved as described.

Both pages were served over `http://127.0.0.1`, not `file://`. The workbench
self-checks its canonical SHA-256 against `lib/unresolved_evidence.py` using
`crypto.subtle`, which requires a secure context; on `file://` that check
fails and the page disables export.

Serving preconditions were confirmed before the check: both pages and all four
generated data files returned HTTP 200 at full byte count
(`workbench_review_queue.js` 2,055,467 bytes;
`missing_text_demo_data.js` 257,258 bytes).

## Why this was needed

Both prototypes changed on 2026-07-30 and neither had been rendered since:

- `demo/workbench_unresolved_prototype.html` passed a smoke test on
  2026-07-29 (`reports/phase5_p4e2_browser_smoke.md`), but the readability
  pass then rewrote its header, sidebar, banner, evidence card, action area,
  and footer.
- `demo/taksan_missing_text_prototype.html` had **never** had a recorded
  browser smoke test, and the empty-middle treatment changed its option card,
  preview dropdown, and select button.

The prior sessions could verify that the scripts parsed (esprima) and that the
markup nested correctly, but not that anything rendered. Two specific risks
motivated the check: the `data-damage` attribute selectors could apply to
nothing silently, and an empty-middle option could still show a percentage.

## Workbench — what passed

1. **Hash self-check reports PASS.** Without this nothing below is
   trustworthy, so it gates the rest.
2. **The subset headline is visible without interaction.** "This is a subset,
   not the corpus" sits outside its disclosure; "What was held out, and why"
   expands below it. This is standing display rule 5 surviving the move to
   progressive disclosure.
3. **The damage-state overlay applies.** Switching *Colour by damage state* →
   *Attested vs. not attested* → *Plain text* restyles the transliteration and
   swaps the legend each time. This was the highest-risk item: the
   `body[data-damage="…"]` selectors could have matched nothing and failed
   invisibly.
4. **Actions render as three labelled groups**, not one flat row of seven, and
   each button exposes a tooltip stating what it records.
5. **The footer quarantine statement is visible**, with provenance collapsed
   below it.
6. **A `WITHHOLD_JUDGMENT` interaction completes** through the in-page dialog
   (not a native popup), collecting reviewer identity, role, and rationale,
   moving the export counter 0 → 1; **reload discards it back to 0**.

## Takšan — what passed

7. **Empty-middle options render as contradictory evidence.** On the
   empty-middle packets (`p2e4-009`, `p2e4-011`, `p2e6-002` — the last at rank
   1 on 19 independent witness families) the card shows `(no sign)`, the
   **NOT A READING** tag, the warning border, and the two-part branch
   explanation.
8. **No percentage appears beside an empty middle.** The audit box renders as
   unavailable under "No rank track record applies here". This is the defect
   the whole treatment exists to remove.
9. **The preview dropdown reads** `(no sign — contradicts the markup, not a
   reading)`.
10. **The select button reads** "Record that no sign stood here (disputes the
    markup)", not "Select this option".
11. **Ordinary options are untouched** in the same packets: signs shown,
    percentage present, normal button label.

## Deliberate bounds — what this did NOT verify

- **No export file was downloaded and no ingest was exercised.** The
  workbench's browser-local event construction was exercised and discarded on
  reload. `phase4_workbench_ingest_events.py`'s verification and refusal paths
  remain covered by the existing Python tests only. The annotation event log
  is still empty and `Phase4/phase4_out/annotation_backups/` still does not
  exist.
- **No expert judgment was recorded, exported, or ingested.** Nothing left
  browser memory.
- **No specialist assessed usefulness or wording.** In particular the four
  empty-middle branch texts are the sentences a Hittitologist will actually
  read; they have been verified to *render*, not reviewed as philological
  prose. That remains open.
- **The two P4-E2 queue exclusions remain unratified.** Rendering the queue
  does not ratify what is in it.
- **No automated regression capture exists.** A future markup change could
  break rendering again without any test catching it. The string-level
  contracts in `tests/test_phase4_workbench_interface.py` and
  `tests/test_taksan_empty_middle_render.py` pin the display *contract* — that
  the required wording and hooks are present — but they cannot observe a CSS
  selector matching nothing. That is the residual gap, and it is the same
  class of gap that made this manual check necessary.

## Reproducing

```powershell
python -m http.server 8765 --bind 127.0.0.1     # from the repository root
```

- http://127.0.0.1:8765/demo/workbench_unresolved_prototype.html
- http://127.0.0.1:8765/demo/taksan_missing_text_prototype.html

Use `127.0.0.1`, not `file://`.
