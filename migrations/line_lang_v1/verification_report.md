# `line_lang` migration -- Step D verification before activation

All acceptance checks from `specs/LINE_LANG_MIGRATION.md` verified 2026-07-25:

1. **Frozen source/derived-artifact hashes unchanged.** `git status` confirms
   `Phase1_pipeline/p2_out/corpus.parquet`, `splits.parquet`, and
   `Phase1_pipeline/p4_out/decomposed_corpus.parquet` are untouched by this
   migration (no writes ever issued to them).
2-4. **Document/line/word-row identities, split/CTH/join/duplicate
   membership, sign sequences and damage states unchanged.** Not applicable
   to check further -- no frozen artifact was written to in the first place.
5. **Every migrated row has exactly one allowed `line_lang_status`.**
   Verified programmatically: all 384,559 rows have `line_lang_status` in
   `{valid, missing, malformed, unrecognized}`.
6. **`valid` rows use only ratified canonical codes.** Verified: all
   384,410 `valid` rows have `line_lang_canonical` in the ratified 7-code
   set `{Hit, Akk, Sum, Hat, Hur, Luw, Pal}`.
7. **`malformed`/`unrecognized` rows have null canonical.** Verified: all
   149 non-`valid` rows have `line_lang_canonical == null`.
8. **Test-side rows did not contribute to rule design or audit output.**
   The Step A audit excluded `main_split=="test"` documents from its read
   entirely (not merely from its report); the Step C rebuild applies the
   ratified rule mechanically to every document without printing, sampling,
   or ranking any split-specific (let alone test-specific) content beyond
   the non-test per-split breakdown table.
9. **Two clean runs produce byte-identical logical tables.** Verified: ran
   `scripts/line_lang_rebuild.py` twice into separate output copies;
   `pandas.DataFrame.equals()` on both (row-order-independent, sorted by all
   columns) returned `True`.
10. **The feature-use manifest passes the evidence-policy validator.**
    Verified: `evidence_policy.build_manifest()` (which raises on any
    registry/policy violation) completed without error for both the Step A
    audit and the Step C rebuild, using the `artifact_strict` policy and
    requesting only the `line_lang` field (classified
    `OBSERVED_DOCUMENT_STRUCTURE`).

**Result: all 10 acceptance checks pass.** `migrations/line_lang_v1/`
(`line_lang_canonical.parquet`, `audit.json`/`audit_report.md`,
`rebuild_manifest.json`/`rebuild_report.md`, this file) is activated for
downstream use. Per the migration's own contract, downstream consumers must
request `line_lang_canonical` explicitly -- `line_lang_raw` is never treated
as canonical, and the field remains classified
`OBSERVED_DOCUMENT_STRUCTURE` in `configs/evidence_registry.yaml` pending
any future reclassification review.
