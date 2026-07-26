# Language layers v2 migration

Phase 4 Gate 1 passed on 2026-07-25.

Rebuild from the repository root:

```powershell
python scripts/phase4_language_layers_v2.py
```

The script performs two independent split-gated builds, reads the persisted
Parquet back, and requires all three logical hashes to match. It never opens
protected-test, unmatched, ambiguous, or duplicate-stem XML payloads.

Tracked Gate 1 records:

- `rebuild_report.md`
- `rebuild_manifest.json`
- `gate1_acceptance.json`
- `verification_report.md`
- `quarantined_source_anomalies.jsonl`

The regenerable `language_spans.parquet` is gitignored. Its accepted logical
SHA-256 is
`d0126c4eacc2c6c58711516e725f90193d9cc964a1700ea2a5def3289c7c9296`.

Gate 1 authorizes Gate 2 token-dataset implementation only. It does not
authorize protected-test access, training-dataset export, or GPU training.
