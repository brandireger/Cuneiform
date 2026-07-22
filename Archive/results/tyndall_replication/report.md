# Tyndall (2012) Fenced Replication -- protocol=tyndall2012

**FENCED: this uses Tyndall's own fragment-level 10-fold-CV-within-compositions protocol, a closed-set classification task fundamentally different from eval_harness.py's zero-shot retrieval tables. Never mix these numbers into the main P3 results.**

- Ambiguous doc_ids excluded (cross-filed under 2 CTH numbers or colliding docID text -- see eval_harness.py docstring): 28
- Eligible population (real, >=2-witness compositions): 426 compositions, 7454 docs
- Approx-scale sample (seed=20260722): 30 compositions, 396 docs (Tyndall 2012: 36 compositions, 389 fragments)

## Scope note: 'plain' vs 'brackets-removed'
Tyndall's 'brackets removed' condition (restorations kept as plain text, bracket punctuation stripped) corresponds to our FULL rendering. His 'plain' condition (bracket markup characters left in the token stream) is NOT reconstructed here -- out of scope. ATTESTED (restorations fully excluded) is a condition Tyndall never tested; it retro-quantifies restoration leakage in his reported numbers.

## Published reference (Tyndall 2012)

| condition | NB all-token | MaxEnt all-token | NB ideogram | MaxEnt ideogram |
|---|---|---|---|---|
| plain | 0.55 | 0.61 | 0.44 | 0.51 |
| brackets_removed | 0.64 | 0.67 | 0.49 | 0.54 |

## approx_scale replication (30 comps, 396 docs)

| classifier | tokenization | rendering | accuracy | n folds used |
|---|---|---|---|---|
| NB | alltoken | full | 0.5038207078439277 | 10 |
| MaxEnt | alltoken | full | 0.3902598966221257 | 10 |
| NB | alltoken | attested | 0.40069866184726866 | 10 |
| MaxEnt | alltoken | attested | 0.3601750487214883 | 10 |
| NB | ideogram | full | 0.6687286121744326 | 10 |
| MaxEnt | ideogram | full | 0.5899898881075352 | 10 |
| NB | ideogram | attested | 0.550582191802006 | 10 |
| MaxEnt | ideogram | attested | 0.5229073146209369 | 10 |

**FULL vs ATTESTED delta (MaxEnt, all-token) -- restoration-leakage estimate: +0.030** (FULL=0.390 vs published brackets-removed MaxEnt_alltoken=0.67)

### Fold class coverage (honest reporting, per spec)
- fold 0: 54 test docs, 54 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 1: 54 test docs, 54 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 2: 50 test docs, 50 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 3: 44 test docs, 44 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 4: 40 test docs, 40 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 5: 38 test docs, 38 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 6: 34 test docs, 34 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 7: 28 test docs, 28 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 8: 28 test docs, 28 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 9: 26 test docs, 26 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded

## full_scale replication (426 comps, 7454 docs)

| classifier | tokenization | rendering | accuracy | n folds used |
|---|---|---|---|---|
| NB | alltoken | full | 0.14899999178797513 | 10 |
| MaxEnt | alltoken | full | 0.1638546523208139 | 10 |
| NB | alltoken | attested | 0.12597811316895827 | 10 |
| MaxEnt | alltoken | attested | 0.12470115157934392 | 10 |
| NB | ideogram | full | 0.34170320340726434 | 10 |
| MaxEnt | ideogram | full | 0.29438303062549215 | 10 |
| NB | ideogram | attested | 0.28856923724817307 | 10 |
| MaxEnt | ideogram | attested | 0.24813197895111733 | 10 |

**FULL vs ATTESTED delta (MaxEnt, all-token) -- restoration-leakage estimate: +0.039** (FULL=0.164 vs published brackets-removed MaxEnt_alltoken=0.67)

### Fold class coverage (honest reporting, per spec)
- fold 0: 970 test docs, 970 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 1: 953 test docs, 953 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 2: 866 test docs, 866 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 3: 799 test docs, 799 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 4: 742 test docs, 742 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 5: 688 test docs, 688 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 6: 651 test docs, 651 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 7: 618 test docs, 618 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 8: 600 test docs, 600 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded
- fold 9: 567 test docs, 567 usable (class seen in train), 0 test-only (unseen-in-train) classes excluded