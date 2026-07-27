# Phase 4 P4-D — language-aware APIs

**Status:** implemented 2026-07-26. No metric artifact was republished; no
protected-test payload was opened; the frozen D14 checkpoint is untouched.

## What P4-D changed

Gates 0–2 produced ratified language rules and a word-aware token dataset.
Nothing downstream consumed them. The only language filtering in active code
was `lib/line_lang_lookup.py` — line granularity, Hittite-or-nothing, passed
as an **optional** keyword argument (`line_lang_lookup=None`). Every call site
supplied it by convention, not by contract, so omitting it silently restored
language-blind behavior.

P4-D replaces that convention with a required, validated scope object.

### New modules

- `lib/language_scope.py` — `LanguageScope`, a frozen value object validated
  once at construction through the ratified `validate_language_scope()`.
  `require_language_scope()` refuses `None`, a bare scope name, `"auto"`,
  `"default"`, and `"language_blind"` at every ingress.
  `manifest_entry()` is the single serialization point for the charter's
  run-manifest requirement.
- `lib/language_lookup_v2.py` — `EffectiveLanguageIndex`, the word-aware
  reader over `Phase4/phase4_out/multilingual_tokens_v2.parquet`. Returns a
  per-line `LineDecision` carrying `in_scope`, a named `reason`, the resolved
  language set, and lexical/unresolved token counts. Decisions are counted by
  reason so a coverage change can be attributed rather than guessed at.

### Migrated call sites

`render_fragments()` — the shared anchor-index construction used by all
active P2-E and real-gap scripts — now takes required `language_scope` and
`language_index` arguments. All eight call sites were updated to the ratified
`HITTITE_ONLY` projection via `llookup.hittite_only_projection()`:
`p2e_witness_recoverability`, `p2e2`, `p2e3`, `p2e4`, `p2e5`, `p2e6`,
`real_gap_witness_check`, `real_gap_multisign_calibration`.

The **query side** of the real-gap path is now language-resolved too. This
was the gap named in CLAUDE.md: `render_fragments` governed which witness
lines could *answer*, but every line in the slice could still *ask*, so a
non-Hittite gap sat in the same denominator as a Hittite one and simply found
no coverage. `real_gap_witness_check.prepare_scope()` and
`real_gap_multisign_calibration.prepare_multisign_scope()` now admit a gap
only under the same explicit scope that governs the witnesses, and record
`gaps_excluded_by_language` and `query_language_counts`.

`real_gap_calibration.py` inherits this through `rgw.prepare_scope()`.

### Two fail-closed properties

**Positional safety.** The Gate 2 dataset is keyed on an exact
`(doc_id, line_index_in_doc, word_pos)` identity, verified unique and
contiguous from 0. The historical decomposed cache that active scripts render
from is **not**: it carries **9,940 rows under duplicated keys across 28
documents** — the archive-stem conflation recorded in the Gate 2 handoff, here
quantified for the first time. Rather than trusting a doc-id blocklist, every
lookup compares the caller's own token count for the line against the Gate 2
count and refuses the line on any mismatch.

**Unresolved is never Hittite.** A line with any unresolved lexical token is
excluded from every language-restricted scope.

### Mixed-line policy

A line whose lexical tokens do not all resolve to the scope's language is
dropped **whole** (`MIXED_LINE_POLICIES = {"EXCLUDE_LINE"}`). Splicing out the
offending words would manufacture token adjacencies that never existed on the
tablet — a bigram anchor spanning a removed Hurrian word is a false anchor,
and the anchor index is exactly what consumes this rendering. Excluding the
line preserves the "anchors never span a language boundary" property the
line-granularity filter had implicitly. A segment-splitting policy is a
coherent future option but changes the per-line list shape that
`line_position_in_fragment` numbering depends on, so it is deliberately not
offered as a half-wired alternative.

## Measured delta (not published)

Probe over the real-gap witness-check slice (top-5 CTHs by gap count:
628, 627, 701, 577, 647; 867 documents), comparing the shipped
line-granularity filter (v1) against the P4-D word-aware projection (v2).

### Witness-index side, per line

| v1 admits | v2 admits | reason | lines |
|---|---|---|---:|
| yes | yes | — | 24,207 |
| no | no | out-of-scope language | 1,095 |
| **yes** | **no** | **mixed-language line** | **846** |
| yes | no | line absent from Gate 2 dataset | 583 |
| yes | no | out-of-scope language | 86 |
| no | no | mixed-language line | 43 |
| no | no | line absent from Gate 2 dataset | 7 |
| no | yes | — | 1 |
| no | no | unresolved lexical language | 1 |

Raw tokens admitted to the witness index: **248,998 → 233,883 (−15,115,
−6.1%)**.

The 846 + 86 = **932 lines that the shipped filter admitted and the word-aware
projection refuses** are the concrete cost of line-granularity: `Hit`-tagged
lines whose explicit `w@lg` words are Hurrian or another language, feeding
non-Hittite content into a "Hittite-only" anchor index.

### Query side

| quantity | value |
|---|---:|
| gap runs, pre-P4-D population (unfiltered) | 25,559 |
| gap runs, P4-D `HITTITE_ONLY` population | 23,124 (90.47%) |
| excluded: out-of-scope language | 1,216 |
| excluded: mixed-language line | 943 |
| excluded: line absent from Gate 2 dataset | 275 |
| excluded: unresolved lexical language | 1 |

**~9.5% of the real-gap denominator was non-Hittite or unresolved queries.**
Every admitted query resolves to `Hit`.

These numbers are a probe, not a republished result. `Phase3/real_gaps_out/`
and `Phase2/phase2_out/` were **not** rerun — that is P4-G work, gated behind
the charter's "only after the new dataset/model pass their gates".

## Investigated and closed: the Gate 2 document-coverage boundary

The `LINE_NOT_IN_LANGUAGE_DATASET` rows above are not all empty. Of 590 such
lines in the slice, 331 are empty in the cache (no content either way) but
**259 carry real content**, concentrated in `Merzifon I`, `Bo 5601+`,
`KBo 30.20`, `CHDS 5.173` and others.

Corpus-wide: the historical decomposed cache holds 21,577 documents; the Gate
2 dataset holds 20,711. The 866-document difference is 754 test plus **112
non-test documents** present in the active pipeline's token cache with no Gate
2 language coverage at all.

This was investigated on 2026-07-26 rather than carried as an open risk into
P4-E. **Every one of the 112 is explained by a stated Gate 1 admission rule.
It is not a defect.**

| cause | docs |
|---|---:|
| `QUARANTINE_DUPLICATE_STEM` — the archive-stem conflation; Gate 1 refused to choose between two payloads under one stem | 18 |
| Not an archive filename stem at all — identifier-form mismatch (below) | 93 |
| `KUB 12.24` — the single `ALLOWED_TRAIN` XML parse error (`mismatched tag: line 45, column 2`) | 1 |

Gate 1's own gate counts reconcile exactly against the pinned corpus:
6,014 train + 745 dev + 13,984 discovery (= 20,743 allowed, less 1 parse error
= 20,742 parsed) + 744 protected test + 36 duplicate-stem + 345 unmatched
= **21,868**, matching the corpus census in CLAUDE.md.

### The identifier-form mismatch (93 documents)

Gate 1 keys strictly on the **archive filename stem** and asserts that the
stem equals the document's `docID`. The historical decomposed cache keys on a
different identifier form. For 93 documents these disagree — `1136/u`,
`2030/g`, `544/f`, `616_KUB 44.2+`, `677/u`, `849/u` and similar — and 26 of
them contain a `/`, which a filename stem cannot carry at all. Those
documents' real archive stems are absent from the frozen split map and were
therefore classified `QUARANTINE_UNMATCHED`.

This is the same canonical-identifier-group problem already flagged as a
prerequisite for any corpus migration in
`reports/corpus_expansion_tlhdig_03_migration_design.md`. It is now confirmed
to also bound Phase 4's document universe, which was not previously recorded.

### Consequences

1. **P4-D's behavior is correct as shipped.** Those lines are refused,
   counted, and named rather than silently language-defaulted.
2. **`Phase4/phase4_out/gate2_token_dataset_report.md` states 20,711
   documents without reconciling that against the active cache's 21,577.**
   The boundary is real and principled but was unreported; it is recorded
   here.
3. **These 112 documents are legitimate P4-E workbench intake**, not an
   obstacle to it. `PARSER_ANOMALY` already exists as a workbench category
   for exactly this material, and the charter principle that unidentified
   content is retained with context rather than discarded applies directly.
   The workbench should extract over the Gate 2 universe and record these 112
   as identifier/parser anomalies.

## Evidence packets — contract 1.1.0

`lib/expert_decision_contract.py` gains a **required** `language` block:

```
language_scope, query_language, query_language_status,
mixed_language_query_line, source_languages,
cross_language_source_languages, cross_language_assistance_enabled,
language_rule_id, language_evidence_class
```

Enforced invariants:

- only `RESOLVED` may carry a non-null `query_language`; every other status
  **obliges** the packet to carry a `LANGUAGE_*` limitation, so a display can
  never present a language-silent packet as though language had been
  established;
- cross-language evidence may not appear while the cross-language assistance
  channel is disabled;
- the query language may not appear in the cross-language channel — the two
  channels stay separable;
- `language_evidence_class` is pinned to `EDITORIAL_TRANSCRIPTION` (Gate 0
  decision 7); a packet cannot upgrade language annotations to observed
  artifact evidence.

`configs/expert_decision_contract.schema.json` was updated to match and the
version constants bumped to 1.1.0.

### Why the demo packets say `UNRESOLVED_IN_SOURCE_RUN`

The exported P2-E4/P2-E6 packets were produced under the pre-Phase-4
line-granularity filter, so their candidate evidence was assembled without
word-aware language resolution. Resolving the query language *now*, from the
Gate 2 dataset, while the displayed evidence still came from a language-blind
index, would be a half-truth. The honest record is `UNRESOLVED_IN_SOURCE_RUN`,
which forces the mandatory `LANGUAGE_UNRESOLVED_IN_SOURCE_RUN` limitation into
the expert UI. Resolved query languages become available once P2-E4/P2-E6 are
rerun under the P4-D projection.

`demo/taksan_missing_text_prototype.html` gains a Language panel showing the
scope, the query language or an explicit "not established" badge, the
mixed-language flag, and the cross-language channel state.
`Phase3/demo_out/` was regenerated so the shipped demo validates under 1.1.0;
this is a derived interface artifact, not a metric republish.

## Named remaining gap: the tokenizer vocabulary path

`lib/hittite_tokenizer.py` (`build_structured_sequence_attested`,
`build_vocab`) still takes the optional line-granularity `line_lang_lookup`,
as does its unadopted consumer `scripts/rebuild_tokenizer_hittite_only.py`.
This was **not** migrated, deliberately: that path feeds the frozen D14
vocabulary, and changing it risks the vocab-size mismatch that already broke
`runs/pretrain_base/checkpoint.pt` once (see `specs/LINE_LANG_MIGRATION.md`).
Vocabulary rebuilding is Gate 3 territory.

## Validation

- 132 unit tests pass (107 at handoff; +25 new across
  `tests/test_language_scope.py` and `tests/test_expert_decision_contract.py`).
- Ruff passes for `lib`, `scripts`, `tests`, `demo`.
- `real_gap_witness_check.prepare_scope()` runs end-to-end on the real slice.
- `demo/dm1_missing_text_export.py` regenerates and validates 28 packets.

New tests pin each way the old defect could return: permissive scope names,
bare-string scopes, query-relative scopes without a query language, word-level
overrides excluding a `Hit`-tagged line, unresolved language never guessed in,
structural tokens excluded from lexical evidence, token-count mismatch
refusing a conflated line, and the packet language invariants.

## Open decisions for Ixca

1. **Rerun scope.** P4-D changes what the active scripts compute but nothing
   was republished, so committed reports in `Phase3/real_gaps_out/` and
   `Phase2/phase2_out/` no longer match the code that produced them. Rerunning
   is P4-G work. Interim mitigation applied 2026-07-26: each affected report
   carries a header note stating it predates P4-D and naming the measured
   direction of the change. The decision to rerun remains open.
2. ~~The uncovered non-test documents~~ — **investigated and closed**, above.
   All 112 are explained by stated Gate 1 admission rules; they become P4-E
   workbench intake rather than a blocker.
3. **Mixed-line policy.** `EXCLUDE_LINE` costs 846 otherwise-usable lines in
   the measured slice. A segment-splitting policy would recover the Hittite
   runs on those lines at the cost of changing the per-line rendering shape.
   Not a P4-E blocker: the workbench should extract under
   `MULTILINGUAL_CONDITIONED`, where mixed lines are admitted with language
   identity attached, per the "code-switched contexts are a named stratum"
   rule in `specs/LANGUAGE_LAYERS_V2.md`.
