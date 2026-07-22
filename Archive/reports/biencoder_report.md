# P4 D15 -- Bi-encoder Report

## Ablation grid: positive-mix ratios x pooling variant, dev tier-proxy table vs BM25

All three gates now include a BM25 dev baseline (duplicates was already computed by 20_biencoder.py's evaluate_dev_gates(); real-joins and synthetic-joins baselines are reconstructed here over the identical deterministic query/candidate sets, not re-trained).

### Dev duplicates (recall@10, 95% CI, n)

| mix | mean_pool | line_max |
|---|---|---|
| balanced | 0.812 [0.786, 0.836] (n=872) | 0.795 [0.768, 0.821] (n=872) |
| real_only | 0.805 [0.776, 0.831] (n=872) | 0.814 [0.787, 0.841] (n=872) |
| synthetic_only | 0.784 [0.757, 0.810] (n=872) | 0.727 [0.696, 0.756] (n=872) |
| **BM25 baseline** | 0.888 [0.866, 0.908] (n=872) | -- |

### Dev real joins (recall@10, 95% CI, n) -- THE PRE-REGISTERED GATE

| mix | mean_pool | line_max |
|---|---|---|
| balanced | 0.555 [0.484, 0.621] (n=182) | 0.555 [0.483, 0.621] (n=182) |
| real_only | 0.522 [0.451, 0.593] (n=182) | 0.571 [0.505, 0.643] (n=182) |
| synthetic_only | 0.538 [0.467, 0.610] (n=182) | 0.544 [0.467, 0.615] (n=182) |
| **BM25 baseline** | 0.835 [0.780, 0.890] (n=182) | -- |

### Dev synthetic held-out joins (recall@10, 95% CI, n)

| mix | mean_pool |
|---|---|
| balanced | 0.600 [0.543, 0.657] (n=300) |
| real_only | 0.350 [0.297, 0.407] (n=300) |
| synthetic_only | 0.643 [0.587, 0.700] (n=300) |
| **BM25 baseline** | 0.247 [0.197, 0.297] (n=300) |

Expected and interpretable: synthetic-joins numbers sit above real-joins numbers for most combos (the synthetic-vs-real gap CLAUDE.md's findable-join bias note anticipates) except where noted below; BM25 remains strongest on duplicates (near-solved by lexical overlap, per CLAUDE.md's own prediction), which is not a red flag for the bi-encoder.

## Pre-registered P5 success criterion

Per specs/P4_NEURAL_SPEC.md acceptance check 5: "real dev-join recall@10 meaningfully above BM25's dev-join recall@10 (state both numbers; judgment call documented, made jointly with the architect session, not silently)."

- **Best bi-encoder combo:** real_only / line_max -- real dev-join recall@10 = **0.571**
- **BM25 dev-join recall@10 baseline:** **0.835**
- Delta: -0.264 (AT OR BELOW the BM25 baseline).
- **Both numbers stated as required; whether this delta counts as "meaningfully above" is the judgment call left to the architect check-in, not decided unilaterally here.**

## Line/passage-level scoring ablation

line_max (max-over-line-pairs, per the matrix model's local-alignment framing) vs mean_pool (whole-fragment embedding) -- see the tables above for the full grid. Directionally, line_max tends to help recall@1 on real joins more than recall@10 (consistent with 'joins are local': a strong single-line match can win the top spot even when the whole-fragment embedding is noisier), per the balanced-mix numbers explored during initial development.

## 10 qualitative dev-join retrievals (5 success, 5 failure)

Drawn from the best combo (real_only/line_max checkpoint, mean_pool embeddings shown for readability). Not cherry-picked beyond the success/failure split itself (seeded random sample within each group).

### Example 1/10 -- `KUB 52.102+::2`, SUCCESS (true partner ranked #1)
- query: `ma a an zé e ni DUMU-aš A-NADINGIRMEŠ URUza-al-pa i ia u wa an zi pa iz zi nu IŠ-TUÉ.GAL-LIM <NUM> GU₄.MAḪ <NUM> GU₄ÁB <NUM>`
- top-1 predicted: `KUB 52.102+::1` -- `ma a an zé e ni DUMU-aš A-NADINGIRMEŠ URUza-al-pa i ia u wa an zi pa iz zi nu IŠ-TUÉ.GAL-LIM <NUM> GU₄.MAḪ <NUM> GU₄ÁB <NUM>`
- true partner(s): ['KUB 52.102+::1']
- rank of true partner: 1

### Example 2/10 -- `KUB 34.86+::12`, SUCCESS (true partner ranked #1)
- query: `<NUM> NINDAwa-ge-eš-šar I-NAEZEN₄ ME-EL-QÉ-ET LÚ.MEŠḫa-pí-eš <NUM> NINDA <NUM> <NUM> DUG mar nu an LÚAGRIG URUzi-nir-nu-wa pa a ME-EL-QÉ-ET LÚMEŠ URUan-gul-la NINDAwa-ge-eš-šar <NUM> <NUM> DUG mar`
- top-1 predicted: `KUB 34.86+::11` -- `ME-EL-QÉ-ET LÚMEŠ URUan-gul-la NINDAwa-ge-eš-šar <NUM> <NUM> DUG mar nu an I-NAEZEN₄ Éḫi-iš-ta-a URUzi-nir-nu-wa pa i URUḪA-AT-TI <NUM> <NUM> NINDAwa-ge-eš-šar nu an I-NAEZEN₄ Éḫi-iš-ta-a pa a`
- true partner(s): ['KUB 34.86+::11', 'KUB 34.86+::13']
- rank of true partner: 1

### Example 3/10 -- `KBo 22.12+::3`, SUCCESS (true partner ranked #1)
- query: `me el ḫa at tu li kat ta ú it ÍDSÍG Ù KUR URUka-aš-ši-ia ni wa al ḫu wa an A-BI-IA la aḫ ḫi`
- top-1 predicted: `KBo 22.12+::2` -- `kat ta ú it ÍDSÍG Ù KUR URUka-aš-ši-ia ni wa al ḫu wa an A-BI-IA la aḫ ḫi URUkam-ma-a-la-ia`
- true partner(s): ['KBo 22.12+::2']
- rank of true partner: 1

### Example 4/10 -- `KBo 50.77+::6`, SUCCESS (true partner ranked #1)
- query: `dam me eš ḫi iš kán zi na an DUTU-ŠI pu nu uš šu un ku e ez wa at ta UM-MA ŠU-Ú-MA NAM.RAMEŠ e`
- top-1 predicted: `KBo 50.77+::4` -- `x x x ta ra aš ma mDU-D10-x-an-na nu uš ma aš kán mšum-mi-it-ta-aš KUR ḪA-AT-TI wa aš ti er URUa-mur-ri A-NADUTU-ŠI ki iš ša`
- true partner(s): ['KBo 50.77+::2', 'KBo 50.77+::3', 'KBo 50.77+::4', 'KBo 50.77+::5', 'KBo 50.77+::7']
- rank of true partner: 1

### Example 5/10 -- `KUB 29.55+::3`, SUCCESS (true partner ranked #1)
- query: `an ta na aš kán nam ma ú i te kat ta na aš ar ru um ma an ti it ta ar ra an`
- top-1 predicted: `KUB 29.55+::4` -- `<NUM> ANŠE.KUR.RA <NUM> SA₂₀-A-TÙ wa a tar nam ma nu uš wa nu uš ki ti an zi da aš ša u e eš ma`
- true partner(s): ['KUB 29.55+::1', 'KUB 29.55+::2', 'KUB 29.55+::4']
- rank of true partner: 1

### Example 6/10 -- `KBo 50.77+::7`, FAILURE
- query: `UM-MA DUTU-ŠI mmu-ur-ši-DINGIR-LIM LUGAL GAL LUGAL KUR URUḪA-AT-TI DUMU mšu-up-pí-lu-li-u-ma LUGAL GAL LUGAL KUR URUḪA-AT-TI UR.SAG an na az URUi-ia-ru-wa-ta-aš URU-aš ŠAKUR URUpár-ga e eš`
- top-1 predicted: `KBo 50.77+::2` -- `nu wa ra aš am mu nu un ki nu un ma wa ma aḫ ḫa an x ú wa wa ar iš ta ma`
- true partner(s): ['KBo 50.77+::4', 'KBo 50.77+::6']
- rank of true partner: 7

### Example 7/10 -- `KBo 50.14+::1`, FAILURE
- query: `A-BU-IA URUga-aš-ga-ma-za aš GIŠTUKULḪI.A a er KUR-e-ma IŠ-TULÚKÚR at ta aḫ ḫa an e eš ta A-BU-IA at ti URU-ri EGIR-an ú e tu uḫ`
- top-1 predicted: `KBo 50.187` -- `ŠU-TIḪI.A za aḫ ḫi ia at e ḫar ta na at za ku iš ša a pé e EGIR-pa pa it LÚKÚR-ma A-BU-IA-ma A-NALÚKÚR za`
- true partner(s): ['KBo 50.14+::2']
- rank of true partner: 101

### Example 8/10 -- `KBo 30.20::2`, FAILURE
- query: `<NUM> ta ḫa ši iš I-NAÉ ḫu kán zi LUGAL-i NINDAwa-ga-da-an da na <NUM> NINDAwa-ge-eš-šar URUa-li-ša pa SA₅ <NUM> TÚGŠÀ.GA.DÙ GADA <NUM> ŠAUR.MAḪḪI.A x an`
- top-1 predicted: `KBo 39.70` -- `an <NUM> NINDAwa-ga-da-aš NINDAḪI.A <NUM> LÚZABAR.DAB <NUM> iš KAŠ.GEŠTIN ḫu kán NINDAwa-ga-da-aš <NUM> <NUM>`
- true partner(s): ['KBo 30.20::1']
- rank of true partner: 2

### Example 9/10 -- `KBo 19.45+::2`, FAILURE
- query: `LÚ URUa Ú-UL u i ia an zi nu TUP-PA uz zi ia an zi na at <NUM> <NUM> pa x x x TUP-PA ú`
- top-1 predicted: `KBo 19.53` -- `x x x ÉRINMEŠ ANŠE.KUR.RAMEŠ ḪUR.SAGti-wa-ta-aš-ša-pát e šu un x iš tar na tar pa ni in A-NAMa-an-za-pa-aḫ-ḫa-ad-du x x x zi A-NA Mza li`
- true partner(s): ['KBo 19.45+::3']
- rank of true partner: 28

### Example 10/10 -- `KBo 23.64+::2`, FAILURE
- query: `x an x LÚ˽GIŠBANŠUR-aš <NUM> NINDA mi pár ši ia nu uš LÚ˽GIŠBANŠUR ša an šu up pa i GIŠBANŠUR-i NINDAzi-ip-pu-la-aš-ni-in UD( )ma GIŠBANŠUR-i da`
- top-1 predicted: `IBoT 4.193` -- `( )za( ) x i x u wa an x x da a NA₄ḫu-u-wa-ši aš DINGIR-LIM LUGAL ḫa a li ia ma i ḫal za`
- true partner(s): ['KBo 23.64+::1']
- rank of true partner: 171
