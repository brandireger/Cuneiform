# Phase 4 Gate 0 ratification

**Status:** PASSED — Gate 1 migration implementation authorized (2026-07-25).

Gate 0 resolves the language-layer and unresolved-workbench design choices
required before implementation. It does not authorize protected-test access,
training-dataset export, or GPU training.

## Decision evidence

The [official HPM guide](https://www.hethport.uni-wuerzburg.de/HPM/hpm.php?p=hpmguide)
states that a paragraph language style identifies the language of a complete
line, while character language styles mark inserted words or incomplete
quotations in another language. The source semantics therefore support a
valid word-level language assignment overriding the line default.

The split-gated audit in
`Phase4/phase4_out/gate0_language_audit_report.md` opened 20,743 uniquely
mapped train, dev, and discovery XML payloads and zero protected-test
payloads. It found:

- 9,409 explicit `w@lg` attributes;
- 7,100 valid word-over-line overrides across 736 documents;
- 21 explicit-empty `w@lg` values; and
- one parse error among the permitted payloads.

## Ratified decisions

1. A valid explicit `w@lg` overrides the enclosing valid `lb@lg`.
2. An absent `w@lg` inherits a valid `lb@lg`.
3. An explicit-empty `w@lg` is preserved as a source anomaly, then inherits a
   valid line language with status `RESOLVED_WITH_SOURCE_ANOMALY` and source
   `LINE_INHERITED_AFTER_EMPTY_WORD_TAG`. It is also logged as
   `EMPTY_LANGUAGE_TAG`. If no valid line value exists, it remains unresolved.
4. A malformed or unrecognized explicit word tag remains unresolved and may
   not fall back to the line or document.
5. Document `xml:lang` is retained as provenance only and is prohibited as an
   effective-language fallback in v2.
6. Raw, canonical, and effective language fields are
   `EDITORIAL_TRANSCRIPTION` evidence.
7. The migration root is `migrations/language_layers_v2`; the token dataset
   path is `Phase4/phase4_out/multilingual_tokens_v2.parquet`; the unresolved
   workbench remains under `Phase4/phase4_out`.
8. The initial occurrence vocabulary adds `EMPTY_LANGUAGE_TAG` and
   `MALFORMED_LANGUAGE_TAG` to the eight prepared categories. Expert statuses
   are `UNREVIEWED`, `GROUPED`, `HYPOTHESIS`, `EXPERT_SUPPORTED`, `REJECTED`,
   and `WITHHELD`.

The executable decision contract is `configs/language_layers_v2.json`, rule
`word_override_else_line_v2`.

## Authorization boundary

| action | Gate 0 disposition |
|---|---|
| Implement Gate 1 language migration | authorized |
| Read train/dev/discovery source under the split gate | authorized |
| Read protected-test XML content | prohibited |
| Export the Phase 4 training dataset | not yet authorized |
| Begin GPU training | not yet authorized |
| Promote expert annotations to corpus truth/training truth | prohibited |

Gate 1 must now prove deterministic rebuilding, stable hashes, unchanged
frozen artifacts, exact row-key coverage, complete quarantine accounting,
and evidence-policy validation before Gate 2 work begins.
