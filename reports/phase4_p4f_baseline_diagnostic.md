# P4-F follow-up — why arm A underperforms D14 on every tier

**Status: ANSWERED 2026-08-03. The cause is a configuration defect in the
Stage 0 integration, not a property of the data, the population, or the
seed.**

`reports/phase4_p4f_stage1.md` recorded three candidate causes and tested
none. This report tests them. Two are eliminated outright, the third is
reduced to 0.81%, and the actual cause — unlisted, because it was not
suspected — is confirmed from D14's own checkpoint.

## The finding

**Arm A and arm B trained on exactly half of D14's examples.**

| | D14 (from its checkpoint) | Stage 1 arms |
|---|---|---|
| `mlm_batch_size` | **32** | **16** |
| `boundary_batch_size` | **32** | **16** |
| `warmup_steps` | **2000** | **500** |
| `max_steps` | 60,000 | 60,000 |
| MLM examples seen | **1,920,000** | **960,000 (50%)** |
| boundary examples seen | **1,920,000** | **960,000 (50%)** |

`scripts/phase4_p4f_pretrain.py`'s `DEFAULT_CONFIG` was copied from
`Archive/scripts/19_pretrain.py`'s hardcoded `DEFAULT_CONFIG` dict, which
carries `mlm_batch_size: 16`, `boundary_batch_size: 16`, `warmup_steps: 500`
and `max_steps: 20000`. D14 did not run under those values: it ran under
`configs/pretrain_config.json`, which overrides them to 32 / 32 / 2000 (and
`max_steps` to 60,000). The `max_steps` override was noticed and matched; the
other three were not.

Proposal §4 said "identical architecture to D14 … Steps: 60,000, matching
D14 exactly." Architecture and step count did match — parameter count is
identical to the unit (12,817,991) and both arms ran 60,000 steps. Examples
per step did not, and the proposal did not name batch size, so nothing
pinned it. **This is a defect in the Stage 0 integration, stated plainly:
the baseline comparison was never like-for-like.**

Confirmed from the authoritative source rather than inferred: D14's
checkpoint stores its own `config` dict, and it reads 32/32/2000.

## What this changes, and what it does not

**Unaffected: the arm A vs arm B comparison.** Both arms ran under
byte-identical config and data — verified at launch by the shared-manifest
guard, which refuses to start an arm whose shared block differs from its
sibling's. The measured conditioning effect stands exactly as reported:

> `in_doc` AUC arm A 0.6981, arm B 0.7263, delta **+0.0282**, paired
> bootstrap 95% CI **[+0.0144, +0.0424]**.

Both arms were equally under-trained relative to D14, so the difference
between them remains attributable to conditioning.

**Affected: the falsifier's second clause.** "Arm B must exceed D14's
0.7461" required a model trained on 960,000 examples to beat one trained on
1,920,000. That was not a test of language conditioning; it was substantially
a test of training budget.

**The verdict is not retroactively overturned.** The rule was pre-registered
and arm B did not clear it. What changes is the *explanation*: the rejection
is attributable to a configuration error in this session's integration, not
to a finding about language conditioning. Reporting it any other way would
let a defect masquerade as a scientific result.

## The three recorded candidates, tested

### 1. Evaluation population — ELIMINATED

The hypothesis was that D14's 0.7461 came from a language-blind dev pool
while the arms were scored on the 883 fragments surviving
`MULTILINGUAL_CONDITIONED` admission, making the comparison cross-population.

`scripts/phase4_p4f_baseline_diagnostic.py` scores **D14's own frozen
checkpoint on the byte-identical evaluation set the arms were scored on**
(same builder, same seed, same 120 batches), importing the construction from
`phase4_p4f_stage1_eval.py` rather than reimplementing it.

| tier | D14 recorded | D14 on Stage 1 population | arm A | arm B |
|---|---|---|---|---|
| `in_doc` | 0.7461 | **0.7552** | 0.6981 | 0.7263 |
| cross_genre | 0.9006 | 0.9139 | 0.8729 | 0.9068 |
| random | 0.9473 | 0.8729 | 0.8388 | 0.9039 |
| pooled | 0.7904 | 0.7996 | 0.7475 | 0.7787 |

D14 scores **higher** on this population than on its own, not lower. The
population is not the explanation, and the gap to arm A widens rather than
closes: **D14 − arm A on `in_doc` = +0.0571, 95% CI [+0.0405, +0.0743]** —
twice the size of the conditioning effect.

The architecture reproduction used for this was verified, not assumed:
`P4FEncoder(condition_on_language=False)` loaded with D14's weights produces
hidden states and boundary logits **bit-identical** to `HittiteEncoder`
(max abs difference 0.00e+00 on both).

### 2. Data admission — REDUCED TO 0.81%, NOT THE CAUSE

Rendering every train/discovery/dev fragment both ways — under
`MULTILINGUAL_CONDITIONED` admission and under D14's language-blind
rendering — and comparing encoded token counts:

| | |
|---|---|
| tokens, admitted rendering | 2,042,993 |
| tokens, D14 language-blind | 2,059,694 |
| **lost to admission** | **16,701 (0.81%)** |
| fragments losing ≥1 token | 108 of 21,920 (0.5%) |
| fragments dropped entirely | **0** |

Both renderings yield the same 21,013-fragment training pool. A 0.81% token
difference cannot produce a 5.7-point AUC gap.

### 3. Seed — STILL UNTESTED, AND NO LONGER THE LEADING CANDIDATE

Separating seed variance requires new training runs, which Gate 3 does not
authorize. It remains untested. It is no longer the leading explanation,
because a 2× training-budget difference is present and sufficient.

## Everything else was checked and is identical

Ruling out provenance drift between D14's inputs and Stage 1's:

- **Tokenizer vocabulary**: `Archive/configs/tokenizer.json` and
  `configs/tokenizer.json` have identical `vocab` dicts (2,374 entries, same
  ids). The differing file checksums are formatting only.
- **Decomposed corpus**: identical content — 3,204,303 rows, 21,577 docs,
  375,950 lines, identical damage-state counts. The live file is larger only
  because P4-D added a `word_index_in_line` column.
- **`edges.parquet`, `splits.parquet`, `corpus.parquet`, `doc_table.parquet`**:
  byte-identical between `Archive/p2_out/` and `Phase1_pipeline/p2_out/`.
- **The samplers**: `p4f_data.sample_mlm_batch` and
  `sample_boundary_batch` were run against D14's originals from
  `Archive/lib/hittite_model.py` on one shared pool with one shared seed —
  **0 mismatches across 200 MLM batches and 200 boundary batches**. The
  P4-F data path is a faithful reimplementation; the `aux` threading is a
  true no-op on token selection.

## Corroboration from the training curves

The curves diverge early and the gap widens, consistent with a halved
training budget rather than a late instability:

| step | D14 mlm | arm A mlm | arm B mlm |
|---|---|---|---|
| 500 | 4.8535 | 4.8909 | 4.8955 |
| 10,000 | 4.3901 | 4.6008 | 4.5948 |
| 30,000 | 4.0334 | 4.2585 | 4.2866 |
| 59,500 | 3.7932 | 4.0810 | 4.0943 |

Final dev mlm: D14 3.8778, arm A 4.0667, arm B 4.0729.

## What should happen next — for Ixca to decide

A corrected Stage 1 rerun at D14's actual config (32/32/2000) would make the
falsifier's second clause a real test for the first time. Two questions
belong to the ratifier, not to this session:

1. **Is a corrected rerun covered by the existing ratification?** It is
   arguably "the two named runs, at the named budget, against the named
   falsifier" executed correctly, the first attempt having been
   mis-configured. It is arguably new GPU training. **Not assumed either
   way; no rerun was started.**
2. **Should the falsifier's second clause survive contact with this?**
   Re-running at matched budget tests it honestly. Note this must be settled
   *before* the rerun, not after seeing its result — the same discipline that
   kept P2-E9's target-sensitivity sweep from being presented as a proposal.

Estimated cost at matched config: batch 32 roughly halves step throughput, so
~6 h per arm on a clear GPU, ~12 h for both.

## Fixed in passing

`load_pretrain_data`'s `lines_emptied_by_language_admission` counter was
never incremented — it reported 0 regardless. A statistic that cannot be
nonzero is worse than no statistic, since it reads as evidence of absence.

## Artifacts

- `scripts/phase4_p4f_baseline_diagnostic.py`
- `Phase4/phase4_out/p4f_baseline_diagnostic.json`
