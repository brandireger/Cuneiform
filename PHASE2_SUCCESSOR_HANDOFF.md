# Phase 2 successor handoff

Prepared 2026-07-23 for the next maintainer of the Cuneiform/Takšan project.

## Executive status

Phase 2 is complete as an exploratory characterization phase. Its central
result is a product and research boundary:

> Present a trained Hittite specialist with a compact, evidence-supported set
> of possible missing signs or spans, typed provenance, historical group audit
> rates, uncertainty, and abstention. Do not claim automatic restoration,
> physical joining from text alone, or per-option truth probabilities.

The frozen test side has not been opened. No Phase 2 probe has been promoted
to a citable measurement. No model output or expert UI action has become
ground truth. No corpus migration or new training run has been performed.

The primary next product task is a small expert UI prototype against
`specs/EXPERT_DECISION_CONTRACT.md`. A separate data-maintenance track may
prototype TLHdig 0.3 ingestion, but it must not replace the pinned 0.2 corpus
or alter the existing frozen splits.

## Why Phase 2 changed direction

Phase 1 treated fragment joining and pairwise ranking as the organizing
problem. Its hardest physical joins were frequently defined by the absence of
shared text, while learned components repeatedly reduced to noisy lexical
similarity. Phase 2 therefore asked a more fundamental question: what missing
information is actually recoverable from the evidence TLHdig encodes?

Three opening probes established the boundary:

- P2-A found that join markup gives member/row attribution but not the
  member-specific within-line fracture column needed to evaluate seam
  localization.
- P2-B found useful symbolic layout and damage markup, but no images, 3D
  geometry, dimensions, curvature, clay composition, break contours,
  paleography, or ancient-hand features.
- P2-D found relation-basis categories, not a usable certainty scale, and did
  not support the hypothesis that the frozen hard set was simply enriched for
  weaker editorial labels.

The resulting premise audit rejected continued pairwise seam modeling as the
default. Joins remain a downstream use case; missing-information prediction
with explicit insufficiency became the scientific center.

## What was completed

### Governance and provenance

Phase 2 added or hardened:

- a fail-closed evidence registry and named assistance policies in
  `configs/evidence_registry.yaml`, `configs/evidence_policies.yaml`, and
  `lib/evidence_policy.py`;
- cleanroom ingress contracts C1–C10 in `lib/contracts.py`;
- content-sensitivity perturbations in `lib/tracer_utils.py`;
- declared-statistics-universe and feature-use manifests for new probes;
- the rule that TLHdig transliteration is editorially mediated and must never
  be described as unqualified artifact-only evidence;
- project-wide denial of `cu`, morphological `mrp*` fields, and their derived
  lemma streams as evaluated model inputs.

Unknown or prohibited fields fail closed. Test IDs fail at ingress. New
semantic inputs must be registered before use.

### Recoverability probes

All numbers below remain exploratory and are not promoted for citation.

| Probe | Main finding | Decision |
|---|---|---|
| P2-A seam feasibility | no encoded member-specific seam column | do not evaluate textual offsets as physical seams |
| P2-B materiality | symbolic layout exists; decisive physical modalities do not | support abstention and document missing modalities |
| P2-D relation reliability | direct `+`, indirect `(+)`, and shared-line expansion are separable; certainty is not encoded | preserve relation basis without inventing confidence |
| P2-E witness coverage | 24.62% of eligible one-sign dev spans had any independent witness-supported middle; 19.39% included the hidden sign | bounded evidence islands, not universal reconstruction |
| P2-E2 calibration | a strict rule reached 90.37% agreement at 4.73% held-out coverage, but the 95% Wilson lower bound was 89.0% | no 90%-guarantee claim |
| P2-E3 cross-calibration | only 1/5 held-out folds retained a 90% lower bound | no global reliability threshold |
| P2-E4 candidate sets | in 5,486 selector-accepted contexts, top-1 inclusion was 89.97%; the complete set reached 92.95% with mean set size 1.34 | strongest starting path for the expert UI |
| P2-E5 alignment rescue | recovered only 6/387 exact-anchor absences at depth five | preserve as a negative result; do not promote |
| P2-E6 multi-sign horizon | effective inclusion fell from 27.36% for two signs to 7.95% for five; equal-support tails reached 237 options | optional abstention-first evidence only |
| P2-E7 decision contract | version 1.0.0 validates typed packets and quarantined expert actions | Phase 2 definition of done |

Composition-macro behavior was consistently more heterogeneous than pooled
span-micro behavior. The 92.95% single-sign figure applies only to
selector-accepted dev audit contexts; it is not an all-lacuna success rate or
the probability that an option is true.

## Expert decision contract

The Phase 2 product boundary is implemented in:

- `specs/EXPERT_DECISION_CONTRACT.md`;
- `configs/expert_decision_contract.schema.json`;
- `lib/expert_decision_contract.py`;
- `phase2_out/p2e7_contract_examples.jsonl`;
- `reports/phase2_p2e7_contract.md`.

The contract supports:

- `SELECT_OPTION`;
- `REJECT_ALL`;
- `OTHER_OR_UNSUPPORTED`;
- `WITHHOLD_JUDGMENT`.

Every decision is hash-bound to the reviewed packet and stored as
`QUARANTINED_EXPERT_JUDGMENT`. The validator rejects hidden evaluation
answers, silent candidate truncation, instance-probability claims, stale
packet hashes, selection during abstention, and automatic truth mutation.

The UI must call uncertainty displays “historical group audit rates,” naming
the estimand, sample size, and 95% Wilson interval. It must not label them
“probability this reading is correct.”

## TLHdig 0.3 expansion work

After Phase 2 closeout, TLHdig Beta 0.3 was audited as a possible corpus
expansion. The raw archive is quarantined under gitignored
`external_corpora/`; TLHdig 0.2 remains pinned.

The split-gated audit and migration-design pass found:

- 23,937 non-junk XML entries in 0.3 versus 21,868 in 0.2;
- 2,137 candidate-only filename stems;
- 49 conservative one-to-one identifier revisions and five candidate stems
  in ambiguous revision groups;
- 2,083 remaining plausible additions, still a filename-level upper bound;
- 1,753/2,083 (84.16%) mapped to discovery-bin CTH folders;
- at most 281 prospective train and 15 dev additions;
- 26 prospective test additions, which remain unopened;
- 132 duplicate filename stems, including 90 crossing frozen split classes or
  an unknown CTH and 21 involving test;
- 12 safely diagnosed non-test parse failures: eight invalid
  `AO:-LineNrExpl` QNames and four other structural XML failures.

The direct-replacement hypothesis is rejected. A future 0.3 ingestion
prototype must first construct canonical identifier groups, quarantine
cross-CTH groups, and apply only reviewed checksum-guarded XML repairs.
Permissive recovery parsing is prohibited because it may silently alter
damage-state order.

Relevant artifacts:

- `specs/CORPUS_EXPANSION_AUDIT.md`;
- `scripts/corpus_expansion_audit.py`;
- `scripts/corpus_migration_design.py`;
- `reports/corpus_expansion_tlhdig_03_audit.md`;
- `reports/corpus_expansion_tlhdig_03_migration_design.md`;
- `corpus_audit_out/tlhdig_03_delta_manifest.json`;
- `corpus_audit_out/tlhdig_03_migration_design_manifest.json`.

External ORACC, SumTablets, CDLI, or eBL ingestion remains deferred until the
upper bound of 281 prospective 0.3 train additions is resolved.

## What the successor must not do

- Do not open or inspect test-side payloads.
- Do not change the frozen 0.2 splits in place.
- Do not feed `cu`, restoration-derived content, morphology, editor identity,
  or model-generated text into evaluated models.
- Do not call same-CTH membership a verified duplicate without an inspectable
  relation basis.
- Do not present textual affinity as physical-fit probability.
- Do not relabel historical group audit rates as per-instance probabilities.
- Do not convert expert UI selections into corpus truth or training labels
  without a separate adjudication design.
- Do not resume model scaling, hyperparameter search, or GPU training without
  a named hypothesis, time budget, tracer, and explicit authorization.
- Do not use permissive XML recovery for TLHdig 0.3.

## Recommended order of work

### Product track — first priority

1. Read `AGENTS.md`, `PHASE2_CLOSEOUT.md`, and
   `specs/EXPERT_DECISION_CONTRACT.md`.
2. Build a small expert UI beginning with the P2-E4 single-sign packet.
3. Render candidate rank, typed support/contradictions, assistance profile,
   historical group audit interval, residual alternatives, and abstention.
4. Implement all four expert actions and persist only validated,
   hash-bound, quarantined decisions.
5. Put P2-E6 multi-sign evidence behind an optional expansion; preserve and
   disclose collapsed equal-support tails.
6. Use usability feedback to name the next missing capability before
   authorizing another scorer.

### Corpus-maintenance track — isolated side track

1. Build canonical 0.3 identifier groups using archive metadata only.
2. Quarantine all duplicate/cross-CTH/test-involving groups.
3. Define a checksum-bound repair registry for the 12 known malformed files.
4. In a separate output namespace, inventory parseability, language content,
   and attested-sign yield for safely eligible additions.
5. Present a new migration decision; do not mutate the 0.2 artifacts.

## Verification and operating notes

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe lib\contracts.py
.\.venv\Scripts\ruff.exe check lib scripts tests demo
git diff --check
```

At handoff, 88 repository tests and all 20 contract self-tests pass, Ruff is
clean, and the corpus-expansion manifests report zero test, unmatched, or
duplicate-stem payload reads.

The raw corpora, derived parquet files, model weights, and local environments
are intentionally gitignored. Small reports, metrics, manifests, and failure
taxonomies are the exchange artifacts.

## Fast reading path

For the shortest accurate orientation, read in this order:

1. `AGENTS.md`;
2. `PHASE2_CLOSEOUT.md`;
3. this handoff;
4. `specs/EXPERT_DECISION_CONTRACT.md`;
5. `reports/phase2_p2e4_candidate_set_audit.md`;
6. `reports/phase2_p2e6_multisign_horizon.md`;
7. `reports/corpus_expansion_tlhdig_03_migration_design.md`.

The standing interpretation is simple: provide inspectable possibilities to
an expert where encoded evidence is informative, preserve alternatives, and
abstain everywhere else.
