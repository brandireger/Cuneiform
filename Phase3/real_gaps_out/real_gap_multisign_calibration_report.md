# Real-gap multi-sign calibration application (step 4)

<!-- p4d-staleness-stamp -->
> **[PREDATES P4-D — numbers not recomputed]** This report was produced before
> the real-gap query side was language-resolved. Under P4-D (2026-07-26) a gap
> may only ASK under the same explicit language scope that governs which
> witness lines may ANSWER; previously every line in the slice could query,
> so non-Hittite gaps sat in the same denominator and simply found no
> coverage. On the measured slice **~9.5% of the gap population** was
> non-Hittite or unresolved. The witness index was also rebuilt word-aware
> (932 previously-admitted lines now refused). The numbers below have **not**
> been recomputed; rerunning is P4-G work. See
> `reports/phase4_p4d_language_aware_apis.md`.

Reuses the already-computed, already-frozen fold calibration from `Phase2/phase2_out/p2e6_multisign_horizon.json` -- no recalibration. Unlike step 3's per-rank P2-E4 rates, this calibration is a **set-inclusion rate**, keyed by (mask_length, adaptive_anchor_length): "Among witness-supported calibration-composition spans with the same mask length and selected adaptive anchor length, the fraction whose intentionally hidden attested span occurs in the tie-complete displayed set"

Scoped to the **39 CTHs** the existing 5 P2-E6 folds actually cover (union of all folds' `evaluation_cth` lists): **741 documents** in scope.

Same-line anchors only -- P2-E6's own folds were fit entirely on synthetic within-line masks, so there is no cross-line calibration to borrow (same posture as step 3's single-sign application).

- **8,900** real gaps with mask length in [2, 3, 4, 5] found in scope.
- **1,317** eligible (a same-line 1-sign anchor exists on both sides -- the base population P2-E6 itself starts from before trying longer anchors).
- **923** presented (some anchor length 1-3 found independent witness support -- the adaptive selection rule, longest anchor first); **394** abstained (no anchor length had any support at all).

### Mask-length distribution among eligible gaps

| mask length | count |
|---|---|
| 2 | 657 |
| 3 | 325 |
| 4 | 206 |
| 5 | 129 |

### Selected adaptive anchor length among eligible gaps

| anchor length | count |
|---|---|
| 1 | 793 |
| 2 | 89 |
| 3 | 41 |
| abstain | 394 |

Of **784** presented `restored` spans checked against the calibrated candidate set: **328** have the editor's reading included in the tie-complete displayed set (a calibrated set-inclusion rate applies), **456** do not (the editor's reading is absent from every witnessed alternative at the selected anchor length), and **0** have no usable calibrated rate for their (mask_length, anchor_length) group (that combination never occurred in the OTHER folds' calibration data for this fold).

## Editor's restoration included in the calibrated candidate set (328 total, up to 8 shown)

- `Bo 3322+`: 2-sign editor reading `a aš` is one of 4 displayed alternatives (adaptive anchor length 2) -- candidate sets in this (mask=2, anchor=2) group have historically included the true attested span about 64.5% of the time (95% CI 63.3-65.6%, n=6,967).
- `Bo 9400+`: 2-sign editor reading `pa an` is one of 3 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 36.4% of the time (95% CI 35.9-36.9%, n=34,288).
- `Bo 9400+`: 2-sign editor reading `na ni` is one of 1 displayed alternatives (adaptive anchor length 2) -- candidate sets in this (mask=2, anchor=2) group have historically included the true attested span about 64.5% of the time (95% CI 63.3-65.6%, n=6,967).
- `Bo 9400+`: 2-sign editor reading `ša an` is one of 1 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 36.4% of the time (95% CI 35.9-36.9%, n=34,288).
- `Bo 9400+`: 4-sign editor reading `ŠU GIŠ AB ia` is one of 11 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 16.3% of the time (95% CI 15.8-16.8%, n=24,447).
- `CHDS 5.12`: 2-sign editor reading `DUG mar` is one of 36 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 32.1% of the time (95% CI 31.6-32.7%, n=30,719).
- `CHDS 5.173`: 2-sign editor reading `ZA LAM` is one of 1 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 32.1% of the time (95% CI 31.6-32.7%, n=30,719).
- `IBoT 1.29`: 2-sign editor reading `NINDA KU₇` is one of 5 displayed alternatives (adaptive anchor length 1) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 35.1% of the time (95% CI 34.6-35.6%, n=36,475).

## Editor's restoration NOT found among the calibrated candidate set (456 total, up to 8 shown)

- `Bo 9400+`: 4-sign editor reading `kán D ka a` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `at I NA É ḫa`) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 16.3% of the time (95% CI 15.8-16.8%, n=24,447). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `a le` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `re`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 36.4% of the time (95% CI 35.9-36.9%, n=34,288). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `UZU ZAG` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `zi <NUM>`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 36.4% of the time (95% CI 35.9-36.9%, n=34,288). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `ZAG an` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `še e ra an`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 36.4% of the time (95% CI 35.9-36.9%, n=34,288). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `Bo 9400+`: 2-sign editor reading `iš ša` does not match any of 1 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `pí da a`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 36.4% of the time (95% CI 35.9-36.9%, n=34,288). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `CHDS 5.2`: 4-sign editor reading `NINDA a a an` does not match any of 5 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `(empty)`) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 14.5% of the time (95% CI 14.1-15.0%, n=26,090). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `CHDS 5.2`: 4-sign editor reading `NINDA LA AB KU` does not match any of 5 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `(empty)`) -- candidate sets in this (mask=4, anchor=1) group have historically included the true attested span about 14.5% of the time (95% CI 14.1-15.0%, n=26,090). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.
- `CHDS 5.2`: 2-sign editor reading `DUG KAŠ` does not match any of 5 displayed alternatives (adaptive anchor length 1; best-witnessed alternative is `(empty)`) -- candidate sets in this (mask=2, anchor=1) group have historically included the true attested span about 35.1% of the time (95% CI 34.6-35.6%, n=36,475). This is NOT the probability the editor is wrong -- it is the group's historical inclusion rate, reported per the same rule as everywhere else in this project.

## What this still does not establish

A group's candidate-set calibration rate is a property of many past comparisons within that (mask_length, adaptive_anchor_length) group, not this specific instance. It also describes the SET as a whole, not any individual displayed alternative -- there is no per-alternative probability here, unlike step 3's per-rank rates. Cross-line multi-sign gaps remain entirely uncalibrated, as do all cross-line single-sign gaps from step 3. Both are real, separately-scoped next steps, not folded in silently here.