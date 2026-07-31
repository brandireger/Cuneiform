# Phase 5 — workbench readability pass and single-language sessions

**Status:** implemented 2026-07-30. **Not browser-verified** — see "What is
not verified". This is the first of the three UI items in
`PHASE5_SUCCESSOR_HANDOFF.md`'s open list; it deliberately does **not**
touch the two unratified queue exclusions or build a unified front door.

## Why these two, and why now

Handoff item 5 is the first real specialist session. A Hittitologist's time
is the scarcest input this project has, and
`reports/phase4_p4e2_expert_interface.md` recorded plainly that no specialist
usability review had occurred and that the form was "still a sequential
prototype". Two problems were fixable without waiting on any ratification:

1. **The interface did not signal what a click would do.** Seven equal-weight
   buttons in a flat grid, no titles, no grouping.
2. **A single-language session was not actually reachable.** The browser has
   an "Effective language" filter, but it narrows a queue that was already
   selected — and the export had no language argument. The default queue's
   queued members were **328 Hittite of 399** (Akk 17, Hur 29, Hat 13, Luw 8,
   Pal 3, Sum 1). Asking to "work on Luwian" got you eight occurrences
   scattered through a Hittite queue.

Deliberately **not** done here: the queue redesign (blocked on ratifying the
placeholder-only and minimum-two-sign exclusions — they decide queue
*content*, and designing around content that may change is wasted work), and
the cover page / search / unified front door, which is handoff item 7's "one
production expert mode" spanning both this page and the Takšan prototype.

## 1. `--language` on the review export

`scripts/phase4_workbench_review_export.py --language Akk` (repeatable, or
comma-separated) restricts the queue to clusters declaring that language.

**It is a declared, counted stage, not a quiet filter.** Language selection
runs after the contentless and minimum-length exclusions and is counted
separately, so the screen can say which exclusion removed what:
`excluded_off_language`, `excluded_off_language_occurrences`, and
`contentful_before_language_selection` join the existing per-channel counts.

**It fails closed on an unknown code.** `--language Akkadian`, `--language
akk`, and `--language AKK` all exit with the ratified code list rather than
building an empty queue. A silently empty session is indistinguishable from
"this language has no unresolved material", which is a different and much
more interesting claim.

**Language comes from the proposal, not from a re-derivation.** The test reads
`supporting_evidence[].languages` — what the clustering run declared under its
validated `language_scope`. Recomputing it here would be a second
implementation of a selection the ratified artifact already made, which is how
E2 happened.

**The selection means different things per channel, by construction**, and the
manifest and report both say so:

- `SAME_LANGUAGE_AS_QUERY` clusters are single-language, so a selection yields
  clusters **wholly** in that language.
- `CROSS_LANGUAGE_PARALLEL` clusters span languages, so a selection yields
  clusters that **involve** it. Their other members are in other languages by
  design — that is the channel working, not a leak. `queued_member_language_counts`
  is now also reported per channel, because the pooled tally made a correct
  Akkadian cross-language session look contaminated.

### What a single-language session could contain

Contentful clusters per language, before any selection — the ceiling:

| channel | `Hit` | `Hur` | `Akk` | `Hat` | `Luw` | `Sum` | `Pal` | `<UNRESOLVED>` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `SAME_LANGUAGE_AS_QUERY` | 2,621 | 129 | 65 | 58 | 15 | 6 | 1 | 2 |
| `CROSS_LANGUAGE_PARALLEL` | 665 | 372 | 209 | 206 | 81 | 13 | 26 | 5 |

Underlying corpus mass (train+dev, non-bin, lexical tokens), for the record:

| lang | tokens | docs | real CTHs | lines | unresolved occ. |
|---|---:|---:|---:|---:|---:|
| Hit | 2,541,890 | 6,146 | 428 | 162,315 | 210,615 |
| Hur | 129,846 | 723 | 47 | 8,897 | 11,339 |
| Akk | 113,374 | 374 | 103 | 8,711 | 8,816 |
| Hat | 41,646 | 320 | 52 | 3,524 | 4,764 |
| Luw | 23,050 | 121 | 19 | 1,537 | 1,769 |
| Sum | 5,893 | 80 | 32 | 1,007 | 1,000 |
| Pal | 4,884 | 10 | **3** | 290 | 367 |

**A single-language queue is a review surface, not a prediction surface**, and
the page now says so. No per-language calibration exists for any language.
Palaic has three real compositions, so it cannot support composition-level
folds at all; `Sum` and `Luw` are in the same regime that manufactured P2-E9's
12.8-point phantom transfer gap on 55 dev-only spans. Whether `Hur`/`Akk`/`Hat`
can carry their own calibration is a separate, separately gated research
question — each would need its own ratified target, because pooling languages
is the same error as pooling cross-line with same-line, one level up.

## 2. Readability pass on the interface

**Actions grouped by what the click records.** Three labelled groups replace
the flat seven-button grid: *Record a claim about this occurrence* (the four
`PROPOSE_*` actions), *Correct this grouping* (`REMOVE_FROM_CLUSTER`,
`REJECT_HYPOTHESIS`), and *Assert nothing* (`WITHHOLD_JUDGMENT`). Every button
carries a `title` stating what it records. Split/merge got the same treatment
as *Correct this cluster as a whole*. Abstention is now visibly its own
category rather than the seventh button in a row.

**Mandated disclosures moved, not deleted.** This is the part worth being
careful about: the verbosity is contractual, not sloppy. Standing display
rules 2–5 and CLAUDE.md's output contract require those statements. So:

| statement | before | after |
|---|---|---|
| "not a probability or a confidence score" | repeated under every evidence item | stated once per evidence section, still adjacent to the counts |
| "absence of a recorded objection…" | inline | unchanged, inline |
| subset headline + full exclusion accounting | one dense paragraph | headline stays visible; itemised accounting behind a disclosure |
| `NOT_CORPUS_TRUTH` / quarantine statement | buried in a footer provenance blob | hoisted above the blob, always visible |
| provenance, hashes, ranking, queue parameters | always-on footer wall | behind a disclosure, no field dropped |

Nine tests in a new `TestBrowserDisclosureContract` pin this, including
ordering assertions that the subset headline and the quarantine statement
appear *before* their disclosures. Collapsing a required statement is a
presentation change; deleting one is a contract breach; in a diff of a
900-line HTML file the two look identical.

**Damage-state overlay with a legend.** A `Sign display` selector offers
*Colour by damage state* (the existing four-state colouring, now with a
legend), *Attested vs. not attested*, and *Plain text*. The middle mode
collapses the four states to the one distinction cleanroom rule 6 turns on —
was this sign on the clay, or not — and de-emphasises everything that was not.
Display only: damage state is corpus-encoded by the document-order state
machine over `<del_in>/<del_fin>` and `<laes_in>/<laes_fin>`, and no mode
adds, hides, or reinterprets a sign.

**Smaller clarity fixes.** The channel buttons got a visible "Evidence
channel" group label and explanatory titles; the free-text box is labelled
*Search* rather than *Filter*; the queue list says what selecting a cluster
does; focus-visible outlines were added throughout.

## What did not change

**The default queue's content hash is byte-identical**:
`3e4e66ea8d7796739901d379b8bb86cc1cb130c7b19226b7857f2a70ae432bee`, before and
after. The rebuilt `workbench_review_queue.js` differs only because the
embedded manifest gained declared fields; `channels_logical_sha256` covers the
channels alone and did not move. No occurrence, cluster proposal, accepted
hash, or annotation log was touched, and the annotation log is still empty.

`cu` is still never read. Gate 3 is still closed. No protected-test material
is reachable. No gloss, lemma, or translation overlay was added — `mrp_selected`,
`mrp_lemma_candidates`, `lemma_full`, and `lemma_attested` remain EXPLICITLY
DENIED in every evidence policy, and unblocking them is a scope decision for
Ixca, not a UI change.

## What is not verified

**Browser-verified 2026-07-31** (`reports/phase5_browser_verification.md`).
At implementation time no browser tool was available and this section recorded
the gap; Ixca has since rendered the page in Chrome and confirmed the subset
headline stays outside its disclosure, the three action groups render with
tooltips, the footer quarantine statement stays visible, the in-page dialog
completes a `WITHHOLD_JUDGMENT` and discards it on reload, and — the
highest-risk item — the `data-damage` attribute selectors actually apply, so
the overlay restyles the transliteration and swaps its legend across all three
modes.

Still unverified: **no export was downloaded and no ingest was exercised**, so
those paths remain covered by the Python tests only. And **no automated
regression capture exists** — the string-level tests pin that the required
wording and hooks are present, but they cannot observe a CSS selector matching
nothing, which is the class of failure that made a manual check necessary.

**No specialist has assessed whether the grouping helps.** The action
taxonomy here is an engineering judgment about what the seven actions *do*,
not a workflow a Hittitologist validated.

**The two queue exclusions remain unratified.** Nothing here ratifies them,
and the page still says so on screen.

## Validation

```powershell
python -m unittest tests.test_phase4_workbench_interface   # 37 pass (was 19)
python -m unittest discover -s tests                       # 233 pass (was 215)
ruff check lib scripts tests demo                          # clean
python lib/contracts.py                                    # 20/20
python scripts/00_tracers.py                               # 0 blocking failures
python scripts/p4d_stamp_stale_reports.py --check          # exit 0
git diff --check                                           # clean
```

Rebuild commands:

```powershell
# default, all languages
python scripts/phase4_workbench_review_export.py
# a single-language review session
python scripts/phase4_workbench_review_export.py --language Akk
python scripts/phase4_workbench_review_export.py --language Hur,Hat
```
