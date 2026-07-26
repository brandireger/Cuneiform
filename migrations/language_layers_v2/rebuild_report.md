# Phase 4 Gate 1 language-layer v2 rebuild

**Status: PASS — Gate 2 token-dataset implementation authorized.**

This migration opened only unique archive stems mapped to frozen train, dev, or discovery. Protected test, unmatched, ambiguous, and duplicate-stem payloads remained unopened. No token training dataset or model input was produced.

- Allowed payloads opened per build: **20,743**.
- Protected-test payloads opened: **0**.
- Parsed documents: **20,742**.
- Parse-error payloads quarantined: **1**.
- Output rows: **389,325** (20,742 document, 359,183 line, 9,400 explicit word spans).
- Explicit word-language attributes outside the primary parser `<text>`: **9**, routed to `PARSER_ANOMALY`.
- Gate 0 explicit `w@lg` census reconciled: **9,409** total.
- Logical table SHA-256: `d0126c4eacc2c6c58711516e725f90193d9cc964a1700ea2a5def3289c7c9296`.
- Frozen artifact hashes unchanged: **True**.
- Two independent builds and persisted-table readback agree: **True**.

## Source status accounting

| level | explicit_empty | malformed | missing | unrecognized | valid |
|---|---:|---:|---:|---:|---:|
| DOCUMENT | 0 | 0 | 21 | 2,587 | 18,134 |
| LINE | 13 | 6 | 63 | 13 | 359,088 |
| WORD | 21 | 0 | 0 | 16 | 9,363 |

## Workbench routing counts

| category | count |
|---|---:|
| `EMPTY_LANGUAGE_TAG` | 34 |
| `MALFORMED_LANGUAGE_TAG` | 6 |
| `PARSER_ANOMALY` | 9 |
| `UNRECOGNIZED_LANGUAGE_TAG` | 2,616 |

The artifact preserves raw values and source checksums. Canonical values are null for missing, explicit-empty, malformed, and unrecognized source values. Explicit-empty word tags may still receive an effective line language under the named anomaly-bearing Gate 0 rule; malformed and unrecognized explicit word tags remain unresolved.

Output: `migrations\language_layers_v2\language_spans.parquet`. Manifest: `migrations\language_layers_v2\rebuild_manifest.json`. Acceptance record: `migrations\language_layers_v2\gate1_acceptance.json`. Quarantine log: `migrations\language_layers_v2\quarantined_source_anomalies.jsonl`.