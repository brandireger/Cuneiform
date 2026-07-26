# Phase 4

Phase 4 Gate 2 passed on 2026-07-25. Language-aware API and Unresolved
Evidence Workbench implementation may proceed; protected-test access and GPU
training are not authorized.

Its two linked tracks are:

1. a word-aware multilingual dataset and language-conditioned reconstruction
   system; and
2. an Unresolved Evidence Workbench for expert grouping and hypothesis
   recording.

Outputs live under `Phase4/phase4_out/`. Large regenerable Parquet
artifacts remain gitignored. Small reports, manifests, schemas, and bounded
candidate/annotation JSONL files are tracked.

The Gate 0 audit is decision evidence, not a model result. See:

- `../PHASE4_CHARTER.md`
- `../specs/LANGUAGE_LAYERS_V2.md`
- `../specs/UNRESOLVED_EVIDENCE_WORKBENCH.md`
- `../configs/phase4_preparation.json`
- `../configs/language_layers_v2.json`
- `../configs/unresolved_evidence_contract.schema.json`
- `../reports/phase4_gate0_ratification.md`

## Activation order

1. Gate 0 human ratification — complete.
2. P4-A non-test language semantics audit — complete.
3. P4-B deterministic language migration — complete (Gate 1 passed).
4. P4-C token dataset implementation and acceptance — complete (Gate 2).
5. P4-D explicit language APIs — next.
6. P4-E unresolved-evidence intake and annotation log — next.
7. Gate 3 GPU authorization.
8. P4-F training and ablations.
9. P4-G downstream reruns and UI integration.

Frozen Phase 1 data, splits, tokenizer, and checkpoint are not overwritten.
