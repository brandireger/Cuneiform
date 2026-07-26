# Phase 4 Gate 0 language audit

**GATE 0 DECISION EVIDENCE — not a model result.**

XML payloads were opened only after a unique filename stem mapped to frozen train, dev, or discovery. Test, unmatched, ambiguous, and duplicate-stem payloads remained unopened.

- Allowed payloads opened: **20,743**.
- Protected test payloads opened: **0**.
- Parse errors among allowed payloads: **1**.
- Explicit `w@lg` values: **9,409**.
- Valid word overrides differing from the line default: **7,100** across **736** documents.
- Explicit empty `w@lg` values: **21**.

## Primary-source semantics

The [official HPM guide](https://www.hethport.uni-wuerzburg.de/HPM/hpm.php?p=hpmguide) states that the paragraph style identifies the language of the whole line, while character language styles mark inserted words or incomplete quotations in another language. This supports word override, otherwise line inheritance. Document `xml:lang` is not needed as fallback.

## Largest valid word overrides

| line | word | count |
|---|---|---:|
| `Hit` | `Hur` | 5,670 |
| `Hit` | `Hat` | 271 |
| `Hit` | `Luw` | 255 |
| `Sum` | `Akk` | 199 |
| `Hit` | `Akk` | 187 |
| `Hur` | `Hit` | 138 |
| `Akk` | `Hit` | 117 |
| `Hit` | `Sum` | 95 |
| `Akk` | `Sum` | 87 |
| `Luw` | `Hit` | 56 |
| `<UNRESOLVED>` | `Hur` | 6 |
| `Sum` | `Hit` | 5 |

## Gate 0 implications

- Valid explicit word language overrides the line default.
- Absence of `w@lg` inherits the valid line language.
- Explicit empty `w@lg` is preserved as an anomaly and may inherit a valid line only with `RESOLVED_WITH_SOURCE_ANOMALY` status.
- Malformed/unrecognized explicit word tags remain unresolved.
- Document language is retained for provenance but is not a fallback.
- Language annotations are `EDITORIAL_TRANSCRIPTION` evidence.