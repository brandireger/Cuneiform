## Evidence provenance and assistance controls (Phase 2 standing rule)

Read `EXPERT_OPINION.md` and `specs/EVIDENCE_POLICY.md` before implementing any new content-consuming model or probe.

Every semantic input field must be registered with an evidence class. Standard classes are: `OBSERVED_ARTIFACT`, `OBSERVED_DOCUMENT_STRUCTURE`, `CATALOG_METADATA`, `EDITORIAL_TRANSCRIPTION`, `EDITORIAL_RESTORATION`, `EDITORIAL_RELATION`, `MODEL_DERIVED`, and `SYSTEM_TECHNICAL`.

New code must fail closed when a requested field is unknown or prohibited by the selected evidence policy. Editorial and model assistance must be disable-able through configuration without changing implementation code. Every new scoring/training run emits a feature-use manifest recording requested and observed fields, evidence classes, prohibited-field checks, hashes, seed, corpus version, git commit, and declared statistics universe.

Do not call a result “artifact-only” merely because restorations were removed. TLHdig transliteration is editorially mediated. Use the named evidence-policy profile in reports (`artifact_strict`, `transcription_assisted`, `catalog_assisted`, `scholar_assisted`, or `discovery_assisted`) and state its permitted evidence classes.

Physical-join output must support abstention when the encoded evidence is insufficient. Candidate output should preserve typed supporting evidence, contradictory evidence, enabled assistance layers, and any model-derived content; a single combined score is never the sole persisted explanation.
