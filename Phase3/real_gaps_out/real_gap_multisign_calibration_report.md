# Real-gap multi-sign calibration application (step 4)

Reuses the already-computed, already-frozen fold calibration from `Phase2/phase2_out/p2e6_multisign_horizon.json` -- no recalibration. Unlike step 3's per-rank P2-E4 rates, this calibration is a **set-inclusion rate**, keyed by (mask_length, adaptive_anchor_length): "Among witness-supported calibration-composition spans with the same mask length and selected adaptive anchor length, the fraction whose intentionally hidden attested span occurs in the tie-complete displayed set"

Scoped to the **42 CTHs** the existing 5 P2-E6 folds actually cover (union of all folds' `evaluation_cth` lists): **749 documents** in scope.

Same-line anchors only -- P2-E6's own folds were fit entirely on synthetic within-line masks, so there is no cross-line calibration to borrow (same posture as step 3's single-sign application).

- **9,022** real gaps with mask length in [2, 3, 4, 5] found in scope.
- **1,338** eligible (a same-line 1-sign anchor exists on both sides -- the base population P2-E6 itself starts from before trying longer anchors).
- **989** presented (some anchor length 1-3 found independent witness support -- the adaptive selection rule, longest anchor first); **349** abstained (no anchor length had any support at all).

### Mask-length distribution among eligible gaps

| mask length | count |
|---|---|
| 2 | 664 |
| 3 | 329 |
| 4 | 213 |
| 5 | 132 |

### Selected adaptive anchor length among eligible gaps

| anchor length | count |
|---|---|
| 1 | 834 |
| 2 | 106 |
| 3 | 49 |
| abstain | 349 |

Of **835** presented `restored` spans checked against the calibrated candidate set: **356** have the editor's reading included in the tie-complete displayed set (a calibrated set-inclusion rate applies), **479** do not (the editor's reading is absent from every witnessed alternative at the selected anchor length), and **0** have no usable calibrated rate for their (mask_length, anchor_length) group (that combination never occurred in the OTHER folds' calibration data for this fold).

## Editor's restoration included in the calibrated candidate set (356 total, up to 8 shown)

- `Bo 3322+`: 2-sign editor reading `a aš` is one of 4 displayed alternatives (adaptive anchor length 2) -- candidate sets in this (mask=2, anchor=2) group have historically included the true attested span about 57.6% of the time (95% CI 56.5-58.6%, n=8,578).
- `Bo 9400+`: 2-sign editor reading `pa an` is one of 3 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 31.4% of the time (95% CI 31.0-31.8%, n=45,059).
- `Bo 9400+`: 2-sign editor reading `na ni` is one of 1 displayed alternatives (adaptive anchor length 2) -- candidate sets in this (mask=2, anchor=2) group have historically included the true attested span about 57.6% of the time (95% CI 56.5-58.6%, n=8,578).
- `Bo 9400+`: 2-sign editor reading `ša an` is one of 1 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 31.4% of the time (95% CI 31.0-31.8%, n=45,059).
- `Bo 9400+`: 4-sign editor reading `ŠU GIŠ AB ia` is one of 11 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 12.7% of the time (95% CI 12.4-13.1%, n=33,446).
- `CHDS 5.12`: 2-sign editor reading `DUG mar` is one of 36 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 28.5% of the time (95% CI 28.0-28.9%, n=42,762).
- `CHDS 5.173`: 2-sign editor reading `ZA LAM` is one of 1 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 28.5% of the time (95% CI 28.0-28.9%, n=42,762).
- `IBoT 1.29`: 2-sign editor reading `NINDA KU₇` is one of 5 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 32.0% of the time (95% CI 31.6-32.4%, n=47,171).

## Editor's restoration NOT found among the calibrated candidate set (479 total, up to 8 shown)

- `Bo 9400+`: 4-sign editor reading `kán D ka a` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `at I NA É ḫa`) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 12.7% of the time (95% CI 12.4-13.1%, n=33,446). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `a le` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `re`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 31.4% of the time (95% CI 31.0-31.8%, n=45,059). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `UZU ZAG` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `zi <NUM>`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 31.4% of the time (95% CI 31.0-31.8%, n=45,059). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `ZAG an` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `še e ra an`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 31.4% of the time (95% CI 31.0-31.8%, n=45,059). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `iš ša` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `pí da a`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 31.4% of the time (95% CI 31.0-31.8%, n=45,059). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `CHDS 5.2`: 4-sign editor reading `NINDA a a an` does not match any of 5 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `(empty)`) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 12.9% of the time (95% CI 12.6-13.3%, n=34,380). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `CHDS 5.2`: 4-sign editor reading `NINDA LA AB KU` does not match any of 5 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `(empty)`) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 12.9% of the time (95% CI 12.6-13.3%, n=34,380). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `CHDS 5.2`: 2-sign editor reading `DUG KAŠ` does not match any of 5 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `(empty)`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 32.0% of the time (95% CI 31.6-32.4%, n=47,171). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.

## What this still does not establish

A group's candidate-set calibration rate is a property of many past comparisons within that (mask_length, adaptive_anchor_length) group, not this specific instance. It also describes the SET as a whole, not any individual displayed alternative -- there is no per-alternative probability here, unlike step 3's per-rank rates. Cross-line multi-sign gaps remain entirely uncalibrated, as do all cross-line single-sign gaps from step 3. Both are real, separately-scoped next steps, not folded in silently here.