# Phase 4 P4-E — unresolved evidence extraction

**Contract:** `unresolved_evidence_contract` v1.1.0. Every record is `NOT_CORPUS_TRUTH`.

- Occurrences: **238,745** (238,736 contiguous token runs plus 9 Gate 1 source anomalies).
- Protected-test occurrences: **0** (the Gate 2 universe contains none and the contract re-checks each split).
- Occurrences with an unresolved effective language: **66**.
- Logical SHA-256 (content, excluding run timestamp): `fd387b97a9aeb1cb9b7e9a89f3b20f8b015ef50af524695cec6567b64b191f47`.

## Occurrences by category

| category | occurrences |
|---|---:|
| `ILLEGIBLE_SIGN` | 131,322 |
| `PARTIALLY_PRESERVED_READING` | 103,097 |
| `UNCERTAIN_TRANSCRIPTION` | 403 |
| `RARE_FORM` | 1,726 |
| `LEXICAL_UNKNOWN` | 0 |
| `TOKENIZER_OOV` | 4,224 |
| `UNRECOGNIZED_LANGUAGE_TAG` | 22 |
| `EMPTY_LANGUAGE_TAG` | 44 |
| `MISSING_LANGUAGE_TAG` | 16 |
| `MALFORMED_LANGUAGE_TAG` | 22 |
| `SYMBOL_OR_ENCODING_ANOMALY` | 1 |
| `PARSER_ANOMALY` | 9 |

An occurrence may carry several categories, so the column sums to more than the occurrence count. Categories are never merged: a `TOKENIZER_OOV` is an engineering vocabulary miss and is not evidence that the word is unknown to Hittitology.

## By split

| split | occurrences |
|---|---:|
| `dev` | 13,846 |
| `discovery` | 126,437 |
| `train` | 98,462 |

Dev-split occurrences are extractable but annotations on them may not influence a dev metric that claims to be held out.

## By effective language

| language | occurrences |
|---|---:|
| `Hit` | 210,615 |
| `Hur` | 11,339 |
| `Akk` | 8,816 |
| `Hat` | 4,764 |
| `Luw` | 1,769 |
| `Sum` | 1,000 |
| `Pal` | 367 |
| `<UNRESOLVED>` | 66 |

## Deliberately not populated

- **`LEXICAL_UNKNOWN`** — the contract requires a governed detector and forbids inferring the category from a tokenizer OOV. No such detector has been ratified, so the category is empty. Approximating it with a frequency threshold would assert a claim about Hittite lexis that this pipeline cannot support. **Requires an Ixca decision** before it can be filled.
- **`restored` spans** — editorial restorations are scholarly hypotheses typed `EDITORIAL_RESTORATION`, not unresolved evidence. Filing 765,291 of them here would reframe editorial proposals as open questions.
- **`cu`** — never read; it renders restored content as real glyphs and is not cleanroom-safe even as a display field.

## Boundaries

- Expert annotations are append-only, hash-bound, and quarantined; `EXPERT_SUPPORTED` means one recorded expert supports a hypothesis, not corpus truth or consensus.
- No annotation enters training without a separate adjudication and export gate.
- Similarity values carry `scores_are_probabilities: false`.

Artifacts: `Phase4\phase4_out\unresolved_occurrences.parquet` (gitignored, regenerable), `Phase4\phase4_out\unresolved_extraction_manifest.json`.
