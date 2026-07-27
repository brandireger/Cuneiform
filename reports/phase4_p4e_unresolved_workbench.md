# Phase 4 P4-E — Unresolved Evidence Workbench

**Status:** implemented 2026-07-26. No protected-test payload was opened; no
annotation entered any training artifact; the frozen D14 checkpoint is
untouched.

## What was built

| component | file |
|---|---|
| Executable contract | `lib/unresolved_evidence.py` |
| Occurrence extraction | `scripts/phase4_unresolved_extraction.py` |
| Deterministic clustering | `scripts/phase4_unresolved_clustering.py` |
| Contract tests | `tests/test_unresolved_evidence.py` (26 tests) |

Artifacts under `Phase4/phase4_out/`: `unresolved_occurrences.parquet` and
`unresolved_cluster_snapshot.parquet` (gitignored, regenerable);
`unresolved_extraction_manifest.json`,
`unresolved_similarity_candidates.jsonl`,
`unresolved_similarity_candidates_cross_language.jsonl`, and
`unresolved_workbench_report.md` (tracked).

## Extraction results

**238,652 occurrences** — 238,643 contiguous token runs plus the 9 Gate 1
source anomalies. Zero protected-test occurrences.

| category | occurrences |
|---|---:|
| `ILLEGIBLE_SIGN` | 131,322 |
| `PARTIALLY_PRESERVED_READING` | 103,092 |
| `TOKENIZER_OOV` | 4,192 |
| `UNCERTAIN_TRANSCRIPTION` | 402 |
| `EMPTY_LANGUAGE_TAG` | 44 |
| `UNRECOGNIZED_LANGUAGE_TAG` | 22 |
| `MALFORMED_LANGUAGE_TAG` | 22 |
| `MISSING_LANGUAGE_TAG` | 16 |
| `PARSER_ANOMALY` | 9 |
| `SYMBOL_OR_ENCODING_ANOMALY` | 1 |
| `LEXICAL_UNKNOWN` | 0 (deliberately — see below) |

By split: 126,419 discovery / 98,385 train / 13,838 dev. By effective
language: Hit 210,561; Hur 11,337; Akk 8,796; Hat 4,762; Luw 1,769; Sum 985;
Pal 367; unresolved 66.

Logical SHA-256 (content, excluding run timestamp):
`32fa7587c2c35695ed4e6f36ec8b6f058f85dffaab8d397bc08a891f67495aad`, reproduced
across two independent builds.

### Determinism is measured logically, not by file bytes

The first reproducibility check failed: two identical extractions produced
different Parquet files. The cause is benign — Parquet footer metadata and the
run's own `created_utc` differ per build — but a file hash cannot distinguish
that from a real content change. The script now reports
`occurrences_logical_sha256` over the stable identity of every occurrence,
excluding provenance, matching how Gate 1 and Gate 2 already verify
themselves. *When* an occurrence was extracted is not part of *what* it is,
and including it would have made the determinism check unfalsifiable.

## Design decisions

**An occurrence is a contiguous run, not a token.** 159,673 illegible and
152,634 partially-preserved tokens are not 312,307 separate questions for an
expert; a run of four illegible signs is one lacuna. Runs are cut whenever the
category set changes, so a run is homogeneous by construction.

**`restored` is not a workbench category.** Editorial restoration is a
scholarly hypothesis already typed `EDITORIAL_RESTORATION` and governed by the
evidence policy. Filing 765,291 restored tokens here would quietly reframe
editorial proposals as open questions.

**`LEXICAL_UNKNOWN` is empty on purpose.** The contract requires a governed
detector and explicitly forbids inferring the category from a tokenizer OOV.
No such detector has been ratified, so the category stays at zero rather than
being approximated with a frequency threshold, which would assert a claim
about Hittite lexis this pipeline cannot support. **This needs an Ixca
decision** before it can be filled.

**`cu` is never read**, even for display: it renders editor-restored content
as real glyphs.

## Two contract defects found at implementation

Both were found because real data would not fit the ratified 1.0.0 schema.
Neither is cosmetic, and both are recorded here rather than worked around.

**1. Text-external anomalies had no representable location.** The Gate 1
quarantine holds 9 explicit word-language attributes recorded *outside* the
primary `<text>` element. By definition they have no enclosing line and no
token span, but 1.0.0 required a non-null `line_index_in_doc` and token span.
The contract could not represent one of its own declared intake sources.
Fixed by making those three fields nullable.

**2. An absent language tag had no category.** The category vocabulary could
name an *empty*, *malformed*, or *unrecognized* language attribute but not an
*absent* one. 71 tokens whose line carries no language attribute at all —
and which therefore have nothing valid to inherit — were silently dropped by
the first extraction pass. That is precisely the failure the charter forbids:
"unidentified content is never silently discarded because it is rare, out of
vocabulary, malformed, or unresolved." Fixed by adding `MISSING_LANGUAGE_TAG`,
keeping the Gate 0 distinction between absent and present-but-invalid intact.

Both changes are in contract **1.0.1**. Two safeguards now make the second
defect unrepeatable:

- `validate_occurrence` refuses any occurrence whose effective language is
  unresolved unless it carries a language category or `PARSER_ANOMALY` — an
  unresolved occurrence filed under damage categories alone would never
  surface in a language-anomaly filter.
- the extraction asserts that **every** unresolved lexical token in the Gate 2
  dataset is covered by some occurrence (currently 247/247). A count that
  merely looks plausible is not evidence of coverage.

## Clustering — deterministic, typed, and channel-separated

Exact normalized sign-sequence matching, no model consulted.

| channel | clusters | multi-document |
|---|---:|---:|
| `SAME_LANGUAGE_AS_QUERY` (default) | 4,555 | 4,285 |
| `CROSS_LANGUAGE_PARALLEL` (opt-in `--cross-language`) | 1,266 | — |

Normalization is limited to case folding. Anything more aggressive — stripping
uncertainty markers, collapsing determinatives — would merge occurrences an
expert needs to keep apart, and the marker is often the very thing under
review.

Every proposal carries `scores_are_probabilities: false`; the member count is
a count, never a confidence. A single-document cluster emits explicit
**contradictory** evidence saying so, since one scribe repeating a form is not
evidence of a recurring one. The two channels write to separate files: sharing
one path would let a cross-language run silently replace the same-language
evidence an expert was working from, and the channels must stay separable on
disk, not only in a field.

Unresolved-language occurrences form their own `<UNRESOLVED>` bucket rather
than being swept into a majority language.

One awkwardness worth flagging: the ratified status vocabulary offers only
`MODEL_PROPOSAL` for anything system-generated, so a deterministic string-match
cluster enters as `MODEL_PROPOSAL` with `method.model_derived: false`. The
second field carries the truth and must be read alongside the first. Adding a
`SYSTEM_PROPOSAL` status would be cleaner but is a contract change I did not
make unilaterally.

## Expert annotation layer

`AnnotationEventLog` is append-only and hash-chained: each event stores the
canonical SHA-256 of the record reviewed and of its predecessor. Appending an
event that does not chain onto the current head is refused, and editing any
earlier event breaks every later link — both are tested.

`project_snapshot()` recomputes cluster membership and occurrence status from
the log alone, so a snapshot can never drift from the record of what an expert
actually did. Merge retains the emptied cluster rather than deleting it, so
history stays inspectable.

Enforced invariants: proposals require a hypothesis; `WITHHOLD_JUDGMENT` may
not carry one; cluster actions must name the cluster they operate on; every
event is `QUARANTINED_EXPERT_JUDGMENT` with `requires_adjudication: true`.
Nothing in the projection promotes anything to `EXPERT_SUPPORTED`
automatically — and even that status means only that one named reviewer
endorsed a hypothesis.

The event log is currently empty, so all 238,652 occurrences project to
`UNREVIEWED`. That is the correct starting position, not a gap.

## Acceptance checks

All twelve from `specs/UNRESOLVED_EVIDENCE_WORKBENCH.md` are covered by
`tests/test_unresolved_evidence.py`, except #3 (no test occurrence displayed in
development mode), which is additionally structural: `main_split` is
constrained to train/dev/discovery in both schema and library, and the Gate 2
source universe contains no test rows.

3,000 sampled occurrences and all 5,821 cluster proposals validate against the
amended schema with zero structural mismatches.

## Open decisions for Ixca

1. **`LEXICAL_UNKNOWN` detector.** The category cannot be populated without a
   ratified definition. A hapax-over-governed-universe detector is the obvious
   candidate, but "rare" is not "unknown to Hittitology," so this is a
   philological call, not an engineering one.
2. **Contract 1.0.1** was amended during implementation on the evidence above.
   It needs ratification like any Gate 0 decision.
3. **`SYSTEM_PROPOSAL` cluster status** — worth adding, or is
   `model_derived: false` sufficient?
4. **No expert interface yet.** The workbench data layer is complete; the UI
   described in the spec's "Expert interface" section is not built. The
   existing Takšan prototype covers missing-text decisions, not unresolved
   occurrences.
5. **Annotation event backup.** The spec requires events to be backed up
   separately before the workbench is used for real expert labor. No backup
   mechanism exists yet, and none should be assumed.
