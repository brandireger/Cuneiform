# P3 Master Acceptance Report

## Corpus caveat discovered in P3 (documented, not silently patched)

28 doc_id values in the frozen splits.parquet are ambiguous: either literal duplicate files cross-filed under two CTH folders in the source zip (e.g. `KUB 4.1.xml` exists under both `CTH 552_XML/` and `CTH 422_XML/`), or two DIFFERENT files whose `<docID>` text happens to collide (e.g. `Bo 3964.xml` and the composite `KBo 59.207+.xml` both report docID "Bo 3964"). Per P3's constraint (nothing may alter frozen corpus/splits/join tiers/bin flags), these are excluded from the fragment universe in eval_harness.py rather than silently resolved to one side -- a real cleanroom risk was averted (some pairs straddled train/test). Flagged here for a future P2.5-style patch upstream.

## Check 1 -- harness determinism

**PASS** -- re-ran bm25_sign's pooled/test_only Task B suite a second time and compared numerically (not just byte-diff, since JSON key order could differ) against the saved metrics.json.
- saved recall@1: {'mean': 0.7919799498746867, 'ci': [0.7619047619047619, 0.818295739348371]}
- rerun recall@1: {'mean': 0.7919799498746867, 'ci': [0.7619047619047619, 0.818295739348371]}

## Check 2 -- test-side positive counts

- Join pairs (test-side): 67 / 1581 total

| tier | join_type | count |
|---|---|---|
| A | direct | 13 |
| A | indirect | 9 |
| B | direct | 1 |
| B | inferred_from_shared_lines | 2 |
| C | direct | 24 |
| C | indirect | 4 |
| C | inferred_from_shared_lines | 14 |
| **totals** | | A=22, B=3, C=42 |

- Duplicate pairs (test-side, fragment-level, join-excluded): 25,785
- Task A eligible queries: 793 (single-witness exclusions: 13)

## Check 3 -- 2x2 leakage matrix (bm25_sign, pooled, test_only)

| query render | index render | recall@1 | MRR | n | delta vs ATTESTED/ATTESTED |
|---|---|---|---|---|---|
| full | full | 0.8697 | 0.8966 | 798 | +0.0777 |
| full | attested | 0.8333 | 0.8649 | 798 | +0.0414 |
| attested | full | 0.8383 | 0.8706 | 798 | +0.0464 |
| attested | attested | 0.7920 | 0.8335 | 798 | +0.0000 |

## Check 4 -- Tyndall replication vs published numbers

See `results/tyndall_replication/report.md` for the full table (fenced, protocol=tyndall2012, never mixed with the tables above). Headline:

- **approx_scale** (30 comps, 396 docs): MaxEnt all-token FULL=0.390, ATTESTED=0.360, delta=+0.030 (published brackets-removed MaxEnt_alltoken=0.67)
- **full_scale** (426 comps, 7454 docs): MaxEnt all-token FULL=0.164, ATTESTED=0.125, delta=+0.039 (published brackets-removed MaxEnt_alltoken=0.67)

## Check 5 -- headline preliminary table (Task A + Task B tier A)

| scorer | task | index | n | recall@1 | CI | MRR |
|---|---|---|---|---|---|---|
| bm25_sign | Task A (LOO) | test-side comps | 793 | 0.7831 | [0.7540983606557377, 0.8108448928121059] | 0.8355 |
| bm25_sign | Task B tier A (joins) | test_only | 34 | 0.0588 | [0.0, 0.14705882352941177] | 0.1384 |
| bm25_sign | Task B tier A (joins) | full_distractor | 34 | 0.0000 | [0.0, 0.0] | 0.0901 |
| bm25_lemma | Task A (LOO) | test-side comps | 793 | 0.8184 | [0.7919293820933165, 0.8424022698612862] | 0.8715 |
| bm25_lemma | Task B tier A (joins) | test_only | 34 | 0.0588 | [0.0, 0.14705882352941177] | 0.1495 |
| bm25_lemma | Task B tier A (joins) | full_distractor | 34 | 0.0294 | [0.0, 0.08823529411764706] | 0.1064 |
| tfidf_cosine_sign | Task A (LOO) | test-side comps | 793 | 0.6482 | [0.6140920554854981, 0.6809583858764187] | 0.7308 |
| tfidf_cosine_sign | Task B tier A (joins) | test_only | 34 | 0.0294 | [0.0, 0.08823529411764706] | 0.1072 |
| tfidf_cosine_sign | Task B tier A (joins) | full_distractor | 34 | 0.0294 | [0.0, 0.08823529411764706] | 0.0939 |

## Check 6 -- failures spot-read (5 illustrative examples, bm25_sign, task_b_pooled)

1. **KUB 3.44** (query = `"ŠEŠ dá"`, 2 tokens) -- true positive buried at rank 680. **Diagnosis: length failure** -- a 2-sign query carries almost no discriminating lexical signal for BM25.
2. **KBo 12.38+::1 / KUB 26.39 / KUB 33.97** -- three unrelated damaged queries ALL false-top-1 to the same candidate, **KUB 14.4** (rendering dominated by very common short syllables: `i da la u x x x ... ku it ki`). **Diagnosis: formulaic/high-frequency-token collision** -- a lexically generic document acts as a BM25 "magnet" for many short, damaged, unrelated queries.
3. **KUB 7.58** -> predicted **KUB 7.58 Vs. I**, with BYTE-IDENTICAL ATTESTED renderings. **Diagnosis: not a real retrieval failure** -- this is one of the 98 exact-dedup groups (dedup guard). BM25 correctly found true duplicate content that isn't registered as a ground-truth positive pair; this is a genuine candidate for the expert-verification queue (CLAUDE.md cleanroom rule 5), not a scorer weakness.
4. **KBo 32.193** (query rendering = empty string -- zero attested signs). **Diagnosis: degenerate/empty query** -- ATTESTED-only evaluation's harshest edge case; nothing for any lexical method to match on.
5. **FHL 158** (query rendering = `"x x"`, illegible-only). **Diagnosis: illegible-only query**, a milder version of #4 -- tokens exist but carry zero identifying content.

## Overall
**ALL CHECKS ADDRESSED**