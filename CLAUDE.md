# CLAUDE.md — Hittite Fragment Matching Project

Standing context for all Claude Code sessions in this repository. Read
fully before acting. This file is the design authority; if a session's
work would contradict it, stop and flag the conflict instead of
improvising. The human collaborator (Ixca) makes final design calls.

## Project identity

Research project building an **evidence-bounded missing-information
reconstruction system for fragmentary Hittite cuneiform texts**, using
the openly licensed TLHdig corpus. The scientific center is predicting
missing textual and structural information from the textual and encoded
artifactual context that actually survives. Composition assignment,
duplicate/parallel discovery, and physical-join suggestion are downstream
applications and evaluation settings, not the project's identity. Two
target outcomes, in order:

1. A working prototype + draft paper with real numbers, used as a
   demonstration artifact for a graduate mentorship pitch (UT Austin
   MSAI application in progress).
2. A submission to the Ancient Language Processing (ALP) workshop
   cycle (venue of Yavasan & Gordin 2025).

Tone of the work: rigorous, over-explicit, honest about negative
results. When in doubt, report more, claim less.

## Research question

What missing textual or structural information is recoverable from
fragmentary Hittite records under explicitly named evidence policies,
with calibrated uncertainty and abstention, and when is the encoded
evidence insufficient? Within that frame, test whether modern
representation learning improves over classical methods for restoration,
composition affinity, duplicate/parallel witnesses, or physical-join
candidates at full-corpus scale with leakage-safe methodology.

### Core epistemic commitment

"Let the artifacts speak" means every prediction is bounded by the
evidence the corpus actually encodes. The project must:

- predict held-out genuinely attested signs/passages for primary
  restoration evaluation; editorial restorations are scholarly
  hypotheses, never unquestioned gold;
- keep textual, structural, catalog, editorial, and model-derived
  evidence typed and separable;
- preserve uncertainty and plausible alternatives, and abstain when
  the encoded evidence does not identify a defensible answer;
- never simulate missing physical evidence (clay, curvature, fracture
  geometry, paleography) and then describe the result as artifact-led;
- treat parallel witnesses as bounded evidence for possible missing
  context, not proof that a lost original had identical wording; and
- treat joins as one downstream case of missing-context inference, not
  the organizing objective.

### Primary user and output contract

The primary user is a **trained Hittite language specialist**, not a lay
reader seeking an automatic restoration. The system is expert decision
support. For a missing sign or bounded span, its default UI output is a
ranked **set of evidence-supported possibilities**, not one asserted
completion.

Each displayed possibility must preserve:

- the proposed sign/span and its rank;
- a calibrated probability-like quantity whose estimand is named
  explicitly (for example, held-out empirical agreement within a
  declared calibration stratum);
- the sample size and confidence interval for that calibration
  estimate;
- typed supporting and contradictory evidence, including independent
  witness sources when used;
- the active evidence-policy/assistance profile; and
- an explicit residual option such as `other / unsupported`, plus
  abstention when the candidate set is not adequately constrained.

A confidence interval over a calibration group is **not** the probability
that one particular lost reading is true. Raw retrieval scores, normalized
heuristic scores, and top-1 margins must not be labeled probabilities unless
their calibration has been measured out of sample. Candidate probabilities
need not exhaust the space: unobserved readings and genuine textual variation
may remain.

The primary intrinsic evaluation therefore measures candidate-set utility:
gold/attested inclusion at `k`, set coverage, set size, calibration error,
selective risk, composition-macro stability, and abstention. Top-1 exact
agreement remains a useful diagnostic, but it is not the product definition.
An expert selection is a provenance-bearing annotation; it is never promoted
automatically to corpus truth or training ground truth.

### Historical Phase 1 benchmark question

Can modern representation learning substantially outperform classical
text classification at connecting fragmentary Hittite transliterations
to (a) their parent compositions and (b) their physical join partners
and duplicate witnesses — evaluated against known joins/duplicates at
full-corpus scale, with leakage-safe methodology?

## Corpus (pinned)

- **TLHdig Beta 0.2.0** — Zenodo DOI 10.5281/zenodo.15459134,
  file `TLHdig_0.2.0-beta.zip` (63.9 MB,
  MD5 93e71e2560f5e109c87713d5590cb059). License **CC BY 4.0**.
  Cite as: Müller, Prechel, Rieken & Schwemer (2025).
- **21,868** real XML documents after excluding zip artifacts (320
  macOS `__MACOSX/` + AppleDouble `._*` junk entries — exclude these
  in every script that reads the zip); 384,667 `<lb>` line elements.
  229 documents (~1.0%) fail to parse (mismatched/invalid XML) — a
  real corpus data-quality issue, not a script bug; P2 must log and
  skip these, never silently drop without a record. Many documents
  are already multi-fragment rejoined texts (these encode our
  ground-truth joins).
- Multilingual layers present: Hittite, Akkadian, Sumerian, Hattic,
  Cuneiform Luwian, Palaic, Hurrian. Do not silently discard
  non-Hittite layers; they matter for parallels.
- Known caveat (per the TLHdig team): philological quality is uneven —
  it is a living community archive, not a critical edition. Quality
  filtering must be explicit and reported, never silent.
- **Actual schema is AOxml/HPM (hethiter.net Hethitologie Portal
  Mainz format), not the SimTex plaintext convention originally
  assumed here — verified via `01_inventory.py` (P1, run
  2026-07-20) against the real corpus. Key structure:**
  - `<lb txtid lnr lg cu>` = one transliterated line. `lnr` = line
    label (e.g. "Vs.? 1′"); `lg` = **per-line** language code (Hit,
    Akk, Hat, Hattian, ...) — the multilingual-layer signal lives
    here, at line granularity, not per-document; `cu` = raw
    cuneiform sign string. **Correction (P2, 02_parse.py damage-
    oracle check, 2026-07-20): `cu` is NOT an attested-only break
    silhouette — do not use it as one.** It renders the editor's
    complete PROPOSED reading, including restored (`<del_in>/
    <del_fin>`) content, as real glyphs; `▒` marks only positions
    where no sign value could be proposed at all (illegible `x`,
    indeterminate-length gaps). Verified: a fully-restored line (every
    sign inside a del-span) rendered with zero `▒`. The real per-sign
    attested/restored/laes/illegible_x state for the matrix model's
    edge profile comes from the transliteration markup itself
    (`sign_damage_states` in `corpus.parquet`, produced by a document-
    order state machine over `<del_in>/<del_fin>`/`<laes_in>/
    <laes_fin>`, since those spans cross word and line boundaries),
    not from `cu`. **`cu` is not cleanroom-safe (P2.5 A5 restatement):
    because it silently mixes in editor-restored content as real
    glyphs, never feed `cu` or any `cu`-derived feature to any
    evaluated model, at train time or test time** — it is a display/
    preview field, not a corpus signal.
  - `<w trans mrp0sel mrp1..mrp7>` = word. `trans` = transliterated
    form (the primary text signal); `mrp*` = ranked morphological
    parse candidates (lemma@gloss@paradigm@class) — rich, but this
    is glossing/analysis, **out of scope** per this file; do not
    build features off `mrp*` beyond incidental inspection.
  - **Break/restoration is NOT encoded as literal bracket
    characters** (raw bracket counts in body text are near-zero:
    12,339 `(` / 12,336 `)` from editorial notes, only 4 `[`, 0
    `]`/`⸢`/`⸣`). It's encoded structurally instead:
    `<del_in/>`/`<del_fin/>` = illegible/damaged span (often wraps a
    literal `x` placeholder sign); `<laes_in/>`/`<laes_fin/>` =
    partially-preserved/restored span; `<gap c="..." t="line">` =
    larger structural lacuna with a free-text description (e.g.
    "Rs. IV bricht ab"); `<space c="N"/>` = N sign-widths of blank
    run. **Reconstruct each fragment's edge profile from these tags
    plus `lb@cu`, not from bracket-character regex.**
  - `<sGr>`/`<aGr>`/`<d>` = Sumerogram / Akkadogram / determinative
    spans (matches the CAPS convention Yavasan & Gordin describe,
    but tag-delimited here rather than case-inferred).
    `<parsep>` = paragraph-ruling separator (real structural
    boundary). `<clb id nr>` = column line break / column number.
  - **CTH composition membership is structural, not textual**: one
    `CTH ###_XML` folder per composition in the zip (**662 distinct
    compositions**, 21,868/21,868 docs covered via folder path). Only
    530/21,868 docs additionally mention "CTH" as body/attribute
    text — do not use in-text regex for CTH labels; read the folder
    path.
  - **Join ground truth**: `docID` / `<AO:TxtPubl>` / `lb@txtid`
    carry the authoritative "+" join notation (e.g. docID
    `KBo 64.15+`, TxtPubl `"KBo 64.15 {€1} + KUB 7.38 {€2}"` — note
    the `{€N}` witness sigla, and per-line witness attribution
    inside composite `lnr` values like `"{€2+1} Vs. 1/Vs. I 1"`,
    which gives an **exact editor-supplied line-level alignment**
    between joined fragments — a strong supervision signal for the
    placement/offset scoring in the matrix model). 866 docs carry
    this authoritative join signal. **Do not** regex-scan all
    attributes/text for "+": `w@mrp*` fields use "+=" for clitic
    attachment (e.g. `"POSP += ma@CNJctr@@"`), which inflates a
    naive scan to 13,981 false-positive "join" docs.
  - `annot@editor` / `annot@date` = per-edit provenance metadata.
    Track for expert-agreement analysis; never use as a model
    feature (it identifies the editing process, not the text).
  - Yavasan & Gordin (ALP 2025, "From Clay to Code") worked from
    these same files — reuse their preprocessing decisions where
    sensible and cite them.
- Schema knowledge must come from `01_inventory.py` output
  (p1_out/, renamed from inventory_out/ 2026-07-21 for consistency
  with p2_out/p25_out/p3_out/p4_out), not assumptions. If inventory
  results and this file disagree, the inventory wins; update this
  file.

## Task definitions

Missing-information prediction is the upstream scientific task. Task A
and Task B below remain valuable benchmarks and discovery applications,
but neither may redefine the project around forced joining.

- **Task A — Composition assignment.** Fragment → CTH composition,
  framed as retrieval (rank compositions). Modernizes Tyndall (2012),
  ACL P12-2048: his setup was 36 CTH texts, 389 fragments, MALLET
  Naive Bayes / MaxEnt, 10-fold CV, best accuracy **0.67** (MaxEnt,
  all tokens, restorations retained). Replicate approximately, then
  scale.
- **Task B — Pairwise matching.** Fragment → ranked corpus fragments,
  positives of two kinds: (i) physical join partners, (ii) duplicate /
  parallel witnesses of the same composition. **Always train pooled if
  sparsity demands, but ALWAYS evaluate and report joins-only,
  duplicates-only, and pooled — the full three-way matrix for every
  model.** This separation is a standing user decision.
- Metrics: recall@k (k=1,5,10,100), MRR; stratify by fragment length
  and by genre where CTH metadata allows.

### Bin reframe (P2.5 A1/A2, accepted 2026-07-21 — "let the artifacts
speak, not editors")

114 of 657 CTH numbers are fragment **catch-all bins**, not real
compositions (e.g. CTH 832 "Hethitische Fragmente verschiedenen
Inhaltes" — 3,583 unrelated fragments filed under one number for lack
of a better home; CTH 470 "Ritualfragmente"; CTH 670
"Festritualfragmente"). Identified via the real CTH catalogue title
(single bulk fetch from an archived hethport.uni-wuerzburg.de/CTH/
snapshot — see `p25_out/bins_report.md`), not guessed from doc counts.
Consequence, binding on both tasks above:
- **Bin documents (14,046) are EXCLUDED from Task A labels, Task B
  duplicate-positive generation, contrastive negative sampling, and
  all reported metrics' truth sets.** A bin fragment may secretly
  belong to any composition, including a test-side one — it is
  unlabeled, not negative.
- Bin documents instead form the **discovery pool**
  (`p25_out/discovery_pool.parquet`) — inference-time queries only,
  never scored as ground truth. Model-proposed assignments of
  discovery-pool fragments to real compositions are a P7 deliverable
  for expert verification (see Cleanroom rule 5, "novel suggestions
  are quarantined").
- Impact was not cosmetic: naive same-CTH-folder duplicate-positive
  pairs = 13,451,014; bins-excluded (real compositions only) =
  234,263 — a 98.3% drop. Without this reframe, duplicate-witness
  supervision would have been almost entirely noise from catch-all
  bins, dominated by CTH 832 alone.
- **Physical joins are unaffected by bin status**: a composite join
  document whose parent CTH folder happens to be a bin still yields a
  valid join pair (the physical fit is real regardless of catalogue
  assignment) — tagged `parent_is_bin=True` in
  `p2_out/join_pairs.jsonl`, reported both included and excluded.
- 543 real compositions remain supervision-eligible. `main_split`
  (train/dev/test) is assigned over real compositions only; bin
  documents carry `main_split='discovery'`, never train/dev/test.

## The fragment-as-matrix model (core design requirement)

A fragment is a 2D grid: rows = lines, columns = sign positions. Four
edge types: left (line-beginnings lost), right (line-endings lost),
top (preceding lines lost), bottom (following lines lost). Bracket
conventions in the transliteration encode the break silhouette —
reconstruct each fragment's edge profile from text.

A candidate join is a 2D **placement**, scored in all directions:
forward/backward horizontally, and both vertical orientations. The
strongest signal is **multi-row consistency**: a true horizontal join
aligns coherently across several consecutive line-pairs at a
consistent offset. Aggregate placement scores over aligned row-pairs;
never rely on a single-edge continuation alone.

## Edge-continuation model ("layered neighbor")

One masked-span / MLM-style model over sign sequences serves three
roles: (1) restoration prediction pre-training, (2) layered
next-element prediction, (3) join scoring.

Granularity ladder (each is a reported intrinsic result, per genre):
- L0: next sign (classification over sign vocabulary)
- L1: next n signs (beam search, n≈2–5)
- L2: next word (respect SimTex word vs. hyphen/clitic boundaries)
- L3: next phrase/line

Join score = PMI-style lift of B's edge as continuation of A's edge
over corpus baseline (raw probability rewards formulaic openings —
don't use it), computed bidirectionally, both axes, aggregated over
the placement per the matrix model. The intrinsic table "how
predictable is Hittite at a fracture edge, per granularity, per
genre" is a standalone deliverable.

### Seam scoring must NEVER assume contiguity (P2.5 A6, design
commitment for P5 — no implementation yet)

Clay crumbles: even direct `+` joins lose signs at the fracture face,
and indirect `(+)` joins are same-tablet pairs separated by an
arbitrary lost span. Therefore:
- Horizontal seam score = plausibility of [A-edge] [unknown-length
  masked span] [B-edge], via span-infilling (T5-sentinel-style
  variable-length mask), never next-token adjacency.
- Vertical seam score = same, with the mask spanning an unknown
  number of whole lines (anchor to `gap t="line"` / "bricht ab"
  events where present).
- Multi-row consistency = alignment at a CONSISTENT but UNKNOWN
  offset across row-pairs, not exact abutment.
- Evaluation stratum: direct `+` pairs test near-contiguous seams;
  indirect `(+)` pairs (213 of 1,581 join-tier pairs, per
  `p25_out/join_tiers_report.md`) are the designated held-out test of
  long-gap tolerance. Report both, never pooled-only.

## Pipeline architecture

1. **Bi-encoder** (contrastive: same-composition witnesses pull
   together) → embed all fragments once, ANN retrieval of top-k.
2. **Edge-continuation scorer** reranks top-k for JOINS.
3. **Cross-encoder / verbatim-overlap scorer** reranks for DUPLICATES.
4. Score fragments at line/passage level and aggregate (max over
   line-pairs) as well as whole-fragment level; report both.

## Model ladder (run in this order; every rung reported)

1. BM25 / TF-IDF over sign n-grams — mandatory baseline; expected
   brutally strong on duplicates. If neural ≈ BM25, that is a finding,
   not a failure.
2. Naive Bayes / MaxEnt — Tyndall replication (original scale approx.
   and full scale).
3. ByT5 (small→base) — primary neural candidate (byte-level; T5
   lineage comparable to Yavasan & Gordin).
4. CANINE — alternate tokenization-free encoder.
5. From-scratch small transformer with a **sign-level tokenizer**
   (hyphen-separated signs as tokens; vocab ≈ few thousand) — the
   domain-native candidate; corpus is small enough to pre-train on
   one GPU.
6. XLM-R / mT5 — subword control, expected to lose; run it anyway.

Model selection on dev split only. All results, including losers, go
in the paper. Single consumer GPU is the compute budget; if a design
exceeds it, redesign.

## Cleanroom rules (non-negotiable)

1. **Test set purity.** Evaluation fragments are stripped to
   epigraphically attested signs only. Nothing restoration-derived,
   model-generated, or refined touches the test set. Test labels come
   from the corpus only.
2. **Split by composition.** All witnesses/fragments of a CTH
   composition land on the same side of every split. Joined fragments
   likewise. No composition-level leakage between train/dev/test.
3. **Restorations are distilled expert knowledge, not ground truth.**
   Scholars restored brackets partly USING duplicate knowledge —
   training signal yes, evaluation signal never. State this framing in
   all writeups.
4. **Self-training loop hygiene.** Pseudo-labels admitted only above a
   confidence threshold; max 2 rounds; full ablation (base vs round 1
   vs round 2). If gains are nil, report and cut.
5. **Novel suggestions are quarantined.** Model-proposed new joins /
   duplicates go in a separate "candidates for expert verification"
   list. They are NEVER counted as positives in any metric. This list
   is a headline deliverable (the mentorship pitch artifact).
6. **Restoration-agreement leakage ablation.** Quantify the
   performance delta of restorations-in vs attested-only — this is a
   contribution, not just hygiene.

## Evidence provenance and assistance controls (Phase 2 standing rule,
added 2026-07-22 per expert advisory input — see `EXPERT_OPINION.md`)

Read `EXPERT_OPINION.md` and `specs/EVIDENCE_POLICY.md` before
implementing any new content-consuming model or probe.

Every semantic input field must be registered with an evidence class.
Standard classes are: `OBSERVED_ARTIFACT`, `OBSERVED_DOCUMENT_STRUCTURE`,
`CATALOG_METADATA`, `EDITORIAL_TRANSCRIPTION`, `EDITORIAL_RESTORATION`,
`EDITORIAL_RELATION`, `MODEL_DERIVED`, and `SYSTEM_TECHNICAL`.

New code must fail closed when a requested field is unknown or
prohibited by the selected evidence policy. Editorial and model
assistance must be disable-able through configuration without changing
implementation code. Every new scoring/training run emits a
feature-use manifest recording requested and observed fields, evidence
classes, prohibited-field checks, hashes, seed, corpus version, git
commit, and declared statistics universe.

Do not call a result "artifact-only" merely because restorations were
removed. TLHdig transliteration is editorially mediated. Use the named
evidence-policy profile in reports (`artifact_strict`,
`transcription_assisted`, `catalog_assisted`, `scholar_assisted`, or
`discovery_assisted`) and state its permitted evidence classes.

Physical-join output must support abstention when the encoded evidence
is insufficient. Candidate output should preserve typed supporting
evidence, contradictory evidence, enabled assistance layers, and any
model-derived content; a single combined score is never the sole
persisted explanation.

Implementation: `lib/evidence_policy.py`, `configs/evidence_policies.yaml`,
`configs/evidence_registry.yaml`. This layer applies to NEW Phase 2
work; it was not retrofitted onto Phase 1's historical scripts or
reports in its first pass (a deliberate scope decision, not an
oversight — see `specs/EVIDENCE_POLICY.md`'s "Scope control").

## Provenance & generalization

Filename/ID prefixes → site (verify against inventory; refine with
expert input): KBo/KUB/Bo/VBoT/IBoT/ABoT = Hattusa; HKM/Mşt =
Maşat/Tapikka; Or. = Ortaköy/Sapinuwa; KuT/KuSa = Kuşaklı/Šarišša;
KpT = Kayalıpınar/Šamuha; RS = Ugarit; Msk = Emar; AT = Alalakh.
Headline generalization experiment: **train on Hattusa, test on
provincial fragments** (simulates deployment on newly excavated
material — the Sapinuwa scenario Tyndall himself named in 2012).
Provincial + multilingual material also supplies hard negatives.

## Engineering standards

- Deterministic seeds everywhere; log seed, git commit, dataset
  version (0.2.0-beta) in every results file.
- Corpus statistics (BM25 IDF/avgdl, calibration distributions,
  vocabulary counts, damage-rate profiles) are fit over the DECLARED
  universe for their phase (typically the full non-test universe),
  never over query-derived subsets. Any deviation is a documented
  decision, not a default. (Added 2026-07-22 after the E1.3
  reconciliation; see p5c_report.md.)
- Model-input encoding goes through
  `hittite_tokenizer.encode_fragment_window()`; local
  re-implementations are forbidden. (Added 2026-07-22 after the E2
  content-blind seam-scoring bug — a per-script reimplementation of
  this exact step silently fed `<UNK>`-only input to the frozen D14
  head for an entire phase; see p5c_report.md / p5c2_report.md.)
- Corpus build = governed dataset with lineage: every transform
  scripted, no hand edits; derived datasets carry provenance metadata.
- Stdlib-or-common-deps preference; pin versions in
  requirements.txt; everything runs on the local laptop.
- Small artifacts (reports, metrics JSON, failure samples) are the
  unit of exchange with the browser-Claude architect sessions; never
  ship the raw corpus or weights back and forth.
- Outputs of every phase: a runnable script + a small human-readable
  report.
- **File layout (Phase 2 reorganization, 2026-07-22):** the complete,
  immutable Phase 1 snapshot lives under `Archive/`, including its
  numbered pipeline scripts and historical results. Selected durable
  utilities and inputs carried into Phase 2 are copied into the live
  `lib/`, `scripts/`, `configs/`, `demo/`, `p2_out/`, and `p4_out/`
  paths. Earlier phase-sequence bullets below reference the historical
  implementations in `Archive/scripts/`; a same-named live copy exists
  only where Phase 2 still needs that asset. Always invoke active scripts
  from the project root, never after `cd scripts` — data paths are
  CWD-relative, only `lib/` imports are resolved relative to the script
  file itself. See `README.md` for the live/archive map.

## Phase sequence

- **P1 Inventory** (`01_inventory.py`) — schema census; where CTH,
  joins (`+` notation), provenance, brackets actually live. GATES ALL
  LATER DESIGN.
- **P2 Parser + dataset builder** — leakage-safe splits per cleanroom
  rules; three-way label structure (join / duplicate / negative).
  **DONE (2026-07-20)**, per `specs/P2_PARSER_SPEC.md`. All 5 acceptance
  checks passed. Superseded/amended by P2.5 below — see
  `p2_out/dataset_report.md` for the original P2-only numbers.
- **P2.5 Amendments** — **DONE, ACCEPTED, FROZEN (2026-07-21)**, per
  `specs/P2.5_AMENDMENTS.md`. Scripts `07_metadata_patch.py` → `08_bins.py`
  → `09_join_tiers.py` → `10_resplit.py`, outputs in `p25_out/` (plus
  amended files in `p2_out/`). All 6 acceptance checks passed. Key
  numbers (supersede the P2 block above): 543 real compositions /
  14,046 bin (discovery-pool) documents, bin reframe above; duplicate
  pairs naive 13,451,014 → bins-excluded 234,263; join pairs 1,581,
  now tiered (478 A / 185 B / 918 C, 431 tier-C testable after the
  exclusive-content degenerate guard) — see `p25_out/join_tiers_report.md`;
  **`main_split` FROZEN 2026-07-21, no further re-rolls**: train 6,073
  / dev 760 / test 760 docs (80.0/10.0/10.0 by documents, greedy
  doc-count-balanced re-roll — see `p2_out/split_report.md`), bin docs
  carry `main_split='discovery'`; `site_split` provincial-eval grew
  201 → 314 docs after the verified DAAM/Kp provenance patch (DAAM is
  a multi-site series — see `p25_out/provenance_patch.md`); repo
  git-initialized, commit hash logged in `p2_out/splits.json`. Full
  detail in `p25_out/p25_report.md`.
- **P3 Baselines** — BM25, Tyndall replication. First real numbers.
  MUST consume `p2_out/splits.parquet`'s frozen `main_split` /
  `site_split` columns and respect the bin reframe (discovery-pool
  docs excluded from all supervision and metrics).
- **P4 Sign tokenizer + masked-span pre-training.**
- **P5 Bi-encoder + edge-continuation scorer + rerankers.**
- **P6 Evaluation matrix + ablations** (restorations, pre-training,
  cross-site, self-training rounds, fragment length, genre).
- **P7 Candidate list for expert verification + draft paper.**

## Out of scope (do not drift)

Morphological glossing; machine translation; sign-image/photo models;
3D break geometry (the CuKa / "3D-Joins und Schriftmetrologie"
projects at Würzburg/Mainz own that modality — our lane is textual
content); decipherment framing of any kind (Hittite is deciphered);
minting new ground-truth labels from model output.

## Open questions — P1 answers (2026-07-20)

1. **What does the XML encode for joins, line structure, bracket
   positions, CTH linkage?** Answered — see the schema bullets under
   "Corpus (pinned)" above: joins via `docID`/`TxtPubl`/`lb@txtid` +
   `{€N}` witness sigla, line structure via `<lb>` (`lnr`/`lg`/`cu`),
   breaks via `<del_in/fin>`/`<laes_in/fin>`/`<gap>`/`<space>` (not
   bracket characters), CTH via folder path (`CTH ###_XML`).
2. **How many join-positive pairs exist?** 866 documents carry
   authoritative join notation (docID/TxtPubl/txtid), out of 21,868.
   That's a real but small positive set at the *document* level —
   P2 needs to actually parse the `{€N}` witness lists and per-line
   `lnr` attributions into pairwise edges (a doc with 3+ witnesses
   yields multiple join pairs) before we know the true pair count.
   Until that count is in hand, plan for **pooled training**
   (joins + duplicates) with separate joins-only/duplicates-only/
   pooled evaluation, per the standing three-way-matrix decision —
   treat joins-only training as likely infeasible until P2 says
   otherwise.
3. **How much provincial-site material is present per site?**
   Answered, and it's sparse: of 21,868 docs, Hattusa-prefixed
   (KBo/KUB/IBoT/ABoT/Bo/VBoT/HT) = 19,370 (~89%); provincial total
   is only ~194 (HKM/Maşat 110, Or/Sapinuwa 34, KuSa+KuT/Kuşaklı 42,
   Msk/Emar 7, RS/Ugarit 7, AT/Alalakh 1); 2,297 docs have no
   recognized prefix (need a widened prefix table or manual check —
   likely additional sigla not yet in `SITE_PREFIXES`). **The
   headline Hattusa→provincial generalization experiment will have a
   test set of at most a few hundred fragments** — flag this
   explicitly as a small-sample limitation in the paper, per "report
   more, claim less."
4. **Does the corpus record duplicate-witness relations explicitly,
   or must duplicates be derived via shared CTH membership?**
   Not yet answered by P1 — no explicit "duplicate of X" field was
   observed in the sampled documents; the working assumption is
   duplicates must be *derived* from shared `CTH ###_XML` folder
   membership (multiple docIDs under one composition = candidate
   duplicate/parallel witnesses), which then needs philological
   sanity-checking (same composition ≠ automatically a usable
   duplicate pair — e.g. distant fragments of a very long text may
   share no actual overlapping content). Confirm/refute in P2 by
   checking whether any element beyond `AO:Manuscripts` cross-
   references sibling docIDs.

## Community & citation obligations

- Attribute TLHdig (CC BY 4.0) in every artifact: Müller, Prechel,
  Rieken & Schwemer 2025, DOI 10.5281/zenodo.15459134.
- Cite Tyndall 2012 (baseline), Yavasan & Gordin 2025 (corpus
  methodology), and the ML-for-ancient-languages survey lineage.
- Outreach to the TLHdig team (tlhdig@uni-wuerzburg.de) happens AFTER
  preliminary numbers exist — approach with evidence in hand (standing
  user decision). The email may also request partial exports of
  post-0.2 data.
- Novel verified joins, tools, and derived datasets are offered back
  to HPM.
