# Real-gap calibration application (step 3)

Reuses the already-computed, already-frozen fold calibration from `Phase2/phase2_out/p2e4_candidate_set_audit.json` -- no recalibration, the same rank-by-rank rates the demo's own packets already display.

Scoped directly to the **42 CTHs** any fold's held-out evaluation set actually covers (union of all 5 folds' `evaluation_cth` lists) -- widened from the first increment, which only intersected step 2's unrelated "top gap count" list and found just CTH 627 overlapping. This increment asks `prepare_scope()` for the calibration-covered CTHs directly: **749 documents** in scope, vs. step 2's original 867.

Further scoped to same-line anchors and length-1 gaps only (this calibration file is anchor_length=2, mask_length=1 specifically -- other lengths and cross-line anchors have no matching calibration and are not guessed at).

- **1,010** real gaps eligible under this scope.
- **44** pass the fold's own selector rule (a real candidate set would be presented); **966** do not (the evidence doesn't meet the bar the calibration itself was computed under -- these would abstain, not receive an unreliable rate).

Of **44** selector-accepted `restored` spans checked against the calibrated ranking: **41** match a ranked witness alternative (a calibrated rate applies), **3** are contradicted by the best-witnessed (rank-1) alternative, and **0** have no usable calibrated rate either way. All totals below are full counts, not just the samples shown.

## Sample: rank-1 candidate with its calibrated track record

- `CHDS 5.173`: rank-1 witness proposal `NINDA` -- historically correct at rank 1 about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `IBoT 4.140+::2`: rank-1 witness proposal `ZU₉` -- historically correct at rank 1 about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 10.25+::1`: rank-1 witness proposal `GIŠ` -- historically correct at rank 1 about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 10.31`: rank-1 witness proposal `LÚ` -- historically correct at rank 1 about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 11.40`: rank-1 witness proposal `li` -- historically correct at rank 1 about 91.4% of the time (95% CI 90.6-92.1%, n=5,118).
- `KBo 11.42+::2`: rank-1 witness proposal `GUR₄` -- historically correct at rank 1 about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 11.52`: rank-1 witness proposal `zi` -- historically correct at rank 1 about 91.5% of the time (95% CI 90.3-92.5%, n=2,705).
- `KBo 15.70+`: rank-1 witness proposal `ḫé` -- historically correct at rank 1 about 90.9% of the time (95% CI 90.1-91.7%, n=4,993).

## Editor's restoration matches a ranked witness alternative (41 total, up to 8 shown)

- `CHDS 5.173`: editor reading `NINDA` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `IBoT 4.140+::2`: editor reading `ZU₉` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 10.25+::1`: editor reading `GIŠ` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 10.31`: editor reading `LÚ` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 11.40`: editor reading `li` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.4% of the time (95% CI 90.6-92.1%, n=5,118).
- `KBo 11.42+::2`: editor reading `GUR₄` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.1% of the time (95% CI 90.1-92.0%, n=3,430).
- `KBo 11.52`: editor reading `zi` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 91.5% of the time (95% CI 90.3-92.5%, n=2,705).
- `KBo 15.70+`: editor reading `ḫé` matches the rank-1 witness alternative -- candidates at that rank have historically been correct about 90.9% of the time (95% CI 90.1-91.7%, n=4,993).

## Editor's restoration contradicted by the rank-1 (best-supported) alternative (3 total, up to 8 shown)

- `KBo 15.72+`: editor reading `ni`, but the best-witnessed alternative is `ni pa a e` -- candidates at rank 1 have historically been correct about 90.9% of the time (95% CI 90.1-91.7%, n=4,993). This is NOT the probability the editor is wrong -- it is the rank's historical track record, reported per the same rule as everywhere else in this project.
- `KBo 27.42`: editor reading `BANŠUR`, but the best-witnessed alternative is `GIDRU` -- candidates at rank 1 have historically been correct about 91.1% of the time (95% CI 90.1-92.0%, n=3,430). This is NOT the probability the editor is wrong -- it is the rank's historical track record, reported per the same rule as everywhere else in this project.
- `KUB 32.19+`: editor reading `šu`, but the best-witnessed alternative is `(empty)` -- candidates at rank 1 have historically been correct about 90.9% of the time (95% CI 90.1-91.7%, n=4,993). This is NOT the probability the editor is wrong -- it is the rank's historical track record, reported per the same rule as everywhere else in this project.

## What this still does not establish

A calibrated rank-1 rate is a property of many past comparisons at that rank, not this specific instance -- exactly the distinction Ixca asked to have made clearer in the demo UI. This is still the full extent of what these 5 folds cover -- CTHs outside this list have no P2-E4 calibration at all, and widening further would mean computing new folds, not reusing these. Multi-sign real gaps need the analogous P2-E6 fold structure; cross-line anchors have no calibration at all yet. Each is a real, separately-scoped next step, not something to fold in silently.