# CONTRIBUTION_LEDGER.md — Human/AI provenance record, architect session of 2026-07-21/22

Purpose: a decision-level attribution record of the collaboration
between Ixca (human researcher) and Claude (AI assistant, architect
session), prepared for transparency, posterity, and critical review.
The raw conversation transcript (exported separately; see
provenance/README) is the primary evidence; this ledger is the
reviewable index of it. Prepared by the AI at the human's request;
the human should review and correct before committing — a provenance
document is only as good as its own review.

Scope: this session only. Earlier sessions (project conception, P1–P3
specification, the original Green Stone conversation, corpus and
baseline decisions) and all Claude Code build sessions are separate
records; the git history and the "Ratified jointly" lines in every
spec extend this ledger across the whole project.

## Honest framing for the critical reviewer

Read this before the table, because it states plainly what a
skeptic will probe.

The technical drafting in this project — specifications, ML
diagnosis, design systems, prose — is overwhelmingly AI-generated.
No one should pretend otherwise, and this ledger does not. The
human contribution is of a different kind, and the record shows it
operating in four ways that gated everything else:

1. DIRECTION. Every phase of work exists because the human chose
   it, scoped it, or reprioritized it (e.g., "demo now, private
   first, public later"; "pause modeling talk, design the
   interface"; "export this for transparency").
2. RATIFICATION. Every consequential decision — branch selections,
   gate deviations, bar amendments, naming, design theses — passed
   through explicit human approval, and several specs exist ONLY
   because approval was granted after options were presented with
   trade-offs. The AI's standing instructions (set by the human,
   earlier sessions) reserve judgment calls for joint decision;
   the transcript shows that reservation honored and used.
3. GENERATIVE QUESTIONS. Several of the system's features
   originated in the human's questions, not the AI's proposals —
   see rows marked [H-origin] below. The determinative/meanings
   layer, the glyph-readability requirement, and the pipeline-wide
   assertion hardening are the clearest cases: the AI elaborated;
   the human originated.
4. STANDARDS. The project's defining epistemics — confidence
   scoring, read-everything-before-responding, measured
   attribution over narrative, pre-registration culture — were
   imposed by the human as standing requirements across sessions.
   The AI operates them; it did not choose them.

Symmetrically, the AI's failures are on this record too: two
calibration misses (the B1 scale prediction; the baseline-delta
attribution) and one mechanism theory built on inputs later shown
content-blind — each caught by the project's measurement
discipline, each acknowledged in-session. A provenance record that
only logged successes would be advertising.

## Decision ledger (this session, chronological)

Legend: [H] human, [AI] assistant, [CC] Claude Code (build
sessions, reported into this one). "Initiated" = who raised it;
"Shaped" = who developed the substance; "Decided" = who made the
call. [H-origin] marks features originating in a human question.

| # | Decision / artifact | Initiated | Shaped | Decided |
|---|---|---|---|---|
| 1 | Resume project from prior session; reconstruct state | [H] | [AI] (retrieval + synthesis) | [H] |
| 2 | Design the demo while P4 trains | [H] | [AI] proposed views/architecture | [H] |
| 3 | Glyph layer: link signs to readable cuneiform, not tablet JPGs [H-origin] | [H] | [AI] (research: Unicode, Cuneify, Ullikummi; found cu field in project's own docs) | [H] |
| 4 | Public hosting ambition + crowdsource wiki concept | [H] | [AI] (GitHub-native three-tier design; diplomacy + policy cautions) | [H] deferred public launch |
| 5 | Private-first distribution; mentor sign-off before committee | [H] | — | [H] |
| 6 | DEMO_SPEC.md (DM0–DM3, cleanroom rules, test-side exclusion) | [AI] | [AI] | [H] ratified |
| 7 | Theming/naming session convened | [H] | [AI] proposed Takšan, seal metaphor, instrument thesis, Green Stone accent | [H] approved all |
| 8 | "What should I add?" — six additions (evidence view, failure gallery, model/data cards, deep links, keyboard flow, glossary) | [H] (open question) | [AI] | [H] approved all six |
| 9 | Green Stone as icon/cornerstone; supplied own 2017 photograph | [H] | [AI] (distribution: mark/pedestal/empty-state/About; pushback on background use) | [H] |
| 10 | English/German layer question [H-origin] | [H] | [AI] (fact-check: TLHdig has no translations; 4-way decomposition; no-MT policy) | [H] ratified |
| 11 | Determinatives/"honorific" categories question [H-origin] -> entire meanings layer | [H] | [AI] (determinative categories, logogram gloss tiers, coverage metrics) | [H] ratified |
| 12 | Consolidation into single TAKSAN_DEMO_SPEC.md | [H] | [AI] | [H] |
| 13 | P4 gate verdict: criterion NOT met; no silent reinterpretation | [CC] reported | [AI] governance framing | joint |
| 14 | P4B diagnostics battery + pre-registered decision tree | [AI] | [AI]; [CC] executed | [H] ratified tree |
| 15 | DM0 bar amendment (coverage vs error) + spot-audit | [AI] | [AI]; [CC] executed | [H] ratified |
| 16 | Branch R selection (drop bi-encoder) | [CC] recommended | [AI] concurred with analysis | [H] decided |
| 17 | P5 spec (hard set, per-tier gates, ceilings, fallback clause) | [AI] | [AI] | [H] ratified |
| 18 | P5 gate failure stop; option analysis; D17c/D17b/fallback structure | [CC] stopped per rule | [AI] two-mechanism analysis (later superseded — see failures note) | [H] ratified |
| 19 | E1.3 IDF reference-set finding | [CC] measured | [CC] (both AI-named causes measured zero) | [H] ratified Option 1 |
| 20 | E2 content-blind scorer finding | [CC] found + verified | [CC] diagnosis; [AI] reinterpretation + audit/hardening plan | [H] approved |
| 21 | Pipeline-wide hardening directive ("anticipate further issues, build in assertions") [H-origin] | [H] | [AI] (contracts C1–C10, tracers T1–T5, genus analysis) | [H] |
| 22 | Provenance export + this ledger | [H] | [AI] drafted; [H] to review/correct | [H] |

## Corrections & failures on the AI side (this session)

- Predicted B1 would narrow the dense-vs-lexical gap at scale;
  measured: it widened (0.264 -> 0.412). Acknowledged in-session.
- Attributed the P4B->P5 baseline delta to two causes "almost
  certainly"; measured contribution of both: zero. A third,
  unnamed mechanism accounted for 100%. Acknowledged in-session.
- Built a two-mechanism theory (with stated confidences 75%/60%)
  of the boundary head's failure on scores later shown to be
  computed over ~83% <UNK> content-blind inputs. Theory
  superseded; lesson codified ("no mechanism story before an
  input audit").
These are retained because the project's claim to credibility is
its audit trail, not its hit rate.

## Attribution guidance for downstream use

- Paper/ALP submission: disclose AI assistance per the venue's
  current policy (check the ALP/ACL call at submission time);
  this ledger + the repo's ratification lines + the exported
  transcripts constitute the supporting record.
- Mentor review: the recommended reading order for a skeptical
  reviewer is (1) this ledger's framing section, (2) any three
  specs' "Ratified jointly" decision trails, (3) transcript
  spot-checks against ledger rows of their choosing.
- Standing practice going forward: each future session appends
  rows; exports are committed to provenance/ at phase
  boundaries; Claude Code session reports already serve as the
  build-side record.

Prepared 2026-07-22 by the AI architect session at the human's
request. UNREVIEWED BY THE HUMAN until this line is replaced with:
"Reviewed and corrected by Ixca on <date>."
