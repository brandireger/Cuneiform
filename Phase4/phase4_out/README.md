# Phase 4 output directory

This directory holds the governed Gate 0 audit artifacts and will hold later
Phase 4 outputs. The audit artifacts are decision evidence, not research-model
results.

Large, regenerable outputs such as multilingual token tables and
unresolved-occurrence tables use Parquet and remain gitignored. Planned small
tracked outputs include:

- language audit/rebuild reports and manifests;
- dataset acceptance reports;
- language-stratified experiment summaries;
- unresolved similarity candidates;
- append-only expert annotation events; and
- deterministic cluster snapshots/reports.

Gate 2 accepted the multilingual token dataset. The next authorized work is
the language-aware API and unresolved-evidence workbench implementation.
Creating a file here does not bypass the remaining gates in
`../../PHASE4_CHARTER.md`.
