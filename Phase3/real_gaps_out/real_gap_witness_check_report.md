# Real-gap witness coverage + editor check (step 2, cross-line anchor extension)

Scope: top 5 CTHs by gap count from step 1 -- CTH [628, 627, 701, 577, 647], 867 documents. Cross-line anchor search capped at **3 lines per side** (Ixca's call, after seeing the uncapped distribution ran as far as 39 lines for a small tail -- capped rather than kept, since "anchor context" stops being meaningfully nearby well before that).

- **25,559** real gaps in scope; **19,339** now have a full 2-sign attested anchor on both sides -- up from 1,960 (7.7%) with no cross-line extension at all.
  - **1,960** same-line (the original, already-calibrated category).
  - **17,379** required crossing into an adjacent line this same witness preserves -- a methodologically distinct category, reported separately below rather than pooled, since the existing calibration was computed same-line only.

### How many lines were crossed to find an anchor

| lines crossed | count |
|---|---|
| 1 | 13,807 |
| 2 | 1,831 |
| 3 | 935 |
| 4 | 511 |
| 5 | 211 |
| 6 | 84 |

### Is this damage interior, or is the whole fragment edge material?

Cross-referenced against `edges.parquet`'s own edge-loss flags -- distinguishes "this witness retains at least one original tablet surface, so the damage is genuinely interior" from "this witness is a chip with every side already lost to breakage," which matters for a different question entirely: whether a heavily-damaged fragment is join-training material (Task B -- concerned with the fragment's own physical edges) versus a missing-text / composition-binning question (Task A and this project's core objective -- concerned with what survives inside).

- **17,684** real gaps sit in fragments with no preserved original edge at all -- every side already a break. For these, interior damage and join-candidacy are not really separable questions: the whole piece is edge material.
- **7,875** real gaps sit in fragments that retain at least one original surface -- for these, the damage is genuinely interior and belongs to the missing-text objective, not the join-training one.
- **0** could not be matched to an edges.parquet row (not resolved as a fault -- reported, not silently dropped).

None of this promotes the editor's restoration to truth, nor witness agreement to truth -- it reports whether independent artifact evidence corroborates, contradicts, or says nothing about each editorial hypothesis.

## Same-line anchors (1,960 gaps)

- **839** (42.8%) have at least one independent-witness proposal; **1,121** have none.
- Of **1,640** `restored` spans checkable here: **568** (34.6%) match independent witnesses, **208** (12.7%) disagree with them, **864** (52.7%) have no independent evidence either way.

Sample matches:
- `AT 454`: editor reading `pát` matches 1 independent proposal(s).
- `AT 454`: editor reading `TUM` matches 2 independent proposal(s).
- `AT 454`: editor reading `ši ia` matches 3 independent proposal(s).
- `Bo 5601+`: editor reading `URU` matches 2 independent proposal(s).
- `Bo 5601+`: editor reading `NIN` matches 1 independent proposal(s).

Sample mismatches:
- `AT 454`: editor reading `ar`, 6 independent proposal(s), none matching -- e.g. ku uš ú et na aš <NUM> an ar; ku uš ú e er na at kán pé ar; ku uš ú et aš <NUM> an ar; ku uš ú et na aš <NUM> ar; (empty).
- `AT 454`: editor reading `it ar`, 8 independent proposal(s), none matching -- e.g. e at <NUM> an ar; et na aš <NUM> 〈an〉 ar; <NUM> an ar; e er na at <NUM> an ar; et na aš kán pé an ar.
- `AT 454`: editor reading `nu`, 1 independent proposal(s), none matching -- e.g. TUKU TUKU u an te eš nu.
- `Bo 5601+`: editor reading `na at`, 1 independent proposal(s), none matching -- e.g. ku ra an da a i na at.
- `Bo 5601+`: editor reading `ḫu te il`, 1 independent proposal(s), none matching -- e.g. ḫu te el.

## Cross-line anchors (17,379 gaps)

- **3,540** (20.4%) have at least one independent-witness proposal; **13,839** have none.
- Of **13,618** `restored` spans checkable here: **784** (5.8%) match independent witnesses, **2,208** (16.2%) disagree with them, **10,626** (78.0%) have no independent evidence either way.

Sample matches:
- `ABoT 2.114+`: editor reading `UP NI` matches 4 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.140`: editor reading `ḫi` matches 1 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.140`: editor reading `a ri` matches 1 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.140`: editor reading `da a i` matches 1 independent proposal(s) (1 line(s) crossed for anchor context).
- `ABoT 2.148`: editor reading `DUMU` matches 2 independent proposal(s) (1 line(s) crossed for anchor context).

Sample mismatches:
- `ABoT 2.114+`: editor reading `le el lu u ri`, 1 independent proposal(s), none matching -- e.g. IŠTAR (1 line(s) crossed).
- `ABoT 2.114+`: editor reading `GAL KÙ BABBAR A NA`, 3 independent proposal(s), none matching -- e.g. <NUM>; (empty); UP NU ŠE GIŠ Ì 〈〈Ì〉〉 (3 line(s) crossed).
- `ABoT 2.114+`: editor reading `A NA D ku šu ur ni`, 3 independent proposal(s), none matching -- e.g. <NUM>; (empty); UP NU ŠE GIŠ Ì 〈〈Ì〉〉 (3 line(s) crossed).
- `ABoT 2.114+`: editor reading `GAL KÙ BABBAR A NA`, 3 independent proposal(s), none matching -- e.g. <NUM>; (empty); UP NU ŠE GIŠ Ì 〈〈Ì〉〉 (4 line(s) crossed).
- `ABoT 2.114+`: editor reading `GAL KÙ BABBAR A NA D da šu un na an zi`, 2 independent proposal(s), none matching -- e.g. SA₂₀ A TI; GAL KÙ BABBAR (2 line(s) crossed).

## What this does not yet tell us

Whether a witness-proposed alternative is MORE likely correct than the editor's own restoration -- that needs the calibration-application layer (step 3), and even then only as a historical group audit rate, never an instance-level probability. Cross-line anchors specifically have never been calibrated at all -- their coverage/agreement numbers above are descriptive only; using them in a scored product would need their own calibration pass, not a borrowed same-line rate.