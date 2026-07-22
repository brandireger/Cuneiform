# TAKSAN_DEMO_SPEC.md — Private Demonstration Workbench (consolidated)

Authority: CLAUDE.md + P2.5 freeze + P3 accepted. This single
document SUPERSEDES AND REPLACES DEMO_SPEC.md, DM_AMENDMENTS.md,
DM_AMENDMENT_2.md, and DESIGN_ADDENDUM.md (delete or archive those;
if any copy survives and conflicts, THIS file wins). Ratified by
Ixca 2026-07-21.

The DM track runs PARALLEL to P4/P5 and must never block or
contaminate them. The demo is a DISPLAY layer over precomputed
artifacts; no model runs at demo time. Distribution: PRIVATE (Ixca,
architect sessions, prospective mentors). No public hosting, no
analytics, no external resource loads — the demo works fully
offline from a local zip. Public-readiness is a design constraint
(see Deferred) but launch is NOT authorized by this spec.

## 1. Identity

System and demo name: **Takšan** (Hittite takšan "jointly; the
middle," from takš- "to join, fit together"). ASCII fold `taksan`
in repo/paths/URLs; display contexts keep the š; first use in any
document carries the gloss. The ALP paper uses Takšan as the
system name.

Design thesis, one line, governs all disputes: **the frame is a
modern precision instrument; only the material is ancient.**
Conservation lab, not museum gift shop. The cuneiform glyphs are
the only "old" element on screen. When in doubt, remove ornament.

## 2. Demo cleanroom rules (binding; restate in demo_report.md)

1. TEST-SIDE EXCLUSION IS ABSOLUTE. No test-side fragment, ID,
   text, or derived statistic appears in any demo artifact until
   P6 freeze. The export script hard-asserts
   `main_split != 'test'` on every emitted fragment and candidate;
   assertion failure aborts the build. Demo queries come from
   dev + discovery pool only.
2. STATUS BADGES ARE STRUCTURAL. Every displayed relation carries
   exactly one status, visually unmistakable in every view
   including placement overlays: SEALED (editor-attested or
   expert-ratified), PROPOSED (model candidate — quarantined per
   Cleanroom rule 5), SET ASIDE (human-reviewed negative). No UI
   state may render PROPOSED with SEALED styling.
3. `cu` IS DISPLAY-ONLY. The glyph layer may use `lb@cu` for
   rendering ONLY. Nothing cu-derived is written into any parquet,
   feature, or model artifact. The demo data file is a leaf node
   of the pipeline DAG — nothing downstream consumes it.
4. RESTORATION HONESTY. Any glyph/token with damage state
   restored/laes renders ghosted in EVERY view and layer. No UI
   state displays restored content styled as attested. The
   restoration toggle hides/shows restored content; it never
   restyles it.
5. LANGUAGE POLICY. Takšan displays only meaning that is
   deterministic or editor-supplied: determinative categories the
   scribes themselves marked, standard reference values for
   logograms, and translated catalogue/apparatus metadata.
   **No machine translation of Hittite text, ever** (out of scope
   per CLAUDE.md; hallucination risk incompatible with the
   project's honesty standards). No reproduction of published
   translations (copyright); link out instead. UI sentence (About
   page + model card): "Meanings shown here come from the
   scribes' own markings and standard sign values — nothing is
   machine-translated."

## 3. Visual identity & interface standards

### 3.1 Color tokens

Two modes, both required. Accent is the Green Stone
(nephrite-mineral green), used ONLY for interactive / selected /
sealed states — never decorative fills. One accent per view
region. No gradients, no drop shadows, no glow.

Fired-dark (default; referent: Boğazköy tablets baked dark in the
destruction of Hattusa):
- `--tk-bg` #181512 page · `--tk-panel` #211D18 · `--tk-cell`
  #2A251E · `--tk-border` #38322A
- `--tk-text` #E8E2D6 (primary / attested ink) · `--tk-text-2`
  #B8B0A2 · `--tk-muted` #8F887C · `--tk-faint` #6B6357
- `--tk-accent` #5DCAA5 · `--tk-accent-2` #1D9E75 ·
  `--tk-accent-bg` #12241D · `--tk-accent-dk` #04342C

Slip-light (referent: pale levigated clay slip):
- `--tk-bg` #F4F1E9 · `--tk-panel` #FCFAF4 · `--tk-cell` #EDE8DC
  · `--tk-border` #D8D2C4
- `--tk-text` #262219 · `--tk-text-2` #55503F · `--tk-muted`
  #7A7466 · `--tk-faint` #A39C8C
- `--tk-accent` #0F6E56 · `--tk-accent-2` #1D9E75 ·
  `--tk-accent-bg` #E1F5EE · `--tk-accent-dk` #04342C

Danger/rejection: one muted red, text-only, reserved for "Set
aside" and destructive confirms (#A32D2D on dark, #E24B4A on
light; never a fill). Mode toggle in footer; both modes ship.

### 3.2 Typography

- Cuneiform layer: Ullikummi (Hittite ductus,
  hethport.uni-wuerzburg.de/cuneifont/), packaged locally for
  PRIVATE use; record its stated terms verbatim in the README and
  flag: public redistribution requires permission or an OFL
  fallback (e.g. Noto Sans Cuneiform) — decision deferred; config
  supports font swap; footer names the active font. Glyphs with
  no coverage (PUA long tail from DM0) fall back to
  transliteration-in-a-cell, counted in the footer.
- UI + body: one OFL humanist sans packaged locally (Inter or
  Source Sans 3 — builder's pick, recorded). Weights 400/500 only.
- Data/IDs/metadata: one OFL mono (Source Code Pro or JetBrains
  Mono). docIDs, lnr labels, provenance stamp, scores.
- NO ornamental display face; view titles are the UI sans at 500.
  The cuneiform is the only characterful type on screen.
- Minimum rendered text 11px; Ullikummi glyph height target
  ≥ 20px.

### 3.3 Mark & pedestal motif

- Mark: isometric green cube, three faces from the accent family
  (mid / darker / darkest), flat fills, no outline. Variants: app
  mark (header), seal-badge (cube in ring), favicon (cube on
  --tk-accent-dk rounded square). SVG committed as
  `brand/taksan-mark.svg`.
- Pedestal line: a single full-width 1px hairline (--tk-border)
  directly under the header mark, reused as THE section divider
  throughout. No other divider styles. Do not explain the motif
  in-product.

### 3.4 Damage-state grammar (identical in every view and layer;
### never color alone — every state has a non-color cue)

1. ATTESTED — full-opacity glyph/token on --tk-cell.
2. RESTORED — 45% opacity PLUS 1.5px dashed underline in
   --tk-muted. Restoration toggle hides restored content (cells
   become lost-edge style); never restyles it as attested.
3. ILLEGIBLE (x) — ╳ in --tk-faint, dotted-bordered cell, no
   glyph.
4. LOST EDGE / GAP — empty cell, 1px dashed border in
   --tk-accent-2; multi-cell gaps render as one labeled band
   (--tk-accent-bg fill, "gap" label). Indirect (+) joins ALWAYS
   show the band; never false abutment (P2.5 A6 applies to
   display).

Legend strip pinned under every fragment grid, using the real
styles as swatches.

### 3.5 Seal status system

Grounded in Hittite treaty sealing practice. Exactly three
states:
- PROPOSED — dashed open-ring icon; neutral chip (--tk-border
  outline, --tk-muted text).
- SEALED — solid ring-and-center icon in accent; chip
  --tk-accent-dk fill with --tk-accent text. Action button:
  "Seal this join".
- SET ASIDE — thin broken-ring icon in --tk-faint; chip outlined,
  muted-red text.
Sealing UI shows reviewer name + timestamp beside the badge.
Beside the export control: "Seals recorded here are private
review decisions, not ground truth."

### 3.6 Motion

One orchestrated moment only: THE JOIN MOMENT. On candidate
select, the partner grid translates to its proposed offset
(180ms ease-out), then aligned line-pairs illuminate sequentially
down the seam (60ms stagger, --tk-accent-bg row tint). Nothing
else animates beyond standard hover/focus.
prefers-reduced-motion: instant render, co-highlight intact.

### 3.7 Copy standards

- Sentence case everywhere; verb-first buttons; no exclamation
  marks; no "please" / "simply" / "successfully".
- Plain names, user's side of the screen: "Fragments", "Proposed
  matches", "Known joins", "Discovery pool", "Awaiting seal".
- Score labels: "Text overlap" (tooltip: BM25 over sign n-grams)
  · "Learned similarity" (tooltip: neural bi-encoder — pending
  P4) · "Edge fit" (tooltip: continuation lift — pending P5).
  Pending scores read "pending P4"/"pending P5" in --tk-faint,
  never blank.
- Honesty Panel leads with sentences, tables beneath. Template:
  "Of 100 fragments with a known physical partner, the current
  system ranks the true partner first about N times." N
  auto-filled from the metrics payload, rounded, never
  hand-edited.
- Errors: what happened + what to do, one sentence, no apology.
- Empty states: headline names the space, one-line body, verb CTA
  where an action exists. THE empty-state illustration is the
  plain green cube with the line "Nothing written here yet." No
  further explanation in-product.
- Glossary terms (dotted underline; hover/tap; one sentence each;
  single source `glossary.json`): CTH, composition, fragment,
  join, duplicate (witness), tier A/B/C, attested, restored,
  discovery pool, recall@k, BM25. Written for a smart layperson;
  keyboard accessible; no term defined in two places.

### 3.8 Accessibility floor (non-negotiable)

Visible keyboard focus everywhere; all states distinguishable
without color; text contrast ≥ 4.5:1 in both modes (verify
--tk-muted on --tk-panel; darken if it fails); reduced motion
respected; hit targets ≥ 32px; screen-reader text for glyph
cells = transliteration value + damage state.

## 4. DM0 — `cu` verification gate (do FIRST; gates glyph layer)

- Dump codepoints for `cu` from 20 sampled lines spanning: fully
  attested, partially restored, fully restored (the P2
  damage-oracle example), lines with `▒`, lines with
  determinatives and Sumerograms/Akkadograms.
- Answer in `dm0_cu_report.md`:
  a. Are `cu` glyphs Unicode cuneiform (U+12000–U+123FF /
     U+12400–U+1247F)? Report out-of-block codepoints (expect
     possible PUA for rare HZL signs — count; they get the
     fallback rendering).
  b. Does `cu` glyph count align 1:1 with `sign_damage_states`
     per line? Measure over 500 random lines. If not 1:1,
     characterize the mismatch and define the alignment
     transform. Glyph layer is BLOCKED until alignment is
     verified or transformed with error < 1% of lines
     (misaligned lines fall back to transliteration-only).
  c. How does `▒` map to damage states (illegible x vs
     indeterminate gap)? Define the render rule for each.
- If (a) fails outright, descope to transliteration + damage
  styling and inform the architect session before further glyph
  work.

## 5. DM1 — `16_demo_export.py` — precomputed data

Emits `demo_data.json` + supporting JSON files +
`demo_data_report.md`. Budget: ≤ 15 MB uncompressed; if over,
trim candidate depth before query count; report trims.

### 5.1 Query sets

a. KNOWN JOINS GALLERY: all dev-side real join pairs (tier A/B;
   tier C only where exclusive-content testable), each with the
   editor's `{€N}` per-line alignment parsed into explicit
   line-pair mappings (ground-truth placement).
b. CANDIDATE GALLERY: per dev-side join query, top-20 ranked
   candidates from the CURRENT best scorer (BM25_sign at build
   time; schema reserves nullable `scores.biencoder`,
   `scores.edge_continuation` so P4/P5 drop in without schema
   change). H1 same-family exclusions apply and are logged.
c. DISCOVERY POOL: top-500 discovery-pool fragments by current
   best assignment confidence, each with top-5 proposed
   compositions (CTH number + title + bin flag).

### 5.2 Per-fragment render data

docID, provenance site, CTH (number/title/bin flag), lines in
order; per line: lnr label, lg code, token list where each token
carries {translit, glyph_string|null, damage_state,
is_determinative, is_logogram}; edge profile from edges.parquet;
gap/parsep events.

### 5.3 Evidence & failures

- Per candidate: `evidence.shared_ngrams` = top-20 shared sign
  n-grams with per-fragment (line, position) spans for
  co-highlighting; computed from ATTESTED tokens only (never cu,
  never restorations). Nullable `evidence.per_line_neural`
  reserved for P4/P5.
- `failures[]` = 5 curated failure cases (query, wrong top
  candidate, true answer if known, one-line plain-language
  diagnosis, the fooling score), selected from the patched-P3
  failures file. Curation: builder proposes 8; architect + Ixca
  pick 5.

### 5.4 Language & meaning data files

- `annotations_lexicon.json` — closed-set DE→EN apparatus
  vocabulary (bricht ab, Vs./Rs., lk./r. Rd., unbeschrieben,
  Kolumne, ...). Builder compiles candidates by frequency census
  over gap@c and annotation strings; architect drafts EN; Ixca
  reviews. Report % of apparatus strings matched.
- `cth_titles.json` — German catalogue titles (from the P2.5
  archived catalogue) + `en_title` for at least all demo-visible
  compositions (full 662 as capacity allows). Workflow: architect
  drafts → Ixca reviews → per-entry `review_status`
  (draft|reviewed). Display: EN first, German in parentheses;
  unreviewed entries display German only.
- `determinatives.json` — determinative → category label (EN+DE).
  Starting inventory: D=deity name, m/Personenkeil=personal name,
  URU=city, KUR=land, LÚ=profession/title, GIŠ=wooden object,
  NA4=stone, É=building, DUG=vessel, TÚG=garment, ÍD=river,
  HUR.SAG=mountain, MUŠEN=bird, UZU=body part/meat, SÍG=wool,
  NINDA=bread/pastry. CENSUS THE CORPUS'S <d> INVENTORY FIRST,
  then map; flag any unmapped determinative rather than guessing.
  Deterministic; spot-check only.
- `logogram_glosses.json` — curated glosses for the top-50
  logograms by TRAIN-side attested frequency, plus demo-salient
  compounds (LUGAL.GAL "Great King", MUNUS.LUGAL "queen", EZEN4
  "festival"). Values from standard references (record which —
  CHD/HZL conventional values). Architect drafts, Ixca reviews,
  per-entry `review_status`. OUT OF SCOPE: syllabic Hittite
  vocabulary — do not cross the lexicography line; flag scope
  creep instead of implementing.
- `edition_links.json` — composition → hethiter.net edition URL
  where an HPM edition exists; verify the link pattern on a
  hand-checked sample of 10; report dead-link rate.
- `glossary.json` per §3.7.
- `cards.model` / `cards.data` — structured model-card and
  data-card payloads (intended use; training data; evaluation
  protocol; leakage controls; known limitations; out-of-scope
  uses). Text sourced from accepted reports verbatim or
  summarized without new claims.

### 5.5 Metrics payload & provenance

Patched-P3 three-way matrix (post-H1), model ladder incl. losers,
restoration-leakage delta, Tyndall verdict summary — copied from
accepted reports, never recomputed. Coverage metrics: % of
attested tokens carrying (a) determinative category, (b) logogram
gloss, (c) either — overall and for demo-featured fragments.
JSON root carries: git hash, corpus version (0.2.0-beta), build
date, split freeze ID, scorer used — rendered in the app footer
at all times.

## 6. DM2 — `taksan.html` — single-file static app

Vanilla JS + inline CSS, ZERO external resource loads: no CDN, no
remote fonts, no analytics. Ships as a zip: `taksan.html` +
`demo_data.json` + supporting JSON + font file(s) + README.
Outbound NAVIGATION links (edition links) are permitted — they
are the only network touchpoints, load nothing into the app, and
are visibly marked with ↗.

Views (all built to §3):

1. JOIN WORKBENCH. Query fragment as 2D grid (rows = lines,
   cells = signs), damage grammar per §3.4, ragged edge
   silhouette from the edge profile. Candidate panel: ranked
   list, per-candidate score decomposition (all columns; pending
   per §3.7), tier, status badge. Selecting a candidate renders
   the PLACEMENT per §3.6 with seam highlight, GAP band for
   indirect joins, aligned line-pairs co-highlighted. For KNOWN
   joins: toggle overlaying the editor's {€N} alignment vs the
   model's proposal.
   EVIDENCE VIEW: on candidate select, shared sign n-grams
   co-highlight in BOTH grids (accent-bg tint + 1px accent
   underline — not color-alone); side panel lists top shared
   n-grams with counts.
2. LAYER STACK. Per-fragment toggles: glyphs / transliteration /
   (translation only IF a translation field exists in the schema
   per the P1 census; if absent, omit the toggle entirely).
   Damage styling constant across layers; restoration toggle per
   rule 4.
   MEANINGS TOGGLE ("Show meanings"): determinative category
   tooltips + logogram glosses. Default OFF in workbench and
   discovery views; ON inside the intro walkthrough.
   Determinatives render superscript (standard convention) with
   dotted-underline tooltip affordance; glossed logograms
   dotted-underlined; tooltips one line; NO new colors.
   LANGUAGE TOGGLE (footer): apparatus, titles, and category
   labels render EN or DE; glyphs and transliteration never
   affected.
3. DISCOVERY POOL. Sortable/filterable table of unassigned
   fragments with ranked proposed compositions (number + title +
   confidence), CSV export. Persistent banner: "Unverified model
   proposals for expert review."
4. HONESTY PANEL. Sentence-first metrics per §3.7, three-way
   matrix, model ladder incl. losers, restoration-leakage number
   with a one-paragraph plain-language explanation, Tyndall
   verdict, provenance stamp.
   FAILURE GALLERY: the 5 curated failures — thumbnail pair +
   one-line diagnosis + the fooling score; styling identical to
   successes, no shame-styling.
   MODEL CARD / DATA CARD tab from cards payloads.
5. INTRO WALKTHROUGH. 60-second first-run panel: one known join
   walked through (this fragment, this partner, this seam, this
   is what the tool proposes at scale). Skippable; meanings ON.
6. ABOUT. The origin story, told honestly: the project began with
   a question about the uninscribed green stone at Hattusa and
   became a tool for reassembling what the Hittites did write.
   State plainly: material unverified (nephrite vs serpentinite),
   purpose unknown, pedestal hypothesis plausible but unproven.
   Image slot reserved for Ixca's own photograph (caption
   "Photo: the author, Hattusa"). Include: the §2.5 language
   policy sentence; gloss reference credits; TLHdig attribution
   (CC BY 4.0 — Müller, Prechel, Rieken & Schwemer 2025, DOI
   10.5281/zenodo.15459134); font credit; private-build notice.

Fragment header shows "German edition ↗" where edition_links has
an entry. No login, no server; core viewing requires no
localStorage (DM3 capture may use it).

## 7. DM3 — review flow

- Per-candidate controls: Seal / Set aside / Uncertain +
  free-text note + reviewer name (self-reported; private tool
  among known parties).
- Persistence: localStorage keyed by candidate ID; "Export
  verifications" downloads `verifications_{name}_{date}.json`
  (candidate ID, decision — field names `sealed` / `set_aside` /
  `uncertain` — note, reviewer, timestamp, build provenance
  stamp). "Import" merges a colleague's export for side-by-side
  display; conflicts shown, never silently merged. These files
  are raw material for a future candidate → endorsement → expert
  ladder; NEVER auto-promoted to ground truth.
- KEYBOARD REVIEW FLOW: j/k next/prev candidate · s seal · a set
  aside · u uncertain · g glyph/translit toggle · r restoration
  toggle · ? key-overlay. Focus ring always visible; full flow
  operable without pointer.
- DEEP LINKS: URL hash encodes {view, fragment, candidate, layer,
  restoration, mode}; copy-link button in header; opening a link
  restores the exact state.

## 8. Deferred (design for, do not build)

Public GitHub Pages deployment; giscus/Issues-backed community
endorsements; the join-puzzle game; TLHdig outreach materials;
Ullikummi public-license resolution; "what changed since last
build" strip (public tier); test-side content (post-P6 only).
The data schema and static architecture must not foreclose these —
that is the only sense in which they constrain DM.

Note for the architect session (not a build item): TLHdig Beta
0.3 (2025-11-01) exists; the 0.2.0-beta pin and frozen splits
STAND for this cycle. Outreach-email agenda: request 0.3
access/changelog; ask about any planned translation layer; font
permission.

## 9. Acceptance checks (`demo_report.md`)

1. DM0 report answers (a)(b)(c) with measured numbers; glyph
   layer go/no-go recorded.
2. Export hard-assert verified: including a test-side docID
   aborts with a named error (show the test).
3. Zip opens from file:// with network disabled; all views
   function; footer provenance stamp correct.
4. Badge audit: DOM check or screenshot proving PROPOSED styling
   is distinct from SEALED in every view incl. placement overlay.
5. Restoration audit: one fully-restored line (the P2
   damage-oracle example) rendered ghosted in glyph AND
   transliteration layers; toggle demonstrably hides it.
6. 10 known joins and 10 candidates spot-rendered (screenshots
   or SVG dumps) for architect review.
7. File size within budget; trims documented.
8. Evidence view: known-join screenshot with co-highlighted
   shared n-grams in both fragments; one case showing a restored
   token correctly NOT highlighted.
9. Failure gallery renders 5 cases with diagnoses; styling
   parity with successes confirmed.
10. Deep-link round-trip: copy in one session, open fresh,
    identical state restored (document the test).
11. Keyboard-only session: seal + set-aside + export completed
    without pointer; ? overlay screenshot.
12. Both theme modes render every view; --tk-muted contrast
    spot-check passes 4.5:1 in both.
13. Glossary: every underlined term resolves; no duplicate
    definitions.
14. Determinative census: every determinative in demo fragments
    mapped or explicitly flagged unmapped (counts reported);
    tooltip screenshots for a deity name and a profession/title.
15. Logogram spot-render: festival fragment with meanings ON
    showing category + gloss tooltips; no syllabic Hittite word
    carries a gloss.
16. Language toggle round-trip: same view EN and DE;
    glyphs/transliteration byte-identical between them.
17. Coverage numbers in demo_data_report.md; unreviewed en_title
    entries verified to fall back to German.
18. Links-out audit: 10-link sample resolves; all outbound links
    carry ↗; network monitor shows zero external resource loads.
19. All runs deterministic (seeded where applicable); build
    provenance logged.

Small artifacts back: demo_report.md, dm0_cu_report.md,
demo_data_report.md (incl. JSON row counts + coverage), the zip
itself (report its size), screenshots for checks 4–6, 8–12, 14–15
embedded in demo_report.md. No parquet, no checkpoints.
