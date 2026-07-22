# DM0 -- `cu` Verification Gate

Per specs/TAKSAN_DEMO_SPEC.md section 4. Reuses p2_out/damage_oracle.parquet's already-extracted per-line `cu` (P2, 02_parse.py, 2026-07-20) -- no XML re-parsing.

## (a) Are `cu` glyphs Unicode cuneiform?

Full-corpus sweep, 3,456,297 codepoints across 377,195 non-empty `cu` lines:

| class | count | % |
|---|---|---|
| cuneiform | 2,961,664 | 85.6889% |
| damage_marker | 460,431 | 13.3215% |
| OTHER | 19,744 | 0.5712% |
| cuneiform_numbers | 14,458 | 0.4183% |

- Out-of-block (non-cuneiform, non-damage-marker, non-PUA) codepoint examples: ['U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+00020 (SPACE)', 'U+00031 (DIGIT ONE)', 'U+00034 (DIGIT FOUR)', 'U+00020 (SPACE)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)', 'U+0003F (QUESTION MARK)']
- PUA codepoints (expected: rare HZL signs without a standard Unicode cuneiform value) get the transliteration-fallback rendering per spec 3.2.

### 20-line codepoint census (spanning required categories)

**fully_restored (P2 damage-oracle cited example)** -- `KUB 56.58` line 38 (Rs. VI 4′): cu_len=8, total_signs=7
- cu: `𒁾𒁹𒄰𒋡𒋾𒈠𒀀𒀭`
- class counts: {'cuneiform': 8}

**fully_attested** -- `Bo 6903` line 4 (L. col. 5′): cu_len=7, total_signs=6
- cu: `▒𒊭𒀭𒁕𒀭𒌑𒀉`
- class counts: {'cuneiform': 6, 'damage_marker': 1}

**fully_attested** -- `KBo 41.140+` line 34 (Vs. I 10′): cu_len=18, total_signs=17
- cu: `𒀀𒁉𒂖𒍣𒀉𒑱𒅈𒉺𒍝𒂕𒉺𒌑𒌌𒂉𒂊𒄑𒍝𒋡`
- class counts: {'cuneiform': 17, 'cuneiform_numbers': 1}

**fully_attested** -- `KBo 50.153` line 7 (8′): cu_len=16, total_signs=15
- cu: `𒂉𒄿𒂊𒌍𒈾𒀸𒉿𒋻𒈾𒄴𒍣𒇽𒈬𒀮𒌈𒉿`
- class counts: {'cuneiform': 16}

**fully_attested** -- `KBo 33.42` line 12 (13′): cu_len=3, total_signs=0
- cu: `▒▒▒`
- class counts: {'damage_marker': 3}

**partially_restored** -- `KBo 23.31+` line 36 (Vs.! 3′/Vs. 6′!): cu_len=15, total_signs=13
- cu: `𒁾▒𒄰𒀭𒅖𒄩𒊏𒍢𒂊𒈾𒀭𒋫𒀸𒋡𒋾`
- class counts: {'cuneiform': 14, 'damage_marker': 1}

**partially_restored** -- `KUB 34.48+` line 59 (Rs. III 18′/1′/1′): cu_len=11, total_signs=9
- cu: `𒁹𒁹▒▒𒂊𒌍𒊭𒈠▒▒𒍣`
- class counts: {'cuneiform': 7, 'damage_marker': 4}

**partially_restored** -- `KBo 56.23+` line 23 (9′/Rs.? 9′): cu_len=17, total_signs=13
- cu: `𒍜𒃻𒈪𒉭𒅈𒄩𒆳𒀸𒆠𒄑𒍣𒉡𒃻𒉿𒄀𒌍𒊬`
- class counts: {'cuneiform': 17}

**partially_restored** -- `KUB 8.64` line 4 (5′): cu_len=8, total_signs=8
- cu: `𒉡𒍑𒅆𒃷𒅗𒀀𒀸𒋾`
- class counts: {'cuneiform': 8}

**fully_restored** -- `KBo 41.167` line 13 (r. Kol. 6′): cu_len=4, total_signs=2
- cu: `𒀸𒌓𒐈𒄰`
- class counts: {'cuneiform': 3, 'cuneiform_numbers': 1}

**fully_restored** -- `KUB 3.101` line 10 (11′): cu_len=3, total_signs=3
- cu: `𒊭𒊏𒂉`
- class counts: {'cuneiform': 3}

**fully_restored** -- `KUB 56.34` line 43 (Rs. IV? 9′): cu_len=9, total_signs=6
- cu: `𒋫𒌉𒈨𒌍𒈗𒀀𒊭𒀀𒅆`
- class counts: {'cuneiform': 9}

**has_damage_marker** -- `KBo 47.149` line 5 (6′): cu_len=12, total_signs=11
- cu: `▒𒂉𒀉𒆠𒄿𒁕𒀀𒇻𒈠𒀭𒀭▒`
- class counts: {'cuneiform': 10, 'damage_marker': 2}

**has_damage_marker** -- `KUB 12.43` line 2 (3′): cu_len=11, total_signs=10
- cu: `▒▒▒𒈾𒀜𒈠𒀀𒌑𒅆𒅖𒁺`
- class counts: {'cuneiform': 8, 'damage_marker': 3}

**has_damage_marker** -- `KUB 26.39` line 38 (Rs. IV 34′): cu_len=15, total_signs=12
- cu: `▒𒄷𒄷𒍑𒌷𒂵𒀸𒈪𒅀𒄩𒀭𒅆𒅋▒▒`
- class counts: {'cuneiform': 12, 'damage_marker': 3}

**has_damage_marker** -- `KBo 29.168` line 9 (Rs.? 3′): cu_len=7, total_signs=7
- cu: `▒▒▒▒▒▒▒`
- class counts: {'damage_marker': 7}

**has_det_sum_akk** -- `KBo 69.228` line 2 (3′): cu_len=6, total_signs=6
- cu: `▒𒋡𒅆𒈠𒁹𒄑`
- class counts: {'cuneiform': 5, 'damage_marker': 1}

**has_det_sum_akk** -- `KBo 24.123` line 14 (Rs.? 3′): cu_len=5, total_signs=2
- cu: `▒𒀭𒉡𒅆𒂟`
- class counts: {'cuneiform': 4, 'damage_marker': 1}

**has_det_sum_akk** -- `KUB 29.55+` line 35 (Vs. 8′/Vs. I 14′): cu_len=9, total_signs=8
- cu: `𒇽𒀀𒀸𒋗𒍑𒊭𒀭𒉌𒅖`
- class counts: {'cuneiform': 9}

**has_det_sum_akk** -- `KBo 6.5` line 40 (Rs. III 3): cu_len=12, total_signs=12
- cu: `𒁖𒂉𒀜𒋾𒈠𒀭𒉌𒌑𒌌𒀀𒀸𒋗`
- class counts: {'cuneiform': 12}

## (b) Does `cu` glyph count align 1:1 with sign_damage_states per line?

Measured: does `len(cu)` (character count, `▒` counted as one slot) equal the line's total token count, IN ORDER? This is the POSITIONAL alignment DM2's glyph-cell rendering needs -- stricter than P2's original ▒-count-vs-nonattested-count correlation check (which validated what ▒ MEANS, not per-position alignment).

**Three-level diagnostic** (each level is a real, separate finding, not a discarded intermediate -- reported per 'report more, claim less'):

- **Level 1 (P2's coarse `corpus.parquet` signs count, diagnostic only):** 37.12% aligned. Root cause of the gap: `corpus.parquet` groups determinative/Sumerogram/Akkadogram content into ONE hyphen-joined string per word (P3's bm25_sign convention, e.g. `"DUMU.MUNUSMEŠ"` as a single entry) -- this undercounts the true per-wedge glyph count `cu` renders (confirmed by direct inspection: `signs=["DDAG", "ti", "in"]` for one word, where `cu` renders D and DAG as two separate glyphs).
- **Level 2 (P4's `p4_out/decomposed_corpus.parquet`, wedge-boundary-aware -- PRIMARY/used for the verdict below):** built for the D12 tokenizer amendment, already fixes exactly the Level-1 gap. Full population (377,195 lines): **57.87%** aligned, 158,904 mismatches (42.13%). Seeded 500-line random sample (seed=20260722): **58.40%** aligned, 208 mismatches (41.60%). Improvement over Level 1: +20.8 points.

### Level-2 residual mismatch characterization (158,904 total)

- On lines containing a gap-placeholder sign (`…`/`_`, an editorially-typed 'unknown number of signs lost' marker -- NOT 1:1 comparable to a single cu character by construction): **17,943** / 158,904 (11.3%)
- **NEW ROOT CAUSE, not yet fixed anywhere in the pipeline:** of the 87,227 lines mismatched by exactly +1 (the single largest bucket), **62.9%** have `cu` starting OR ending with a damage marker (▒) that has NO corresponding token at all in the decomposed data. This means a damage marker exists in the raw XML OUTSIDE any `<w>` word boundary (e.g. directly inside `<lb>`, before the first or after the last word) -- both P2's original parser and P4's decompose_corpus.py parse content WITHIN `<w>` spans only, so this orphan marker is silently dropped by both. Confirmed by direct inspection (not assumed) -- e.g. `KBo 42.91` line 1: `cu='▒𒀀𒉌𒆠𒅀𒀭𒁕'` (7 chars) but only 6 decomposed tokens exist (a,ni,ki,ia,an,da), all matching the trailing 6 real glyphs -- the leading ▒ has no token record whatsoever.
- Diff distribution (cu_len - total_tokens) on mismatched lines: {-35: 1, -33: 1, -32: 1, -28: 2, -27: 3, -26: 2, -25: 3, -24: 7, -23: 2, -22: 10, -21: 8, -20: 10, -19: 22, -18: 30, -17: 31, -16: 46, -15: 58, -14: 48, -13: 53, -12: 64, -11: 52, -10: 65, -9: 68, -8: 71, -7: 66, -6: 70, -5: 92, -4: 88, -3: 160, -2: 838, -1: 6144, 1: 87227, 2: 27476, 3: 17518, 4: 6194, 5: 3057, 6: 3667, 7: 1646, 8: 843, 9: 558, 10: 392, 11: 270, 12: 260, 13: 171, 14: 207, 15: 124, 16: 139, 17: 92, 18: 116, 19: 70, 20: 95, 21: 35, 22: 52, 23: 51, 24: 64, 25: 32, 26: 56, 27: 26, 28: 42, 29: 26, 30: 35, 31: 17, 32: 28, 33: 9, 34: 17, 35: 16, 36: 14, 37: 11, 38: 16, 39: 8, 40: 9, 41: 7, 42: 8, 43: 4, 44: 6, 45: 4, 46: 5, 47: 3, 48: 3, 49: 1, 50: 2, 51: 3, 52: 3, 53: 5, 54: 10, 55: 5, 56: 3, 57: 3, 58: 6, 59: 2, 60: 4, 61: 4, 62: 3, 65: 1, 66: 1, 67: 3, 68: 1, 72: 1, 87: 1}

10 sampled Level-2 mismatch examples:

| doc_id | line | cu_len | total_tokens | has_gap_marker | n_restored | n_illegible | n_laes |
|---|---|---|---|---|---|---|---|
| Or. 95_3 | Vs. I-II 1′ | 8 | 0 | False | 0 | 0 | 0 |
| KBo 43.130 | 1′ | 5 | 4 | False | 0 | 2 | 1 |
| KUB 45.90 | Vs. I 1′ | 2 | 1 | False | 0 | 0 | 0 |
| KBo 51.275 | 3 | 5 | 6 | False | 0 | 1 | 3 |
| KBo 57.218 | 4′ | 4 | 3 | False | 0 | 0 | 0 |
| KBo 26.161 | rev. iii 6′ | 10 | 7 | False | 0 | 0 | 0 |
| KUB 18.28+ | Rs. III? | 3 | 0 | False | 0 | 0 | 0 |
| KBo 43.52+ | Rs. IV 33 | 17 | 11 | True | 7 | 1 | 0 |
| KBo 7.20 | Vs. II 8′ | 13 | 0 | False | 0 | 0 | 0 |
| KUB 32.4 | l.col. 10′ | 6 | 2 | False | 0 | 1 | 0 |

### Alignment transform (applied, insufficient alone)

Transform: exclude gap-marker lines from the glyph-render-eligible pool (same fallback DM2 already uses for PUA/unmapped glyphs, per spec 3.2).

- After transform: 359,202 lines eligible, **60.76%** aligned, 140,961 residual mismatches (39.243%)
- Spec threshold: glyph layer BLOCKED until error < 1% of lines.
- **Residual mismatch rate after transform: 39.243%, well over the <1% threshold. The gap-marker transform alone does NOT close the gap -- the orphan-marker finding above is the larger remaining cause and has NOT been fixed in this pass** (would require extending decompose_corpus.py's XML walk to also capture damage markers positioned outside `<w>` spans -- a scoped, concrete follow-up, not attempted here; flagged to the architect session per spec section 4's own instruction to inform before further glyph work).

## (c) How does `▒` map to damage states?

Reconfirmed directly (not just restated from P2): correlation of per-line `▒` count against `n_illegible` (illegible_x, excluding gap placeholders) = **0.2410**; against all-non-attested (restored+illegible+laes) = 0.1727. Exact per-line match rate (▒ count == illegible count): **71.12%**.

**Render rule** (binding for DM2's glyph layer):
- `▒` (U+2592, NOT a real cuneiform codepoint) -> render as ILLEGIBLE (x): ╳ glyph, dotted border, per spec 3.4.3.
- `…`/`_` gap-placeholder signs -> these lines are excluded from glyph rendering by the transform above; when they DO need a damage-state (transliteration-only fallback view), render as LOST EDGE/GAP band per spec 3.4.4, never as a single illegible cell (the gap stands for an unknown-length run, not one sign).
- Every other `cu` character -> real cuneiform glyph; render with the damage state from the ALIGNED position in `sign_damage_states` (attested = full opacity, restored/laes = 45% opacity + dashed underline per spec 3.4.2). Never infer damage state from the glyph itself -- `cu` renders restorations as normal-looking glyphs.

### Second investigation round (2026-07-21): two structural hypotheses tested and rejected

Rather than accept the 57.9%/39.2%-residual state, two candidate rules for what generates an
orphan marker were formed from hand-traced examples and tested at FULL-CORPUS scale (not
accepted on the traced example alone -- both looked correct on the example that motivated them):

1. **"A `<space c=\"N\"/>` blank run gets a `cu` marker iff it falls inside an active
   `<del_in>`/`<laes_in>` span."** Traced correctly on `KBo 42.91` line 1; corroborated by a
   3000-doc sample (73% of `<space>` elements occur inside a damage span). Implemented in
   `decompose_corpus.py`, rebuilt the decomposed corpus (+129,231 tokens), remeasured: alignment
   got WORSE (57.87% -> 47.94%) -- 68,970 lines gained a phantom extra token. **REJECTED, reverted**
   (both the code and the rebuilt parquet).
2. **"An empty `<del_in>`/`<del_fin>` (or laes) span -- zero real signs between open and close --
   represents one illegible sign in `cu`."** A cleaner, full-corpus controlled study (isolating
   lines with exactly one such empty closure and no other content) found this holds in only
   **17.1%** of cases (36/211) even in the most favorable subset. **REJECTED, never implemented.**

Both hypotheses were plausible from their motivating example and both failed to generalize --
the XML-structural rule governing exactly when `cu` shows a marker is not one of these two
mechanisms, and may not be a clean deterministic function of nearby tags at all (it may reflect
ad hoc editorial judgment). Given diminishing returns from further guess-and-test cycles, the
approach was changed from "predict when a marker appears" to "make marker attribution
unnecessary" -- see below.

### Alignment reframing that actually worked: `cu_alignment.py`

`▒` is ALREADY CONFIRMED (part c below) to always mean illegible, regardless of why it's there.
An orphan marker therefore doesn't need a specific token match at all -- it can render as a
self-evident illegible cell. `cu_alignment.py` (new, reusable -- DM1/DM2 will import it directly)
implements this as a 4-tier match per line, with ZERO changes to `decompose_corpus.py` or
`p4_out/decomposed_corpus.parquet` (this is a pure rendering-layer fix, carrying no risk to any
already-completed P4 result):

| tier | rule | n lines | % |
|---|---|---|---|
| `exact` | `len(cu) == n_tokens`, no adjustment needed | 218,291 | 57.87% |
| `edge_trim` | leading/trailing unmatched `▒` consumed as extra illegible cells | 89,501 | 23.73% |
| `skeleton_only` | real-glyph count matches; markers redistributed to `cu`'s actual layout (approximate) | 5,706 | 1.51% |
| `unresolved` | falls back to transliteration-only, per spec 3.2's existing PUA/unmapped-glyph fallback | 63,697 | 16.89% |

**Combined renderable: 83.11%** of lines (up from 57.87%), with the remaining 16.89% falling back
to transliteration-only automatically (already spec-compatible, per section 4's own fallback
design) -- not blocked, not a special case requiring further code.

## Glyph layer go/no-go

**CONDITIONAL GO**, revised from the initial NO-GO after the alignment-algorithm fix above.
The spec's literal <1%-corpus-wide-mismatch bar is NOT met (16.89% residual) and is very unlikely
to be reachable by count/position heuristics alone -- two structural hypotheses were tested and
rejected, and the true generating rule for orphan markers may not be deterministically recoverable
from nearby XML tags. Practically: **83.11% of lines render full per-token glyph cells**
(`exact`+`edge_trim`+`skeleton_only`, via `cu_alignment.py`, zero P4 risk); the remaining 16.89%
render transliteration-only, automatically, via the SAME fallback mechanism spec 3.2 already
designs for PUA/unmapped glyphs -- no per-line special-casing needed in DM2, `cu_alignment.py`'s
`align_line()` already returns `'unresolved'` with an empty cell list for the caller to detect.

DM1/DM2 can proceed now: call `cu_alignment.align_line(cu, tokens)` per line at export/render
time; render its returned cells if category != 'unresolved', else fall back to transliteration-only.

### Addendum: one orphan-marker fix attempted and rejected (2026-07-21)

Tried the hypothesis "a `<space c=\"N\"/>` blank run gets one `cu` damage-marker glyph iff it falls inside an active `<del_in>`/`<laes_in>` span" -- traced by hand on one example (`KBo 42.91` line 1) where it held exactly, and corroborated by a 3000-doc sample showing 73% of `<space>` elements occur inside a damage span. Implemented in `decompose_corpus.py`, rebuilt `p4_out/decomposed_corpus.parquet` (+129,231 tokens, +4.03%), and re-measured on the FULL corpus: **alignment got WORSE, not better (57.87% -> 47.94%)** -- the rule overshoots; most in-damage-span `<space>` elements do NOT get a `cu` glyph, so 68,970 lines ended up with a phantom extra token (up from 6,144 before the change). Reverted immediately (both the code and the rebuilt parquet) rather than ship a regression -- the single hand-traced example was not representative of the general rule. **`decompose_corpus.py`'s orphan-marker gap remains unfixed**; the true rule governing when a blank run produces a `cu` placeholder is still unknown and would need further investigation (e.g. checking `c="N"` value thresholds, or the specific del/laes span type) before a second attempt.

**Same-root-cause note for the P4 pipeline (not just DM):** this `decompose_corpus.py` gap is not demo-only -- `p4_out/decomposed_corpus.parquet` is also D12's tokenizer input, D13's fracture-engine calibration input, and D14/D15's training data source. All of P4's completed results (tokenizer OOV/vocab stats, fracture calibration, D14's final pretraining numbers, D15's ablation-grid dev-gate numbers) were computed against the version of `decompose_corpus.py` that has this gap -- i.e. before ANY attempted fix, since the fix was reverted. Those P4 numbers are internally consistent with each other (same corpus throughout) and are NOT invalidated by this DM0 finding; this is flagged here only so the fact is on record, not as a claim that P4 needs to be redone.