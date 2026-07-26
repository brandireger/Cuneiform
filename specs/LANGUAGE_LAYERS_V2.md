# Language layers v2 — governed multilingual dataset specification

**Status:** GATE 2 PASSED; LANGUAGE-AWARE API/WORKBENCH WORK AUTHORIZED (2026-07-25).

## Purpose

Replace the provisional line-only Hittite filter with a versioned,
word-aware language layer that preserves TLHdig's source encoding and can
support Hittite-only, same-language, multilingual-conditioned, and explicitly
cross-language workflows.

This specification does not modify `migrations/line_lang_v1/`. That artifact
remains the accepted canonicalization of `lb@lg`; v2 adds narrower source
spans and an explicit effective-language derivation after human ratification.

## Source facts and open semantics

Known source levels:

| level | source | current state |
|---|---|---|
| document | `<text xml:lang>` | materialized as `doc_lang`, but contains placeholder and malformed-looking values; not approved as fallback |
| line | `<lb lg>` | canonicalized by `line_lang_v1` |
| word | `<w lg>` | inventoried (10,846 attributes), not materialized in the token cache |

The Phase 1 inventory proves `w@lg` exists. The governed non-test audit found
9,409 explicit word tags and 7,100 valid word-over-line overrides across 736
documents. The official HPM guide states that the paragraph style marks the
language of the complete line and character language styles mark inserted
words or incomplete quotations. Gate 0 therefore ratifies word override,
otherwise line inheritance.

## Proposed v2 records

### Source-span language record

One record per language-bearing source span:

| field | meaning |
|---|---|
| `doc_id` | technical document identifier |
| `line_index_in_doc` | line key, null only for document-level records |
| `word_index_in_line` | word key, null for document/line records |
| `language_level` | `DOCUMENT`, `LINE`, or `WORD` |
| `language_raw` | exact source attribute value |
| `language_canonical` | ratified code or null |
| `language_status` | `valid`, `missing`, `explicit_empty`, `malformed`, or `unrecognized` |
| `language_rule_id` | stable canonicalization rule |
| `source_archive_member` | technical lineage reference |
| `source_payload_sha256` | source-document checksum |

Raw fields are never replaced by canonical ones. A malformed or unrecognized
value is not "cleaned" into the nearest code.

### Effective token-language record

One record per decomposed token:

| field | meaning |
|---|---|
| `doc_id`, `line_index_in_doc`, `word_index_in_line`, `word_pos` | exact join key to the token cache |
| `token` | existing decomposed transliteration token |
| `damage_state` | existing attested/restored/laes/illegible state |
| `line_lang_canonical` | accepted line value or null |
| `word_lang_canonical` | accepted explicit word value or null |
| `effective_lang_canonical` | result of the ratified rule or null |
| `effective_lang_status` | `resolved` or a named unresolved reason |
| `effective_lang_source` | `WORD_EXPLICIT`, `LINE_INHERITED`, `LINE_INHERITED_AFTER_EMPTY_WORD_TAG`, or `UNRESOLVED` |
| `language_span_id` | stable contiguous-language-span identifier within the document |
| `language_switch_before` | whether the effective language changes before this token |
| `mixed_language_line` | line contains more than one resolved language |
| `mixed_language_document` | document contains more than one resolved language |

`effective_lang_canonical` is a derived semantic selection field. Its
dependency closure must include every raw/canonical language field used by
the ratified rule.

## Gate 0 decisions

The executable contract is `configs/language_layers_v2.json`, rule
`word_override_else_line_v2`:

1. A valid explicit `w@lg` governs that word.
2. If `w@lg` is absent, inherit a valid `lb@lg`.
3. If `w@lg` is explicitly empty, preserve and log the anomaly, then inherit
   a valid line value with status `RESOLVED_WITH_SOURCE_ANOMALY`. Without a
   valid line value, remain unresolved.
4. If `w@lg` is malformed or unrecognized, remain unresolved without line or
   document fallback.
5. Document language is retained as provenance and prohibited as an
   effective-language fallback in v2.
6. Tokens not belonging to a word (`<PAR>` and structural specials) inherit
   line language for sequence-layout purposes but are excluded from lexical
   language counts.
7. Raw, canonical, and effective language fields are classified as
   `EDITORIAL_TRANSCRIPTION`.

## Explicit language scopes

Every active renderer, dataset builder, retriever, scorer, and calibration
script must require one of:

| scope | behavior |
|---|---|
| `HITTITE_ONLY` | semantic tokens resolved as `Hit`; structural positions retained |
| `SAME_LANGUAGE_AS_QUERY` | candidates restricted to the query span's resolved language |
| `MULTILINGUAL_CONDITIONED` | all resolved languages retained with language identity supplied to the model |
| `CROSS_LANGUAGE_PARALLEL` | different-language evidence allowed and labeled as a separate assistance channel |
| `ALL_LANGUAGES_UNCONDITIONED` | language identity removed intentionally; ablation only |

`None`, omitted arguments, `"auto"`, and permissive fallbacks are prohibited.
An unresolved query language produces an explicit limitation/abstention unless
the caller selects a separately ratified unresolved-language workflow.

## Dataset construction

- Migration root: `migrations/language_layers_v2/`.
- Effective span artifact:
  `migrations/language_layers_v2/language_spans.parquet`.
- Token dataset: `Phase4/phase4_out/multilingual_tokens_v2.parquet`.
- Workbench root: `Phase4/phase4_out/`.
- Frozen `Phase1_pipeline/p4_out/decomposed_corpus.parquet` is read-only.
- The Phase 4 builder joins v2 language records to existing token keys; it
  does not re-tokenize from a lossy source.
- Any necessary XML re-walk is scripted and checksum-guarded.
- Test-side content cannot contribute to vocabulary, rules, sampling weights,
  examples, or acceptance thresholds.
- Train + discovery may supply self-supervised pretraining content. Bin
  documents remain excluded from supervised composition/duplicate truth.
- Dev is evaluation/model-selection only.
- `cu`, `mrp*`, editor identity, and model suggestions are prohibited inputs.

## Vocabulary and model conditioning

The primary proposal is one sign vocabulary plus a separate language-ID
channel. Language identity may be implemented as:

- a learned language embedding summed with token/position embeddings; or
- explicit language-span markers, if control tests show equivalent behavior.

The choice is a Gate 3 model decision. It must not collapse lexical language
with Sumerogram/Akkadogram/determinative tags. The vocabulary is rebuilt from
the governed non-test universe and written to a new path; the existing
`configs/tokenizer.json` and D14 checkpoint stay intact.

Sampling reports both:

- natural corpus frequency; and
- controlled/temperature-based language sampling.

Minority-language oversampling must be recorded and ablated. It may not be
hidden inside a generic data loader.

## Training constraints

- Masked spans may not cross an unresolved language boundary.
- Boundary/continuation examples record the language on both sides.
- Same-language hard negatives are reported separately from cross-language
  negatives.
- Cross-language negatives may not inflate the apparent difficulty or
  accuracy of the primary Hittite task.
- Code-switched contexts are a named stratum, not silently assigned to the
  document majority.
- Every run manifest includes the language-layer hash, rule version,
  language scope, observed language distribution, sampling distribution,
  unresolved exclusion count, corpus version, split hash, seed, and commit.

## Evaluation matrix

Report at minimum:

- Hittite primary metrics;
- each other canonical language where sample size supports a result;
- mixed-language versus single-language contexts;
- resolved versus unresolved-language abstention;
- same-language versus cross-language witness support;
- micro and composition-macro results;
- candidate-set coverage, set size, calibration error, selective risk, and
  abstention.

No pooled multilingual number is sufficient on its own.

## Acceptance checks

1. Frozen artifacts and split assignments are unchanged.
2. No test value influenced rule design or reported examples.
3. Every source language value has one status and stable rule ID.
4. Every token has exactly one effective status; resolved tokens have exactly
   one canonical language.
5. Word-level joins are one-to-one on the declared key or fail closed.
6. Malformed or unrecognized explicit word tags do not silently inherit a
   line value; explicit-empty tags follow the separately named anomaly rule.
7. Structural specials are excluded from lexical-language statistics.
8. Two clean builds produce logically identical tables and hashes.
9. Every projection is deterministic and declares its language scope.
10. Evidence-policy validation includes all language fields used to select
    semantic content.
11. Unit tests cover word overrides, absent tags, explicit empty tags,
    malformed/unrecognized tags, language switches, and unresolved queries.
12. A tracer demonstrates that changing only language IDs affects a
    conditioned model but not an intentionally unconditioned ablation.

Gate 1 checks 1–10 as applicable to the source-span migration passed on
2026-07-25. The migration contains 389,325 keyed source spans, reconciles all
9,409 Gate 0 explicit word-language attributes (9,400 primary-text spans plus
9 parser anomalies), opened zero protected-test payloads, preserved all
frozen hashes, and reproduced logical SHA-256
`d0126c4eacc2c6c58711516e725f90193d9cc964a1700ea2a5def3289c7c9296`.
Checks specific to token projections passed at Gate 2; conditioned-model
tracing remains Gate 3 work.

Gate 2 passed on 2026-07-25 with 2,923,640 non-test token rows. All five
projection definitions are recorded in
`Phase4/phase4_out/language_projection_manifest.json`; omitted/automatic
scopes fail closed, query-relative scopes require a resolved query language,
and the unconditioned projection is labeled ablation-only. The remaining
conditioned-model tracer is a Gate 3 requirement, not a Gate 2 model result.

## Rollback

Rollback is selection-based: active code points back to the prior artifacts.
No frozen file is overwritten, and the historical D14 checkpoint remains
loadable with its original vocabulary.
