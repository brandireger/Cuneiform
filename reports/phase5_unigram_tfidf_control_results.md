# Unigram TF-IDF decomposition control — results

**Status: COMPLETE POST-HOC REVIEWER AUDIT, 2026-08-04.**
**Not preregistered; dev-only; test never loaded; not for citation as a
confirmatory result.** Protocol and disclosure:
`reports/phase5_unigram_tfidf_control_protocol.md`.

## Result

The original statement that a sign-bigram context feature accounts for
approximately +0.10 Task A recall@1 was incomplete. The gain has two measured
components in this historical dev-only setup:

| arm | recall@1 | delta | query-bootstrap 95% CI |
|---|---:|---:|---:|
| BM25 | 0.6312 | — | — |
| BM25 + unigram TF-IDF | 0.6832 | +0.0520 | [+0.0266, +0.0786] |
| BM25 + unigram+bigram TF-IDF | 0.7329 | +0.1017 | [+0.0774, +0.1272] |
| bigram arm minus unigram arm | — | +0.0497 | [+0.0289, +0.0705] |

Thus, about half of the original +0.1017 is recoverable without adding
sequence context: BM25 and unigram TF-IDF/cosine are complementary scoring
rules over the same sign tokens. The remaining paired difference between the
separately tuned arms is consistent with additional sign-sequence context.

The last comparison is not a formal conditional-increment model because the
two arms tune their weights separately. A confirmatory factorial design must
separate unigram-only and bigram-only channels and tune them jointly inside
the training folds.

## Composition-cluster audit

The original query bootstrap treated correlated queries as independent. This
audit additionally resamples compositions:

| comparison | query-micro delta, cluster CI | composition-macro delta, cluster CI | positive / negative / tied compositions |
|---|---:|---:|---:|
| unigram arm vs BM25 | +0.0520, [+0.0181, +0.0902] | +0.0345, [−0.0192, +0.0820] | 20 / 12 / 10 |
| bigram arm vs BM25 | +0.1017, [+0.0738, +0.1414] | +0.0936, [+0.0576, +0.1378] | 22 / 1 / 19 |
| bigram arm vs unigram arm | +0.0497, [+0.0325, +0.0707] | +0.0591, [+0.0171, +0.1056] | 20 / 5 / 17 |

The bigram-arm result is not explained by the largest compositions alone.
The weaker unigram ensemble is less stable under the product-relevant
composition-macro estimand.

## Corrected conclusion

> In this closed-world dev reproduction, adding a second lexical similarity
> score improves BM25, and adding sign-sequence context improves it further.
> The full approximately +0.10 effect must not be attributed to context alone.

No result here validates the prohibited dev-fitted statistics universe, a
full-distractor index, Task B, physical-join tiers, character granularity, or
the protected test split.

## Artifacts

- `scripts/phase5_unigram_tfidf_control.py`
- `Phase4/phase4_out/p5_unigram_tfidf_control.json`
- `Phase4/phase4_out/p5_unigram_tfidf_control_per_query.jsonl`
- `Phase4/phase4_out/p5_unigram_tfidf_control_manifest.json`
