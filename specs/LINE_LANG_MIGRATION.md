# `line_lang` governed migration proposal

- **Status:** RATIFIED AND IMPLEMENTED (2026-07-25). Steps A-D below are
  complete; see `migrations/line_lang_v1/` (audit, rebuild, and
  verification reports) and `scripts/line_lang_audit.py` /
  `scripts/line_lang_rebuild.py`. Ratified decisions, recorded here for
  the historical record (the original proposal text below is otherwise
  unchanged, including its still-open "Deferred decisions"):
  - **Canonical vocabulary (7 codes):** `Hit, Akk, Sum, Hat, Hur, Luw, Pal`.
  - **Ratified non-identity mapping:** `Hattian -> Hat` (same language,
    two source spellings).
  - **Quarantined as `unrecognized`** (not guessed at, revisit with more
    context later): `Lu`, `5f_`, `ign`.
  - **Quarantined as `malformed`**: XML-markup-like raw values (one
    confirmed source-XML defect, `KUB 43.50+` lines 40-43; one
    unverified-origin case, `KBo 53.12`).
  - Propagated into a shared lookup (`lib/line_lang_lookup.py`) and
    wired into `hittite_tokenizer.py` and
    `p2e_witness_recoverability.render_fragments` (the anchor-index/
    witness-matching layer) as an opt-in filter, now the DEFAULT for
    every P2-E script and the real-gap pipeline. **The tokenizer vocab
    itself was rebuilt once then REVERTED** — it broke the pretrained
    `runs/pretrain_base/checkpoint.pt` (vocab-size-mismatched embedding
    matrix); retraining is a multi-hour job, out of scope for this
    integration. `configs/tokenizer.json` remains the original Phase 1,
    language-blind vocab; only the anchor-index/witness-matching layer
    is Hittite-only-filtered. See git log 2026-07-25 for the full
    sequence and every rerun's before/after numbers.
  - **Phase 4 successor scope:** this migration governs `lb@lg` only.
    The Phase 1 inventory also records 10,846 `w@lg` attributes, so v1
    is not an effective word-aware language layer. Do not extend v1 in
    place or proceed directly to the deferred Hittite-only retraining.
    `PHASE4_CHARTER.md` and `specs/LANGUAGE_LAYERS_V2.md` now govern the
    document/line/word audit, v2 dataset, and retraining gates.
- **Scope:** derived-data repair only; no model, probe, or research result
- **Affected field:** `Phase1_pipeline/p2_out/corpus.parquet::line_lang`
- **Evidence class:** `EDITORIAL_TRANSCRIPTION` (resolved by Phase 4 Gate 0
  on 2026-07-25; language labels are editorial philological assignments)

## Decision requested

Approve a versioned, deterministic migration that validates the raw AOxml
`<lb lg>` value, preserves that value verbatim, and adds an explicit canonical
language field plus a validation status. The migration must not overwrite the
frozen Phase 1 parser, frozen P2 artifacts, split assignments, or historical
reports.

This proposal does **not** ratify a language-code vocabulary, reinterpret a
source value, or authorize implementation. Those decisions follow the
non-test audit described below.

## Why a migration is needed

The evidence-registry review found values in the derived `line_lang` column
that contain XML fragments rather than a language code. The historical parser
in `Archive/scripts/02_parse.py` copies `lb@lg` directly into each word row
without validating its shape or membership in an accepted vocabulary. The
observed values therefore cannot safely be treated as canonical language
labels.

This is a data-lineage problem, not evidence that the original XML is
necessarily invalid. The first audit must distinguish at least:

1. a malformed-but-parseable source attribute;
2. a parser-boundary or serialization defect;
3. an unrecognized but legitimate source language code; and
4. a missing language annotation.

No malformed value may be silently trimmed, split, regex-extracted, or mapped
to the nearest familiar code.

## Non-negotiable invariants

- `Archive/` remains immutable.
- Existing `Phase1_pipeline/p2_out/` and `p25_out/` artifacts remain byte-for-byte unchanged.
- Frozen `main_split` and `site_split` assignments remain unchanged.
- No `cu` value or `cu`-derived feature is read as semantic evidence.
- No model input, score, label, or candidate list is produced.
- Rule design and example inspection use the declared non-test universe only:
  `train`, `dev`, and `discovery`.
- Test-side values are never manually inspected and never influence the
  vocabulary, mapping rules, thresholds, or acceptance criteria.
- Any later full-corpus transform applies the ratified deterministic rules to
  test rows without revealing their content during development.
- Unknown or prohibited fields fail closed under
  `configs/evidence_registry.yaml` and the selected evidence policy.

## Proposed output contract

Write new artifacts under a versioned directory such as
`migrations/line_lang_v1/`. Do not reuse an existing output path.

The migrated line-level record must retain:

| Field | Meaning |
|---|---|
| `line_lang_raw` | Exact source `lb@lg` string, including malformed content; null only when absent. |
| `line_lang_canonical` | Ratified canonical code; null unless an exact value or explicitly approved mapping applies. |
| `line_lang_status` | One of `valid`, `missing`, `malformed`, or `unrecognized`. |
| `line_lang_rule_id` | Stable identifier for the exact validation/mapping rule used. |

The original derived `line_lang` value may be carried for comparison, but it
must not be relabeled as canonical. Downstream consumers must request
`line_lang_canonical` explicitly after it is registered and approved.

### Status semantics

- `valid`: the raw value exactly matches a ratified code.
- `missing`: the `lg` attribute is absent or empty.
- `malformed`: the raw value violates the ratified lexical shape, contains
  markup-like content, or cannot be represented as one code.
- `unrecognized`: the raw value is lexically well formed but is not in the
  ratified vocabulary.

Malformed and unrecognized values are quarantined for reporting. They are not
coerced into `valid`.

## Migration sequence

### A. Non-test audit

1. Verify hashes for the pinned TLHdig zip, frozen split artifact, current
   corpus parquet, parser source, registry, and policy configuration.
2. Join source documents to the frozen split assignment using identifiers
   only; exclude all `main_split == "test"` rows before inspecting `lg`.
3. Compare the exact raw `lb@lg` value with the current derived `line_lang`
   value and identify where corruption first appears.
4. Produce aggregate counts and a bounded sample for each proposed status.
5. Propose a vocabulary from documented AOxml/TLHdig usage and the declared
   full non-test universe. Human review must approve every canonical code and
   every non-identity mapping.
6. Emit a feature-use manifest even though this is an audit rather than a
   model run. Requested semantic content is limited to `line_lang` /
   `lb@lg`; identifiers and split labels are control-flow fields.

### B. Ratification gate

Ixca reviews:

- the diagnosed corruption boundary;
- the proposed canonical vocabulary;
- every mapping that is not exact identity;
- aggregate non-test counts by status and split; and
- the final output directory and artifact names.

Implementation stops here unless the proposal is explicitly accepted.

### C. Versioned deterministic rebuild

After ratification, run one implementation over the pinned corpus. The
implementation may process all splits mechanically, but it must not print,
sample, rank, or otherwise expose test-side language values. It writes only
to the new versioned directory and records its lineage.

### D. Verification before activation

Compare the new and frozen datasets using identifiers and aggregate invariants.
Do not activate the canonical field for downstream work until every acceptance
check passes and the evidence registry is updated in a separate reviewed
change.

## Required manifest

The migration manifest must record:

- corpus name, version, DOI, zip filename, and MD5;
- git commit and dirty-worktree status;
- script, config, registry, policy, split, input, and output hashes;
- declared statistics universe and excluded splits;
- requested and observed fields with evidence classes;
- prohibited-field checks;
- canonical vocabulary and stable rule identifiers;
- counts by `line_lang_status` and non-test split;
- row/document/line counts before and after;
- parse-error counts before and after; and
- deterministic seed, even if no stochastic step is expected.

Public reports must not include raw test-side values or test-derived
vocabulary statistics.

## Acceptance checks

The migration is acceptable only if all checks pass:

1. Frozen source and derived-artifact hashes are unchanged.
2. Document, line, and word-row identities and counts are unchanged except
   where a separately ratified parser defect requires an explicit amendment.
3. `main_split`, `site_split`, bin status, CTH membership, joins, and
   duplicate relations are unchanged.
4. Sign sequences, damage states, edge fields, and restoration flags are
   unchanged.
5. Every migrated row has exactly one allowed `line_lang_status`.
6. `valid` rows use only ratified canonical codes.
7. `malformed` and `unrecognized` rows have null canonical values unless a
   specific human-ratified mapping says otherwise.
8. Test-side rows did not contribute to rule design or audit output.
9. Two clean runs produce byte-identical logical tables and matching hashes.
10. The feature-use manifest passes the evidence-policy validator.

## Rollback

Rollback is selection-based: downstream code continues to consume the frozen
artifact and ignores the versioned migration directory. Because no frozen
file is overwritten, rollback does not require reconstructing or editing
historical data.

## Deferred decisions

- The authoritative language-code vocabulary.
- ~~Whether `line_lang_canonical` remains
  `OBSERVED_DOCUMENT_STRUCTURE` or is reclassified after expert review.~~
  Resolved by Phase 4 Gate 0 as `EDITORIAL_TRANSCRIPTION`.
- Whether the source defect warrants a new active parser implementation.
- Whether any downstream language-stratified result should be rerun. No such
  reported result is currently known.
