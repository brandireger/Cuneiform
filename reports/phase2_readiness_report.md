# Phase 2 readiness review

- **Review date:** 2026-07-23
- **Branch:** `codex/phase2-readiness`
- **Scope:** active tree only; `Archive/` treated as immutable history

## Verdict

The repository is ready for governed, reversible Phase 2 structural
probes after the hardening in this change. It is not appropriate to run
the original P2-A boundary-head score as written: the opening
feasibility probe found no encoded within-line seam target.

New content-consuming probes still need a split-projecting canonical
loader and a probe-specific T1 tracer before their first score. The
legacy `scripts/13_bm25.py` and `lib/eval_harness.py` remain
policy-unaware Phase 1 carryovers and are not templates for new Phase 2
work.

## Readiness defects found and resolved

1. **Strict encoding was bypassed in the mandatory tracer.**
   Normal D14 tracer paths used `Tokenizer.encode(..., strict=False)`.
   They now use strict encoding and run C1/C7 checks at seam ingress.
   The non-strict path remains available only for the named historical
   E2 retro-reproduction.
2. **BM25's scramble tracer was mathematically invalid.** It permuted
   token order, which a bag-of-words scorer cannot observe, and then
   compared a word-grain original with a decomposed-sign perturbation.
   The apparent historical PASS was therefore not evidence of the
   claimed property. BM25 now receives deterministic token-identity
   corruption in the same representation.
3. **BM25 statistics drifted inside the tracer.** The tracer refit IDF
   for each candidate over a sampled/query-modified reference. It now
   fits once over the declared full non-test universe, stamps that
   universe, and reuses the fixed statistic object.
4. **A known scientific diagnostic blocked the tracer process.** T4's
   negative D18 context result remains prominently reported, but is
   classified as a non-blocking diagnostic. Plumbing failures still
   produce a nonzero exit.
5. **C1–C10 were not exercised in CI.** The contract self-test no
   longer imports the GPU/data stack and now runs in the quality
   workflow.
6. **Active Python had unchecked static defects.** Sixteen unused or
   ambiguous constructs were removed, and Ruff now checks `lib/`,
   `scripts/`, `tests/`, and `demo/` in CI.
7. **Tracer perturbations lacked regression tests.** Three tests now
   verify the distinct invariants of sequence permutation and
   bag-of-words identity corruption.
8. **Run hashes were abbreviated and dirty state unrecorded.**
   Evidence manifests now emit full SHA-256 values and `git_dirty`.
9. **Local environments were not ignored or documented precisely.**
   `.venv/` is ignored, the README names the Python prerequisite, and
   lightweight quality dependencies are centralized in
   `requirements-ci.txt`.

## Data and process checks

- Pinned corpus MD5:
  `93e71e2560f5e109c87713d5590cb059` — matches the design authority.
- Frozen split counts: train 6,073; dev 760; test 760; discovery
  14,046.
- Split values are limited to train/dev/test/discovery.
- Edge universe: 22,757 rows and 22,757 unique fragment IDs.
- All 26 frozen canary references resolve to `dev`; zero are test-side.
- The two join examples accidentally displayed during review were
  immediately checked and both are train-side; no test content was
  exposed.
- The accepted `line_lang` concern is reproducible in the non-test
  universe: 49 markup-like word rows and 155 missing word rows. These
  are audit counts only, not a migration result; the governed
  migration remains a separate versioned action.
- Frozen active and archived split/corpus parquet hashes match for the
  checked artifacts.

## Validation

- Ruff active-tree check: passed.
- Unit/governance tests: 23/23 passed.
- C1–C10 executable self-tests: 20/20 passed.
- Local `.venv` dependency check: passed with Python 3.12.13,
  pandas 3.0.3, pyarrow 25.0.0, scipy 1.18.0,
  scikit-learn 1.9.0, PyYAML 6.0.3, and PyTorch 2.6.0+cu124.
  CUDA is available on the NVIDIA GeForce RTX 3060.
- Mandatory tracer: zero blocking failures.
  - T1 seam: 8/8 changed under order permutation.
  - T1 BM25: 8/8 changed under same-representation identity
    corruption.
  - T2: 26/26 self-similarity checks passed.
  - T3: 5/5 easy joins ranked top-10 in the toy universe.
  - T4: 1/5 positive context lift, retained as a non-blocking
    diagnostic finding.
  - T5: 20/20 deterministic rescoring checks passed.

## Phase 2 opening action

`scripts/p2a_feasibility.py` ran on dev-only relation metadata and
structural line membership. It did not decode test join payloads,
transliteration, restorations, `cu`, or model output.

The canonical mapped universe contains 182 dev join pairs:

| structural target | pairs |
|---|---:|
| consistent shared-row offset | 92 |
| ordering only | 22 |
| interleaved, no shared row | 32 |
| shared rows, inconsistent positional offset | 36 |
| encoded within-line seam column | 0 |

Two additional dev relation rows did not map to the canonical edge
universe, one ambiguous-parent relation row was quarantined before
payload decoding, and four records disagreed with the edge-table
shared-row count. These remain visible in the probe artifact.

The result is labeled **[PROBE — not for citation]**. It rules out
calling D17's whole-row skip parameter a true editor-supplied seam
offset. It does not rule out a row-alignment reformulation or an
unmaterialized source field.

## Remaining work

- Decide whether P2-A should be reformulated as row alignment or
  closed as unanswerable from the materialized corpus.
- Proceed to P2-D, the other highest-priority, non-training probe.
- Build a split-projecting content loader before P2-C, P2-E, or any
  other semantic scorer.
- Execute the separately approved `line_lang` migration through its
  versioned audit/ratification sequence; do not overwrite P2.
- Keep B5 withdrawn unless it is rerun through canonical encoding.
