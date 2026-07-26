# Phase 4 successor handoff — Gates 0–2 complete

**Handoff date:** 2026-07-26
**Repository state:** Gate 2 accepted; P4-D language-aware APIs and P4-E
Unresolved Evidence Workbench implementation are next. Protected-test access
and GPU training remain unauthorized.

Read `AGENTS.md` first. It remains the design authority. This handoff records
the operational state and does not widen any authorization boundary.

## Completed work

### Gate 0 — language design

Ratified rule `word_override_else_line_v2`:

- valid explicit `w@lg` overrides `lb@lg`;
- absent `w@lg` inherits a valid line language;
- explicit-empty `w@lg` is preserved and inherits only with
  `RESOLVED_WITH_SOURCE_ANOMALY`;
- malformed or unrecognized explicit word tags remain unresolved;
- document `xml:lang` is provenance only, never a fallback; and
- language annotations are `EDITORIAL_TRANSCRIPTION`.

The split-gated audit opened 20,743 permitted payloads and zero protected-test
payloads. It found 9,409 explicit word-language attributes.

Authoritative records:

- `reports/phase4_gate0_ratification.md`
- `configs/language_layers_v2.json`
- `Phase4/phase4_out/gate0_language_audit_report.md`

### Gate 1 — source-span migration

Accepted artifact:
`migrations/language_layers_v2/language_spans.parquet`.

- 389,325 rows: 20,742 document, 359,183 line, and 9,400 keyed explicit-word
  spans;
- 9 additional word-language attributes outside the primary parser `<text>`
  are preserved in `quarantined_source_anomalies.jsonl`;
- zero protected-test payloads opened;
- frozen hashes unchanged; and
- two builds plus persisted readback reproduced logical SHA-256
  `d0126c4eacc2c6c58711516e725f90193d9cc964a1700ea2a5def3289c7c9296`.

Rebuild:

```powershell
python scripts/phase4_language_layers_v2.py
```

### Gate 2 — multilingual token dataset

Accepted artifact:
`Phase4/phase4_out/multilingual_tokens_v2.parquet`.

- 2,923,640 token rows across 20,711 non-test documents;
- 62,810 structural tokens retained and excluded from lexical statistics;
- 247 unresolved lexical tokens retained;
- effective lexical counts: Hit 2,541,890; Hur 129,846; Akk 113,374;
  Hat 41,646; Luw 23,050; Sum 5,893; Pal 4,884;
- 8,445 of 9,400 explicit word-language spans apply to at least one token;
  the other 955 remain preserved in Gate 1, generally because the source word
  produced no decomposed token;
- all five language scopes are explicit and deterministic;
- zero protected-test rows emitted;
- frozen hashes unchanged; and
- two builds plus persisted readback reproduced logical SHA-256
  `35914a01ff03863f76ee0a56352d2d870881dc581c1253430a2eda102e9bfb6a`.

Rebuild:

```powershell
python scripts/phase4_multilingual_token_dataset.py
```

The Parquet artifacts are intentionally gitignored. The small reports,
manifests, acceptance records, projection contract, and quarantine JSONL are
tracked.

## Important cache-collision finding

Do not treat
`Phase1_pipeline/p4_out/decomposed_corpus.parquet` as an unambiguous Phase 4
row source. Gate 2 found that it collapses at least one distinct archive-stem
pair under one `doc_id`, producing conflicting token content at the same
technical key. The historical cache remains immutable.

The accepted Gate 2 builder instead:

1. reads the exact `source_archive_member` admitted by Gate 1;
2. verifies `source_payload_sha256`;
3. calls the shared lossless `lib.decompose_corpus.decompose_document()`;
4. joins the resulting exact line/word keys to the Gate 1 language spans; and
5. fails on duplicate or unsorted identities.

Do not silently choose, merge, or deduplicate conflicting cached rows.

## Next work

### P4-D — language-aware APIs

- Route every active language-sensitive renderer, retriever, scorer, and
  calibration entry point through `lib/language_layers_v2.py`.
- Require an explicit `language_scope`; omitted, `None`, `auto`, `default`,
  and `language_blind` must fail closed.
- `SAME_LANGUAGE_AS_QUERY` and `CROSS_LANGUAGE_PARALLEL` require a resolved
  query language.
- Candidate/evidence packets must expose query language, source language,
  mixed-language status, enabled cross-language assistance, unresolved
  limitations, and the active evidence policy.
- Preserve same-language and cross-language evidence as separate channels.

Do not retrofit every historical Phase 1 script indiscriminately. Start with
the active Phase 3 real-gap path and the expert-facing interface, then add
bounded tests around each migrated call site.

### P4-E — Unresolved Evidence Workbench

Implement the contract in
`specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` and machine schema in
`configs/unresolved_evidence_contract.schema.json`.

Initial intake sources:

- token rows with non-empty `workbench_categories`;
- the 247 unresolved lexical token rows;
- Gate 1 `quarantined_source_anomalies.jsonl`;
- illegible/partially preserved/uncertain transcription states;
- tokenizer OOVs kept distinct from lexical unknowns; and
- parser and symbol/encoding anomalies.

Required boundaries:

- no protected-test occurrences in development mode;
- same-language grouping by default;
- cross-language parallels as an explicit assistance channel;
- model clusters remain `MODEL_PROPOSAL`;
- expert events are append-only and hash-bound;
- `EXPERT_SUPPORTED` is not corpus truth; and
- no annotation enters training without a separate adjudication/export gate.

## Training remains gated

Do not begin P4-F or alter the frozen D14 checkpoint. Gate 3 still requires a
named hypothesis, config, compute estimate, GPU budget, falsifier, new output
paths, sampling policy, and the conditioned-versus-unconditioned tracer.

## Validation and useful commands

Full lightweight validation at handoff:

- 107 unit tests passed;
- Ruff passed for `lib`, `scripts`, `tests`, and `demo`; and
- `git diff --check` passed.

Commands:

```powershell
python -m unittest discover -s tests
ruff check lib scripts tests demo --output-format concise
git diff --check
```

Key Gate 2 records:

- `Phase4/phase4_out/gate2_token_dataset_report.md`
- `Phase4/phase4_out/gate2_token_dataset_manifest.json`
- `Phase4/phase4_out/gate2_acceptance.json`
- `Phase4/phase4_out/language_projection_manifest.json`

If a rebuilt logical hash changes, stop and diagnose it. Do not update the
accepted hash in documentation merely to make a check pass.
