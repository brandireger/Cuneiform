# P4 D14 -- Pretraining Report

- Checkpoint: `runs\pretrain_base\checkpoint.pt`, final step **59999** (config max_steps=60000, so all steps completed)
- Git commit: 703fa46ee3e7b06114d3675b2e99ab28bbea47fd. Corpus version: TLHdig_0.2.0-beta. Seed: 20260722.
- Architecture: 6 layers, d_model=384, 6 heads, d_ff=1536, seq_len=512. 12,817,991 params.
- Data: TRAIN + discovery-pool ATTESTED sequences for gradient updates; DEV used only for loss curves / diagnostics below; TEST never touched.

## 1. Final losses

- Train (last logged step 59999): mlm_loss=3.8785, boundary_loss=0.2830, total_loss=4.1615
- Dev, last training-loop eval (step 59500): mlm_loss=3.8778, span_exact(pooled, token-level)=0.2117, boundary_auc(pooled)=0.7716
- Dev, FRESH final pass (n_batches=20, this report): mlm_loss=3.9419, boundary_accuracy=0.7328, boundary_auc(pooled)=0.8073
- First eval (step 0, for reference): mlm_loss=7.8523, span_exact(token)=0.0, boundary_auc=0.4757 (chance)

## 2. Span-infilling exact-match by span-length band (dev, SPAN-level, not token-level)

Note: this differs from the training-loop's pooled `dev_span_exact` above, which is TOKEN-level accuracy at masked positions. Here, a span counts as a hit only if EVERY position in that contiguous masked run is predicted correctly -- a stricter, per-span-length-banded metric, per the acceptance checklist.

| span length | n spans | exact-match rate |
|---|---|---|
| 1 | 2634 | 0.413 |
| 2 | 1493 | 0.111 |
| 3 | 890 | 0.024 |
| 4 | 593 | 0.010 |
| 5 | 423 | 0.002 |
| 6 | 265 | 0.000 |
| 7 | 200 | 0.000 |
| 8 | 141 | 0.000 |
| 9 | 90 | 0.000 |
| 10 | 53 | 0.000 |
| 11-20 | 120 | 0.000 |
| >20 | 1 | 0.000 |

## 3. Boundary-head AUC by negative type (dev)

- Overall pooled AUC (this report's fresh pass, n=1920): 0.7904

| negative tier | AUC vs true_continuation | n_positive | n_negative |
|---|---|---|---|
| in_doc | 0.7461 | 938 | 711 |
| cross_genre | 0.9006 | 938 | 236 |
| random | 0.9473 | 938 | 35 |

Per spec: "the curriculum's hard negatives are the number that matters" -- `random` is the easiest tier (unrelated text, any genre); `cross_genre` is harder (same genre_band, different composition); `in_doc` is hardest (a shuffled position from the SAME fragment, so surface style/vocabulary give no signal at all).

## 4. Restoration-agreement diagnostic (dev)

Diagnostic only -- restorations are distilled expert judgment, per CLAUDE.md's cleanroom rule 3 ("training signal yes, evaluation signal never"). This measures AGREEMENT with the editor's proposal, not correctness against ground truth, and was NEVER used to select or train this (already-frozen) checkpoint.

- Real editor-restored spans sampled from dev fragments: **309** (cap 400)
- Token-level agreement rate: 0.2096
- Span-level EXACT agreement rate (every token in the span matches): 0.1165

## 5. Ten qualitative examples (5 agreements, 5 disagreements -- not cherry-picked)

### Example 1/10 -- `KBo 10.28+::2`, span_len=1, AGREE
- context before: `<LINE> pé e da i <PAR> <LINE> ŠA`
- **editor's restoration**: `LÚ`
- **model's proposal**: `LÚ`
- context after: `MEŠ SANGA GIŠ BANŠUR ḪI A da an`
- token-level agreement on this span: 1.00

### Example 2/10 -- `KUB 10.13`, span_len=1, AGREE
- context before: `pí an zi LÚ ta az zi el`
- **editor's restoration**: `li`
- **model's proposal**: `li`
- context after: `<LINE> <NUM> TÚG da a an pé e`
- token-level agreement on this span: 1.00

### Example 3/10 -- `KBo 56.105`, span_len=2, AGREE
- context before: `<GAP> ši ia tal li iš ke`
- **editor's restoration**: `ez zi`
- **model's proposal**: `ez zi`
- context after: `<LINE> UZU ZAG UDU ḪUR SAG ḪI A`
- token-level agreement on this span: 1.00

### Example 4/10 -- `KBo 50.77+::2`, span_len=1, AGREE
- context before: `EGIR pa <LINE> wa ra aš ku e`
- **editor's restoration**: `da`
- **model's proposal**: `da`
- context after: `ni ik ki pé eḫ ḫi <LINE> x`
- token-level agreement on this span: 1.00

### Example 5/10 -- `KBo 50.187`, span_len=1, AGREE
- context before: `<GAP> ÉRIN MEŠ ŠU TI ḪI`
- **editor's restoration**: `A`
- **model's proposal**: `A`
- context after: `<LINE> LÚ KÚR za aḫ ḫi ia at`
- token-level agreement on this span: 1.00

### Example 6/10 -- `KBo 7.35+::5`, span_len=7, DISAGREE
- context before: `ma <LINE> a ra a i ta ka`
- **editor's restoration**: `ne na an ta aš ta ru`
- **model's proposal**: `a aš aš zi an tu lu`
- context after: `uk zi ša ra a az zi it`
- token-level agreement on this span: 0.00

### Example 7/10 -- `KBo 30.69`, span_len=4, DISAGREE
- context before: `ŠA ḪUR SAG ta a pa la <LINE>`
- **editor's restoration**: `D ma li ia`
- **model's proposal**: `D an an an`
- context after: `an ŠA D IMIN IMIN BI D KAL`
- token-level agreement on this span: 0.25

### Example 8/10 -- `KUB 4.46+`, span_len=7, DISAGREE
- context before: `si TÚG sú NU DADAG <LINE> ZA <LINE>`
- **editor's restoration**: `i na ITU AB BA È ZA`
- **model's proposal**: `i ŠÈ šu šu šu šu a`
- context after: `ši gu <LINE> i na ITU ŠU NUMUN`
- token-level agreement on this span: 0.14

### Example 9/10 -- `KBo 22.195+::2`, span_len=2, DISAGREE
- context before: `zi ŠA LÚ MEŠ UR GI₇ DUGUD NÍG`
- **editor's restoration**: `BA ŠU`
- **model's proposal**: `BÀR MUNUS`
- context after: `LUGAL un pu nu uš ša an zi`
- token-level agreement on this span: 0.00

### Example 10/10 -- `KBo 52.15b`, span_len=5, DISAGREE
- context before: `MEŠ ta pa ri ia li it <LINE>`
- **editor's restoration**: `… QA DU LÚ MEŠ`
- **model's proposal**: `x ta ta ta at`
- context after: `ta pa ri ia li it <PAR> <GAP>`
- token-level agreement on this span: 0.00
