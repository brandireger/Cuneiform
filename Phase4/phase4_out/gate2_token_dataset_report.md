# Phase 4 Gate 2 multilingual token dataset

**Status: PASS — language-aware API/workbench implementation may proceed; training remains unauthorized.**

The dataset joins the accepted Gate 1 source spans to token keys rebuilt from those same exact checksum-guarded XML members through the shared lossless decomposition function. This is necessary because the historical frozen token cache conflates at least one distinct archive-stem pair under one document identifier; it remains unchanged as a historical comparison artifact, not the Gate 2 row source.

- Token rows: **2,923,640** across **20,711** documents.
- Protected-test rows emitted: **0**.
- Structural tokens retained: **62,810**; all are excluded from lexical-language statistics.
- Mixed-language line token rows: **41,656**.
- Mixed-language document token rows: **544,107**.
- Explicit word-language spans used by at least one token: **8,445** of **9,400**; unused spans remain preserved in Gate 1 (typically words with no decomposed token).
- Logical SHA-256: `35914a01ff03863f76ee0a56352d2d870881dc581c1253430a2eda102e9bfb6a`.
- Two builds and persisted readback agree: **True**.
- Frozen hashes unchanged: **True**.

## Lexical tokens by effective language

| language | tokens |
|---|---:|
| `Hit` | 2,541,890 |
| `Hur` | 129,846 |
| `Akk` | 113,374 |
| `Hat` | 41,646 |
| `Luw` | 23,050 |
| `Sum` | 5,893 |
| `Pal` | 4,884 |
| `<UNRESOLVED>` | 247 |

## Projection contract

All five Gate 0 scopes are materialized as deterministic projection definitions in `language_projection_manifest.json`. Structural layout tokens are retained in every projection but never counted as lexical evidence. `SAME_LANGUAGE_AS_QUERY` and `CROSS_LANGUAGE_PARALLEL` require a resolved query language; omitted/automatic scopes fail closed. `ALL_LANGUAGES_UNCONDITIONED` explicitly removes language identity and is labeled ablation-only.

Dataset: `Phase4\phase4_out\multilingual_tokens_v2.parquet`. Manifest: `Phase4\phase4_out\gate2_token_dataset_manifest.json`. Acceptance: `Phase4\phase4_out\gate2_acceptance.json`.