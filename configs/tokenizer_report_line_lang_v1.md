# Tokenizer rebuild -- Hittite-only line filter (line_lang migration v1)

Supersedes the vocab (not the report) in `tokenizer_report.md` (Phase 1, `Archive/scripts/17_tokenizer.py`, untouched since Phase 1 closeout). That vocab was built without any language check -- non-Hittite lines (Akkadian, Sumerian, Hattic, Luwian, Palaic, Hurrian) contributed tokens to it. This rebuild excludes their content via `migrations/line_lang_v1/line_lang_canonical.parquet` (ratified vocabulary + Step C rebuild, this phase).

- Vocabulary source: TRAIN-side + discovery-pool ATTESTED, HITTITE-ONLY text (21,037 fragments)
- min_df: 2
- **Vocab size (incl. specials): 1,957** (was 2,374 before this rebuild, -417)
- **Dev OOV rate (Hittite-only content): 0.1410%** (188 / 133,371 tokens) -- PASS (target <1%)
- Dev tokens excluded as non-Hittite (not counted toward OOV either way): **31,541**

## Round-trip examples (5 seeded TRAIN fragments, Hittite-only rendering)

### KBo 51.228+::3
- original (4 tokens): `<GAP> <LINE> <LINE> <GAP>`
- decoded (exact_match=True, unk_count=0): `<GAP> <LINE> <LINE> <GAP>`

### KBo 25.157+::3
- original (164 tokens): `<GAP> x <LINE> nu <LINE> ( )pé da ú wa x <LINE> x kán zi na at <LINE> wa a an na ú e <LINE> LÚ ˽ GIŠ GIDRU LÚ MEŠ ḫa a <LINE> ta pa ap pí an zi <PAR> <LINE> D ši ú na aš a ni ia at ta <LINE> e ša DUMU MEŠ É GAL ki` ...
- decoded (exact_match=True, unk_count=0): `<GAP> x <LINE> nu <LINE> ( )pé da ú wa x <LINE> x kán zi na at <LINE> wa a an na ú e <LINE> LÚ ˽ GIŠ GIDRU LÚ MEŠ ḫa a <LINE> ta pa ap pí an zi <PAR> <LINE> D ši ú na aš a ni ia at ta <LINE> e ša DUMU MEŠ É GAL ki` ...

### KBo 11.29
- original (288 tokens): `<EDGE_T> x x x x <LINE> LÚ GUDU₁₂ <NUM> NINDA GUR₄ RA a i <LINE> LÚ SANGA ni pa a i LÚ SANGA ša <LINE> x ra LÚ SANGA ni e ep zi <LINE> ia aš pé ra an da a i <PAR> <LINE> an zi kat ta an UZU NINDA GUR₄ RA ki it ta <LINE> TÚG it wa aš` ...
- decoded (exact_match=True, unk_count=0): `<EDGE_T> x x x x <LINE> LÚ GUDU₁₂ <NUM> NINDA GUR₄ RA a i <LINE> LÚ SANGA ni pa a i LÚ SANGA ša <LINE> x ra LÚ SANGA ni e ep zi <LINE> ia aš pé ra an da a i <PAR> <LINE> an zi kat ta an UZU NINDA GUR₄ RA ki it ta <LINE> TÚG it wa aš` ...

### KBo 31.113
- original (67 tokens): `<GAP> UD <NUM> KAM x <PAR> <LINE> UD <NUM> KAM DINGIR LAM x <LINE> MAḪ A NA LUGAL MUNUS LUGAL x <LINE> ap pu wa az ú da at <LINE> at ša ma ša at uk tu <PAR> <LINE> ku it PA NI DINGIR LIM ki <LINE> ša li ma az Ù TÚG <LINE> kán ki nu zi nu <LINE>` ...
- decoded (exact_match=True, unk_count=0): `<GAP> UD <NUM> KAM x <PAR> <LINE> UD <NUM> KAM DINGIR LAM x <LINE> MAḪ A NA LUGAL MUNUS LUGAL x <LINE> ap pu wa az ú da at <LINE> at ša ma ša at uk tu <PAR> <LINE> ku it PA NI DINGIR LIM ki <LINE> ša li ma az Ù TÚG <LINE> kán ki nu zi nu <LINE>` ...

### KuSa I_1.18
- original (137 tokens): `<GAP> x x x x an <LINE> x ZI D NAM <LINE> <NUM> x x xpal x <LINE> x za x SILIM x SIG₅ <PAR> <LINE> tar ku it ŠU za DIB ú <LINE> da an ZI ME aš nu kán GAM ku uš <LINE> A GÍD 〈DA〉 mi nu mar na aš DINGIR MAḪ SUM za x <PAR> <LINE>` ...
- decoded (exact_match=False, unk_count=1): `<GAP> x x x x an <LINE> x ZI D NAM <LINE> <NUM> x x <UNK> x <LINE> x za x SILIM x SIG₅ <PAR> <LINE> tar ku it ŠU za DIB ú <LINE> da an ZI ME aš nu kán GAM ku uš <LINE> A GÍD 〈DA〉 mi nu mar na aš DINGIR MAḪ SUM za x <PAR> <LINE>` ...

## What this changes for downstream consumers

Every script that calls `hittite_tokenizer.Tokenizer.load()` now gets this vocab, not the Phase 1 one -- their token ids and OOV behavior change even though no code in those scripts changed. Anything with a frozen numeric result computed against the old vocab (P2-E1 through P2-E7, the real-gap pipeline built earlier this phase) needs re-running under the new vocab to stay consistent, tracked as a separate step in this phase's work.