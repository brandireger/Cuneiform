# P2 Dataset Report (Deliverable 5 -- master acceptance checks)

Aggregates: parse_report.md (D1), unjoin_semantics.md + join_stats.md (D2), edges_report.md (D3), split_report.md (D4). This file adds the cross-cutting acceptance-check items from P2_PARSER_SPEC.md Deliverable 5 not already covered individually.

## Acceptance checks summary

1. Word-token count within ~10% of 1.52M `<w>` elements: **PASS** (-0.02% delta) -- see parse_report.md
2. Damage-state oracle agreement reported: **DONE** -- naive hypothesis rejected, corrected hypothesis confirmed (75.2% exact match on gap-marker-free lines) -- see parse_report.md
3. >=90% of composite docs unjoined or quarantined: **PASS (100.0%)** -- see join_stats.md
4. Zero composition-leakage across splits (asserted): **PASS** -- see split_report.md
5. This report: per-split counts, sign totals, largest compositions, FULL vs ATTESTED samples -- below

## Sign totals (attested / restored / laes / illegible_x)

| scope | attested | restored | laes | illegible_x | restored share |
|---|---|---|---|---|---|
| overall | 1,734,454 | 764,965 | 151,779 | 162,044 | 27.2% |
| train | 1,396,807 | 618,084 | 119,604 | 120,852 | 27.4% |
| dev | 185,382 | 79,307 | 18,568 | 30,140 | 25.3% |
| test | 152,265 | 67,574 | 13,607 | 11,052 | 27.6% |

## Top-20 largest compositions (by document/witness count)

| CTH | documents |
|---|---|
| 832 | 3583 |
| 670 | 3067 |
| 470 | 1805 |
| 500 | 463 |
| 582 | 379 |
| 215 | 335 |
| 628 | 301 |
| 791 | 262 |
| 530 | 253 |
| 627 | 188 |
| 209 | 177 |
| 819 | 171 |
| 626 | 170 |
| 701 | 164 |
| 458 | 157 |
| 212 | 150 |
| 790 | 144 |
| 745 | 143 |
| 590 | 141 |
| 370 | 136 |

## Per-site document counts

| site | documents |
|---|---|
| Hattusa | 19096 |
| unknown | 2263 |
| Masat/Tapikka | 110 |
| Hattusa(coll.) | 79 |
| Kusakli/Sarissa | 42 |
| Ortakoy/Sapinuwa | 34 |
| Emar | 7 |
| Ugarit | 7 |
| Alalakh | 1 |

## Fragment / pair / composition counts (cross-reference)
- Fragments (edges.parquet): 22,757
- Join pairs (join_pairs.jsonl): 1,581
- Compositions (CTH): 657
- Documents: 21,639

## FULL vs ATTESTED rendering samples (seed=20260720, 5 fragments, human sanity check)

ATTESTED = restored (`<del_in>/<del_fin>`) sign content removed entirely; laes (damaged-but-legible) kept; illegible_x kept as its literal `x` mask token; words that were *entirely* restored vanish from the ATTESTED line. This is the strict eval-time rendering (cleanroom rule: test labels come from attested content only) -- not annotated for readability.

### UBT 28

- **1′**
  - FULL:     `PA ZÌ.DA`
  - ATTESTED: `PA ZÌ.DA`
- **2′**
  - FULL:     `DIŠTAR ṢE-E-RI`
  - ATTESTED: `ṢE-E`
- **3′**
  - FULL:     `7 PA`
  - ATTESTED: `7 PA`
- **4′**
  - FULL:     `DUGKA.GAG.A`
  - ATTESTED: ``
- **5′**
  - FULL:     `DIŠTAR ṢE-E-RI`
  - ATTESTED: `ṢE-E-RI`
- **6′**
  - FULL:     `x ITU x`
  - ATTESTED: `x ITU x`
- **7′**
  - FULL:     `x x`
  - ATTESTED: `x x`
### CHDS 5.22

- **lk. Kol. 1′**
  - FULL:     `x x x`
  - ATTESTED: `x x x`
- **lk. Kol. 2′**
  - FULL:     `x an-da`
  - ATTESTED: `x an-da`
- **lk. Kol. 3′**
  - FULL:     `pur-pu-ru-uš`
  - ATTESTED: `pur-pu-ru-uš`
- **lk. Kol. 4′**
  - FULL:     `ḫar-kán-zi`
  - ATTESTED: `ḫar-kán-zi`
- **lk. Kol. 5′**
  - FULL:     `ta-an iš-ḫu-u-wa-an-zi`
  - ATTESTED: `ta-an iš-ḫu-u-wa-an-zi`
- **lk. Kol. 6′**
  - FULL:     `x pa-iz-zi`
  - ATTESTED: `x pa-iz-zi`
- **lk. Kol. 7′**
  - FULL:     `x-a-i kat-ta-an ti-ia-zi`
  - ATTESTED: `x-a-i kat-ta-an ti-ia-zi`
- **lk. Kol. 8′**
  - FULL:     `x EGIR-an-da`
  - ATTESTED: `x EGIR-an-da`
- **lk. Kol. 9′**
  - FULL:     `Éḫa-le-en-tu-u-wa-aš`
  - ATTESTED: `Éḫa-le-en-tu-u-wa-aš`
- **lk. Kol. 10′**
  - FULL:     `É A-BI A-BI-IA DUTU-ŠI`
  - ATTESTED: `É A-BI A-BI-IA DUTU-ŠI`
- **lk. Kol. 11′**
  - FULL:     `x-x-zi`
  - ATTESTED: `x-x-zi`
- **lk. Kol. 12′**
  - FULL:     `LÚḫal-li-ia-ri-eš`
  - ATTESTED: `LÚḫal-li-ia-ri-eš`
- **lk. Kol. 13′**
  - FULL:     `a-an-x x x`
  - ATTESTED: `a-an-x x x`
- **lk. Kol. 14′**
  - FULL:     `x-it`
  - ATTESTED: `x-it`
- **r. Kol. 1′**
  - FULL:     `BADḪI.A-kán`
  - ATTESTED: `BADḪI.A-kán`
- **r. Kol. 2′**
  - FULL:     `ḫu-u-ma-an`
  - ATTESTED: ``
- **r. Kol. 3′**
  - FULL:     `ta-at x`
  - ATTESTED: `x`
- **r. Kol. 4′**
  - FULL:     `ta-aš-ta NINDA`
  - ATTESTED: ``
- **r. Kol. 5′**
  - FULL:     `x-x-pí an`
  - ATTESTED: `x-x`
- **r. Kol. 6′**
  - FULL:     `ta-aš-ta`
  - ATTESTED: ``
- **r. Kol. 7′**
  - FULL:     `GIŠDAG-ti ti-x`
  - ATTESTED: `x`
- **r. Kol. 8′**
  - FULL:     `GIŠDAG-ti an-da`
  - ATTESTED: ``
- **r. Kol. 9′**
  - FULL:     `nu A-NAMUNUSMEŠ`
  - ATTESTED: ``
- **r. Kol. 10′**
  - FULL:     `KÁ.GAL x`
  - ATTESTED: `x`
- **r. Kol. 11′**
  - FULL:     `ḫa-aš-ša`
  - ATTESTED: ``
- **r. Kol. 12′**
  - FULL:     `x`
  - ATTESTED: `x`
### KBo 64.109

- **1′**
  - FULL:     `zi`
  - ATTESTED: `zi`
- **2′**
  - FULL:     `x GEŠTIN LÀL Ì.GIŠ`
  - ATTESTED: `x GEŠTIN LÀL Ì.GIŠ`
- **3′**
  - FULL:     `ta ud-da-a-ar`
  - ATTESTED: `ta ud-da-a-ar`
- **4′**
  - FULL:     `ta Dma-az`
  - ATTESTED: `ta Dma-az`
- **5′**
  - FULL:     `UD 26KAM I-NA`
  - ATTESTED: `26KAM I-NA`
- **6′**
  - FULL:     `UD 27KAM I-NA`
  - ATTESTED: `I`
- **7′**
  - FULL:     `x-ia(-)`
  - ATTESTED: `x-ia(-)`
### KBo 59.139

- **1′**
  - FULL:     `a-al-li`
  - ATTESTED: `a-al-li`
- **2′**
  - FULL:     `pé-ra-an 1-ŠU`
  - ATTESTED: `pé-ra-an 1-ŠU`
- **3′**
  - FULL:     `da-a-i`
  - ATTESTED: `a-i`
- **4′**
  - FULL:     `É.GAL ša-x`
  - ATTESTED: `É.GAL ša-x`
- **5′**
  - FULL:     `LUGAL-i pa`
  - ATTESTED: `LUGAL-i pa`
- **6′**
  - FULL:     `x x`
  - ATTESTED: `x x`
### KBo 46.186

- **1′**
  - FULL:     `É EN.NU.UN`
  - ATTESTED: `É EN.NU.UN`
- **3′**
  - FULL:     `na-aš-ma NINDA-i ku-e-da-x`
  - ATTESTED: `NINDA-i ku-e-da-x`
- **4′**
  - FULL:     `KU₇ im-mi-ia-an-za`
  - ATTESTED: `im-mi-ia-an-za`
- **5′**
  - FULL:     `na-aš-ma-kán A-NADUGÚTUL`
  - ATTESTED: `kán A-NADUGÚTUL`
- **6′**
  - FULL:     `nu-kán a-pé-e-ez IŠ-TU`
  - ATTESTED: `a-pé-e-ez IŠ-TU`
- **7′**
  - FULL:     `x e-ez-za-i na-aš`
  - ATTESTED: `x e-ez-za-i na-aš`
- **8′**
  - FULL:     `x a-ni-ia`
  - ATTESTED: `x a-ni-ia`
- **9′**
  - FULL:     `wa`
  - ATTESTED: `wa`
- **10′**
  - FULL:     `x x x`
  - ATTESTED: `x x x`