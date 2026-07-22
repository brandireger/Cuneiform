# Expert Opinion — Provenance-First Design for Takšan Phase 2

**Prepared:** 2026-07-22  
**Purpose:** Standing methodological guidance for Claude Code and future architect sessions.  
**Authority:** Advisory. `CLAUDE.md`, `PHASE2_CHARTER.md`, `SANDBOX_RULES.md`, frozen splits, and ratified human decisions remain controlling.

## Executive judgment

Takšan should proceed as a provenance-aware evidence system, not as a single opaque “join predictor.” The repository’s Phase 1 failures support three conclusions:

1. **Composition affinity, duplicate/parallel detection, and physical joining are different inference tasks.** They may share candidate-generation infrastructure, but must not share a single headline score or undifferentiated label.
2. **Transliteration-only evidence may be sufficient for textual affinity and duplicates, but insufficient for many no-overlap physical joins.** A null result here is scientifically useful if measured cleanly.
3. **The project’s most important engineering requirement is not another model. It is an enforceable evidence-provenance layer that records exactly which artifact observations, editorial judgments, metadata, and model-generated fields were used.**

The artifacts should speak for themselves as far as the corpus allows. Editorial and model assistance may be used, but must be visible, separately measurable, and removable without rewriting the pipeline.

## 1. Separate the scientific tasks

All code, reports, configs, and result schemas should use the following task vocabulary.

### T1 — Textual affinity

Question: do two fragments plausibly belong to the same composition, passage, formula, genre, or textual tradition?

Expected useful evidence:
- attested transliteration signs;
- sign and word n-grams;
- line and paragraph structure;
- language layers;
- optional catalog metadata in assisted modes.

BM25 is a legitimate principal method here, not merely a disposable baseline.

### T2 — Duplicate or parallel witness detection

Question: do two artifacts preserve overlapping or parallel versions of substantially the same passage?

Expected useful evidence:
- local sequence alignment;
- repeated multi-line correspondence;
- monotonic line mapping;
- passage overlap length;
- formula-frequency-adjusted similarity.

Candidate generation may use BM25. Final evidence should be an inspectable alignment, not only a score.

### T3 — Physical join compatibility

Question: could two fragments occupy adjacent or otherwise compatible positions on one physical tablet?

Textual evidence is only one channel. For no-overlap joins, the correct output may be “insufficient encoded evidence.” Physical joining must not be inferred solely from same-composition or duplicate-like similarity.

## 2. Required evidence provenance taxonomy

Every model-consumable field must be assigned exactly one primary evidence class:

- `OBSERVED_ARTIFACT` — directly observed physical or epigraphic state, insofar as represented in the source.
- `OBSERVED_DOCUMENT_STRUCTURE` — line, column, ruling, spacing, orientation, or other source-encoded document structure.
- `CATALOG_METADATA` — publication, collection, findspot, CTH assignment, site, date, series, identifiers.
- `EDITORIAL_TRANSCRIPTION` — scholarly reading or normalization of visible signs.
- `EDITORIAL_RESTORATION` — supplied, restored, or reconstructed missing content.
- `EDITORIAL_RELATION` — asserted join, duplicate, composition, witness, or alignment relation.
- `MODEL_DERIVED` — predictions, embeddings, generated continuations, pseudo-labels, inferred attributes.
- `SYSTEM_TECHNICAL` — row IDs, hashes, split labels, execution metadata; allowed for control flow but never as semantic evidence.

When a field mixes origins, it must be decomposed or assigned the most interpretive class. Mixed fields may not be silently treated as artifact evidence. `lb@cu` is the canonical warning case: it includes editor-restored glyphs and is therefore not cleanroom-safe model input.

## 3. Named evidence policies

Implement field-level policies, then expose these standard profiles:

### `artifact_strict`

Permitted:
- `OBSERVED_ARTIFACT`
- `OBSERVED_DOCUMENT_STRUCTURE`
- `SYSTEM_TECHNICAL`

This profile is the strongest claim about what the encoded artifact itself supports. In practice, much TLHdig transliteration may remain editorially mediated; reports must state that limitation rather than relabel editorial transcription as direct physical observation.

### `transcription_assisted`

Adds:
- `EDITORIAL_TRANSCRIPTION`

Excludes restorations, editorial relation labels as features, model-derived content, and catalog metadata unless separately requested.

### `catalog_assisted`

Adds:
- `CATALOG_METADATA`

This mode may help discovery but must never be described as artifact-only.

### `scholar_assisted`

Adds:
- `EDITORIAL_RESTORATION`
- selected `EDITORIAL_RELATION` fields where leakage rules permit.

This is an explicit ablation mode, not the default evaluation condition.

### `discovery_assisted`

May add:
- `MODEL_DERIVED`

Outputs are hypotheses for expert review and never become ground truth automatically.

## 4. Mandatory run manifest

Every scoring or training run must emit a machine-readable manifest containing at least:

```json
{
  "task": "textual_affinity | duplicate_parallel | physical_join",
  "evidence_policy": "artifact_strict",
  "features_requested": [],
  "features_observed": [],
  "evidence_classes_used": [],
  "prohibited_features_encountered": [],
  "editorial_content_fraction": null,
  "restored_content_fraction": null,
  "model_derived_content_fraction": null,
  "dataset_manifest_hash": "",
  "split_manifest_hash": "",
  "config_hash": "",
  "git_commit": "",
  "corpus_version": "TLHdig 0.2.0-beta",
  "seed": null,
  "declared_statistics_universe": "",
  "created_utc": ""
}
```

A run must fail closed if a prohibited semantic field is accessed. Logging a warning is insufficient.

## 5. Candidate output: evidence packet, not one unexplained probability

Every candidate relation should expose typed evidence and contradictions:

```json
{
  "fragment_a": "...",
  "fragment_b": "...",
  "proposed_relation": "POSSIBLE_LEFT_RIGHT_JOIN",
  "evidence_policy": "transcription_assisted",
  "evidence": {
    "textual_affinity": 0.82,
    "local_parallelism": 0.11,
    "edge_language_compatibility": 0.63,
    "line_structure_compatibility": 0.77,
    "column_structure_compatibility": 0.41,
    "physical_geometry": null
  },
  "support": [],
  "contradictions": [],
  "editorial_features_used": [],
  "model_features_used": [],
  "abstention_reason": null
}
```

A combined rank may be computed, but the evidence vector and provenance must remain available in every persisted result.

## 6. Editorial dependence audit

For any promoted method, recompute candidate rankings under nested evidence policies. Report rank and score changes at minimum for:

- `artifact_strict`;
- `transcription_assisted`;
- `catalog_assisted` when used;
- `scholar_assisted`.

Define an editorial dependence measure from score or rank change. Its purpose is descriptive, not punitive. A result may be valuable and highly scholarship-dependent, but it must not be presented as artifact-led.

## 7. Required abstention behavior

Physical-join tooling must support an explicit abstention state. Examples:

- too few attested signs;
- no preserved edge context;
- all or mostly illegible placeholders;
- formulaic content produces many indistinguishable candidates;
- evidence channels materially disagree;
- no physical modality is available for a no-overlap case;
- candidate retrieval ceiling excludes any defensible conclusion.

Evaluate coverage, selective performance, and risk-versus-coverage. Do not force a ranked physical-join conclusion for every fragment.

## 8. Controls required for new content-consuming scorers

In addition to existing tracers, record a control-response signature where relevant:

- token scramble;
- line-order scramble;
- edge swap;
- restoration removal;
- metadata shuffle;
- candidate-ID permutation;
- all-`x` or near-empty input;
- formula-only passage;
- same-parent wrong member;
- duplicate transliteration attached to a distinct artifact.

A scorer’s claimed mechanism must match its control sensitivity. For example, an edge-local scorer should be more sensitive to edge perturbation than to arbitrary interior changes.

## 9. Recommended Phase 2 order

1. Complete P2-A seam localization using true pairs and wrong offsets.
2. Complete P2-D ground-truth audit, recording relation type, assertion basis, and certainty where recoverable.
3. Implement the evidence registry, evidence policies, and run manifest before adding more learned scorers.
4. Develop a local-alignment reranker for duplicates and parallels.
5. Test witness-mediated bridging for no-overlap textual reconstruction.
6. Introduce graph constraints only after pairwise evidence is typed and inspectable.
7. Treat image, 3D, clay, curvature, and paleographic channels as future independent modules rather than concatenating them into an opaque embedding.

## 10. Implementation constraints for Claude Code

- Do not modify frozen split assignments.
- Do not touch test-side content.
- Do not convert model suggestions into labels.
- Do not infer evidence provenance from column names at runtime; maintain a reviewed registry.
- Do not create a permissive fallback policy. Unknown fields must be rejected until classified.
- Do not replace existing tracer or contract infrastructure; integrate with it.
- Do not claim `artifact_strict` means unmediated access to clay. It means the strictest evidence profile available in the encoded corpus.
- Keep changes reversible and small. First implementation should be infrastructure plus tests, not a pipeline rewrite.

## 11. Definition of success

This intervention succeeds when a future reader can answer, from saved artifacts alone:

1. Which evidence classes were available?
2. Which were enabled?
3. Which exact fields were consumed?
4. Which editorial or model-derived inputs changed the candidate’s rank?
5. What evidence supported and contradicted the proposed relation?
6. Why did the system abstain, when it abstained?
7. Can all assisted evidence be disabled by configuration without editing code?

A model improvement is optional. Auditability is not.
