# Real-gap witness coverage + editor check (step 2, cross-line anchor extension)

Scope: top 5 CTHs by gap count from step 1 -- CTH [628, 627, 701, 577, 647], 867 documents. Cross-line anchor search capped at **3 lines per side** (Ixca's call, after seeing the uncapped distribution ran as far as 39 lines for a small tail -- capped rather than kept, since "anchor context" stops being meaningfully nearby well before that).

- **23,124** real gaps in scope; **17,240** now have a full 2-sign attested anchor on both sides -- up from 1,960 (7.7%) with no cross-line extension at all.
  - **1,741** same-line (the original, already-calibrated category).
  - **15,499** required crossing into an adjacent line this same witness preserves -- a methodologically distinct category, reported separately below rather than pooled, since the existing calibration was computed same-line only.

### How many lines were crossed to find an anchor

| lines crossed | count |
|---|---|
| 1 | 12,232 |
| 2 | 1,647 |
| 3 | 866 |
| 4 | 481 |
| 5 | 197 |
| 6 | 76 |

### Is this damage interior, or is the whole fragment edge material?

Cross-referenced against `edges.parquet`'s own edge-loss flags -- distinguishes "this witness retains at least one original tablet surface, so the damage is genuinely interior" from "this witness is a chip with every side already lost to breakage," which matters for a different question entirely: whether a heavily-damaged fragment is join-training material (Task B -- concerned with the fragment's own physical edges) versus a missing-text / composition-binning question (Task A and this project's core objective -- concerned with what survives inside).

- **15,965** real gaps sit in fragments with no preserved original edge at all -- every side already a break. For these, interior damage and join-candidacy are not really separable questions: the whole piece is edge material.
- **7,159** real gaps sit in fragments that retain at least one original surface -- for these, the damage is genuinely interior and belongs to the missing-text objective, not the join-training one.
- **0** could not be matched to an edges.parquet row (not resolved as a fault -- reported, not silently dropped).

None of this promotes the editor's restoration to truth, nor witness agreement to truth -- it reports whether independent artifact evidence corroborates, contradicts, or says nothing about each editorial hypothesis.

## Same-line anchors (1,741 gaps)

- **740** (42.5%) have at least one independent-witness proposal; **1,001** have none.
- Of **1,452** `restored` spans checkable here: **504** (34.7%) match independent witnesses, **178** (12.3%) disagree with them, **770** (53.0%) have no independent evidence either way.

Sample matches:
- `AT 454`: editor reading `pát` matches 1 independent proposal(s).
- `AT 454`: editor reading `TUM` matches 2 independent proposal(s).
- `AT 454`: editor reading `ši ia` matches 3 independent proposal(s).
- `Bo 7850`: editor reading `ma aš ša` matches 1 independent proposal(s).
- `CHDS 4.226`: editor reading `pár` matches 2 independent proposal(s).

Sample mismatches:
- `AT 454`: editor reading `ar`, 6 independent proposal(s), none matching -- e.g. ku uš ú et aš <NUM> an ar; ku uš na aš <NUM> an ar; ku uš ú e er na at kán pé ar; ku uš ú et na aš <NUM> ar; ku uš ú et na aš <NUM> an ar.
- `AT 454`: editor reading `it ar`, 8 independent proposal(s), none matching -- e.g. <NUM> an ar; e at <NUM> an ar; et na aš kán pé an ar; et na aš <NUM> an ar; et na aš <NUM> 〈an〉 ar.
- `AT 454`: editor reading `nu`, 1 independent proposal(s), none matching -- e.g. TUKU TUKU u an te eš nu.
- `DAAM 1.56+`: editor reading `UL`, 1 independent proposal(s), none matching -- e.g. A NA DINGIR MEŠ.
- `DAAM 1.56+`: editor reading `iš`, 1 independent proposal(s), none matching -- e.g. iš ŠA.

## Cross-line anchors (15,499 gaps)

- **3,071** (19.8%) have at least one independent-witness proposal; **12,428** have none.
- Of **12,057** `restored` spans checkable here: **666** (5.5%) match independent witnesses, **1,901** (15.8%) disagree with them, **9,490** (78.7%) have no independent evidence either way.

Sample matches:
- `ABoT 2.114+`: editor reading `UP NI` matches 4 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.140`: editor reading `da a i` matches 1 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.148`: editor reading `DUMU` matches 2 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.148`: editor reading `DUMU aš QA TAM` matches 2 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.230`: editor reading `da` matches 23 independent proposal(s) (1 line(s) crossed for anchor context).

Sample mismatches:
- `ABoT 2.114+`: editor reading `le el lu u ri`, 1 independent proposal(s), none matching -- e.g. IŠTAR (1 line(s) crossed).
- `ABoT 2.114+`: editor reading `GAL KÙ BABBAR A NA`, 3 independent proposal(s), none matching -- e.g. <NUM>; (empty); UP NU ŠE GIŠ Ì 〈〈Ì〉〉 (3 line(s) crossed).
- `ABoT 2.114+`: editor reading `A NA D ku šu ur ni`, 3 independent proposal(s), none matching -- e.g. <NUM>; (empty); UP NU ŠE GIŠ Ì 〈〈Ì〉〉 (3 line(s) crossed).
- `ABoT 2.114+`: editor reading `GAL KÙ BABBAR A NA`, 3 independent proposal(s), none matching -- e.g. <NUM>; (empty); UP NU ŠE GIŠ Ì 〈〈Ì〉〉 (4 line(s) crossed).
- `ABoT 2.114+`: editor reading `GAL KÙ BABBAR A NA D da šu un na an zi`, 2 independent proposal(s), none matching -- e.g. GAL KÙ BABBAR; SA₂₀ A TI (2 line(s) crossed).

## What this does not yet tell us

Whether a witness-proposed alternative is MORE likely correct than the editor's own restoration -- that needs the calibration-application layer (step 3), and even then only as a historical group audit rate, never an instance-level probability. Cross-line anchors specifically have never been calibrated at all -- their coverage/agreement numbers above are descriptive only; using them in a scored product would need their own calibration pass, not a borrowed same-line rate.