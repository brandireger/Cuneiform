# Unresolved Evidence Workbench contract

**Status:** GATE 0 RATIFIED; machine schema version 1.0.0 (2026-07-25).

## Purpose

Retain unidentified or uncertain material in a governed expert-review zone
where a trained specialist can compare occurrences, assemble contextual
clusters, and record possible readings, lexical identities, language
assignments, or phrases.

The workbench is a discovery and annotation system. It does not automatically
create corpus truth, training labels, restorations, dictionary entries, or
language assignments.

Machine-readable records validate against
`configs/unresolved_evidence_contract.schema.json`.

## Categories remain distinct

The intake pipeline must not merge different kinds of uncertainty:

| category | meaning |
|---|---|
| `ILLEGIBLE_SIGN` | source explicitly records an unreadable sign/placeholder |
| `PARTIALLY_PRESERVED_READING` | `laes` or comparable partial-preservation state |
| `UNCERTAIN_TRANSCRIPTION` | editorial uncertainty/correction marker |
| `LEXICAL_UNKNOWN` | a governed detector flags a rare or unresolved form; never inferred solely from tokenizer OOV |
| `TOKENIZER_OOV` | engineering vocabulary miss |
| `UNRECOGNIZED_LANGUAGE_TAG` | source language value is not ratified |
| `EMPTY_LANGUAGE_TAG` | source contains an explicit-empty language attribute; preserve even when the ratified line-inheritance rule resolves effective language |
| `MALFORMED_LANGUAGE_TAG` | source language value cannot be represented or canonicalized safely |
| `SYMBOL_OR_ENCODING_ANOMALY` | private-use, unusual Unicode, or unexplained symbol |
| `PARSER_ANOMALY` | source/parser structure cannot be represented reliably |

An occurrence may carry multiple categories, but each category remains
visible. For example, a tokenizer OOV is not evidence that the underlying
word is unknown to Hittitology.

## Occurrence record

Each occurrence preserves:

- immutable occurrence ID and record version;
- exact document/fragment/line/word/token location;
- cleanroom split class as technical control metadata;
- raw display form and token sequence where policy permits;
- damage states and uncertainty markers;
- left/right and full-line context;
- document-, line-, word-, and effective-language assignments with statuses;
- CTH/site only as typed catalog assistance;
- source archive member and payload checksum;
- evidence policy and enabled assistance layers;
- extraction rule/config/commit/seed;
- explicit `NOT_CORPUS_TRUTH` status.

The extraction process does not use `cu` as semantic input. If a future expert
display exposes a `cu` preview, it is labeled editorial/restoration-bearing
and stored outside the clean model-input fields.

## Similarity and clustering

Candidate clusters may be generated from separately typed channels:

- exact or normalized sign sequence;
- local left/right textual context;
- monotonic passage alignment;
- document structure;
- same-language contextual embeddings;
- explicitly enabled cross-language parallels.

Every cluster proposal records:

- member occurrence IDs;
- method and evidence class;
- language scope;
- raw similarity values;
- whether model assistance was used;
- support and contradictions;
- `scores_are_probabilities: false`.

Model clusters begin as `MODEL_PROPOSAL`. A trained expert may merge, split,
accept for organization, reject, or leave them unresolved. Even an expert-
curated cluster is an annotation collection, not a corpus fact.

## Append-only expert events

Expert interaction is recorded as an event log. Permitted actions are:

- `ADD_TO_CLUSTER`;
- `REMOVE_FROM_CLUSTER`;
- `MERGE_CLUSTERS`;
- `SPLIT_CLUSTER`;
- `PROPOSE_READING`;
- `PROPOSE_LANGUAGE`;
- `PROPOSE_LEXICAL_IDENTITY`;
- `PROPOSE_PHRASE`;
- `REJECT_HYPOTHESIS`;
- `WITHHOLD_JUDGMENT`.

Every event stores the reviewed object hash, opaque reviewer ID, declared
role, assistance acknowledgment, timestamp, optional rationale, prior-event
hash, and proposed hypothesis where applicable. Events are never rewritten.
A current cluster snapshot is a deterministic projection of the event log.

Statuses visible in the UI:

- `UNREVIEWED`;
- `GROUPED`;
- `HYPOTHESIS`;
- `EXPERT_SUPPORTED`;
- `REJECTED`;
- `WITHHELD`.

`EXPERT_SUPPORTED` means only that the recorded expert supports the
hypothesis. It does not mean corpus truth or consensus.

## Cleanroom and dataset boundary

- The default workbench development universe is discovery plus explicitly
  permitted non-test material.
- Frozen test content is excluded.
- Dev annotations may not influence a dev metric that claims to be held out.
- Expert annotations never enter model training automatically.
- Promotion to a future training dataset requires a separate adjudication
  contract, versioned export, leakage audit, and explicit Ixca decision.
- Novel readings remain quarantined until independently reviewed.

## Expert interface

The interface should provide:

- filters by category, language, mixed-language status, damage type, site,
  CTH, and review state;
- side-by-side occurrences with surrounding lines;
- clear separation of observed/editorial/model/catalog evidence;
- same-language clusters by default;
- cross-language parallels as an optional, visibly enabled channel;
- cluster merge/split controls;
- competing hypotheses rather than one forced reading;
- an always-available withhold-judgment action;
- full provenance and source links for every occurrence.

The UI must not call a similarity score a probability or hide contradictory
occurrences.

## Storage layout

Regenerable derived data:

- `Phase4/phase4_out/unresolved_occurrences.parquet`
- `Phase4/phase4_out/unresolved_cluster_snapshot.parquet`

Small, tracked artifacts:

- `Phase4/phase4_out/unresolved_extraction_manifest.json`
- `Phase4/phase4_out/unresolved_similarity_candidates.jsonl`
- `Phase4/phase4_out/expert_annotation_events.jsonl`
- `Phase4/phase4_out/unresolved_workbench_report.md`

The Parquet files are gitignored and rebuilt from the pinned corpus plus
append-only annotation events. Annotation events must be backed up separately
before the workbench is used for real expert labor.

## Acceptance checks

1. Every occurrence has a stable source location and checksum.
2. Categories are non-empty and remain distinct.
3. No test occurrence is extracted or displayed in development mode.
4. Every semantic field passes the selected evidence policy.
5. Model-derived clusters are visibly labeled and never treated as truth.
6. Similarity values carry `scores_are_probabilities: false`.
7. Expert events are append-only and hash-bound to the reviewed record.
8. Cluster snapshots reproduce deterministically from the event log.
9. Expert annotations cannot mutate TLHdig or a training artifact.
10. Same-language and cross-language evidence remain separable.
11. Withhold judgment is always available.
12. A separate adjudication gate is required before any training export.

## Relationship to the missing-text decision contract

The existing expert decision contract governs choices among missing-text
possibilities. This workbench contract governs unresolved occurrences,
clusters, and hypotheses. A missing-text decision may link to a workbench
occurrence, but neither contract silently upgrades the other one's record to
ground truth.
