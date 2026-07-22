# SUPERSEDED — see results_p3_patched_v2/

This directory (v1) was generated with a buggy H1 family-exclusion
implementation that silently deleted every join query's own true
partner (composite-doc siblings always share a `parent_doc`, so the
old `fragment_family()`-based check always judged them "the same
family"). Joins tier-A/B recall in this directory reads exactly 0.0
as a result of that bug, not a real regression.

Fixed in `lib/eval_harness.py` (2026-07-22, found during P5 D16
candidate generation). Corrected results: `results_p3_patched_v2/`.
Erratum: `h1_patch_report.md`'s "Erratum" section.

This directory is kept for the record, not deleted — do not cite its
joins-tier numbers for anything going forward.
