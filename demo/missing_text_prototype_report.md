# Missing-text expert UI — small prototype report

Built 2026-07-24. Scope decided jointly with Ixca: a small prototype against
`specs/EXPERT_DECISION_CONTRACT.md` (Phase 2's actual recommended next step),
not TAKSAN_DEMO_SPEC.md's join workbench (a different, pre-Phase-2-pivot
product — see the scope note at the top of `dm1_missing_text_export.py`).

**Revision (same day):** moved from the 4 hand-curated example packets to
**all 28 real packets** already produced by the P2-E4 and P2-E6 probes (16
single-sign + 12 multi-sign), per Ixca's request to test the UI on the real
dataset rather than a hand-picked sample.

## What this is

Two files:

- `dm1_missing_text_export.py` — reads every packet from
  `Phase2/phase2_out/p2e4_candidate_set_packets.jsonl` (16) and
  `p2e6_multisign_packets.jsonl` (12), adapts each through
  `lib/expert_decision_contract.py`'s `adapt_p2e4_packet()`/
  `adapt_p2e6_packet()` — the same functions `scripts/p2e7_contract_check.py`
  used for its 4 curated examples — which strip hidden evaluation gold
  (the raw source's `outcome`, top-level `evidence`/`support`/
  `contradictions`/`observable_*` fields are never read) and run
  `validate_suggestion_packet()`. It then cross-checks every packet's
  fragment_id against `Phase1_pipeline/p2_out/splits.parquet`'s frozen
  `main_split` column and hard-aborts if anything resolves to other than
  `dev` — stronger than the check the original P2-E7 script performs.
  Emits `dm_out/missing_text_demo_data.js` (213.5 KB, well inside any
  reasonable size budget) + `dm_out/missing_text_demo_data_report.md`.
- `taksan_missing_text_prototype.html` — single self-contained page (vanilla
  JS, inline CSS, zero network calls, opens from `file://`). Renders each
  packet's query context, ranked options (or the abstention banner), group
  audit rates with the mandated "not a probability" labeling, witness
  support, collapsed-tail disclosure, limitations, and assistance profile.
  Offers exactly the four contract actions, filtered per-packet to
  `workflow.allowed_actions`. A sidebar filter (fragment/mode/status text
  match) was added once the packet count grew past the point a flat list
  stays easy to scan.

Of the 28: 16 single-sign / 12 multi-sign; 24 present-candidates / 4 abstain;
3 carry a collapsed tail (largest: 12 of 48 options shown, 36 collapsed).

**Revision 2 (same day):** added a full-fragment context panel, per Ixca's
request to see the entire tablet a missing-text location was drawn from, not
just its two-token window — plus CTH composition titles and determinative
categories. Scope decided jointly with Ixca (AskUserQuestion): **deterministic
glosses only, no machine translation of Hittite text.** CLAUDE.md rules
machine translation out of scope specifically for hallucination risk, and
that risk is exactly what a mentor-facing, evidence-bounded demo cannot
afford. What was added:

- `dm1_missing_text_export.py` now also emits `dm_out/fragment_context_data.js`
  (1.9 MB): the complete line-by-line transliteration, in document order, for
  all 18 fragments the 28 packets reference — read directly from
  `Phase1_pipeline/p2_out/corpus.parquet`, with per-sign damage states
  (attested/restored/laes/illegible).
- CTH composition titles, read from the already-fetched
  `Archive/p25_out/cth_titles.csv` catalogue snapshot (CATALOG_METADATA —
  a real published catalogue entry, not a translation of the tablet's text).
  All 18 fragments' titles were found.
- Determinative categories (e.g. "URU" = city, "D" = deity name) for words
  whose leading sign matches CLAUDE.md's own already-vetted starting
  inventory — corrected to the corpus's real Unicode encoding (Ḫ, subscript
  digits) rather than the plain-ASCII spelling CLAUDE.md's prose happened to
  use, which is why a naive first attempt matched 0/696 words before I found
  and fixed the encoding mismatch (see below). Real census over the 18
  fragments: **499/696 (71.7%)** of determinative-marked words matched the
  vetted list; the remaining 197 are labeled "uncategorized" in the UI
  rather than guessed (they're real categories — MUNUS "woman", M/F
  personal-name markers, KAM ordinal markers, ḪI.A/MEŠ plural markers — just
  outside the small list CLAUDE.md happened to name; extending that list is
  a deliberate follow-up decision, not something this export makes on its
  own).
- Sumerogram (logogram) words are tagged as such — a structural fact from
  the corpus's own `is_sum` flag — with **no English gloss attached**. A real
  gloss needs a citable reference (CHD/HZL); I don't have one available, and
  guessing would be exactly the fabrication this project exists to avoid.
- The panel highlights the correct **line** for a packet's query location
  (`line_index_in_doc` is a direct, unambiguous match against the same
  corpus column) but deliberately does **not** highlight the exact sign
  within that line. Chasing that down properly, I found the packet's
  `sign_offset_in_line` indexes into a *third* token stream —
  `Phase1_pipeline/p4_out/decomposed_corpus.parquet`, which splits
  determinative-prefixed compounds like `URUiš` into `URU`+`iš` and excludes
  restored signs via `lib/hittite_tokenizer.encode_fragment_window` — not
  the per-word `signs` column this panel renders from. I verified this by
  reproducing the packet's own `left_context`/`right_context` tokens exactly
  from the decomposed stream (`['URU','iš']` ... `['ḫa','ra']`, gap = `'da'`,
  a genuinely attested sign), so the offset semantics are now understood and
  correct — but reconciling that stream back to this panel's word-grouped
  display needs the same determinative-splitting function the decomposed
  corpus was built with, which I hadn't fully traced. Given CLAUDE.md's own
  scar tissue here (the prior "E2" bug came from exactly this class of
  hand-rolled tokenization mismatch), shipping a wrong-but-confident sign
  highlight seemed worse than shipping none. The line highlight plus the
  existing left/right context tokens (already rendered above the fragment
  panel) let a reviewer locate the gap by eye. A future pass should resolve
  this properly rather than reattempt it ad hoc.
  **Resolved in Revision 3 below** — fixed at the source
  (`lib/decompose_corpus.py`), not reattempted ad hoc.

To regenerate the data and open the app:

```
python demo/dm1_missing_text_export.py
```

then open `demo/taksan_missing_text_prototype.html` directly in a browser
(no server needed).

## Why this can be trusted, not just eyeballed

I don't have a browser available in the environment I built this in, so I
verified it with headless Chrome (`chrome.exe --headless=new --dump-dom`)
instead of assuming the JS is correct:

1. **Hash self-check.** The page computes SHA-256 over a fixed test object
   using its own client-side canonical-JSON + `crypto.subtle` implementation
   and compares it to a hash precomputed with the real
   `lib/expert_decision_contract.canonical_sha256()`. It matched exactly —
   confirmed live in headless Chrome (`Hash self-check: PASS`), not just
   read from the source.
2. **Real-packet hash agreement.** Separately, the export script's Python
   run and the browser's independent JS computation produced the *same*
   64-character SHA-256 for the real `p2e7-example-single-sign` packet
   (`d824336d...4af8`) without either seeing the other's output.
3. **End-to-end validator round-trips, on the real dataset.** I scripted
   headless runs that click through actual UI paths against real P2-E4/
   P2-E6 packets — `SELECT_OPTION` on a single-sign packet, `REJECT_ALL` on
   a multi-sign packet with a collapsed tail (`p2e6-002`, 12/48), and
   `OTHER_OR_UNSUPPORTED` with a proposed sign sequence on a real abstention
   packet (`p2e6-001`) — captured the exact decision JSON each produced,
   and fed each one, unmodified, into the real, unaltered
   `lib.expert_decision_contract.validate_expert_decision()`. All passed.
   This is the strongest evidence available short of a live multi-user
   session: browser-generated decisions against real dev-set packets
   survive the same validator the rest of the project trusts.
4. All 28 packets render without error in headless Chrome (28/28 nav items,
   filter narrows correctly — e.g. filtering "abstain" returns exactly the
   4 abstention packets). Spot-checked against source JSON: abstention
   packets show only `OTHER_OR_UNSUPPORTED`/`WITHHOLD_JUDGMENT`; the
   12-of-48 packet shows the exact disclosure sentence; empty-`signs`
   options render as "a witnessed omission," not an error.
5. No console errors in any headless run (checked stderr for
   error/exception/uncaught — none found).
6. **Fragment panel spot-checked against source data.** For `KBo 14.11`
   (packet `p2e4-001`), confirmed in the rendered DOM: CTH title
   "Šuppiluliumas Mannestaten" present, all 15 lines of the fragment
   rendered, damage-state classes (`attested`/`restored`/`laes`) match
   `corpus.parquet`'s own per-sign `sign_damage_states`, determinative
   badges match the census (e.g. "URUal-mi-na-an" → `det: city`), Sumerogram
   badges appear with no attached gloss, and the target line (`obv. 14′`)
   is the one highlighted — verified independently by reproducing the
   packet's exact `left_context`/`right_context`/masked-sign tokens from
   `decomposed_corpus.parquet` and confirming they land inside that same
   line. Re-ran the full decision-recording test harness (select, reject,
   other, withhold across multiple packets) with the fragment panel present
   — still 0 failed contract checks, no console errors.

What headless `--dump-dom` cannot verify: real mouse/keyboard interaction
timing, visual layout/contrast, or multi-session behavior. Those need an
actual person opening the file in a real browser.

## Deliberately deferred (small-prototype scope, not oversights)

Per the "small prototype" scope decision, this intentionally does **not**
implement:

- dual light/dark theme toggle, custom fonts, or the motion design in
  `specs/TAKSAN_DEMO_SPEC.md` §3 (that spec is for a different, join-centric
  product anyway — see the scope note);
- `localStorage` persistence across sessions or an import/merge flow for a
  colleague's exported decisions (decisions live only in the current page
  session; "Export decisions" downloads them as JSON);
- keyboard-only review flow (j/k/s/a/u bindings) or deep-linkable URL state;
- accessibility contrast/keyboard audits;
- the full 5,486-context P2-E4 dev audit population — this build uses all
  28 packets the probes already *exported* to `Phase2/phase2_out/`, not a
  fresh bulk export from the underlying dev audit run. Scaling further
  would mean changing `scripts/p2e4_candidate_set_audit.py` itself to emit
  more packets, which is a probe-script change, not a demo change.

None of these are hard — they're the natural next increments once the
interaction pattern itself has been validated with a real expert.

## Revision 3 (2026-07-25): exact gap alignment, candidate preview, restoration workspace

Three changes, requested together: fix the sign-alignment problem from
Revision 2's report, add a top-options preview with confidence intervals,
and add a way to track a researcher's provisional selections across a
whole fragment.

### The alignment fix, at the source

Revision 2 deliberately stopped at line-level highlighting because a
packet's `sign_offset_in_line` indexes into
`Phase1_pipeline/p4_out/decomposed_corpus.parquet` — a stream that splits
determinative-prefixed compounds (`URUiš` → `URU`+`iš`) and excludes
restored signs — while the fragment panel renders from
`Phase1_pipeline/p2_out/corpus.parquet`'s word grouping. There was no
shared key between the two tables to translate one into the other.

Traced the root cause into `lib/decompose_corpus.py::decompose_document()`:
it already knows which word each token came from (each word's tokens are
produced together inside one `flush_word()` call, triggered per `<w>`
element) — that information was just never written out.
`build_decomposed_cache()` only kept `word_pos`, a flat per-line sign
counter, not a word index.

Fix: added a `word_index_in_line` counter to `decompose_document()` —
increments on every `<w>` start, resets on every `<lb>` — verified against
`Archive/scripts/02_parse.py` to hit the identical events in the identical
order, so it lands on the exact same numbering `corpus.parquet`'s own
`word_index_in_line` already uses. Threaded it through
`build_decomposed_cache()` as a new column. `<PAR>` (paragraph-separator)
tokens get `word_index_in_line = null`, since 02_parse.py's own counter is
likewise untouched by `<parsep>`.

Rebuilt `Phase1_pipeline/p4_out/decomposed_corpus.parquet` (the old file
was moved aside, not deleted, until the rebuild was verified). Token count
matched the old file exactly (3,204,303 — same content, only the new
column added); parse-error count (229) matches CLAUDE.md's documented
figure exactly.

**Verification, not assumption:** `dm1_missing_text_export.py` now computes
each packet's exact gap location and checks it two ways before trusting it:
1. Re-derives the restored/SPECIALS-filtered stream itself, then asserts
   it matches `lib/hittite_tokenizer.encode_fragment_window()`'s real
   output token-for-token — catches drift from the canonical filter rather
   than trusting a second implementation of it.
2. Reconstructs `left_context`/`right_context` from that stream at the
   packet's own offset and asserts they match the packet's own (separately,
   probe-computed) context fields exactly.

A packet is only included in `gap_locations_data.js` if both checks pass;
**28/28 did**. Spot-checked `p2e4-001` (`KBo 14.11`) by hand: the fix
correctly identifies word_index_in_line=5 (`URUiš-da-ḫa-ra`), with only
`da` (the one masked sign, damage state `laes`) marked as the gap — exactly
matching independent manual analysis done before the fix existed.

The fragment panel now renders the gap-touched word from these exact
decomposed tokens (not `corpus.parquet`'s coarser merged signs), with the
non-gap tokens shown normally and the exact gap tokens outlined —
precise, sign-level, not word-level or line-level.

### Top-candidates preview dropdown

Above the candidate cards (unchanged, still the full disclosed list), a
dropdown lists up to the top 5 ranked options, each labeled with its
signs and confidence interval (e.g. "#1 ta — 90.9% [90.0%–91.6%],
n=5214"; "no group audit rate" where `option_audit.kind` is
`UNAVAILABLE`). Selecting one immediately splices that option's signs into
the fragment panel's gap — dashed border, labeled "previewing" — without
recording anything. This is a "what if" tool; committing to an actual,
tracked decision still requires the existing action buttons. If more than
5 options exist, a note says how many more are available as cards below
(the dropdown narrows access, it never hides anything the packet already
discloses).

### Restoration workspace

The fragment panel now has a mode toggle: **Encoded text** (default — the
as-transcribed corpus content, gap outlined but unfilled) and **My
restoration (provisional)**. Deliberately reuses the *existing* decision
log as its only data source rather than adding parallel state — no new
place for "what did I choose" to live or drift out of sync with the
already-exportable record:

- `SELECT_OPTION` → splices the selected option's signs into that gap.
- `OTHER_OR_UNSUPPORTED` with a proposed sequence → splices that text.
- `REJECT_ALL`, `WITHHOLD_JUDGMENT`, or `OTHER_OR_UNSUPPORTED` with no
  proposed text → gap stays open (there is no replacement to show).
- If a packet has more than one recorded decision this session, the
  latest one wins (matches "I changed my mind" naturally).

Restoration mode covers **every gap in the current fragment**, not just
the currently-selected packet — a fragment with multiple gap packets
(e.g. `CHDS 3.71` has three: `p2e6-001`, `-002`, `-005`) shows all of
them filled in together, so the effect on the fragment "as a whole" is
visible in one place. A persistent banner states the count ("N of M gaps
have a recorded selection") and the same language used throughout the
contract work: **"quarantined expert judgments, not corpus truth or an
official restoration, never auto-promoted."** This is not new wording
invented for this view — it's the same status every recorded decision
already carries (`QUARANTINED_EXPERT_JUDGMENT`, `requires_adjudication`).

**Verified in headless Chrome, not just visually:** scripted a run that
previews an option (confirmed the dashed preview renders), records a
`SELECT_OPTION` decision on one packet and an `OTHER_OR_UNSUPPORTED` with
custom signs on a second packet in the *same* fragment, switches to
restoration mode, and confirms both inserts render correctly with the
right labels and the right banner count. Both decisions — captured
verbatim from the browser — were then fed into the real, unmodified
`lib.expert_decision_contract.validate_expert_decision()` and passed.
Reviewer name/role now persist across the full re-render a decision
triggers (previously would have been silently cleared, since recording a
decision now re-renders the whole panel so restoration mode can pick it
up immediately). Zero failed contract checks, zero console errors, full
88-test Python suite still green.

## Revision 4 (2026-07-25): fixed duplicate insertion across multi-word gaps

Bug reported by Ixca: selecting an option for a gap that spans more than
one word (5 of the 28 packets: `p2e6-001/003/006/009/011`, spanning 2-3
words each) rendered the FULL selected text at *every* touched word — e.g.
previewing a 2-sign option on `p2e6-003` (gap spans "NAM-**RA**" and
"**GU₄**", two separate words) showed "RA GU₄" once at the first word and
"RA GU₄" *again* at the second, instead of the option appearing once.

Root cause: `buildGapOverrides()` attached the same override object to
every word `TAKSAN_GAP_LOCATIONS` listed for a packet, and
`renderGapWord()` rendered whatever override it was given, with no
awareness that multiple words could share one override.

Fix: a gap spanning multiple words now renders its replacement once, at
the first (leftmost) touched word; the other touched word(s) simply lose
their gap tokens rather than each repeating the full text. This isn't a
per-word split (e.g. "RA" at word one, "GU₄" at word two) because the
contract explicitly allows a witnessed alternative's sign count to differ
from the span it replaces (`option-001` on this same packet has 5 signs
for a 2-position gap) — there's no general 1:1 mapping between original
gap positions and a candidate's own signs, so distributing them position-
by-position would be a guess `option-001` immediately falsifies. Showing
the whole alternative once, where the gap begins, is the only place this
representation makes it possible to show accurately.

Verified in headless Chrome: previewing on `p2e6-003` and `p2e6-011`
(2-word and 3-word gaps) now shows exactly one insert per gap, not one per
word; the *non*-override (default, nothing chosen yet) rendering still
shows each word's real encoded content separately, since nothing about
displaying actual corpus content was ever wrong — only replacing it
needed the fix. Re-confirmed the single-word case and the full decision-
recording/validator round-trip still pass with zero regressions.

**Follow-up same day:** Ixca reported the fragment showing a selection
without touching the dropdown, and the dropdown not offering it as a
choice. Confirmed via headless Chrome that a genuinely fresh load has
zero insertions and the dropdown defaults to "No preview" — the behavior
was almost certainly session state (a recorded decision plus the "My
restoration" toggle) persisting in an already-open browser tab across
several rounds of file edits, since Chrome reuses an open tab for a
`file://` URL rather than hard-reloading it. Separately, found and fixed a
real disconnect either way: the preview dropdown stayed active-looking in
restoration mode even though it has no effect there (restoration mode is
driven by recorded decisions, not the live preview) — it now replaces
itself with an explanation and a "Switch to Encoded text" button in that
mode, verified in headless Chrome (dropdown absent + switch button present
in restoration mode; dropdown reappears and the decision-driven insert
disappears after switching).

**Second follow-up same day:** Ixca reported that selecting a packet from
the sidebar immediately showed a sign in the fragment even with the
dropdown at "No preview," and that the shown sign wasn't one of the
dropdown's own choices. Checked the actual data before touching any code:
in **18 of the 28 packets**, the fragment's own actually-encoded content at
the gap does not match *any* candidate option (e.g. `p2e4-001`'s fragment
has `da` recorded there; the top candidate proposes `ta`). That's not a
bug — it's the real thing these probes measure: independent witnesses
often propose a different reading than what a specific fragment itself
shows. What *was* wrong: the box showing that real content
(`.fp-gap-target`) used the same accent-colored, bordered styling as an
actual selection (`.fp-gap-insert`), and its explanation was tooltip-only
(invisible without hovering) — so it looked exactly like an unexplained,
unreachable selection. Fixed: `.fp-gap-target` is now neutral/muted
(dotted gray border, no accent fill) rather than accent-colored, and
carries an always-visible inline label ("as encoded — not a candidate"),
not just a hover tooltip; the panel's explanatory text now states the
distinction up front rather than leaving it to be inferred.

## Revision 5 (2026-07-25): library landing page + explicit training-mode framing

Prompted by Ixca's own reframing of the use case: the mentor-facing
product is choosing a real tablet and filling real gaps; the 28 packets
built so far are training/calibration data (artificially-hidden attested
signs, not real damage — see Revision 4's follow-up above), useful for a
separate playground/validation purpose but never to be shown as if it
were live restoration work. Scoped this session to the two pieces that
don't require new pipeline engineering (a real-gaps production mode is
its own future phase — see the conversation's design discussion);
building those two now:

**Library landing page.** New default view: an 18-tablet grid (`doc_id`,
CTH number + German title, site, line count, gap count), sourced from
`TAKSAN_FRAGMENT_CONTEXT` + `PACKETS` — no new data export needed.
Searchable by docID/CTH/site. Organized into three sections — Restored
shelf / In progress / Not started — computed from `sessionDecisions`, not
guessed. Clicking a card opens that tablet's workspace (the existing
fragment-panel UI), now correctly scoped to *that tablet's* gaps only
(the sidebar previously listed all 28 packets globally regardless of
fragment).

**Restored shelf.** A tablet moves to the shelf only on an explicit
"Move to restored shelf" click — never automatically (not even when every
gap has a decision), consistent with the project's standing rule that
state changes are a human action, never inferred. Explicitly **does not**
implement the "algorithm re-scores the restoration" half of Ixca's
request — that requires the real-gaps production pipeline (an infilled
gap becoming usable context for a neighboring gap's own witness lookup)
which doesn't exist yet; the shelf here is organizational only, and says
so nowhere implicitly.

**Explicit training-mode framing**, added in three places so it can't be
missed: a persistent header badge ("TRAINING PLAYGROUND — CALIBRATION
DATA"), a library intro paragraph stating plainly that these are
artificially-hidden attested signs and that real damage is a separate,
unbuilt phase, and the header subtitle reflecting current view/tablet.

Verified in headless Chrome: fresh load shows the library (not the old
flat packet list); opening a tablet correctly scopes the sidebar (e.g.
"3 of 3 gaps in CHDS 3.71", not "28"); recording a decision updates the
shelf-progress counter live; shelving a tablet and returning to the
library shows it under "Restored shelf" with the right card count; the
header home button and the in-workspace "← Library" button both return
correctly. Zero console errors, zero failed contract checks, full
88-test Python suite still green.

## Revision 6 (2026-07-25): clarified witness-support vs. track-record

Ixca flagged a real, concrete confusion in `p2e4-013`: rank 1 (`A-BI-A`,
3 witness families) shows a 90.9% track-record; rank 2 (`A`, 1 witness
family) shows 9.2% — and the fragment's own actual encoded content is
`A`, the low-percentage, weakly-witnessed option. Checked this wasn't a
one-off: the same pattern (rank 1 heavily witnessed and high-percentage,
rank 2 lightly witnessed and low-percentage, truth matching rank 2 in
every case) recurs across all six two-option single-sign packets. Not a
bug — witness count sets the *rank* (more independent agreement genuinely
is stronger evidence), while the percentage is a *calibration* statistic
about how often that rank position has been right historically, over many
different queries. The two numbers are unrelated in a way the UI didn't
make clear.

Fixed:
- The rate box now leads with natural-frequency phrasing ("In about 91 of
  100 similar past comparisons...") instead of a bare percentage + CI —
  reusing the exact house style `specs/TAKSAN_DEMO_SPEC.md`'s Honesty
  Panel copy standard already established ("...ranks the true partner
  first about N times"), not a new convention.
- For `OPTION_RANK`-scoped rates specifically, an explicit sentence now
  states the rate describes the rank position, not this candidate, and
  that a well-witnessed candidate can still be the exception.
- A one-time explainer appears above any packet with more than one
  option, stating plainly that witness support and track-record are
  different kinds of number.
- Option cards now separate "Witness support (evidence, not a rate)" from
  "Track record of this rank (calibration, not evidence)" with distinct
  labels.

Also addressed: "options should feel like choosing something." Cards are
now clickable anywhere (not just a small button) to preview that option
in the fragment panel, with a visible highlighted/previewed state — verified
in headless Chrome that clicking the second of two option cards sets the
preview correctly and doesn't also fire the card's own "Select" button
(guarded against event-bubbling). `Reject all` / `Withhold judgment` /
`Other or unsupported` are no longer a bare button row after the reviewer
fields — each now has a one-line description framing it as an equally
legitimate decision, not a fallback for when there's nothing to pick.
Deliberately did **not** fabricate additional candidate options where the
data has none — for genuinely single-witnessed positions, the honest
choice set is "this one reading, or reject/withhold/propose your own,"
and no invented alternative changes that.

## Revision 7 (2026-07-25): library search fixes

Ixca couldn't find `p2e4-013` via the library search, and had no way to
recover from a search with no results. Both real gaps:

- Search only matched a tablet's own `docId`/CTH/site — a packet ID like
  `p2e4-013` (the exact thing referenced two turns earlier in this
  conversation) matched nothing, since packet IDs weren't in the search
  haystack at all. Fixed: search now also matches every packet_id a
  tablet contains, so searching `p2e4-013` finds `KBo 5.6` directly.
- No way to get back to the full list after a search matched nothing —
  the empty-state message had no action, and there was no persistent
  clear control on the search box itself. Fixed: a "Clear" button next
  to the input (disabled when the box is already empty), a "Show all
  tablets" button inside the empty-state message itself, and Escape
  clears the field — three ways back, verified working independently in
  headless Chrome (search "p2e4-013" → exactly one tablet, `KBo 5.6`;
  search garbage → empty state with clear button → clicking it restores
  all 18; the persistent Clear button and Escape key both do the same).

## Honest limitation

Everything above proves the *mechanism* is correct (hashing, schema
compliance, action gating). It does not establish that a trained
Hittitologist finds the interaction usable or the evidence legible — that
question, per `PHASE2_CLOSEOUT.md`'s own framing, can only be answered by
putting this in front of one.

And per Revision 5: this is still a training/calibration playground, not
yet the product. The real-gaps production pipeline — finding genuine
`restored`/`illegible` spans, querying the existing witness index for
them, applying already-calibrated group-audit rates prospectively — is
the acknowledged, scoped, not-yet-built next phase everything else here
is a shell for.
