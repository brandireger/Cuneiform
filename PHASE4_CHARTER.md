# PHASE4_CHARTER.md — governed multilingual reconstruction and unresolved evidence

**Status:** GATE 2 PASSED; P4-D/P4-E AUTHORIZED (2026-07-25).

Phase 4 is the successor to the Phase 3 expert-playground and real-gap work.
It corrects the language model at the data boundary before any new training,
then makes multilingual evidence and unresolved material first-class parts of
the research system. This charter authorizes preparation and read-only
non-test audits. It does **not** authorize test access, a corpus migration,
GPU training, or promotion of expert annotations to ground truth.

## 1. Why Phase 4 exists

The July 25 `line_lang` migration established a valid canonical value for
`lb@lg` and stopped the witness index from treating every line as Hittite.
That was a necessary containment measure, not the final language design.

The governed split-gated audit opened 20,743 permitted train/dev/discovery
payloads and zero protected-test payloads. It found 9,409 explicit `w@lg`
values and 7,100 valid word assignments in 736 documents that differ from
their enclosing line default, including 5,670 `Hit`-line to `Hur`-word cases.
See `Phase4/phase4_out/gate0_language_audit_report.md`.

The current state therefore has four limitations:

1. `decomposed_corpus.parquet` has no language field.
2. The 60,000-step D14 checkpoint is multilingual-but-unconditioned: it saw
   mixed-language text without being told which language a token belonged to.
3. The current Hittite-only filter operates at whole-line granularity and
   cannot preserve word-level language switches.
4. Language-based content selection is not yet fully represented in the
   evidence registry and downstream run manifests.

Phase 4 treats the frozen checkpoint as a historical unconditioned baseline.
It is not deleted or silently relabeled as a clean Hittite model.

## 2. Phase objective

Build and verify a versioned, word-aware multilingual dataset for TLHdig
0.2.0-beta; expose explicit language policies throughout preprocessing,
retrieval, calibration, and expert-facing output; create an unresolved-
evidence workbench for expert lexical discovery; then train and compare a new
language-conditioned model only after the dataset and compute gates pass.

Hittite remains the primary scientific target. Akkadian, Sumerian, Hattic,
Hurrian, Cuneiform Luwian, and Palaic are typed evidence layers, comparison
strata, and possible sources of parallels—not disposable contamination and
not a new machine-translation objective.

## 3. Binding principles

- Preserve the frozen Phase 1 artifacts and frozen split assignments.
- Exclude the test split from audit, rule design, vocabulary design,
  thresholds, examples, and expert workbench development.
- Preserve raw document-, line-, and word-level language values separately.
- Do not guess malformed, missing, or unrecognized language values.
- Do not equate `<sGr>`, `<aGr>`, or determinative markup with passage
  language. Writing system and linguistic language remain separate fields.
- Every content-selection rule must be an explicit `language_scope`, not an
  omitted optional argument.
- Every language field used to select or transform semantic content must be
  registered and listed in the run manifest.
- Model-produced clusters are `MODEL_DERIVED`; expert decisions are
  provenance-bearing, quarantined annotations.
- Unidentified content is retained with context. It is never silently
  discarded because it is rare, out of vocabulary, malformed, or unresolved.

## 4. Work packages

### P4-A — Source-language semantics audit

Run a read-only, split-gated audit of:

- document `xml:lang`;
- line `lb@lg`;
- word `w@lg`;
- missing, empty, malformed, and unrecognized values;
- within-line language changes and mixed-language documents.

The audit must distinguish absence from an explicit empty value and must not
assume precedence among document, line, and word tags. Deliver a runnable
script, JSON, manifest, and a short report. No test XML may be decoded merely
to discover its `docID`; the safe archive-name/identifier gate must be
resolved first.

### P4-B — Language-layer v2 migration

Gate 0 authorizes building a new versioned language artifact without
modifying `line_lang_v1` or frozen Phase 1 data. It must preserve raw values,
canonical values, validation
statuses, rule IDs, inheritance/override sources, and unresolved states at
the narrowest available source span.

### P4-C — Multilingual token dataset

Create a new token-level dataset under `Phase4/phase4_out/` that joins the
ratified language layer to decomposed tokens using document, line, and
`word_index_in_line`. Required fields and acceptance checks are specified in
`specs/LANGUAGE_LAYERS_V2.md`.

Build explicit projections for:

- `HITTITE_ONLY`;
- `SAME_LANGUAGE_AS_QUERY`;
- `MULTILINGUAL_CONDITIONED`;
- `CROSS_LANGUAGE_PARALLEL`;
- `ALL_LANGUAGES_UNCONDITIONED` (ablation only).

### P4-D — Language-aware functions and evidence packets

Replace silent language-blind defaults in active code with a required
language-scope object. Candidate packets must expose query language, source
language, language compatibility, mixed-language context, enabled
cross-language assistance, and unresolved-language limitations.

### P4-E — Unresolved Evidence Workbench

Build an append-only expert-review zone for illegible signs, partially
preserved readings, uncertain transcriptions, lexical unknowns, tokenizer
OOVs, unrecognized language tags, symbol/encoding anomalies, and parser
anomalies.

The workbench contract is `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md`; its
machine schema is `configs/unresolved_evidence_contract.schema.json`.
Similarity clusters are suggestions. Expert grouping and hypotheses do not
mutate TLHdig or enter a training set automatically.

### P4-F — Language-conditioned pretraining

Training is a separate, explicit gate. The proposed model adds a language
embedding or equivalent span-level conditioning to the sign-level encoder.
It trains on permitted train + discovery self-supervised content, uses dev
only for selection, and never touches test. Sampling must report natural and
balanced language distributions.

Required comparisons:

1. frozen multilingual-unconditioned D14 baseline;
2. clean Hittite-only retraining;
3. multilingual retraining without language conditioning;
4. multilingual language-conditioned retraining;
5. line-only versus word-aware language assignment;
6. natural-frequency versus controlled language sampling.

### P4-G — Downstream reruns and product integration

Only after the new dataset/model pass their gates:

- rerun affected witness, real-gap, and calibration artifacts;
- stratify coverage, candidate-set utility, calibration, and abstention by
  language and mixed-language status;
- expose the production real-gap pipeline and unresolved workbench in the
  expert interface;
- retain same-language and cross-language evidence as separate channels.

## 5. Ratification and execution gates

### Gate 0 — design ratification

Ixca decides:

- the semantics and precedence of `xml:lang`, `lb@lg`, and `w@lg`;
- the treatment of explicit empty word tags;
- whether document language may ever be used as a fallback;
- the evidence classification of canonical/effective language fields;
- the new dataset/output paths;
- the initial workbench categories and expert status vocabulary.

Gate 0 passed on 2026-07-25. The binding choices are:

- valid explicit word language overrides a valid line language;
- absent word language inherits a valid line language;
- explicit-empty word language is preserved as an anomaly and inherits a
  valid line only with `RESOLVED_WITH_SOURCE_ANOMALY`;
- malformed or unrecognized explicit word language remains unresolved;
- document language is provenance only, never a v2 fallback;
- language fields are `EDITORIAL_TRANSCRIPTION` evidence; and
- paths, categories, and expert statuses are fixed in
  `configs/language_layers_v2.json` and
  `reports/phase4_gate0_ratification.md`.

Gate 1 migration implementation is authorized. Test access, training export,
and GPU training remain unauthorized.

### Gate 1 — migration acceptance

Requires deterministic rebuilds, stable hashes, unchanged frozen artifacts,
complete quarantine accounting, exact row-key coverage, and evidence-policy
validation.

**Passed 2026-07-25.** The split-gated migration produced 389,325 source-span
rows (20,742 document, 359,183 line, and 9,400 keyed explicit-word spans).
Nine additional explicit word-language attributes outside the primary parser
`<text>` were reconciled to the Gate 0 census and routed to
`PARSER_ANOMALY`. Two independent builds and Parquet readback share logical
SHA-256
`d0126c4eacc2c6c58711516e725f90193d9cc964a1700ea2a5def3289c7c9296`;
all frozen hashes remained unchanged and zero protected-test payloads were
opened. See `migrations/language_layers_v2/verification_report.md`.

### Gate 2 — dataset acceptance

Requires token/line/word identity preservation, no `cu` or `mrp*` dependency,
explicit language coverage, reproducible projections, split-purity checks,
and language-aware unit tests.

**Passed 2026-07-25.** The accepted non-test dataset contains 2,923,640
checksum-guarded token rows across 20,711 documents, including 62,810
structural tokens excluded from lexical-language statistics and 247
unresolved lexical tokens. All seven canonical languages and all five
explicit language scopes are represented. Two builds and persisted readback
share logical SHA-256
`35914a01ff03863f76ee0a56352d2d870881dc581c1253430a2eda102e9bfb6a`;
frozen hashes remained unchanged and zero protected-test rows were emitted.

Gate 2 also found that the historical frozen decomposed-token cache collapses
at least one distinct archive-stem pair under one `doc_id`, producing
conflicting token content at the same technical key. The accepted builder
therefore re-walks the exact Gate 1 archive member and verifies its checksum,
using the existing lossless `decompose_document()` implementation. It does
not choose between conflated cached versions or rewrite the historical cache.
See `Phase4/phase4_out/gate2_token_dataset_report.md`.

### Gate 3 — training authorization

Requires a named hypothesis, config, time estimate, GPU budget, falsifier,
checkpoint/output paths, and confirmation that the new vocabulary and model
dimensions cannot overwrite the frozen D14 run.

### Gate 4 — result promotion

Exploratory results remain `[PROBE — not for citation]` until rerun under the
full manifest/tracer regime and jointly promoted.

## 6. Phase definition of done

Phase 4 is complete when:

1. a trained expert can see which language assignment applies to every
   displayed token and why;
2. all unresolved values remain inspectable rather than being dropped;
3. every training and retrieval run declares its language scope;
4. the new model has been compared fairly with Hittite-only and unconditioned
   baselines;
5. language-stratified calibration and abstention are reported with sample
   sizes;
6. unresolved occurrences can be clustered and annotated without becoming
   corpus truth;
7. saved artifacts alone reveal the corpus version, splits, language rules,
   evidence classes, model assistance, and expert annotation provenance.

## 7. Governing artifacts

- `specs/LANGUAGE_LAYERS_V2.md`
- `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md`
- `configs/phase4_preparation.json`
- `configs/language_layers_v2.json`
- `configs/unresolved_evidence_contract.schema.json`
- `Phase4/README.md`
- `reports/phase4_gate0_ratification.md`
- `migrations/language_layers_v2/rebuild_report.md`
- `migrations/language_layers_v2/gate1_acceptance.json`
- `Phase4/phase4_out/gate2_token_dataset_report.md`
- `Phase4/phase4_out/gate2_acceptance.json`
- `Phase4/phase4_out/language_projection_manifest.json`

Gate 2 acceptance authorizes P4-D language-aware APIs and P4-E workbench
implementation. These files do not change an evaluation universe or authorize
test access or GPU training.
