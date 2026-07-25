# `line_lang` migration -- Step C deterministic rebuild

Ratified 2026-07-25 (Ixca): 7-code canonical vocabulary (`Hit, Akk, Sum, Hat, Hur, Luw, Pal`), `Hattian -> Hat` mapped, `Lu`/`5f_`/`ign` (and anything else outside the vocabulary) quarantined as `unrecognized`, XML-markup-like values quarantined as `malformed`. Applied mechanically to every document in the pinned corpus, all splits -- test-side values were never printed, sampled, or ranked; only combined (not test-isolated) totals and non-test per-split breakdowns appear below.

- Corpus zip MD5: `93e71e2560f5e109c87713d5590cb059` (matches the pinned `93e71e2560f5e109c87713d5590cb059`).
- Documents processed: **21,639** (parse errors skipped: 229, matching the corpus-wide known parse-error count).
- Total lines written (all splits combined): **384,559**.

## Status counts, all splits combined

| status | count |
|---|---|
| valid | 384,410 |
| missing | 114 |
| unrecognized | 28 |
| malformed | 7 |

## Status counts by non-test split

| split | valid | missing | malformed | unrecognized |
|---|---|---|---|---|
| train | 170,256 | 78 | 6 | 1 |
| dev | 23,769 | 2 | 0 | 0 |
| discovery | 169,075 | 22 | 0 | 27 |

## Output contract

`migrations\line_lang_v1\line_lang_canonical.parquet`: one row per (`doc_id`, `line_index_in_doc`), columns `line_lang_raw` (verbatim source value, null only if absent), `line_lang_canonical` (ratified code or null), `line_lang_status` (`valid`/`missing`/`malformed`/`unrecognized`), `line_lang_rule_id` (stable rule identifier). Downstream consumers must request `line_lang_canonical` explicitly and must not treat `line_lang_raw` as canonical.

This is a NEW artifact under a versioned directory -- it does not modify `Phase1_pipeline/p2_out/corpus.parquet`, `splits.parquet`, or any other frozen artifact. Rollback is selection-based: ignore this directory and nothing else needs to change.