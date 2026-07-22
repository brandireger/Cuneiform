# P4 H1 -- Harness Patch Report

## docID-family normalization

- Family pairs found (exhaustive regex sweep over all corpus doc_ids, base form independently verified to exist): **5**
  - `IBoT 2.118` <-> `IBoT 2.118 Rs. IV`
  - `KBo 8.96` <-> `KBo 8.96 Vs.`
  - `KUB 41.18` <-> `KUB 41.18 Vs. I`
  - `KUB 7.13` <-> `KUB 7.13 Vs. I`
  - `KUB 7.58` <-> `KUB 7.58 Vs. I` (the pair originally flagged in P3's failures spot-read -- confirmed byte-identical ATTESTED content, now excluded from ranking rather than silently scored as a false positive)
- Total same-family candidate exclusions applied across the full re-run (all scorers x tasks x index variants): **6,408**

## Exact-dedup groups (98) -- verified, no additional action needed

The family-key mechanism above already subsumes the required "same-family dedup excluded" behavior (the one dedup group that is ALSO a real family match -- KUB 7.58 -- is excluded via family_map, not via a separate dedup-specific rule). The remaining 97 dedup groups were manually inspected (see scratch diagnostics): they are near-empty/degenerate fragments (very short or all-`x` attested content) from genuinely unrelated tablets across many different sites and publication series, coincidentally identical only because there's so little content to differ on. Per spec, these correctly STAY in ranking as real formulaic collisions -- part of the task, not a bug.

## P3 table deltas (unpatched results/ vs patched results_p3_patched/)

| scorer | metric | unpatched | patched | delta |
|---|---|---|---|---|
| bm25_sign | task_a_recall@1 | 0.7831 | 0.7844 | +0.0013 |
| bm25_sign | task_b_pooled_test_only_recall@1 | 0.7920 | 0.7794 | -0.0125 |
| bm25_sign | task_b_tier_A_test_only_recall@1 | 0.0588 | 0.0000 | -0.0588 |
| bm25_lemma | task_a_recall@1 | 0.8184 | 0.8159 | -0.0025 |
| bm25_lemma | task_b_pooled_test_only_recall@1 | 0.8258 | 0.8108 | -0.0150 |
| bm25_lemma | task_b_tier_A_test_only_recall@1 | 0.0588 | 0.0000 | -0.0588 |
| tfidf_cosine_sign | task_a_recall@1 | 0.6482 | 0.6482 | +0.0000 |
| tfidf_cosine_sign | task_b_pooled_test_only_recall@1 | 0.6667 | 0.6441 | -0.0226 |
| tfidf_cosine_sign | task_b_tier_A_test_only_recall@1 | 0.0294 | 0.0000 | -0.0294 |

**Honest note (per spec's own framing, but the actual result differs from its expectation):** the amendment anticipated "expect small improvements" from this patch. What was actually observed is a small DECREASE in pooled/Task-A recall for most scorers -- because the pre-patch numbers were inflated by a handful of queries trivially "solved" by matching their own uncredited docID-family sibling (an unlabeled near-duplicate, not a genuine retrieval success). Removing that loophole is a strictly more honest number, even though it moves in the opposite direction from what was expected -- reported as observed, not adjusted to match the anticipated direction.

## Full patched tables

See `results_p3_patched/{scorer}/metrics.json` and `report.md` for the complete re-emitted P3 tables (all tiers, both index variants, 2x2 leakage, Task A) under the H1-patched harness. **v1 -- see erratum below.**

## Erratum (2026-07-22, found during P5 D16 candidate generation; fix ratified per specs/P5C_SPEC.md E1)

**The bug.** `top_k_ranking()`'s family-exclusion check compared `fragment_family(query)` against `fragment_family(candidate)` using only each fragment's `parent_doc` (the `::N` member suffix is stripped before lookup). Two members of the SAME composite join document (e.g. `KBo 23.64+::1` and `KBo 23.64+::2`) therefore ALWAYS produced the same family value -- not because of any of the 5 real H1 docID-family pairs, but simply because they share a `parent_doc` by construction. Since a join query's own true partner IS such a sibling by definition, the patched harness silently excluded the true partner from every join query's candidate list, for every join pair in the corpus, independent of the 5-pair H1 mechanism entirely.

**What it affected.** The `results_p3_patched/` (v1) directory's joins-tier numbers only: `joins_tier_A`, `joins_tier_B`, and `joins_tier_C_full_UPPER_BOUND_contaminated` recall all read exactly **0.0** under v1 for every scorer -- e.g. bm25_sign tier-A recall@1 patched=0.0 (see table above), which this report originally described as an unexpected "small decrease" without identifying the true partner was being deleted from the candidate pool outright. That framing was incomplete; this erratum corrects it. `joins_tier_C_exclusive_HONEST` was also affected (its own recomputed exclusive-content candidates go through the same family check).

**What it did NOT affect.** (a) The original UNPATCHED `results/` numbers (the frozen P3 baseline, including the "0.059" tier-A recall@1 number-to-beat cited throughout CLAUDE.md/P4B_DIAGNOSTICS.md) -- those never applied family_map at all. (b) The DUPLICATES task -- duplicate-pair candidates are, by `build_duplicate_positives()`'s own construction, drawn from DIFFERENT parent_docs than any join pair (join pairs are explicitly excluded from the duplicate-pair universe), so the same-parent_doc collision this bug depended on essentially never arose there. (c) Task A (composition assignment) -- family exclusion there operates as originally intended (excluding a query's own composition-siblings from "proving" its own composition), and is not affected by this specific bug since it isn't scoring join-partner recall.

**The fix.** `lib/eval_harness.py::top_k_ranking()` now additionally checks whether the query's and candidate's `parent_doc` (not family-mapped, the raw value) are IDENTICAL before applying a family exclusion -- if they are, the candidate is never excluded on family grounds, regardless of family_map's mapping (composite-doc siblings are always genuinely distinct physical fragments, never "the same family" by definition). The 5 real H1 pairs (which have DIFFERENT parent_docs that map to a shared family) are unaffected by this guard and continue to be excluded correctly.

**Corrected results:** `results_p3_patched_v2/` (re-run with the fixed function; joins tier-A/B recall now reproduces the unpatched baseline exactly, 0.0588/0.5 for bm25_sign, confirming the fix). `results_p3_patched/` (v1) is retained for the record, marked superseded (see its `SUPERSEDED.md`), not deleted or silently overwritten.

**Date:** 2026-07-22. **Git hash:** fix is part of this session's uncommitted changes on top of `703fa46ee3e7b06114d3675b2e99ab28bbea47fd` (the commit `results_p3_patched/` v1 was originally built against) -- will carry a concrete hash once committed.