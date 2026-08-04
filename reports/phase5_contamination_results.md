# Contamination control — results

> **CORRECTIVE REVIEW 2026-08-04.** `MEMORISATION_REJECTED` below is the
> historical preregistered label, not the current causal interpretation.
> Retention 1.016 establishes that correct Hittite passage sequence is not
> necessary for aggregate gain. It does not exclude every memorised component
> in the original run: replacement tokens remain real transliteration strings,
> alpha is refit, and per-query mechanism stability was not measured. See
> `reports/phase5_classical_control_review.md`.

**Status: COMPLETE 2026-08-04. Historical preregistered verdict:
MEMORISATION_REJECTED. Current interpretation: correct passage sequence is
not necessary for aggregate gain.**
`[PROBE — not for citation]`; dev split only, test never loaded.

Executes `reports/phase5_contamination_protocol.md` (PRE-REGISTERED, committed
as `786db09` before the run). Training-free.

## Result

Five bijective, character-length-preserving permutations of the 1,339-sign
dev vocabulary. **BM25 invariance passed on all five** — its 865 per-query
records were byte-identical before and after, which is the correctness proof
that each permutation really is a consistent bijection.

| seed | relabeled | CANINE Δ | 95% CI | XLM-R Δ | 95% CI |
|---|---|---|---|---|---|
| 20260804 | 95.54% | +0.0474 | [+0.0243, +0.0705] | +0.0347 | [+0.0139, +0.0566] |
| 20260805 | 99.95% | +0.0474 | [+0.0243, +0.0717] | +0.0208 | [+0.0023, +0.0405] |
| 20260806 | 99.97% | +0.0439 | [+0.0208, +0.0682] | +0.0370 | [+0.0173, +0.0566] |
| 20260807 | 97.61% | +0.0416 | [+0.0208, +0.0624] | +0.0243 | [+0.0035, +0.0463] |
| 20260808 | 99.90% | +0.0543 | [+0.0324, +0.0775] | +0.0347 | [+0.0173, +0.0543] |

Pooled (mean per-query delta across permutations, paired bootstrap over
queries):

| | mean Δ | 95% CI | retention vs +0.0462 |
|---|---|---|---|
| **CANINE-s** | **+0.0469** | [+0.0266, +0.0687] | **1.016** |
| XLM-R base | +0.0303 | [+0.0141, +0.0490] | 0.656 |

By the pre-registered rule (retention ≥ 0.50 and CI excludes zero):
**MEMORISATION REJECTED.**

CANINE's retention is **1.016** — the aggregate gain is preserved under
relabeling and every permutation clears zero. This establishes that correct
passage sequence is unnecessary for the aggregate effect; it does **not**
measure or exclude a memorised component in the original run. XLM-R also
survives (0.656), attenuated, consistent with—but not proving—a sensitivity
to changed subword segmentation.

This is the survival branch of the historical one-sided rule. The corrected
causal reading is narrower because the test permits mechanism substitution
and retains real transliteration strings.

## The implication is not entirely comfortable

The relabeled corpus is **not Hittite**. It is not any language — it is
pseudo-text produced by permuting sign identities. CANINE's contribution to
the combiner is *completely unaffected* by that.

So the honest reading cuts both ways:

- **Good**: the +0.0462 cannot be an artifact of TLHdig or hethiter.net
  appearing in multilingual Wikipedia. The result is real and reportable, and
  the contamination section a Gate-3 proposal owes can now cite a measurement
  rather than an argument.
- **Deflating, and more important**: whatever CANINE contributes, **it is not
  knowledge of Hittite**. If linguistic transfer from pretraining were doing
  the work, destroying the language would have destroyed the gain. It did
  not. What survives is generic character-sequence similarity — a fuzzy
  string matcher, not a language model bringing knowledge to a low-resource
  script.

That directly weakens the *stated motivation* for rungs 4 and 6. The ladder
frames them as testing whether transfer from large pretrained multilingual
models helps fragmentary Hittite. On this evidence the transfer that is
actually operating is not linguistic, so fine-tuning on Hittite has less
obvious headroom to unlock than the framing assumed.

## What this makes worth testing next

If the useful signal is generic character-sequence similarity and not
language knowledge, then **a classical character n-gram model should be able
to recover it** — no pretrained weights, no GPU, no contamination question at
all. That is now the cheapest way to find out whether either owed rung is
worth writing, and it is the natural successor to this run. Pre-registered
separately.

## Limitations

- Relabeling is length-preserving *per sign*, so total sequence length and
  truncation are held fixed; 95.5–99.97% of sign occurrences actually moved
  (the residue is fixed points, unavoidable in the five singleton
  length-classes and by chance elsewhere), and the realised fraction is
  reported per seed rather than assumed.
- The test bounds one alternative explanation for one measured gain. It does
  not prove TLHdig is absent from any pretraining corpus, says nothing about
  the test split, and licenses no claim about fine-tuned performance.
- Dev only, five permutations, one fold assignment.

## Artifacts

- `scripts/phase5_contamination_relabel.py`
- `Phase4/phase4_out/p5_contamination_relabel.json`
