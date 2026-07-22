# P2.5 A5 -- Metadata Patch Report

## A5.1/A5.2 -- side/column/physical-edge remap (corpus.parquet patched in place)

- Word-token rows: 1,525,888
- `side` unmapped before patch: 671,453 rows -> after: 420,006 rows (37.4% recovered)
- New `on_physical_edge` field: 7,699 word-token rows sit on a line marked as a physical tablet edge (u./o./lk./r. Rd.) -- these lines are direct evidence the fragment is NOT broken at that boundary, strengthening the top/bottom-edge-lost heuristic in edges.parquet.

## A5.3 -- Provenance patch (DAAM/Kp)

**Amendment hypothesis was only half right.** WebSearch verification found DAAM ("Documenta Antiqua Asiae Minoris") is a MULTI-SITE series, not single-site:
- DAAM 1 = *Keilschrifttafeln aus Kayalipinar 1* (Rieken 2019) -> Kayalipinar/Samuha
- DAAM 2 = *The Akkadian and Sumerian Texts from Ortakoy-Sapinuwa* (Schwemer & Suel 2021) -> Ortakoy/Sapinuwa (contradicts the amendment's blanket Kayalipinar hypothesis)
- DAAM 3 = *Bogazkoy Tablets in the Museum of Anatolian Civilisations* (Bozgun 2025) -> Hattusa
- DAAM 4 = *Bogazkoy Tablets ... (Bo 9032-9097)* (Cilingir Cesur 2025) -> Hattusa
- Applied PER VOLUME NUMBER (parsed from `DAAM N.M` docIDs), not as a blanket prefix mapping.
- `Kp` confirmed as a Kayalipinar/Samuha variant siglum (direct extension of the already-known `KpT` prefix already in SITE_PREFIXES) -- high confidence, applied.
- DAAM docs repatched: 159. Kp docs repatched: 7.
- **Provincial-site document count: 201 -> 314** (target range from the amendment: ~201 -> ~365; actual result below/above that estimate should be read against the fact that not all DAAM volumes are provincial -- vols 3-4 add to Hattusa, not provincial).

## Remaining unknown prefixes -- proposals, UNAPPLIED

Per spec: proposed at ~0.6-0.7 confidence (some lower where evidence was weak), NOT applied to site/site_split. Expert review or Konkordanz verification required before use. Full table in `prefix_mapping_proposals.csv`.

| prefix | proposed site | confidence | evidence |
|---|---|---|---|
| CHDS | Hattusa | 0.7 | Chicago Hittite Dictionary Supplements -- confirmed via WebSearch to publish 'Unpublished Bo-Fragments' (Bo = Boghazkoy prefix), i.e. Hattusa-origin fragments held/catalogued by the U. Chicago CHD project, not an excavation-findspot siglum itself. |
| DBH | Hattusa | 0.65 | Dresdner Beitraege zur Hethitologie -- German publication series historically focused on Boghazkoy material; not independently re-verified per-volume here. |
| FHL | Hattusa | 0.5 | No definitive series identification found via WebSearch; appears in bibliographies alongside other Boghazkoy-fragment sigla but evidence is weak -- lower confidence than the others in this list. |
| VSNF | Hattusa | 0.65 | Vorderasiatische Schriftdenkmaeler Neue Folge -- Berlin museum (Vorderasiatisches Museum) publication series; VAT-collection-adjacent, predominantly Boghazkoy-origin holdings historically. |
| HFAC | Hattusa | 0.7 | Hittite Fragments in American Collections (Beckman) -- published private/museum US holdings, predominantly Boghazkoy-origin material that entered the antiquities market/collections. |
| Privat | Hattusa | 0.55 | Generic 'private collection' label -- plausibly Boghazkoy-origin by base rate (most dispersed Hittite tablets in private hands trace to early Boghazkoy excavations/antiquities market) but no specific verification performed. |
| VAT | Hattusa | 0.65 | Vorderasiatische Tontafeln -- Berlin Vorderasiatisches Museum inventory prefix; largely Boghazkoy-origin historical holdings. |
| HHCTO | unknown | 0.3 | No identification found; insufficient evidence for a confidence-bearing proposal. |
| Gurney | Hattusa | 0.55 | O.R. Gurney published-collection siglum (British); plausibly Boghazkoy-origin by base rate, not independently verified. |
| Dispersa | Hattusa | 0.5 | Likely a 'dispersed tablets' catalog label; plausibly Boghazkoy-origin by base rate, not verified. |
| FHG | unknown | 0.3 | No identification found; insufficient evidence. |
| HHT | unknown | 0.3 | No identification found; insufficient evidence. |
| Durham | Hattusa | 0.5 | UK museum/university collection siglum; plausibly Boghazkoy-origin by base rate, not verified. |
| AMUM | Hattusa | 0.55 | Possibly Anadolu Medeniyetleri Muezesi (Museum of Anatolian Civilisations, Ankara) -- this museum holds substantial Boghazkoy excavation material (cf. DAAM 3/4 Bo-range tablets), but the prefix expansion itself is not confirmed. |
| München | Hattusa | 0.6 | Munich museum collection siglum; plausibly Boghazkoy-origin historical holdings, not verified. |
| AAA3 | unknown | 0.3 | No identification found; insufficient evidence. |
| UK | unknown | 0.3 | Ambiguous short prefix; no confident identification found. |