# P2.5 A1 -- Bins Report

## Data source

- Single bulk fetch from Wayback Machine archived snapshot (2025-05-14) of the legacy CTH catalogue index page, cached to `cth_index_raw.html` -- **1 HTTP request total**, not 657 (the live per-number endpoint is dead; see script docstring).
- 836 distinct base CTH titles parsed from source.
- Corpus CTH numbers: 657. Missing titles: 0 

## Classification summary (POST human sign-off resolution)

- **is_bin=True**: 114 compositions, 14,046 documents
- **bin_uncertain=True (unresolved)**: 0 compositions, 0 documents
- **real composition**: 543 compositions, 7,593 documents

Classification rule: bin keyword (DE/FR/EN fragment-bin patterns) present AND title <= 6 words -> is_bin. Bin keyword present but title longer/more specific -> bin_uncertain (NOT auto-decided). No bin keyword -> real composition, unless the seed list flagged it (then also uncertain, for cross-check).

## Seed-list cross-check (hypotheses from P2.5_AMENDMENTS.md, NOT used to override title-driven classification)

- Seed hypotheses confirmed by title: 16 -- [209, 212, 215, 458, 470, 500, 530, 582, 590, 670, 745, 790, 791, 819, 831, 832]
- Seed hypotheses NOT confirmed by title (seed was wrong or title misleading): 9 -- [626, 627, 628, 826, 827, 828, 829, 830, 833]
- Bins found by title that were NOT in the seed list (seed list was incomplete, as expected): 98 -- [2, 3, 9, 10, 17, 22, 23, 24, 39, 61, 101, 126, 140, 170, 187, 208, 210, 211, 213, 214, 216, 246, 248, 249, 250, 275, 287, 309, 310, 332, 335, 337, 346, 350, 351, 352, 353, 370, 385, 386, 389, 420, 428, 452, 453, 456, 457, 459, 460, 473, 556, 560, 595, 596, 625, 635, 639, 640, 642, 643, 644, 645, 646, 648, 649, 650, 651, 652, 653, 655, 659, 664, 665, 669, 674, 675, 676, 678, 685, 692, 694, 706, 720, 731, 734, 744, 754, 763, 767, 768, 769, 770, 778, 781, 795, 807, 813, 824]

## Uncertain list -- HUMAN SIGN-OFF RECORDED 2026-07-21

Per P2.5_AMENDMENTS.md acceptance check 1. User reviewed this 31-entry list (shown below in its pre-resolution state) and decided: (1) the 25 entries with a bin keyword + long/specific title -> **BIN** (rationale: cataloguer explicitly labeled these "fragments" even with a narrower theme; safer to exclude from duplicate-positive supervision); (2) the 6 seed-list entries with NO bin keyword at all (626, 627, 628, 826, 827, 828) -> **REAL** (no textual bin evidence; the seed hypothesis was simply wrong for these). Final decision recorded per-row in cth_bins.csv's `reason` column (suffix `RESOLVED 2026-07-21`).

| CTH | title | doc_count | pre-resolution reason |
|---|---|---|---|
| 500 | Fragmente von Fest- und Beschwörungsritualen aus Kizzuwatna | 463 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 628 | (ḫ)išuwa-Fest | 301 | seed hypothesis flagged this as a possible bin, but title has NO fragment-bin keyword -- seed was wrong or title is misleading; human review requested |
| 530 | Fragmente von Kultinventaren ohne Kultbild- oder Festbeschreibungen | 253 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 627 | KI.LAM-Fest | 188 | seed hypothesis flagged this as a possible bin, but title has NO fragment-bin keyword -- seed was wrong or title is misleading; human review requested |
| 626 | Fest der Eile (EZEN₄ nuntarrijašḫaš) | 170 | seed hypothesis flagged this as a possible bin, but title has NO fragment-bin keyword -- seed was wrong or title is misleading; human review requested |
| 635 | Fragmente der Feste von Zippalanda und dem Berg Daḫa | 111 | bin keyword present but title is long/specific (9 words) -- may be a real composition whose title mentions fragments; human review requested |
| 706 | Fragmente von Festritualen für Teššup und Ḫebat | 86 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 61 | Annalen Muršilis II. (.I Zehnjahresannalen, .II Ausführliche Annalen, .III nicht zugeordnete Fragmente) | 57 | bin keyword present but title is long/specific (12 words) -- may be a real composition whose title mentions fragments; human review requested |
| 778 | Fragmente des Mundwaschungsrituals mit Nennung Tašmišarris und Taduḫepas | 54 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 645 | Fragmente der Feste für die unterirdischen Gottheiten | 51 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 652 | Festfragmente mit Nennung eines „Mannes des Wettergottes“ (LÚ D10) | 50 | bin keyword present but title is long/specific (9 words) -- may be a real composition whose title mentions fragments; human review requested |
| 560 | Fragmente hethitischer und akkadischer Omina (.I Akkadisch, .II Hethitisch) | 46 | bin keyword present but title is long/specific (9 words) -- may be a real composition whose title mentions fragments; human review requested |
| 646 | Fragmente der von der Königin gefeierten Feste | 46 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 249 | Inventare und Inventarfragmente (.I Gemischte Inventare, .II Textile und Kleidungsstücke, .III Edelmetall- und Steinobjekte und Schmucksachen, .IV Elfenbein- und Ebenholzobjekte, .V Waffen und Werkzeug) | 46 | bin keyword present but title is long/specific (24 words) -- may be a real composition whose title mentions fragments; human review requested |
| 335 | Fragmente der Mythen von verschwindenden und wiederkehrenden Gottheiten | 32 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 248 | Mit dem Staatskult im Zusammenhang stehende Inventare (.I Tempelinventare mit Kommentar über Versorgung, .II Detaillierte Beschreibungen von Kultbildern, .III Texte zu Votivobjekten, .IV Inventarfragmente von Kultbildern und Figuren) | 24 | bin keyword present but title is long/specific (28 words) -- may be a real composition whose title mentions fragments; human review requested |
| 385 | Fragmente der Gebete an die Sonnengöttin von Arinna | 19 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 3 | Erzählung um die Stadt Zalpa und Fragmente mit Erwähnung der Stadt Zalpa | 16 | bin keyword present but title is long/specific (12 words) -- may be a real composition whose title mentions fragments; human review requested |
| 644 | Fest- oder Ritualfragmente mit Nennung des Pirinkir | 14 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 140 | Fragmente der Verträge Arnuwandas I. mit den Kaškäern | 10 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 386 | Fragmente der Gebete an den Wettergott von Nerik | 9 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 310 | Hethitische Fragmente des šar tamḫāri "König der Schlacht" | 8 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 332 | Mythos von Verschwinden und Wiederkehr des Wettergottes: mugawar-Fragmente | 7 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 213 | Fragmente von Götterzeugenlisten in Verträgen und Instruktionen | 7 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 2 | Fragmente mit Erwähnung Anum-Ḫirbis und der Stadt Zalpa | 3 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 10 | Fragmente mit Erwähnung des Feldzugs Muršilis I. gegen Babylon | 3 | bin keyword present but title is long/specific (9 words) -- may be a real composition whose title mentions fragments; human review requested |
| 17 | Fragmente mit Bezug auf Kämpfe mit Hurritern | 1 | bin keyword present but title is long/specific (7 words) -- may be a real composition whose title mentions fragments; human review requested |
| 353 | Fragmente mit Erwähnung der Tochter der Plejaden (DIMIN.IMIN.BI) | 1 | bin keyword present but title is long/specific (8 words) -- may be a real composition whose title mentions fragments; human review requested |
| 826 | Etikett: Anrufung? in fehlerhaftem Hethitisch | 1 | seed hypothesis flagged this as a possible bin, but title has NO fragment-bin keyword -- seed was wrong or title is misleading; human review requested |
| 827 | Orakel in archaischer Sprache | 1 | seed hypothesis flagged this as a possible bin, but title has NO fragment-bin keyword -- seed was wrong or title is misleading; human review requested |
| 828 | Orakelanfragen | 1 | seed hypothesis flagged this as a possible bin, but title has NO fragment-bin keyword -- seed was wrong or title is misleading; human review requested |

## Top-20 largest compositions, re-annotated with is_bin (dataset_report.md cross-reference)

| CTH | documents | is_bin | bin_uncertain | title |
|---|---|---|---|---|
| 832 | 3583 | True | False | Hethitische Fragmente verschiedenen Inhaltes |
| 670 | 3067 | True | False | Festritualfragmente |
| 470 | 1805 | True | False | Ritualfragmente |
| 500 | 463 | True | False | Fragmente von Fest- und Beschwörungsritualen aus Kizzuwatna |
| 582 | 379 | True | False | Orakelfragmente |
| 215 | 335 | True | False | Undifferenzierte Fragmente historischer Texte |
| 628 | 301 | False | False | (ḫ)išuwa-Fest |
| 791 | 262 | True | False | Hurritische Fragmente |
| 530 | 253 | True | False | Fragmente von Kultinventaren ohne Kultbild- oder Festbeschreibungen |
| 627 | 188 | False | False | KI.LAM-Fest |
| 209 | 177 | True | False | Fragmente hethitischer Briefe |
| 819 | 171 | True | False | Akkadische Fragmente |
| 626 | 170 | False | False | Fest der Eile (EZEN₄ nuntarrijašḫaš) |
| 701 | 164 | False | False | Trankopfer für den Thron der Ḫebat |
| 458 | 157 | True | False | Fragmente von Beschwörungsritualen |
| 212 | 150 | True | False | Fragmente von Verträgen oder Instruktionen |
| 790 | 144 | True | False | Fragmente hethitisch-hurritischer Rituale und Beschwörungen |
| 745 | 143 | True | False | Hattische Fragmente |
| 590 | 141 | True | False | Fragmente der Traum- und Gelübdetexte |
| 370 | 136 | True | False | Mythologische Fragmente (.I Hethitisch, .II Hurritisch) |

## A2 -- Discovery pool + supervision-eligible corpus (acceptance checks 2-3)

- **Discovery pool** (`discovery_pool.parquet`, is_bin=True docs, inference-time queries only, never scored as ground truth): **14,046 documents**
- **Supervision-eligible** (confirmed real compositions, bin_uncertain=False): 7,593 documents, 543 compositions
- **Pending review** (bin_uncertain=True, held out of BOTH pools until sign-off -- conservative default): 0 documents, 0 compositions

### Duplicate-positive pair counts (same-CTH combinatorial pairs, before/after bin exclusion)
- **Naive (all 657 compositions, no bin filtering)**: 13,451,014 pairs
- **Bins excluded, uncertain still included**: 234,263 pairs (98.3% drop)
- **Bins excluded, uncertain ALSO excluded (conservative, current supervision-eligible number)**: 234,263 pairs (98.3% drop from naive)

The large drop is expected and is the whole point of the bin reframe: CTH 832 alone ("Hethitische Fragmente verschiedenen Inhaltes", 3,583 docs) contributes 6,417,153 naive same-folder pairs by itself, none of which are real duplicate-witness evidence -- they're unrelated fragments an editor filed under the same catch-all number for lack of a better home.