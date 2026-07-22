# P4 D12 -- Tokenizer Report

- Vocabulary source: TRAIN-side + discovery-pool ATTESTED text only (21,037 fragments)
- min_df: 2
- Specials: ['<PAD>', '<UNK>', '<MASK>', '<GAP>', '<LINE>', '<PAR>', '<EDGE_L>', '<EDGE_R>', '<EDGE_T>', '<EDGE_B>']
- **Vocab size (incl. specials): 2,374**
- **Dev OOV rate: 0.1625%** (267 / 164,301 tokens) -- PASS (target <1%)

## Amendment 2026-07-22 (approved by architect): sign-level logogram decomposition

The first tokenizer run reused P3's bm25_sign rule verbatim (whole-word logogram tokens) and landed at vocab=14,170 / dev OOV=3.66%, missing both stated targets ("low thousands" / <1%). Diagnosis at the time: 12,632 of 14,160 vocab entries were whole-word logogram/Sumerogram/Akkadogram forms (each inflected combination, e.g. `DUTU-ŠI` vs `DUTU-uš`, its own atomic entry) -- excellent for BM25 term weighting, combinatorially expensive for a fixed neural vocabulary. Flagged rather than silently fixed, per CLAUDE.md. Architect decision: decompose logograms into their constituent signs (what's physically on the tablet), splitting sGr/aGr/d content on `-`/`.` (`DINGIR-LIM` -> `DINGIR` + `LIM`; `DUTU-uš` -> `D` + `UTU` + `uš`), except `×`-ligature compounds (`KA×U`) which stay atomic -- one wedge-cluster, one token. This required re-deriving token boundaries from the raw XML's `<d>`/`<sGr>`/`<aGr>` tag edges directly (P2's corpus.parquet flattens a word's text before hyphen-splitting, losing those edges) -- see decompose_corpus.py, a new P4-only derived artifact; P2/P2.5's corpus.parquet stays frozen and untouched. P3's BM25 tables are unaffected (they already ran and are frozen; this tokenizer is P4-only).
- **Result: vocab 2,374 entries (1,022 logogram-class + 1,342 syllabic/other), dev OOV 0.16%** -- meets the <1% target.
- Sequence-length truncation rate at D14's planned seq_len=512 (decomposition makes sequences longer than the old flat token count, as expected): **3.82%** of all 22,726 fragments exceed 512 tokens (length percentiles: p50=49, p90=244, p99=1,378, max=8,450 -- a few very large multi-column composite documents drive the long tail; the vast majority of fragments fit comfortably).

## Top 30 tokens (by document frequency in TRAIN+discovery)

| token | doc_freq |
|---|---|
| `x` | 19,624 |
| `an` | 13,869 |
| `a` | 12,024 |
| `aš` | 11,068 |
| `zi` | 10,583 |
| `ma` | 9,778 |
| `i` | 9,427 |
| `na` | 9,337 |
| `ia` | 9,248 |
| `wa` | 8,757 |
| `da` | 8,752 |
| `ša` | 8,574 |
| `ta` | 8,519 |
| `<NUM>` | 8,395 |
| `e` | 8,247 |
| `pa` | 8,046 |
| `nu` | 7,965 |
| `ḫa` | 7,944 |
| `A` | 7,436 |
| `ši` | 7,185 |
| `iš` | 6,987 |
| `ra` | 6,777 |
| `ku` | 6,759 |
| `ni` | 6,542 |
| `kán` | 6,484 |
| `D` | 6,390 |
| `za` | 6,355 |
| `ti` | 6,333 |
| `MEŠ` | 6,255 |
| `u` | 6,135 |

## Round-trip examples (5 seeded TRAIN fragments)

Round-trip must reconstruct the original transliteration string exactly (hyphens/dots re-insertable by joining decomposed tokens) for in-vocab tokens; mismatches are attributable only to genuine OOV -> `<UNK>` substitution, shown via unk_count.

### Bo 9201
- original (60 tokens): `<GAP> a i ú <LINE> a na ḪUR <LINE> at ti li x <LINE> ḫa as su i x <LINE> x li id din šum ma x <LINE> ḫat ti LÚ mu un na ab tu₄ <LINE> x šum ma la a ú ta ar <PAR> <LINE> iš tu KUR URU a mur ra <LINE> mu nab tu₄ a <GAP>`
- decoded (exact_match=True, unk_count=0): `<GAP> a i ú <LINE> a na ḪUR <LINE> at ti li x <LINE> ḫa as su i x <LINE> x li id din šum ma x <LINE> ḫat ti LÚ mu un na ab tu₄ <LINE> x šum ma la a ú ta ar <PAR> <LINE> iš tu KUR URU a mur ra <LINE> mu nab tu₄ a <GAP>`

### KUB 58.96+::1
- original (40 tokens): `<GAP> x <LINE> x SISKUR an x <LINE> a an li in kán( )ta( <PAR> <LINE> TUP PU QA TI ŠA SISKUR ḫa li in <LINE> <NUM> <PAR> <LINE> <NUM> <LINE> i MUNUS ŠU GI <LINE> UN an <PAR> <GAP>`
- decoded (exact_match=True, unk_count=0): `<GAP> x <LINE> x SISKUR an x <LINE> a an li in kán( )ta( <PAR> <LINE> TUP PU QA TI ŠA SISKUR ḫa li in <LINE> <NUM> <PAR> <LINE> <NUM> <LINE> i MUNUS ŠU GI <LINE> UN an <PAR> <GAP>`

### KUB 32.36
- original (30 tokens): `<GAP> x e eš te e en na <LINE> x wa a li ḫa na du x <LINE> x ši ni ik kal a al la <LINE> pí <PAR> <GAP>`
- decoded (exact_match=True, unk_count=0): `<GAP> x e eš te e en na <LINE> x wa a li ḫa na du x <LINE> x ši ni ik kal a al la <LINE> pí <PAR> <GAP>`

### KUB 49.25
- original (107 tokens): `<GAP> EGIR <LINE> <LINE> <LINE> <LINE> <PAR> <LINE> <LINE> <LINE> di Ú UL pé eš ši ia <LINE> ḪI A ar ḫa pé eš <LINE> ia aš kán EGIR GAM ku <LINE> pa it <NUM> TI₈ <LINE> x x <LINE> miš <LINE> pa <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> x <LINE> <EDGE_L> x DINGIR LUM pí an <LINE> <EDGE_L> DINGIR LIM` ...
- decoded (exact_match=True, unk_count=0): `<GAP> EGIR <LINE> <LINE> <LINE> <LINE> <PAR> <LINE> <LINE> <LINE> di Ú UL pé eš ši ia <LINE> ḪI A ar ḫa pé eš <LINE> ia aš kán EGIR GAM ku <LINE> pa it <NUM> TI₈ <LINE> x x <LINE> miš <LINE> pa <LINE> <LINE> <LINE> <LINE> <LINE> <LINE> x <LINE> <EDGE_L> x DINGIR LUM pí an <LINE> <EDGE_L> DINGIR LIM` ...

### KBo 22.134
- original (504 tokens): `<GAP> i ka a <LINE> eš pí re eš ta a ki <LINE> u ru un ne eš wa <LINE> pa kal le eš ku up <LINE> it ti ir ri iš <LINE> al la e ne eš <LINE> D IŠKUR up šu u ra at <LINE> ge e la tu še na <PAR> <LINE> nu za LÚ AZU <NUM>` ...
- decoded (exact_match=True, unk_count=0): `<GAP> i ka a <LINE> eš pí re eš ta a ki <LINE> u ru un ne eš wa <LINE> pa kal le eš ku up <LINE> it ti ir ri iš <LINE> al la e ne eš <LINE> D IŠKUR up šu u ra at <LINE> ge e la tu še na <PAR> <LINE> nu za LÚ AZU <NUM>` ...
