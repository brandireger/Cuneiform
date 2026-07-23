# Repository Hardening Report

Date: 2026-07-22  
Branch: `codex/repo-hardening`  
Scope: governance contracts, repository onboarding, and lightweight
verification only. No research probe, scoring run, model selection, split
change, or frozen-artifact rewrite was performed.

## Changes

1. Evidence-policy validation now propagates explicit denials through the
   complete dependency closure. A derived feature cannot bypass the global
   denial of `cu`, `mrp*`, or another explicitly prohibited source.
2. Run-manifest construction now rejects a displayed evidence-policy label
   that differs from the `EvidencePolicy` object used for validation.
3. `assert_no_test()` now fails closed for missing IDs and unrecognized split
   values, in addition to rejecting test-side IDs.
4. Added regression tests for all three defects.
5. Added a Phase 2 root `README.md` distinguishing active assets from the
   immutable Phase 1 snapshot under `Archive/`.
6. Added a lightweight GitHub Actions workflow for governance tests and
   syntax/JSON artifact validation.
7. Activated the pinned PyTorch CUDA 12.4 package index in
   `requirements.txt`.
8. Corrected the active Phase 1 BM25 copy's terminology from
   "artifact-only" to "transcription-assisted" and marked its lemma path as
   historical and prohibited for new work. Historical reports and results
   were not changed.

## Verification

- `python -m unittest discover -s tests -v`: **20/20 passed**.
- All tracked Python sources parse successfully.
- All tracked JSON and JSONL artifacts parse successfully.
- `git diff --check`: clean.
- Pinned corpus MD5 remains
  `93e71e2560f5e109c87713d5590cb059`.
- No file under `Archive/` was modified.

PyYAML 6.0.3 was installed into a temporary test directory for verification;
the full CUDA/scientific dependency stack was not reinstalled.

## Deferred decisions

- Select a source-code license and confirm author metadata before adding
  `LICENSE` and `CITATION.cff`.
- Address the documented malformed `line_lang` values only through a formal
  parser/data-artifact migration; frozen P2 artifacts remain unchanged.
- Preserve the existing Phase 1 archive. Any future deduplication or
  tag/release migration requires an explicit archival-policy decision.
- A future Phase 2 scorer must integrate the evidence registry and manifest
  directly; labeling the retained Phase 1 utility does not retrofit it.
