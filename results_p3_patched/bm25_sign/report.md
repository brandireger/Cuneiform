# bm25_sign -- P3 Baseline Report

## Exact-dedup guard
- 98 groups of identical ATTESTED renderings (552 / 22726 fragments affected)

## Task B (test_only index)

- **joins_tier_A**: n=34, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_B**: n=6, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_C_full_UPPER_BOUND_contaminated**: n=68, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_C_exclusive_HONEST**: n=23, recall@1=0.043478260869565216 (CI [0.0, 0.13043478260869565]), recall@10=0.30434782608695654 (CI [0.13043478260869565, 0.5217391304347826]), MRR=0.14638126328010165 (CI [0.055558377279430755, 0.265445289804451])
- **duplicates**: n=793, recall@1=0.7843631778058008 (CI [0.7540983606557377, 0.8133669609079445]), recall@10=0.9104665825977302 (CI [0.8890290037831021, 0.9293820933165196]), MRR=0.8270816064865921 (CI [0.8020766015779439, 0.850797420603938])
- **pooled**: n=798, recall@1=0.7794486215538847 (CI [0.7493421052631579, 0.8057644110275689]), recall@10=0.9047619047619048 (CI [0.8834586466165414, 0.924812030075188]), MRR=0.8218993909071021 (CI [0.7970893689984984, 0.8443946836458931])

## Task B (full_distractor index) -- discovery pool as unlabeled distractors; metrics are CONSERVATIVE LOWER BOUNDS (discovery pool may contain unknown true positives scored as negatives)

- **joins_tier_A**: n=34, recall@1=0.0 (CI [0.0, 0.0])
- **joins_tier_B**: n=6, recall@1=0.0 (CI [0.0, 0.0])
- **duplicates**: n=793, recall@1=0.5498108448928121 (CI [0.5157629255989912, 0.5825977301387137])
- **pooled**: n=798, recall@1=0.5463659147869674 (CI [0.5112468671679198, 0.581453634085213])

## Task A -- zero-shot composition assignment (leave-one-out)

- n=793 (excluded single-witness: 13), recall@1=0.7843631778058008 (CI [0.755359394703657, 0.8121059268600253]), recall@5=0.8877679697351829 (CI [0.8650378310214375, 0.9092055485498108]), MRR=0.8361470363621533

## 2x2 leakage ablation (pooled, test_only)

| query render | index render | recall@1 | MRR | n |
|---|---|---|---|---|
| full | full | 0.8621553884711779 | 0.8895992591662809 | 798 |
| full | attested | 0.8208020050125313 | 0.8543641326430235 | 798 |
| attested | full | 0.8258145363408521 | 0.8608469898569998 | 798 |
| attested | attested | 0.7794486215538847 | 0.8218993909071021 | 798 |