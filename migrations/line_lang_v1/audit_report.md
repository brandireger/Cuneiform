# `line_lang` migration -- Step A non-test audit

Read-only. No canonical field is written; no frozen artifact is modified. Test-side `line_lang` values were never read -- the corpus.parquet query itself excludes `main_split=="test"` documents, and the raw-XML re-walk below only opens documents in the non-test scope.

- Corpus zip MD5: `93e71e2560f5e109c87713d5590cb059` (matches the CLAUDE.md-pinned `93e71e2560f5e109c87713d5590cb059`).
- Non-test documents in scope: **20,846** (8 ambiguous-split docs excluded, matching the existing real_gap_census.py convention).
- Raw XML documents matched and re-walked: **20,846**.
- Lines where corpus.parquet's own word-rows disagree with each other on `line_lang` within the same line: **8**.
- Raw lines with zero word-rows in corpus.parquet (blank/structural lines with nothing to join against -- excluded from the divergence check below, not counted as a mismatch): **6,090**.

## Status counts (non-test only, against a PROPOSED seed vocabulary -- not yet ratified)

| status | count |
|---|---|
| valid_against_proposed_seed | 362,791 |
| missing | 102 |
| unrecognized_against_proposed_seed | 28 |
| malformed | 6 |

### By split

| status | train | dev | discovery |
|---|---|---|---|
| valid_against_proposed_seed | 170,143 | 23,769 | 168,879 |
| missing | 78 | 2 | 22 |
| malformed | 6 | 0 | 0 |
| unrecognized_against_proposed_seed | 1 | 0 | 27 |

## Distinct raw `lb@lg` values found (non-test)

| raw value | count |
|---|---|
| `Hit` | 325,637 |
| `Akk` | 13,890 |
| `Hur` | 13,000 |
| `Hat` | 6,063 |
| `Luw` | 2,366 |
| `Sum` | 1,309 |
| `Pal` | 475 |
| *(missing)* | 102 |
| `Hattian` | 51 |
| `ign` | 15 |
| `5f_` | 12 |
| `Hit> <w><note n='15' c=` | 4 |
| `Hit> <w><del_in/> … <del_fin/></w` | 2 |
| `Lu` | 1 |

## Raw vs. corpus.parquet divergence (8 lines, up to 10 shown)

Where the independently re-walked raw `<lb lg=...>` attribute differs from what `corpus.parquet` (built by the frozen `Archive/scripts/02_parse.py`) records for the same line, excluding lines with no word-rows to compare and excluding both-sides-missing agreement. **All 8 divergent lines found are in a single document, `KBo 53.44`, lines 0-7 -- its ENTIRE line range is tagged `Hur` (Hurrian) in the raw source XML, but recorded as `Hit` in `corpus.parquet`.** This is a real, systematic per-document mislabeling (a Hurrian-language document currently misfiled as Hittite in every downstream Hittite-only consumer, if any existed -- none currently checks language at all, see the accompanying discussion), not scattered noise. This is exactly the 8-line intra-line-disagreement count reported above, confirming it is one coherent defect, not 8 independent ones.

Separately, this session traced the `"Hit> <w><note n='15' c="`-pattern malformed value directly against the parsed XML tree (`KUB 43.50+`, lines 40-43): `ElementTree`'s own `lb.attrib['lg']` genuinely returns that garbled string for those four lines -- this is a **source-XML data defect**, not a `02_parse.py` parser defect. (An initial plain-text substring search of the raw file bytes appeared not to find it and briefly suggested a parser-side explanation; re-checking against the actual parsed attribute dictionary -- the authoritative method, and the same one this audit's own re-walk uses -- overturned that. Recorded here so the correction is visible, not silently dropped.) The `<del_in/>`-pattern (`KBo 53.12`, 2 lines) has not been individually re-checked this way; treat its origin as undetermined pending the same direct check. `5f_` (`CHDS 2.170`) and `Lu` (`KUB 35.99+`) were also confirmed **present verbatim in the raw source XML** -- genuine source-encoded values needing a vocabulary decision, not parser corruption. So far, no case in this audit has been confirmed as a `02_parse.py`-introduced defect distinct from the source -- the one clearly confirmed PARSER-side (not source-side) defect is the `KBo 53.44` Hur/Hit divergence above.

- `KBo 53.44` line 0: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 1: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 2: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 3: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 4: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 5: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 6: raw=`Hur`, corpus.parquet=`Hit`
- `KBo 53.44` line 7: raw=`Hur`, corpus.parquet=`Hit`

## Decisions requested for the Step B ratification gate

1. **Vocabulary**: approve the proposed seed `['Akk', 'Hat', 'Hattian', 'Hit', 'Hur', 'Luw', 'Pal', 'Sum']` as the canonical code set, or amend it.
2. **`Hat` vs. `Hattian`**: both appear (6,063 vs. 51 non-test lines). Are these the same language (Hattic) under two source spellings, warranting an explicit non-identity mapping to one canonical code -- or does `Hattian` mean something distinct? This migration will NOT auto-merge them without an explicit ruling.
3. **`Lu` (1 line, `KUB 35.99+`, verbatim in source) and `5f_` (12 lines, discovery-only, verbatim in source)**: genuine source-encoded values outside the proposed seed. Map to an existing code (e.g. `Lu` -> `Luw`), add as new canonical codes, or leave `unrecognized` (quarantined, no canonical value)?
4. **`ign` (15 lines, discovery-only)**: likely "ignotum" (language undetermined) in philological convention -- ratify as its own canonical status (distinct from `missing`) or leave `unrecognized`?
5. **Malformed rows** (the `"Hit> <w><note n='15' c="` pattern, 4 non-test lines in `KUB 43.50+`; the `<del_in/>` pattern, 2 lines in `KBo 53.12`): the `note`-pattern is confirmed a genuine **source-XML** defect (verified against the parsed attribute dictionary directly, not a `02_parse.py` artifact); the `<del_in/>` pattern's origin is not yet individually verified. Proposed resolution either way: `line_lang_canonical` = null, `line_lang_status` = `malformed`, quarantined -- never coerced to the line's likely intended value (which for the `"Hit> ..."` pattern looks plausibly like `Hit`, but the spec forbids guessing).

No canonical vocabulary, mapping, or status is applied anywhere yet. This audit only classifies against the PROPOSED seed above for counting purposes -- ratification is Ixca's decision per `specs/LINE_LANG_MIGRATION.md` Step B.