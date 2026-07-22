# bm25_lemma -- P3 Baseline Report

## Exact-dedup guard
- 98 groups of identical ATTESTED renderings (552 / 22726 fragments affected)

## Task B (test_only index)

- **joins_tier_A**: n=34, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_B**: n=6, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_C_full_UPPER_BOUND_contaminated**: n=68, recall@1=0.0 (CI [0.0, 0.0]), recall@10=0.0 (CI [0.0, 0.0]), MRR=0.0 (CI [0.0, 0.0])
- **joins_tier_C_exclusive_HONEST**: n=23, recall@1=0.043478260869565216 (CI [0.0, 0.13043478260869565]), recall@10=0.5652173913043478 (CI [0.34782608695652173, 0.782608695652174]), MRR=0.1920099017716058 (CI [0.10797506577193494, 0.29985152606399557])
- **duplicates**: n=793, recall@1=0.8158890290037831 (CI [0.7881462799495587, 0.8411097099621689]), recall@10=0.9382093316519546 (CI [0.9217843631778058, 0.9520807061790668]), MRR=0.8602108827400782 (CI [0.8371156509959147, 0.8802748295931728])
- **pooled**: n=798, recall@1=0.8107769423558897 (CI [0.7819548872180451, 0.8370927318295739]), recall@10=0.9323308270676691 (CI [0.9147869674185464, 0.949874686716792]), MRR=0.8548210902417068 (CI [0.8333674733549369, 0.8754613758709696])

## Task B (full_distractor index) -- discovery pool as unlabeled distractors; metrics are CONSERVATIVE LOWER BOUNDS (discovery pool may contain unknown true positives scored as negatives)

- **joins_tier_A**: n=34, recall@1=0.0 (CI [0.0, 0.0])
- **joins_tier_B**: n=6, recall@1=0.0 (CI [0.0, 0.0])
- **duplicates**: n=793, recall@1=0.6065573770491803 (CI [0.5737704918032787, 0.6418663303909206])
- **pooled**: n=798, recall@1=0.6027568922305765 (CI [0.568922305764411, 0.6365914786967418])

## Task A -- zero-shot composition assignment (leave-one-out)

- n=793 (excluded single-witness: 13), recall@1=0.8158890290037831 (CI [0.7894073139974779, 0.8411097099621689]), recall@5=0.9306431273644389 (CI [0.9129571248423707, 0.9482976040353089]), MRR=0.8693767148308764

## 2x2 leakage ablation (pooled, test_only)

| query render | index render | recall@1 | MRR | n |
|---|---|---|---|---|
| full | full | 0.8721804511278195 | 0.8977589054617169 | 798 |
| full | attested | 0.8483709273182958 | 0.8805472528195621 | 798 |
| attested | full | 0.8333333333333334 | 0.8681831218855525 | 798 |
| attested | attested | 0.8107769423558897 | 0.8548210902417068 | 798 |