# tfidf_cosine_sign -- P3 Baseline Report

## Exact-dedup guard
- 98 groups of identical ATTESTED renderings (552 / 22726 fragments affected)

## Task B (test_only index)

- **joins_tier_A**: n=34, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_B**: n=6, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_C_full_UPPER_BOUND_contaminated**: n=68, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_C_exclusive_HONEST**: n=23, recall@1=0.043478260869565216 (CI [0.0, 0.13043478260869565]), recall@10=0.34782608695652173 (CI [0.17391304347826086, 0.5652173913043478]), MRR=0.14757205243343433 (CI [0.0630036706150413, 0.2586153233322529])
- **duplicates**: n=793, recall@1=0.648171500630517 (CI [0.6153530895334174, 0.6809899117276166]), recall@10=0.8638083228247163 (CI [0.8398486759142497, 0.8865069356872636]), MRR=0.7200365018271325 (CI [0.6937015719469636, 0.7469747983230435])
- **pooled**: n=798, recall@1=0.6441102756892231 (CI [0.6127819548872181, 0.6766917293233082]), recall@10=0.8583959899749374 (CI [0.8345864661654135, 0.8809523809523809]), MRR=0.7155249949234538 (CI [0.6901969005433192, 0.7422917458401262])

## Task B (full_distractor index) -- discovery pool as unlabeled distractors; metrics are CONSERVATIVE LOWER BOUNDS (discovery pool may contain unknown true positives scored as negatives)

- **joins_tier_A**: n=34, recall@1=0.0 (CI [0.0, 0.0])
- **joins_tier_B**: n=6, recall@1=0.0 (CI [0.0, 0.0])
- **duplicates**: n=793, recall@1=0.38461538461538464 (CI [0.3530580075662043, 0.41992433795712486])
- **pooled**: n=798, recall@1=0.38220551378446116 (CI [0.3483395989974937, 0.41729323308270677])

## Task A -- zero-shot composition assignment (leave-one-out)

- n=793 (excluded single-witness: 13), recall@1=0.648171500630517 (CI [0.6141235813366961, 0.6796973518284993]), recall@5=0.832282471626734 (CI [0.8045397225725095, 0.8575031525851198]), MRR=0.7306192753881192

## 2x2 leakage ablation (pooled, test_only)

| query render | index render | recall@1 | MRR | n |
|---|---|---|---|---|
| full | full | 0.7305764411027569 | 0.7897095405699588 | 798 |
| full | attested | 0.6854636591478697 | 0.7539606903488711 | 798 |
| attested | full | 0.6591478696741855 | 0.7235382150264447 | 798 |
| attested | attested | 0.6441102756892231 | 0.7155249949234538 | 798 |