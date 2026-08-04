# AGENTS.md — Hittite Fragment Matching Project

Standing context for all Codex sessions in this repository. Read
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
- **TLHdig Beta 0.3 is audited but not adopted** (2026-07-23). The
  split-gated audit found 2,137 candidate-only filename stems, but also
  increased duplicate-stem ambiguity and 11 introduced non-test XML parse
  errors. TLHdig 0.2 remains pinned and the frozen splits remain controlling.
  Before any migration, resolve identifiers and parser compatibility under
  `specs/CORPUS_EXPANSION_AUDIT.md`; see
  `reports/corpus_expansion_tlhdig_03_audit.md`.
  The completed metadata-first follow-up reduced the 2,137 candidate-only
  stems to 2,083 plausible additions after conservative identifier
  reconciliation. Of those, 1,753 (84.16%) map to discovery bins and only 281
  prospectively to train compositions. Candidate 0.3 also contains 90
  duplicate identifiers spanning frozen split classes or an unknown CTH,
  including 21 involving test. Direct replacement is therefore prohibited;
  the next gate is a separate versioned ingestion prototype with canonical
  identifier groups and checksum-guarded XML repairs. See
  `reports/corpus_expansion_tlhdig_03_migration_design.md`.
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
  **P4-D (2026-07-26):** active language selection goes through
  `lib/language_scope.py` (a required, validated `LanguageScope`) and
  `lib/language_lookup_v2.py` (word-aware effective language over the Gate 2
  dataset). `p2e_witness_recoverability.render_fragments` — the shared
  anchor-index construction behind every P2-E script and the real-gap
  pipeline — REQUIRES `language_scope` and `language_index`; the old
  optional `line_lang_lookup=None` default is gone. The real-gap QUERY side
  is language-resolved too: a gap may only ASK under the same explicit scope
  that governs which witness lines may ANSWER. `lib/hittite_tokenizer.py` and
  `scripts/rebuild_tokenizer_hittite_only.py` deliberately keep the older
  line-granularity argument (frozen D14 vocabulary path, Gate 3 territory).
  See `reports/phase4_p4d_language_aware_apis.md`.
- Known caveat (per the TLHdig team): philological quality is uneven —
  it is a living community archive, not a critical edition. Quality
  filtering must be explicit and reported, never silent.
- **Actual schema is AOxml/HPM (hethiter.net Hethitologie Portal
  Mainz format), not the SimTex plaintext convention originally
  assumed here — verified via `01_inventory.py` (P1, run
  2026-07-20) against the real corpus. Key structure:**
  - `<lb txtid lnr lg cu>` = one transliterated line. `lnr` = line
    label (e.g. "Vs.? 1′"); `lg` = the **line-level** language code
    (Hit, Akk, Hat, Hattian, ...), but it is not the only language
    signal. The Phase 1 inventory records **10,846 `w@lg` attributes**,
    often on embedded spans whose value differs from the enclosing
    `lb@lg`. Document `xml:lang`, line `lb@lg`, and word `w@lg` must
    therefore remain separate until their precedence is ratified under
    `specs/LANGUAGE_LAYERS_V2.md`. The July 25 line-only Hittite filter
    is a containment measure, not the final language model. `cu` = raw
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
  - `<w trans lg mrp0sel mrp1..mrp7>` = word. `trans` = transliterated
    form (the primary text signal); optional `lg` marks a narrower
    language span and must not be discarded by token decomposition;
    `mrp*` = ranked morphological
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
  (`Archive/p1_out/`, renamed from `inventory_out/` 2026-07-21 for
  consistency with `Archive/`'s p2_out/p25_out/p3_out/p4_out), not
  assumptions. If inventory results and this file disagree, the
  inventory wins; update this file.

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
  `Phase1_pipeline/p2_out/join_pairs.jsonl`, reported both included and excluded.
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
- Phase 4 language-aware code must additionally require an explicit
  `language_scope`; omitted/`None`/`auto` language behavior is prohibited.
  Language-based selection is semantic evidence and must be registered and
  included in the run manifest.
- Corpus build = governed dataset with lineage: every transform
  scripted, no hand edits; derived datasets carry provenance metadata.
- Stdlib-or-common-deps preference; pin versions in
  requirements.txt; everything runs on the local laptop.
- Small artifacts (reports, metrics JSON, failure samples) are the
  unit of exchange with the browser-Codex architect sessions; never
  ship the raw corpus or weights back and forth.
- Outputs of every phase: a runnable script + a small human-readable
  report.
- **File layout (reorganized 2026-07-21, once D14/D15 finished running):**
  numbered pipeline scripts live in `scripts/`, reusable modules in
  `lib/`, active configs in `configs/`, the parallel demo track in
  `demo/`. Earlier phase-sequence bullets below reference bare script
  names (e.g. "`01_inventory.py`") from before this reorg — read those
  as `scripts/01_inventory.py` etc. Always invoke from the project
  root (`python scripts/19_pretrain.py ...`), never after `cd scripts`
  — data paths are CWD-relative, only `lib/` imports are resolved
  relative to the script file itself. See `README.md`'s "Where things
  are" for the full map.
- **Phase-folder split (2026-07-23):** the complete, immutable Phase 1
  snapshot stays under `Archive/` — do not rewrite it in place.
  `Archive/superseded_docs/` is a separate, non-frozen holding area for
  root docs absorbed into a canonical file or superseded by a newer
  handoff (see `Archive/superseded_docs/README.md`); unlike the frozen
  snapshot, it gains new entries over time. Live per-phase outputs are
  split by phase folder: `Phase1_pipeline/` holds carried-forward
  outputs of the original numbered P2/P3/P4 steps (`p2_out/`,
  `p3_out/`, `p4_out/`); `Phase2/` holds its lettered research outputs;
  `Phase3/` holds the real-gap/demo outputs; and `Phase4/` is reserved
  for the prepared multilingual-dataset and unresolved-evidence phase.
  Give every later phase its own top-level folder.

## Current successor program (Gate 3 Stage 1 complete; Phase 5 handoff current)

`PHASE4_CHARTER.md` governs the successor phase. It has two linked
deliverables:

1. a word-aware multilingual language layer, token dataset, explicit
   language APIs, and language-conditioned retraining; and
2. an Unresolved Evidence Workbench that preserves unknown signs, words,
   language tags, and anomalies with context for expert grouping.

`PHASE4_SUCCESSOR_HANDOFF.md` preserves the accepted hashes, rebuild commands,
and Gates 0–2 history. The current operational status and next bounded work are
recorded in `PHASE5_SUCCESSOR_HANDOFF.md`.

**Phase 4 Gate 2 passed 2026-07-25.** The deterministic, split-gated
language-span migration and 2,923,640-row multilingual token dataset are
accepted. P4-D language-aware APIs, P4-E, P4-E2, and the pre-training P4-G
rerun are complete. **Gate 3 was ratified 2026-08-02 for Stage 0 and the two
named Stage 1 runs only; both ran, and the pre-registered hypothesis was
REJECTED (see the P4-F bullets below). Stage 2 is NOT authorized.** All other
GPU training, and protected-test access in any form, remain
unauthorized. The frozen D14 checkpoint remains a historical
multilingual-unconditioned baseline. Expert workbench records are append-only
quarantined annotations and never become corpus truth automatically.

Gate 2 found that the historical frozen decomposed-token cache conflates at
least one distinct archive-stem pair under one `doc_id`, yielding conflicting
token content at the same technical key. New Phase 4 token datasets must use
the exact checksum-guarded Gate 1 archive member and the shared
`decompose_document()` implementation; do not choose or deduplicate a
conflated cached version silently. The historical cache remains immutable.

**P4-E Unresolved Evidence Workbench implemented 2026-07-26.** Unresolved
material (illegible signs, partially preserved readings, uncertain
transcriptions, tokenizer OOVs, language-tag anomalies, encoding and parser
anomalies) is retained in a governed expert-review zone rather than dropped:
`lib/unresolved_evidence.py` is the executable contract,
`scripts/phase4_unresolved_extraction.py` builds 238,745 occurrences, and
`scripts/phase4_unresolved_clustering.py` emits deterministic same-language
(default) and opt-in cross-language cluster proposals. Everything there is
`NOT_CORPUS_TRUTH`; expert events are append-only, hash-chained, and
quarantined. `LEXICAL_UNKNOWN` stays empty by design — it is reserved for
expert assertion and is never set by extraction. The machine schema was
amended during implementation (nullable location for text-external anomalies;
new `MISSING_LANGUAGE_TAG`) and ratified as **1.1.0**; the interim 1.0.1 was
never released. See `reports/phase4_p4e_unresolved_workbench.md`.

- **Ratified 2026-07-27** (`reports/phase4_p4de_ratification.md`): workbench
  contract **1.1.0** (nullable location for text-external anomalies;
  `MISSING_LANGUAGE_TAG`; `RARE_FORM`; `SYSTEM_PROPOSAL`). `RARE_FORM` is
  populated by a governed frequency detector and is a claim about THIS CORPUS;
  `LEXICAL_UNKNOWN` is reserved for expert assertion and is never set by
  extraction, because frequency cannot establish that a form is unknown to
  Hittitology. Deterministic groupings are `SYSTEM_PROPOSAL`, not
  `MODEL_PROPOSAL`. Annotation events must be backed up via
  `scripts/phase4_workbench_backup.py` before and after every expert session.
  Mixed-line policy stays `EXCLUDE_LINE`. The P2-E/real-gap rerun under P4-D is
  deferred but MUST precede any P7 paper drafting -- ten affected reports carry
  a `[PREDATES P4-D]` stamp until then.

- **P4-E2 expert interface (2026-07-27).** The workbench now has a UI:
  `scripts/phase4_workbench_review_export.py` builds a review queue,
  `demo/workbench_unresolved_prototype.html` renders it, and
  `scripts/phase4_workbench_ingest_events.py` is the ONLY supported path from
  a browser export into the append-only log -- it recomputes each event's
  `reviewed_record_sha256` against the record on disk, refuses on mismatch,
  refuses when the log's head is in no backup ledger entry, and re-chains onto
  the real head. A queue is a VIEW: it never mutates an occurrence, a proposal,
  or an accepted hash. Queue policy `contentful_sequence_length_v2` excludes
  placeholder-only sequences and sequences under 2 signs and ranks by sequence
  length before document count -- clustering is Zipfian (largest same-language
  cluster: 95,530 members, sequence `x`; ranking by document count instead
  surfaces the single signs `a`, `i`, `e`). **The two exclusions were decided
  separately on 2026-07-31** -- see the ratification bullet below. **Browser smoke
  test passed 2026-07-29** after unsupported native prompts were replaced with
  an accessible in-page dialog. The test event remained browser-local and was
  discarded; nothing was exported or ingested. See
  `reports/phase5_p4e2_browser_smoke.md`.

- **P4-G downstream rerun DONE (2026-07-27)** (`reports/phase4_p4g_rerun.md`).
  All ten artifacts recomputed under the required word-aware `HITTITE_ONLY`
  scope; ratification decision 5's deadline is met and P7 drafting is no longer
  blocked on language-contaminated numbers. Nine `[PREDATES P4-D]` stamps are
  gone because the reports are current; `real_gap_census_report.md` KEEPS its
  note -- the census is deliberately language-blind, so that note was a scope
  disclosure, not a staleness claim. `scripts/p4d_stamp_stale_reports.py --check`
  now runs in CI and enforces a two-sided invariant: a stale report cannot lose
  its warning, and a report listed in `RERUN_UNDER_P4D` cannot keep one.
  Direction of the correction: the witness side loses ~5% of eligible spans and
  coverage rates RISE (a1_m1 72.06% -> 73.73%) -- the contamination was
  inflating denominators with material the index could never serve. Query-side
  exclusions measured at 9.5%, matching P4-D's estimate, now typed by reason.
  Calibrated coverage is **839 of 181,051 corpus real gaps (0.46%)**;
  cross-line anchors remain **89.9% of anchored gaps and entirely
  uncalibrated** -- the highest-leverage remaining backend item.

- **P2-E8 cross-line recoverability census DONE (2026-07-27)**
  (`reports/phase2_p2e8_cross_line_recoverability.md`,
  `scripts/p2e8_cross_line_recoverability.py`). The prerequisite for any
  cross-line calibration: it establishes whether cross-line anchors have
  recoverable witness support at all. **It is a census, not a calibration** --
  no number in it may be shown beside a candidate as a rate. Key result: at
  `a2_m1`, same-line spans include the true reading in 20.94% of eligible
  cases and cross-line spans in **4.27%**. Borrowing a same-line rate for a
  cross-line anchor would have overstated the evidence by ~5x on 89.9% of
  anchored real gaps -- the standing prohibition, adopted on principle, now
  has a number. Two witness-admission rules are measured side by side and
  BOTH await ratification: `STRICT` (only boundary-crossing witnesses) and
  `LAYOUT_AGNOSTIC` (also same-line witnesses, on the ground that line
  division is scribal layout, not textual structure), which roughly doubles
  gold inclusion (4.27% -> 7.21%). Where the break falls barely matters
  (2.87-3.62% across all five boundary regions); that a break is crossed at
  all is what costs. 41.5% of adjacent line boundaries are REFUSED rather
  than crossed because a neighbouring line is out of scope -- crossing one
  would fabricate adjacency, the same fabrication `EXCLUDE_LINE` prevents.

- **P2-E9 cross-line calibration DONE (2026-07-28)**
  (`reports/phase2_p2e9_cross_line_calibration.md`,
  `scripts/p2e9_cross_line_calibration.py`). Fold-structured per-rank
  calibration for cross-line anchors at cell `a2_m1`, reusing P2-E3's
  composition folds and P2-E2/P2-E4's selector and rank machinery rather than
  reimplementing them (a second implementation is a second chance to get
  leakage wrong). **Result: every fold abstains under both admission rules.**
  Cross-line raw top-1 agreement is 24.2% (`STRICT`) / 32.9%
  (`LAYOUT_AGNOSTIC`), and the best selector reaching >=50 accepts tops out at
  79.7% / 81.2% -- short of the inherited **0.90** calibration target that
  same-line spans clear at ~91%. The pipeline abstaining on every cross-line
  gap is therefore CORRECT BEHAVIOUR, not a failure: it refuses to present a
  candidate at a rate it cannot certify. A target-sensitivity sweep is
  reported (0.70 -> 308 spans @ 71.4% STRICT / 778 @ 73.0% LA; 0.80 ->
  unreachable STRICT / 233 @ 81.1% LA) and is **explicitly NOT a proposal**:
  choosing a target after seeing which one yields output would report a search
  as a measurement. **Ixca must ratify (a) `STRICT` vs `LAYOUT_AGNOSTIC` and
  (b) whether cross-line gets its own declared calibration target.** Until
  then `real_gap_calibration.py` keeps gating on `if not g["is_cross_line"]`.

- **`LAYOUT_AGNOSTIC` RATIFIED 2026-07-28** (`reports/phase2_p2e9_ratification.md`).
  A cross-line gap may be answered by any independent witness occurrence of its
  anchor pair, INCLUDING same-line ones: line division is scribal layout, not
  textual structure. `STRICT` is retained as a declared ablation, never
  deleted. Policy lives in `configs/p2e9_cross_line_calibration.json`.
  **The cross-line calibration target remains UNRATIFIED (null) and every
  consumer fails closed via `require_calibration_target()`** -- cross-line tops
  out near 81% under the ratified rule, so inheriting same-line's 0.90 would
  encode permanent abstention as if it were a policy. Adopting the admission
  rule alone changes NOTHING operationally; `real_gap_calibration.py` still
  correctly gates on `if not g["is_cross_line"]`.

- **Cross-line calibration universe widened + held-out rates adopted
  (2026-07-28).** `p2e9` now fits over the governed non-test universe
  (train + dev, non-bin, test excluded AND asserted) rather than dev only,
  declared in `configs/p2e9_cross_line_calibration.json`. Safe because this
  calibration consumes NO model -- it counts independent witness families in
  an anchor index -- and folds stay composition-level. Effect: held-out
  accepts 55 -> **8,208** across 279 compositions, and the 12.8-point
  calibration-transfer gap seen on dev-only collapsed to **0.0** (fit-set
  77.5%, held-out 77.5%). It was a small-sample artifact, not a property of
  cross-line evidence. **The ratified 0.75 target is met on held-out
  compositions.** `LAYOUT_AGNOSTIC` beats the `STRICT` ablation on both mass
  (3.3x) and transfer (0.0 vs 2.3 pts). Consumers MUST display
  `rank_calibration_held_out`; `rank_calibration_calibration_set` exists only
  to keep the transfer gap visible and would have overstated by ~13 points on
  the dev-only run.

- **Cross-line APPLIED to the real-gap pipeline (2026-07-28).**
  `real_gap_calibration.py` no longer gates on `if not g["is_cross_line"]`.
  Cross-line gaps are scored against their OWN P2-E9 calibration
  (`LAYOUT_AGNOSTIC`, target 0.75) using `p2e9.merged_ranking` -- the same
  ranking construction that was calibrated, never a second implementation.
  `prepare_scope()` now exposes `line_sequences` so the cross-line witness
  index is built over the same rendered, language-resolved lines. Result:
  5,062 cross-line gaps eligible, **61 accepted**, on top of same-line's
  unchanged 703/41 -- single-sign calibrated coverage 41 -> **102**.
  **Same-line and cross-line are scored and reported SEPARATELY and must
  never be pooled** (different populations, different ratified targets).
  **Critical distinction, now enforced in both scripts:** the rate ATTACHED to
  a gap is `rank_calibration_calibration_set` (fit on compositions disjoint
  from the fold's evaluation CTHs, matching P2-E4); `rank_calibration_held_out`
  is the QUALITY claim only -- it is measured on the very compositions the
  gaps come from, so attaching it per-gap would be circular. If the cross-line
  artifacts are missing or the target is unratified, cross-line stays gated
  rather than borrowing same-line rates.

- **Real-gap production scope widened (2026-07-28).** The first cross-line
  application above inherited P2-E4's 38-CTH same-line scope, even though
  P2-E9 has usable folds for 279 CTHs. `real_gap_calibration.py` now passes the
  UNION of the applicable same-line and cross-line CTH sets to
  `prepare_scope()` while preserving each population's own eligibility check:
  38 same-line CTHs + 279 cross-line CTHs = **288 distinct CTHs / 6,145
  documents**. Same-line remains exactly **703 eligible / 41 accepted**;
  cross-line expands from 5,062 / 61 to **46,118 eligible / 577 accepted**.
  This is a scope correction, not recalibration: P2-E4 and P2-E9 artifacts,
  targets, fold assignments, and held-out quality claims are unchanged.
  Missing or unratified P2-E9 artifacts still fail closed to the same-line
  scope. See `reports/phase5_real_gap_scope_widening.md`.

- **P2-E10 cross-line MULTI-SIGN calibration DONE (2026-07-28) -- NEGATIVE
  RESULT, deliberately not applied** (`reports/phase2_p2e10_cross_line_multisign.md`).
  Set-inclusion estimand (not per-rank; an expert is shown a SET), adaptive
  anchor length reusing `p2e6.build_adaptive_records` unchanged. Set inclusion
  is **13.8% at two signs falling to 6.7% at five**, with a **0.0-point**
  transfer gap on 235,628-377,379 held-out spans -- the calibration is sound,
  and what it establishes is that the channel does not work. **Do NOT wire
  P2-E10 into `real_gap_multisign_calibration.py`**: a calibrated 8%
  set-inclusion rate is honest but not decision-support. This bounds where
  cross-line evidence helps -- single-sign yes (P2-E9, applied), multi-sign no.

- **Empty-middle display treatment RATIFIED (2026-07-30)**
  (`reports/phase5_empty_middle_census.md`,
  `reports/phase5_empty_middle_display_treatment.md`). Both anchor-index
  builders iterate `range(MAX_WITNESS_MIDDLE + 1)`, so a middle of length ZERO
  -- the two anchors standing adjacent in a witness -- is a first-class
  proposal and can rank first on real support. For a single-sign gap it is not
  a reading: observed gold lengths are `{1: 703}`, so it can be ranked but
  never correct. Measured before acting: **109 of 577 accepted cross-line gaps
  (18.9%)** show it at rank 1, against 1 of 41 same-line, and in **79 of those
  109 it is the ONLY alternative** -- filtering surfaces an abstention, not a
  better reading (zero rank-1 changes, accepts 577 -> 517). Filtering is also
  not free: the empty middle was in the index when P2-E4 and P2-E9 were FIT,
  so any filter must ship with a refit or it decouples the rate from the thing
  it rates. **Adopted: the option keeps its rank and witness support but is
  rendered as typed contradictory evidence, not a candidate reading, and its
  rank-level group rate is WITHHELD** -- that rate's estimand is agreement with
  the true attested middle, which this option cannot be. Four branches by query
  kind (`lib/expert_decision_contract.py`), because they are four different
  situations: illegible trace (57), **editorial restoration (41) -- the system
  catching a scholarly bracket the witness tradition contradicts, cleanroom
  rules 3 and 6 in operation**, indeterminate lacuna (11), hidden attested sign
  (evaluation only). Schema validation is two-sided: an option proposing no
  signs MUST carry a display block, and a display block on an option that
  proposes signs is rejected.

- **P4-E2 queue policy RATIFIED, in part (2026-07-31)**
  (`reports/phase5_p4e2_queue_policy_ratification.md`,
  `configs/p4e2_queue_policy.json`). The two exclusions had been bundled since
  P4-E2; measured separately they are not comparable, so they got different
  answers. **Contentless-sequence exclusion: RATIFIED**, character set widened
  on the line *the editor's apparatus is contentless; anything that could have
  been on the tablet is not*. It is load-bearing -- with the rule off, 21 of
  the 60 visible same-language slots become runs of `x` and `_`, and since
  ranking is length-DESCENDING the top item would be twelve underscores.
  **Digits are deliberately kept**: `10` alone occurs in 81 documents and
  `d 10` in 70 -- the Storm God with a damaged determinative; `30` is the Moon
  God. Excluding digits would silently delete divine names from expert review.
  Safety invariant: no sequence carrying a sign value can be caught, since the
  only letter in the set is the illegible placeholder `x`. The set is pinned
  **by codepoint** in tests after a homoglyph near-miss (corpus uses
  U+2329/U+232A; the visually identical CJK U+3008/U+3009 occur zero times).
  **Minimum sequence length 2: UNRATIFIED, DEFERRED** to the second queue --
  it is a no-op (rebuilding with 1 leaves the queue content hash
  byte-identical), and its rare tail is not noise (468 of 592 rare
  single-sign clusters are plain sign readings, largely Sumerograms).
  `phase4_workbench_review_export.load_queue_policy()` fails closed without the
  record; per-rule status travels into the manifest as `selection_rule_status`
  and onto the screen. Policy versioned `contentful_sequence_length_v2`,
  because a changed selection rule changes the queue an expert worked from.
  `max_clusters_per_channel`, `max_members_displayed_per_cluster`, the ranking,
  and `context_lines_per_side` remain UNRATIFIED.

- **Both expert prototypes browser-verified (2026-07-31)**
  (`reports/phase5_browser_verification.md`) -- first ever recorded browser
  check for `demo/taksan_missing_text_prototype.html`. A human visual check
  against a supplied checklist, not an automated capture; no screenshots or DOM
  dumps were retained. Still open and named there: no export was downloaded and
  no ingest exercised, and **no automated regression capture exists** -- the
  string-level tests pin that required wording and hooks are present but cannot
  observe a CSS selector matching nothing.

- **Empty-middle branch wording reviewed as copy (2026-08-02)**
  (`reports/phase5_empty_middle_copy_review.md`). Closes the former handoff
  item 3: the four `EMPTY_MIDDLE_QUERY_KINDS` texts in
  `lib/expert_decision_contract.py` had been reviewed as logic but never as
  the prose a Hittitologist reads cold, mid-review, with nothing else on
  screen.

- **The second queue DONE (2026-08-02)** (`reports/phase5_second_queue.md`,
  `scripts/phase4_workbench_second_queue_export.py`). Closes the former
  handoff item 4 at the **data/export layer only -- no UI**. Two populations
  were structurally unreachable through the first queue: **468-599 rare
  single-sign clusters** (surfaced by `RARE_BY_RARITY`, ranked by ascending
  document count -- the literal opposite of the first queue's rank key) and
  **~13,900 ungrouped occurrences** whose sequence is unique (surfaced by
  `LOCAL_CONTEXT_PARALLEL`, a genuinely new channel grouping by flanking
  attested context rather than own content). A separate script, never a mode
  on the first queue: `workbench_review_queue.js`'s
  `channels_logical_sha256` is a pinned invariant and stays untouched.
  Window size was measured, not guessed (window=1 joins 4,089 of 13,901;
  window=2 joins 73). `minimum_sequence_length` remains
  `UNRATIFIED_DEFERRED` -- `RARE_BY_RARITY` exists precisely to admit what
  its length-descending sibling suppresses.

- **Deferred-issues sweep (2026-08-02)**
  (`reports/phase5_deferred_issues_sweep.md`). Three real fixes, each
  confirmed by running it: `line_lang_rebuild.py`/`line_lang_audit.py`
  requested `artifact_strict` while asking for `line_lang`, which Gate 0
  reclassified to `EDITORIAL_TRANSCRIPTION` (both had been throwing on their
  manifest step ever since, after the visible artifact was already written);
  `07_metadata_patch.py`'s auto-chain to `04_edges.py` never resolved under
  its own documented usage; four `Archive/scripts` files hardcoded a Windows
  git path. **Known and unfixed: JSON key-order nondeterminism** from
  Python's per-process hash randomization -- values are identical, byte order
  is not, so a rebuilt report diffs dirty without meaning anything changed.
  Pinning `PYTHONHASHSEED` is a project-wide reproducibility decision, not a
  discrete bug.

- **P4-F Gate 3 RATIFIED 2026-08-02** (`reports/phase4_p4f_gate3_proposal.md`).
  Authorizes **Stage 0 (code) and Stage 1 (two named runs) ONLY**. Stage 2
  (Hittite-only retrain, sampling ablation, granularity ablation), any use of
  a conditioned checkpoint beyond `[PROBE -- not for citation]`, any P4-G
  rerun against a new checkpoint, and protected-test access all remain
  separately gated. `--tag base` is reserved and refused: it is D14's own path.

- **P4-F Stage 1 DONE (2026-08-03) -- pre-registered hypothesis REJECTED**
  (`reports/phase4_p4f_stage1.md`, `scripts/phase4_p4f_pretrain.py`,
  `scripts/phase4_p4f_stage1_eval.py`). Both arms reached 60,000 steps.
  `in_doc` AUC: arm A (unconditioned) **0.6981**, arm B (conditioned)
  **0.7263**, delta **+0.0282**, paired bootstrap 95% CI **[+0.0144,
  +0.0424]**. The margin clause (>= +0.02) is met on the point estimate; the
  clause requiring arm B to exceed **D14's 0.7461** is NOT met, and either
  failure rejects. **Stage 2 is therefore not authorized.**
  Kept distinct from the verdict: **conditioning helped on every tier**
  (cross_genre +0.034, random +0.065, pooled +0.031) and the CI excludes
  zero, so the effect is real -- but the CI's lower bound sits BELOW the
  margin, so "conditioning helps" is supported while "helps by >= +0.02" is
  not. What failed is the absolute bar: **arm A, the control, is below D14 on
  every tier**, and arm B adds its ~+0.03 to that lower baseline. Candidate
  causes recorded, none tested: `MULTILINGUAL_CONDITIONED` admission refuses
  7,610 lines D14 trained on (2.1%); different seed; and the falsifier's D14
  clause compares against a number computed on a different fragment
  population. **The rule was not relitigated after seeing the data.**
  The verdict is deliberately NOT read off the loss curve -- training-time
  evals see ~80 examples and swing ~4 AUC points with no trend, and arm B's
  final one read 0.8839. The eval reproduces D14's protocol exactly, verified
  rather than assumed: same tier composition to the example (`in_doc` n=1,649
  of 1,920) under a different seed, with the arms paired on one shared,
  model-independent example set.
  **Standing constraint for Phase 4 data code:** data admission is NOT an
  arm's conditioning scope. Handing an unconditioned arm the ratified
  `ALL_LANGUAGES_UNCONDITIONED` scope silently gives it MORE data, because
  `language_lookup_v2._classify` short-circuits every filter for an ablation
  scope. Both arms admit under `MULTILINGUAL_CONDITIONED`; only conditioning
  differs.


- **P4-F Stage 1 CORRECTED RERUN DONE (2026-08-04) -- STILL REJECTED, ON THE
  OTHER CLAUSE** (`reports/phase4_p4f_stage1_matched.md`). The first attempt
  trained both arms at half D14's batch size
  (`reports/phase4_p4f_baseline_diagnostic.md`); both were retrained at D14's
  actual config (32/32/warmup 2000, seed 20260722), authorized as covered by
  the existing Gate 3 ratification. Falsifier, eval script, example set and
  seed all UNCHANGED, so the numbers are directly comparable.
  `in_doc` AUC: arm A **0.7521**, arm B **0.7594**, delta **+0.0073**, 95% CI
  **[-0.0063, +0.0196] -- INCLUDES ZERO**. The clauses swapped: the margin is
  now NOT met while arm B now DOES clear D14's 0.7461. Both clauses have now
  been tested under conditions where they could pass; neither does.
  **Headline: at a correct training budget the conditioning effect is not
  distinguishable from zero.** The +0.0282 measured at half budget did not
  survive proper training, and the per-tier picture agrees -- arm B is now
  BELOW arm A on cross_genre (0.8996 vs 0.9033), which is what noise looks
  like. **NOT claimed:** that the two deltas differ significantly; their CIs
  overlap, so "conditioning helps only when under-trained" is a hypothesis
  consistent with two runs, not a result.
  The batch-size diagnosis is confirmed on the falsifier's own metric:
  **matched arm A 0.7521 vs D14 0.7552** (gap 0.003, against the batch-16
  arm's 0.057), which also retires seed as an explanation for the original
  gap. **Stage 2 remains NOT authorized and is now HARDER to justify** -- the
  first rejection could be blamed on a defective baseline; this one cannot.
  Any future proposal should lead with seed variance: one seed per arm is
  still the binding limitation, and an effect this small cannot be settled by
  a single draw. The batch-16 pair is RETAINED as a training-budget ablation.

## Phase sequence

- **P1 Inventory** (`01_inventory.py`) — schema census; where CTH,
  joins (`+` notation), provenance, brackets actually live. GATES ALL
  LATER DESIGN.
- **P2 Parser + dataset builder** — leakage-safe splits per cleanroom
  rules; three-way label structure (join / duplicate / negative).
  **DONE (2026-07-20)**, per `specs/P2_PARSER_SPEC.md`. All 5 acceptance
  checks passed. Superseded/amended by P2.5 below — see
  `Phase1_pipeline/p2_out/dataset_report.md` for the original P2-only numbers.
- **P2.5 Amendments** — **DONE, ACCEPTED, FROZEN (2026-07-21)**, per
  `specs/P2.5_AMENDMENTS.md`. Scripts `07_metadata_patch.py` → `08_bins.py`
  → `09_join_tiers.py` → `10_resplit.py`, outputs in `p25_out/` (plus
  amended files in `Phase1_pipeline/p2_out/`). All 6 acceptance checks passed. Key
  numbers (supersede the P2 block above): 543 real compositions /
  14,046 bin (discovery-pool) documents, bin reframe above; duplicate
  pairs naive 13,451,014 → bins-excluded 234,263; join pairs 1,581,
  now tiered (478 A / 185 B / 918 C, 431 tier-C testable after the
  exclusive-content degenerate guard) — see `p25_out/join_tiers_report.md`;
  **`main_split` FROZEN 2026-07-21, no further re-rolls**: train 6,073
  / dev 760 / test 760 docs (80.0/10.0/10.0 by documents, greedy
  doc-count-balanced re-roll — see `Phase1_pipeline/p2_out/split_report.md`), bin docs
  carry `main_split='discovery'`; `site_split` provincial-eval grew
  201 → 314 docs after the verified DAAM/Kp provenance patch (DAAM is
  a multi-site series — see `p25_out/provenance_patch.md`); repo
  git-initialized, commit hash logged in `Phase1_pipeline/p2_out/splits.json`. Full
  detail in `p25_out/p25_report.md`.
- **P3 Baselines** — BM25, Tyndall replication. First real numbers.
  MUST consume `Phase1_pipeline/p2_out/splits.parquet`'s frozen `main_split` /
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
