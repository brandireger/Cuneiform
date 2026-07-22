# P4 D13 -- Fracture Engine Report

- Eligible TRAIN fragments for cut pairs (>= 8 lines, >= 60 attested signs): **3333**
- Eligible for self-supervised views (TRAIN + discovery pool): **17644**
- Dev-diagnostic set materialized: 2000 cut pairs (p4_out\fracture_dev_diagnostic.jsonl)
- **Generator is streaming/seeded for D14/D15 -- millions of pairs are never materialized to disk.**

## Calibration summary (full detail in fracture_calibration.json)

- Del-span length: mean=4.7, median=2.0, p90=10.0 signs (n=99,218 spans)
- Top edge lost rate: 76.5%, bottom edge lost rate: 97.8%
- Illegible-x rate (of non-restored signs): 4.14%
- Left edge state distribution: {'illegible_x': 0.13917979721045365, 'laes': 0.04890631694197172, 'restored': 0.41418336744894557, 'attested': 0.39773051839862905}
- Right edge state distribution: {'illegible_x': 0.11741919360213263, 'attested': 0.5224984528966535, 'restored': 0.3089208359118389, 'laes': 0.05116151758937497}
- Real seam geometry share (from join tiers): {'horizontal': 0.5806451612903226, 'vertical': 0.41935483870967744}
- **Note on vertical gap width**: tier A/B n_shared_lines is ~always 0 by definition (that IS the no-overlap seam signature) -- true real vertical GAP WIDTH (how many whole lines are lost between two stacked members) is not directly measurable from this field; the fracture engine's gap-line-count sampling below is a documented modeling assumption (Poisson), not corpus-calibrated, and is flagged as such rather than silently presented as measured.

## Distribution-match: synthetic vs real (shown, not asserted)

| metric | real mean | real p50 | real p90 | synth mean | synth p50 | synth p90 |
|---|---|---|---|---|---|---|
| n_lines | 25.4 | 15.0 | 52.0 | 26.0 | 16.0 | 54.0 |
| n_attested_signs | 167.4 | 59.0 | 344.5 | 157.8 | 71.0 | 350.1 |

## 10 rendered examples (before/after, both members, seam params)

### Example 1/10 -- source `KBo 1.18`, vertical cut
- params: {"cut_type": "vertical", "boundary_line": 22, "gap_width_lines": 1, "n_lines_total": 76}
- member_a ({'n_lines': 10, 'n_attested_signs': 24}): `x x x x x <LINE> <LINE> <LINE> <LINE> iṣ bat qa ab li ù <LINE> <LINE> <LINE> x <LINE> <LINE> <LINE> <LINE> x <LINE> x <LINE> x <LINE> x <LINE> pa at ú ul i ia a <LINE> <LINE> <LINE> <LINE>`
- member_b ({'n_lines': 48, 'n_attested_signs': 278}): `<LINE> <LINE> <LINE> x <LINE> <LINE> x <NUM> x a x <LINE> x <LINE> x <LINE> x at <LINE> x bi <LINE> x mu un <LINE> da a an <LINE> x e x <LINE> x <LINE> za e ì <LINE>`

### Example 2/10 -- source `KBo 49.15`, horizontal cut
- params: {"cut_type": "horizontal", "mean_offset_frac": 0.5, "jitter": 0.15, "per_line_offsets": [5, 4, 6, 7, 8, 5, 6, 4, 4, 1], "per_line_erosions": [0, 2, 2, 0, 1, 2, 0, 1, 1, 2]}
- member_a ({'n_lines': 9, 'n_attested_signs': 40}): `x É ḫi lam ni <LINE> ḫu u <LINE> pa É ḫa le <LINE> an da ar nu wa an zi <LINE> x x a ḫu u wa an <LINE> u wa an <LINE> A x ḫa pu pí it`
- member_b ({'n_lines': 8, 'n_attested_signs': 31}): `an da IŠ TU <LINE> <LINE> aš an da <LINE> <NUM> NINDA GUR₄ RA <LINE> MEŠ A BI da <LINE> wa ar <LINE> MUŠEN MUŠEN ḪUR RI Ù x <LINE> lam ni GAM an <LINE> D li lu u <LINE>`

### Example 3/10 -- source `KBo 54.123`, vertical cut
- params: {"cut_type": "vertical", "boundary_line": 48, "gap_width_lines": 0, "n_lines_total": 67}
- member_a ({'n_lines': 42, 'n_attested_signs': 216}): `x <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> un na DAM <LINE> KÙ BABBAR GAR RA <LINE> x nu uš IT TI <LINE> <LINE> na at <LINE> x x <LINE> <NUM> aš PA NI DUMU LUGAL <LINE> lam ni it QA`
- member_b ({'n_lines': 19, 'n_attested_signs': 150}): `an x x šar ra an zi <LINE> <NUM> x <NUM> x ḪI A LÚ MEŠ x URU ga aš ḫa <LINE> da an zi na an I NA MU <NUM> KAM <LINE> A NA EZEN₄ MEŠ ŠA D te`

### Example 4/10 -- source `KBo 3.6+::1`, horizontal cut
- params: {"cut_type": "horizontal", "mean_offset_frac": 0.5, "jitter": 0.15, "per_line_offsets": [8, 9, 11, 7, 13, 13, 11, 10, 8, 14, 12, 12, 10, 13, 9, 10, 7, 15, 15, 9, 10, 7, 10, 15, 12, 10, 9, 9, 8, 11, 8, 10, 13, 12, 13, 14, 14, 16, 10, 13, 7, 9, 12, 10, 7, 11, 3, 5, 5, 8, 8, 4, 5, 3, 2, 3, 2, 1, 12, 14, 10, 8, 17, 11, 10, 13, 8, 10, 11, 16, 10, 15, 14, 13, 10, 8, 10, 7, 7, 8, 8, 12, 8, 9, 13, 14, 8, 13, 12, 12, 8, 9, 12, 9, 10, 11, 12, 10, 9, 0, 1, 9, 5, 6, 3, 2, 2, 1, 2, 1, 1, 1, 3, 3, 7, 6, 6, 10, 6, 8, 8, 8, 4, 10, 9, 8, 8, 15, 14, 14, 14, 15, 8, 11, 11, 9, 8, 9, 10, 14, 12, 8, 12, 11, 9, 11, 9, 8, 12, 14, 10, 10, 9, 9, 9, 14, 7, 13, 7, 13, 14, 13, 6, 12, 5, 4, 6, 6, 8, 4, 6, 8, 6, 5, 8, 4, 6, 6, 5, 4, 6, 5, 2, 3, 2, 1, 5, 6, 7], "per_line_erosions": [1, 2, 2, 1, 0, 0, 1, 1, 0, 0, 2, 0, 1, 2, 2, 2, 0, 1, 1, 1, 0, 2, 2, 1, 1, 0, 0, 1, 0, 0, 0, 2, 2, 0, 0, 2, 0, 0, 0, 0, 0, 2, 2, 1, 2, 1, 1, 2, 0, 2, 1, 2, 2, 0, 2, 1, 2, 0, 0, 0, 1, 1, 1, 2, 1, 2, 2, 0, 1, 0, 1, 1, 2, 1, 1, 0, 1, 2, 1, 1, 2, 2, 0, 2, 0, 1, 0, 1, 0, 2, 1, 2, 1, 0, 0, 1, 0, 0, 0, 0, 1, 2, 1, 0, 1, 0, 2, 0, 2, 1, 0, 0, 0, 2, 1, 2, 2, 0, 2, 1, 1, 0, 0, 0, 1, 1, 2, 0, 1, 1, 2, 1, 0, 1, 0, 2, 0, 1, 0, 0, 1, 0, 2, 1, 2, 0, 1, 1, 2, 1, 1, 1, 1, 0, 1, 0, 1, 2, 2, 1, 2, 0, 1, 0, 0, 1, 1, 2, 0, 2, 0, 0, 0, 0, 0, 2, 0, 1, 0, 1, 0, 2, 1, 0, 0, 0, 2, 1, 2]}
- member_a ({'n_lines': 182, 'n_attested_signs': 1487}): `UM MA M ta ba ar na <LINE> LUGAL x URU ḪA x TI DUMU <LINE> DUMU DUMU ŠÚ ŠA M šu up pí lu <LINE> ŠÀ BAL LÁ ŠA M ḫa <LINE> ŠA D IŠTAR pa ra a ḫa`
- member_b ({'n_lines': 183, 'n_attested_signs': 1440}): `at tu x li LUGAL GAL <LINE> LUGAL GAL LUGAL KUR URU ḪA x TI <LINE> GAL LUGAL KUR URU ḪA AT TI <LINE> ši li x URU ku uš šar <LINE> ma aḫ ḫi na x DUMU NAM LÚ`

### Example 5/10 -- source `KBo 39.157`, horizontal cut
- params: {"cut_type": "horizontal", "mean_offset_frac": 0.5, "jitter": 0.15, "per_line_offsets": [2, 2, 1, 5, 8, 6, 4, 4, 5, 5, 1, 5, 4, 6, 2, 4, 6, 5, 5, 4, 4, 1, 2, 2], "per_line_erosions": [0, 1, 0, 1, 1, 1, 2, 0, 2, 1, 0, 0, 2, 1, 1, 0, 0, 1, 2, 2, 0, 0, 0, 2]}
- member_a ({'n_lines': 23, 'n_attested_signs': 73}): `x ḪI <LINE> É <LINE> x <LINE> x TIM x AB <LINE> x a ap pa <NUM> NINDA SIG <LINE> x pár ši ia KI <LINE> D x <LINE> it pár ši ia <LINE> <NUM> NINDA SIG <LINE> KI MIN`
- member_b ({'n_lines': 22, 'n_attested_signs': 98}): `A x <LINE> ap <LINE> <LINE> ÍD ḪI A <LINE> D ni na at ta <LINE> ap pa ma <NUM> NINDA SIG A NA D <LINE> ta pár ši ia <LINE> KI MIN a ap pa ma <LINE> i na`

### Example 6/10 -- source `KBo 40.55`, horizontal cut
- params: {"cut_type": "horizontal", "mean_offset_frac": 0.5, "jitter": 0.15, "per_line_offsets": [1, 3, 3, 2, 5, 6, 6, 5, 5, 6, 4, 1], "per_line_erosions": [0, 0, 2, 1, 1, 1, 2, 1, 1, 1, 2, 0]}
- member_a ({'n_lines': 12, 'n_attested_signs': 35}): `x x <LINE> x x GAM <LINE> x <LINE> UD <LINE> x nu kán an <LINE> QA DU URU LIM ŠU <LINE> a A NA DINGIR <LINE> x x an pa <LINE> ḫa pa it ḫa <LINE> ú it na aš`
- member_b ({'n_lines': 11, 'n_attested_signs': 37}): `x <LINE> ku uš <LINE> <LINE> GIG TUR ia x <LINE> aš ša u i <LINE> iš šu u wa an <LINE> šu u wa an zi <LINE> MUŠEN gun zi ú it <LINE> pí eš ma <LINE> KA×U ŠÚ`

### Example 7/10 -- source `KUB 52.85`, vertical cut
- params: {"cut_type": "vertical", "boundary_line": 12, "gap_width_lines": 0, "n_lines_total": 24}
- member_a ({'n_lines': 12, 'n_attested_signs': 112}): `x x x <LINE> x an ar ḫa an ka <LINE> x zi nu KIN SIG₅ ru <LINE> mu u wa an PAB nu mar ME <LINE> ni A NA KASKAL NI an da <LINE> x ša ak ti LÚ`
- member_b ({'n_lines': 11, 'n_attested_signs': 99}): `aš Ú x pa iz zi nu x NU SIG₅ du <LINE> ME aš nu kán DINGIR MEŠ NU SIG₅ <LINE> zi nu KIN NU SIG₅ du <LINE> NU SIG₅ <LINE> zi nu KIN NU SIG₅ du <LINE> <LINE> SIG₅`

### Example 8/10 -- source `KUB 7.60`, horizontal cut
- params: {"cut_type": "horizontal", "mean_offset_frac": 0.5, "jitter": 0.15, "per_line_offsets": [1, 1, 2, 4, 3, 3, 7, 6, 5, 6, 11, 4, 8, 7, 5, 6, 4, 7, 4, 5, 8, 5, 6, 5, 5, 7, 5, 5, 5, 9, 10, 7, 6, 7, 7, 5, 5, 6, 4, 3, 2, 1, 3, 4, 3, 5, 5, 9, 3, 5, 10, 6, 9, 5, 4, 4, 7, 5, 6, 6, 6, 5, 5, 6, 5, 6, 4, 8, 6, 7, 6, 9, 5, 8, 6, 5, 5, 3, 2, 1, 1, 1, 1, 1, 0, 0, 1], "per_line_erosions": [1, 0, 2, 1, 2, 0, 0, 1, 1, 2, 2, 1, 1, 2, 0, 0, 0, 1, 1, 0, 2, 0, 0, 1, 2, 1, 2, 1, 0, 2, 2, 2, 2, 1, 0, 1, 0, 0, 1, 2, 0, 1, 1, 2, 0, 1, 0, 2, 0, 0, 2, 1, 2, 1, 1, 2, 2, 1, 1, 1, 0, 2, 0, 0, 1, 0, 1, 2, 2, 1, 0, 0, 1, 1, 1, 1, 2, 0, 2, 1, 0, 1, 0, 0, 0, 0, 0]}
- member_a ({'n_lines': 79, 'n_attested_signs': 354}): `<LINE> <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> x <LINE> <LINE> IŠ TU UZU <LINE> iš <LINE> x DUG GEŠTIN <LINE> TÚG ku re eš šar ḪI A <LINE> pé ra an kat ta <LINE> ŠA Ì DU₁₀`
- member_b ({'n_lines': 81, 'n_attested_signs': 384}): `<LINE> <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> ḫi <LINE> <LINE> <LINE> x <LINE> GUR tar <LINE> GA KIN <LINE> GIŠ BANŠUR <LINE> da a i GUB la az <LINE> A NA GIŠ BANŠUR <LINE> ga i nu <NUM> KASKAL MEŠ`

### Example 9/10 -- source `KUB 42.91`, vertical cut
- params: {"cut_type": "vertical", "boundary_line": 57, "gap_width_lines": 1, "n_lines_total": 60}
- member_a ({'n_lines': 54, 'n_attested_signs': 613}): `<LINE> x <LINE> x <LINE> bi <LINE> <LINE> x <LINE> x x UP NI <LINE> x <LINE> <LINE> x <LINE> x i ia za ḫa an x i SI×SÁ <LINE> <NUM> BÁN ZÌ DA DUR₅ <NUM> NINDA GUR₄ RA UP`
- member_b ({'n_lines': 2, 'n_attested_signs': 6}): `x <LINE> pár ši ia an x`

### Example 10/10 -- source `KUB 14.8`, vertical cut
- params: {"cut_type": "vertical", "boundary_line": 26, "gap_width_lines": 0, "n_lines_total": 94}
- member_a ({'n_lines': 26, 'n_attested_signs': 513}): `x x x x <LINE> ru na aš ma wa at za kán <LINE> za ma me ma a ú x MEŠ ma mu <LINE> ḪA AT TI ḫi in kán Ú UL SIG₅ at <LINE> at <LINE> DINGIR MEŠ IA x`
- member_b ({'n_lines': 68, 'n_attested_signs': 1387}): `ku in e ep per na an ma ḫa an I NA KUR URU ḪA AT pa ú wa te e er <LINE> nu kán I NA ŠÀ BI LÚ MEŠ ŠU DAB BI ḪI A ḫi in kán ki`
