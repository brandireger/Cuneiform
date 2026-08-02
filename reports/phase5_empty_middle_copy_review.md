# Empty-middle branch wording — copy review

**Status: DONE 2026-08-02.** Closes handoff item 3. The four branch texts in
`lib/expert_decision_contract.py`'s `EMPTY_MIDDLE_QUERY_KINDS` were written
from the encoded evidence and reviewed as logic when the display treatment
was adopted (`reports/phase5_empty_middle_display_treatment.md`), but never
reviewed as the prose a Hittitologist will actually read cold, mid-review,
with no other context on screen.

## Method

Read all four `headline`/`detail` pairs side by side, checking for: whether
the headline's claim matches the epistemic weight of its own detail, whether
voice and register are consistent across the four branches, and whether any
terminology is used without the context needed to parse it. Cross-checked
any proposed wording against every other place it appears verbatim
(`grep`), since some of this language is quoted in three other places, not
just the live packet.

## Finding

`ILLEGIBLE_TRACE` was the only one of the four written in second person
("**your** trace is off-formula"). The other three are impersonal and
attribute the reading to the artifact, not the reader: "**the edition**
restores a sign here," "**the edition** marks a lacuna," "a genuinely
attested sign was hidden." That's not a stylistic accident — the packet is
reviewed by whichever Hittitologist is on the queue that session, who is
very often *not* the scholar who originally transcribed the trace as
illegible decades earlier. "Your trace" tells the wrong story: it reads as
the system accusing the current reviewer of a misreading they may have had
no part in making. The other three branches get this right by construction;
this one didn't.

The detail for the same branch already carries the correct, hedged framing —
"**Either** the trace is not a separate sign, **or** this manuscript carries
a variant the witnesses do not" — so the fix is narrowly the headline's
voice, not the underlying claim, which was already right.

## Fix

`your trace is off-formula` → `the trace is off-formula` — corrected in
both places the string is live rather than a historical record:

- `lib/expert_decision_contract.py`'s `EMPTY_MIDDLE_QUERY_KINDS["ILLEGIBLE_TRACE"]["headline"]`
  (what the expert actually sees).
- `scripts/real_gap_calibration.py`'s report-generating table (regenerated;
  `Phase3/real_gaps_out/real_gap_calibration_report.md` now reflects it).

**Deliberately not touched:** `reports/phase5_empty_middle_display_treatment.md`,
the historical ratification record that used the original phrase when the
treatment was adopted — changing it would rewrite what was actually said at
ratification time, the same reason the P4-D staleness stamps are never
silently dropped.

## What was checked and found already correct

- **EDITORIAL_RESTORATION**'s "two editorial judgements" framing is precise,
  not vague: it correctly treats the witness tradition itself as
  editorially-mediated transcription, not ground truth, matching this
  project's standing evidence-policy stance (`specs/EVIDENCE_POLICY.md`) —
  not a restoration-vs-truth comparison, but restoration-vs-another-edition.
- **INDETERMINATE_LACUNA**'s detail correctly separates "whether a gap
  exists" from "how long it is" — the one distinction this whole branch
  exists to make (`reports/phase5_lacuna_scope_decision.md`).
- **HIDDEN_ATTESTED_SIGN**'s "cannot be correct by construction" is exact:
  this is the only branch describing a synthetic evaluation context, not a
  real gap, and the wording doesn't let that blur.
- The em-dash, two-clause structure of `ILLEGIBLE_TRACE`'s headline (vs. the
  other three's single clause) was considered and left alone — it's carrying
  a genuine second fact (what witnesses show, and what that implies for this
  specific trace) that the other three fold into one clause because their
  significance already fits in the same breath. Forcing uniformity here
  would have cost clarity for no real gain.
- "Off-formula" was kept rather than redefined or expanded. It's established
  philological shorthand already used identically in three other places
  (the ratification report and the calibration report/generator), and this
  review's job was to fix a voice defect, not redesign settled terminology.

## Validation

```
python -m unittest discover -s tests      # 291 pass, no wording-pinned test broke
python scripts/real_gap_calibration.py    # regenerated; 46,118/43,393/577 unchanged
```
