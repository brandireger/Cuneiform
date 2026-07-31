# Real-gap calibration application (step 3)

Reuses already-computed, composition-disjoint fold calibrations -- P2-E4 for same-line gaps and the separately ratified P2-E9 calibration for cross-line gaps. No recalibration happens here, and their rates and counts are never pooled.

Production scope is the union of **38 same-line CTHs** covered by P2-E4 and **279 cross-line CTHs** covered by usable P2-E9 folds: **288 distinct CTHs and 6,145 documents**. The previous application passed only the same-line set into `prepare_scope()`, unintentionally discarding cross-line CTHs before P2-E9 eligibility was checked.

Same-line remains restricted to anchor_length=2, mask_length=1 under P2-E4. Cross-line remains restricted to P2-E9's own single-sign cell and ratified policy. Neither population borrows the other's calibration.

- **703** real gaps eligible under this scope.
- **41** pass the fold's own selector rule (a real candidate set would be presented); **662** do not (the evidence doesn't meet the bar the calibration itself was computed under -- these would abstain, not receive an unreliable rate).

Of **40** selector-accepted `restored` spans checked against the calibrated ranking: **38** match a ranked witness alternative (a calibrated rate applies), **2** are contradicted by the best-witnessed (rank-1) alternative, and **0** have no usable calibrated rate either way. All totals below are full counts, not just the samples shown.

## Sample: rank-1 candidate with its calibrated track record

- `IBoT 4.140+::2`: rank-1 witness proposal `ZU₉` -- historically correct at rank 1 about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 10.25+::1`: rank-1 witness proposal `GIŠ` -- historically correct at rank 1 about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 10.31`: rank-1 witness proposal `LÚ` -- historically correct at rank 1 about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 11.40`: rank-1 witness proposal `li` -- historically correct at rank 1 about 91.2% of the time (95% CI 90.3-92.0%, n=4,408).
- `KBo 11.42+::2`: rank-1 witness proposal `GUR₄` -- historically correct at rank 1 about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 11.52`: rank-1 witness proposal `zi` -- historically correct at rank 1 about 91.4% of the time (95% CI 90.5-92.2%, n=3,797).
- `KBo 16.23`: rank-1 witness proposal `rad` -- historically correct at rank 1 about 91.2% of the time (95% CI 90.3-92.0%, n=4,408).
- `KBo 19.109a`: rank-1 witness proposal `ki` -- historically correct at rank 1 about 91.6% of the time (95% CI 90.7-92.4%, n=4,370).

## Editor's restoration matches a ranked witness alternative (38 total, up to 8 shown)

- `IBoT 4.140+::2`: editor reading `ZU₉` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 10.25+::1`: editor reading `GIŠ` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 10.31`: editor reading `LÚ` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 11.40`: editor reading `li` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.2% of the time (95% CI 90.3-92.0%, n=4,408).
- `KBo 11.42+::2`: editor reading `GUR₄` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.4% of the time (95% CI 90.3-92.4%, n=2,730).
- `KBo 11.52`: editor reading `zi` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.4% of the time (95% CI 90.5-92.2%, n=3,797).
- `KBo 16.23`: editor reading `rad` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.2% of the time (95% CI 90.3-92.0%, n=4,408).
- `KBo 19.109a`: editor reading `ki` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.6% of the time (95% CI 90.7-92.4%, n=4,370).

## Editor's restoration contradicted by the rank-1 (best-supported) alternative (2 total, up to 8 shown)

- `KBo 27.42`: editor reading `BANŠUR`, but the best-witnessed alternative is `GIDRU` -- candidates at rank 1 have historically been correct about 91.4% of the time (95% CI 90.3-92.4%, n=2,730). This is NOT the probability the editor is wrong -- it is the rank's historical track record, reported per the same rule as everywhere else in this project.
- `KBo 45.89`: editor reading `ma`, but the best-witnessed alternative is `(empty)` -- candidates at rank 1 have historically been correct about 91.4% of the time (95% CI 90.5-92.2%, n=3,797). This is NOT the probability the editor is wrong -- it is the rank's historical track record, reported per the same rule as everywhere else in this project.

## What this still does not establish

A calibrated rank-1 rate is a property of many past comparisons at that rank, not this specific instance -- exactly the distinction Ixca asked to have made clearer in the demo UI. Same-line CTHs outside the P2-E4 set have no applicable same-line calibration; cross-line CTHs outside the usable P2-E9 folds have no applicable cross-line calibration. Multi-sign real gaps use the separate P2-E6 path. P2-E10 measured cross-line multi-sign and found it unfit for decision-support, so it remains deliberately unapplied.

## Cross-line gaps (separate population, separate calibration)

Admission rule **LAYOUT_AGNOSTIC**, ratified target **0.75**. Cross-line has its own calibration (P2-E9) and its own target; this is NOT the same-line 0.90 rate applied to a wider population.

- **46,118** cross-line gaps eligible (single-sign, CTH covered by a usable P2-E9 fold).
- **577** pass the fold's own selector; 45,541 do not, and abstain rather than receive an uncertified rate.
- Of 458 selector-accepted `restored` spans, 308 have the editor's reading somewhere among the witness-ranked alternatives -- corroboration, never proof.

**Which rate is attached.** `rank_calibration_calibration_set` -- fit on compositions disjoint from this fold's evaluation CTHs, matching how the same-line path applies P2-E4. The held-out table is the quality claim, not the per-gap number: it is measured on the very compositions these gaps come from, so attaching it here would be circular.

**How good is that calibration?** It transfers: 77.5% rank-1 agreement on 8,208 held-out spans, transfer gap 0.0 points.

**Never pool these with the same-line counts above.** Cross-line and same-line differ by roughly 5x in gold inclusion and have different ratified targets (0.75 vs 0.90). A combined count would describe neither.

**The empty middle: measured, and resolved by display.** A rank-1 proposal may be the *empty* middle -- witnesses attesting the two anchors adjacent with nothing between. For a one-sign gap that is disagreement with the query's own structure, not a reading. It was measured (`reports/phase5_empty_middle_census.md`): **109 of 577 accepted cross-line gaps (18.9%)**, against 1 of 41 same-line.

It is **deliberately still ranked**. Filtering it was measured too and does not surface a better reading -- it surfaces an abstention (zero rank-1 changes; net accepts 577 -> 517). More importantly the empty middle was in the index when P2-E4 and P2-E9 were FIT, so the ratified rates already price it in, and removing it at application time only would decouple the rate from the thing it rates.

The adopted remedy is display-layer: the option keeps its rank and witness support, but is labelled as typed contradictory evidence rather than a reading, and its rank-level group rate is withheld -- that rate's estimand is agreement with the true attested middle, which this option cannot be. See `lib/expert_decision_contract.py`'s `annotate_empty_middle_options()`. The wording branches on what the editor actually wrote, because these are four different situations, not one:

| the gap is | share of the 109 | what 'witnesses show nothing' means |
|---|---:|---|
| illegible trace (`x`) | 57 | your trace is off-formula for this collocation |
| an editorial restoration | 41 | **the witnesses contradict a scholarly bracket** |
| an indeterminate lacuna (`…`) | 11 | the parallel tradition has no gap here |
| a hidden attested sign (evaluation contexts only) | n/a | cannot be correct by construction |
