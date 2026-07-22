# P2 Deliverable 1 -- Parse Report

- Documents scanned: 21868
- Parse errors (excluded from corpus): 229
- Word-token rows (== raw `<w>` element count): **1,521,968** (inventory top_tags target: 1,522,256; delta -0.02%)
- Line rows (== raw `<lb>` element count): **384,559** (inventory top_tags target: 384,667; delta -0.03%)
- Documents parsed: 21639

## Damage-state oracle (cu ▒ vs. sign damage state, per line)

**Naive hypothesis (▒ = any non-attested sign: restored+laes+illegible_x) -- REJECTED.** Weak/near-zero correlation, investigated rather than accepted at face value:
- Full corpus (384,559 lines): exact match 33.2%, mean abs diff 2.48, corr 0.182
- Seeded 500-line sample (seed=20260720): exact match 31.8%, mean abs diff 2.34, corr 0.202

**Root cause (confirmed by manual inspection of counterexamples, e.g. KUB 56.58 line 38 -- 4 words, every sign inside a `<del_in>/<del_fin>` restored span, cu shows 8 real glyphs and ZERO ▒):** `cu` renders the editor's complete PROPOSED reading, including restored content, as real cuneiform glyphs. ▒ is used only where no sign value at all could be proposed: illegible_x (literal `x`) and indeterminate-length gaps (`…`, `_`). It is **not** an attested-only break silhouette -- do not use `cu` for that purpose; use the transliteration markup (sign_damage_states) captured in corpus.parquet instead.

**Corrected hypothesis (▒ = illegible_x only, excluding `…`/`_` gap placeholders which stand for an unknown-length run and aren't 1:1 comparable) -- CONFIRMED:**
- Full corpus: exact match 71.7%, mean abs diff 0.778, corr 0.246
- Lines with no `…`/`_` gap markers (366,566 / 384,559, 95.3%): exact match 75.2%, mean abs diff 0.413, corr 0.622

## Site distribution

- Hattusa: 19096
- unknown: 2263
- Masat/Tapikka: 110
- Hattusa(coll.): 79
- Kusakli/Sarissa: 42
- Ortakoy/Sapinuwa: 34
- Emar: 7
- Ugarit: 7
- Alalakh: 1

## Unknown-prefix docIDs (top 20 by count)

- `CHDS` (850): CHDS 3.7; CHDS 4.40; CHDS 5.45
- `DBH` (399): DBH 46_2.145; DBH 43_2.148; DBH 43_2.125
- `FHL` (165): FHL 123; FHL 87; FHL 186
- `DAAM` (159): DAAM 2.6; DAAM 1.53; DAAM 1.54
- `UBT` (158): UBT 147; UBT 99; UBT 31
- `VSNF` (123): VSNF 12.42; VSNF 12.10; VSNF 12.132
- `HFAC` (122): HFAC 104; HFAC 50; HFAC 93
- `Privat` (36): Privat 159; Privat 8; Privat 25
- `HHCTO` (16): HHCTO 1; HHCTO 12; HHCTO 11
- `Gurney` (13): Gurney 5; Gurney 14; Gurney 9
- `Dispersa` (10): Dispersa 2; Dispersa 23; Dispersa 27
- `FHG` (8): FHG 22; FHG 4; FHG 16
- `HHT` (7): HHT 36; HHT 69; HHT 81
- `Durham` (7): Durham 2467; Durham 2464; Durham 2461
- `Kp` (7): Kp 15_45a; Kp 22_356-357_20; Kp 19_671
- `AMUM` (6): AMUM 2431; AMUM 1997; AMUM 1998
- `München` (4): München 4; München 2; München 1
- `AAA3` (4): AAA3 Nr.3; AAA3 Nr.2; AAA3 Nr.4
- `UK` (4): UK 12.E.5; UK 12.E.4; UK 12.E.3
- `VAT` (4): VAT 7767; VAT 7463; VAT 7436

## side_raw tokens observed (leading line-label text before line number)

- `Vs.` : 101555 -> obverse
- `Rs.` : 76000 -> reverse
- `r. Kol.` : 13931 -> OTHER/unmapped
- `obv.` : 13711 -> OTHER/unmapped
- `Vs.?` : 12200 -> obverse
- `Rs.?` : 10976 -> reverse
- `rev.` : 9613 -> OTHER/unmapped
- `lk. Kol.` : 9392 -> OTHER/unmapped
- `Vs. II?` : 2163 -> OTHER/unmapped
- `Vs. r. Kol.` : 1672 -> OTHER/unmapped
- `Vs. lk. Kol.` : 1601 -> OTHER/unmapped
- `Rs. r. Kol.` : 1543 -> OTHER/unmapped
- `Rs. IV?` : 1541 -> OTHER/unmapped
- `Rs. III?` : 1475 -> OTHER/unmapped
- `obv.?` : 1468 -> OTHER/unmapped
- `rev.?` : 1324 -> OTHER/unmapped
- `Vs. I?` : 1270 -> OTHER/unmapped
- `Kol.` : 1229 -> OTHER/unmapped
- `obv. i` : 1087 -> OTHER/unmapped
- `Rs. lk. Kol.` : 1057 -> OTHER/unmapped
- `r. col.` : 927 -> OTHER/unmapped
- `u. Rd.` : 737 -> OTHER/unmapped
- `l. col.` : 722 -> OTHER/unmapped
- `lk. Rd.` : 658 -> OTHER/unmapped
- `Rs. V?` : 658 -> OTHER/unmapped
- `obv. ii` : 615 -> OTHER/unmapped
- `Vs.? r. Kol.` : 596 -> OTHER/unmapped
- `Vs.!` : 580 -> OTHER/unmapped
- `Vs. III?` : 580 -> OTHER/unmapped
- `rev. iv` : 561 -> OTHER/unmapped
- `Rs.!` : 555 -> OTHER/unmapped
- `rev. iii` : 531 -> OTHER/unmapped
- `Rs. (III)` : 476 -> OTHER/unmapped
- `Vs. (II)` : 473 -> OTHER/unmapped
- `Rs.? r. Kol.` : 425 -> OTHER/unmapped
- `Vs.? lk. Kol.` : 393 -> OTHER/unmapped
- `Seite A` : 391 -> OTHER/unmapped
- `obv. II?` : 376 -> OTHER/unmapped
- `Rs. (IV)` : 347 -> OTHER/unmapped
- `Vs. (I)` : 339 -> OTHER/unmapped

*Full detail in corpus.parquet / doc_table.parquet / damage_oracle.parquet.*