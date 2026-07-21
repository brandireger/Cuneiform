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

See `results_p3_patched/{scorer}/metrics.json` and `report.md` for the complete re-emitted P3 tables (all tiers, both index variants, 2x2 leakage, Task A) under the H1-patched harness.