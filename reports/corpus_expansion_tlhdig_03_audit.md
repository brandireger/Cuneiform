# TLHdig 0.3 corpus expansion audit

**[AUDIT — not a corpus migration or citable model result]**

## Cleanroom boundary

Candidate checksum: PASS. Payload reads were limited to unique filename stems mapped to frozen train/dev/discovery. 714 candidate test entries and 2,464 unmatched candidate entries were not opened. Frozen splits, the 0.2 archive, and all training artifacts were unchanged.

## Central-directory findings

| | TLHdig 0.2 | TLHdig 0.3 |
|---|---:|---:|
| non-junk XML entries | 21,868 | 23,937 |
| unique filename stems | 21,850 | 23,795 |
| CTH folders | 662 | 663 |
| duplicate filename stems | 18 | 132 |

Shared stems: 21,658; candidate-only stems: 2,137; baseline-only stems: 192. Candidate-only means unmatched by filename, not yet proven new.

## Split-gated non-test delta

Among 20,479 safely comparable documents, 20,052 (97.91%) changed bytes and 427 were identical. Parse errors changed from 1 to 12; parsed `<lb>` counts changed from 359,251 to 350,888.

On common allowed stems, candidate XML introduced 11 parse errors, resolved 0, and retained 1. The 97.91% raw-byte change rate is a change detector, not evidence that 97.91% of transliterated content changed.

Introduced parse-error stems: `AT 454, IBoT 2.85+, KBo 18.142, KBo 18.192, KBo 31.190, KBo 39.105, KBo 47.71, KBo 52.74, KBo 66.131, KBo 71.216, KUB 52.25`. Persistent parse-error stems: `KUB 12.24`.

Schema additions: tags `CTH-Nr, ann, aufheb, aufloes, kor1kf, neu, uebern`; attributes `ann@date, ann@editor, ann@part, annot@comment, annot@part, aufheb@date, aufheb@editor, aufheb@frgm, aufheb@part, aufloes@date, aufloes@editor, aufloes@frgm, aufloes@part, cth@part, format@part, join@part, kolfot2@comment, kolfot@part, kolon@comment, kolon@part, koltaf@frgm, koltaf@part, kor1kf@date, kor1kf@editor, kor1kf@part, kor2@part, kor@comment, kor@part, korof@part, trlst@part, uebern@date, uebern@editor, uebern@part, uebern@src, val@part`. Tags absent from the comparable candidate set: `KolonNr, TextPubl`.

## Recommendation

**OPEN A CONTROLLED 0.3 MIGRATION-DESIGN PASS** — The filename inventory contains a material candidate addition, but non-test parse errors and duplicate stems increased. Do not replace 0.2 yet: first resolve quarantined identifiers, diagnose the parser regressions, define new splits, and run a versioned parser rebuild.

Cost: 20.9s compute; budget ≤4h. No scoring or training occurred, so a content-sensitivity tracer was not applicable.

**Falsifier:** this migration recommendation would be wrong if identifier resolution shows that most quarantined candidate-only entries duplicate protected or existing material, or if a full non-test parser rebuild exposes semantic schema incompatibilities not visible in this inventory.

Corpus sources: Müller, Prechel, Rieken & Schwemer, TLHdig Beta 0.2.0, DOI 10.5281/zenodo.15459134 (CC BY 4.0); TLHdig Beta 0.3, DOI 10.5281/zenodo.20328284 (CC BY 4.0).
