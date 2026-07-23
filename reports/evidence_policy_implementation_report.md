# Evidence Policy Implementation Report

Per `cuneiform_expert_patch/IMPLEMENTATION_REQUEST_FOR_CLAUDE.md`.
Advisory input from `cuneiform_expert_patch/EXPERT_OPINION.md` and
`EVIDENCE_POLICY_SPEC.md`, 2026-07-22. Authority: advisory; CLAUDE.md,
PHASE2_CHARTER.md, SANDBOX_RULES.md, frozen splits, and ratified human
decisions remain controlling — nothing below overrides any of those.

## Files changed

New:
- `EXPERT_OPINION.md` (repo root, verbatim copy of the advisory input)
- `specs/EVIDENCE_POLICY.md` (adapted from `EVIDENCE_POLICY_SPEC.md`,
  with the registry section replaced by verified, real-schema findings)
- `lib/evidence_policy.py` (`EvidenceClass`, `FieldEvidence`,
  `EvidencePolicy`, `EvidencePolicyError`, `load_registry`,
  `load_policy`, `effective_class`, `validate_fields`,
  `validate_semantic_features`, `build_manifest`, `write_manifest`)
- `configs/evidence_policies.yaml` (5 named policies)
- `configs/evidence_registry.yaml` (72 fields, all checked against real
  parsed artifacts)
- `tests/test_evidence_policy.py` (14 tests, stdlib `unittest`)
- `scripts/evidence_policy_smoke.py` (standalone smoke script, not a probe)
- `requirements.txt`: added `pyyaml==6.0.3` (new dependency — the
  original spec's config format is YAML; this project had no prior
  YAML precedent, everything else is JSON. Installing PyYAML rather
  than switching the spec's requested format to JSON was the smaller
  deviation. Flagging the addition since it's the one new third-party
  dependency this pass introduces.)

Modified:
- `CLAUDE.md` — inserted the standing-rule text from
  `CLAUDE_MD_INSERT.md`, placed after the Cleanroom rules section and
  before "Provenance & generalization" (as instructed: "near the
  cleanroom/engineering standards sections").

Not modified: `lib/eval_harness.py`, `lib/fracture_engine.py`,
`lib/hittite_tokenizer.py`, `lib/contracts.py`, and every historical
(Phase 1) script and report — per the implementation request's explicit
scope control ("Do not refactor all historical phases in this commit").

## One addition beyond the literal spec, and why

`validate_fields()` alone cannot express "technical IDs are permitted
for joins/control flow but rejected if passed into a semantic feature
matrix" (spec test #10) — every standard policy's `allow` list
legitimately includes `SYSTEM_TECHNICAL` (row IDs are needed for joins),
so a plain class-membership check would let a technical ID through
into model input too. Added `validate_semantic_features()`: identical
fail-closed behavior, plus an unconditional rejection of
`SYSTEM_TECHNICAL` fields regardless of policy. `build_manifest()` uses
this stricter function, since a manifest describes what went into
model input. This is an implementation detail filling a gap in the
spec's own stated test list, not a change to any policy's semantics —
flagging it rather than leaving it undisclosed.

## Registry decisions and uncertainties

Full detail in `specs/EVIDENCE_POLICY.md`'s "Registry decisions and
uncertainties" section. Summary:

- **72 fields registered**, every one checked against an actual parsed
  artifact (`p2_out/corpus.parquet`, `p2_out/edges.parquet`,
  `p2_out/doc_table.parquet`, `p2_out/splits.parquet`,
  `p4_out/decomposed_corpus.parquet`, or
  `eval_harness.load_fragment_universe()`'s rendered columns) — not
  guessed from the original spec's abstract examples.
- **`mrp_selected`/`mrp_lemma_candidates` explicitly denied in every
  policy**, including `discovery_assisted` — the original spec's
  registry list didn't name these fields at all; the denial follows
  CLAUDE.md's pre-existing, standing "morphological glossing... out of
  scope" rule, not a new invention.
- **`lemma_full`/`lemma_attested` explicitly denied via mixed-dependency
  lineage** — they fall back to `trans`/`signs` only when
  `mrp_lemma_candidates` is empty, so their most-interpretive
  dependency is a denied field. Flagged as a decision point since
  neither field was named in the original patch.
- **Six fields flagged uncertain, not silently resolved**: `line_lang`
  and the five `is_sum`/`is_akk`/`is_det`/`is_num`/`is_syllabic`
  markup-classification flags. Tentative classification given
  (`OBSERVED_DOCUMENT_STRUCTURE`), with the counter-argument
  (`EDITORIAL_TRANSCRIPTION`) stated explicitly in the registry's own
  rationale text, for Ixca's review.
- **`annot@editor`/`annot@date`** (CLAUDE.md describes these as present
  in the raw AOxml) are **not registered** — no parsed artifact in this
  pipeline currently materializes them. A field that isn't accessible
  anywhere can't be validated against real data; `validate_fields`
  correctly fails closed ("absent from registry") if anything requests
  them regardless.
- **No field is currently registered as bare `OBSERVED_ARTIFACT`.**
  TLHdig transliteration is editorially mediated throughout this
  pipeline; `artifact_strict` in practice permits
  `OBSERVED_DOCUMENT_STRUCTURE` + `SYSTEM_TECHNICAL` on this corpus.
  Stated explicitly in `specs/EVIDENCE_POLICY.md` rather than left
  implicit.

## Conflicts with current parser schemas — one real finding

While verifying `line_lang` against real corpus values (needed to
decide its evidence class), a **parser data-quality issue** surfaced:
a sample of `line_lang` values contains malformed entries with
leftover XML fragments, e.g. `"Hit> <w><del_in/> ... <del_fin/></w"` and
`"Hit> <w><note n='15' c=..."`, instead of clean language codes. This
is a real bug in whatever produced `corpus.parquet`'s `line_lang`
column (likely `02_parse.py`, not inspected further — out of this
task's scope). **Not fixed here** — patching a historical parsing
script without being asked is exactly the kind of retrofit the
implementation request says to raise, not improvise. Flagged as a
decision point: whether/when to patch `02_parse.py` and whether any
downstream `line_lang`-dependent numbers (none currently exist in any
reported result, checked) need re-verification.

No other conflicts found. The registry's field set was checked against
every parquet/JSON artifact `lib/eval_harness.py`, `lib/fracture_engine.py`,
and `lib/hittite_tokenizer.py` actually read (traced by grep, not
assumed) — no field claimed here that isn't real.

## Tests run and results

`python tests/test_evidence_policy.py` — **14/14 passed**:

```
test_catalog_field_denied_under_strict_and_transcription ... ok
test_cu_denied_everywhere ... ok
test_derived_feature_inherits_strongest_dependency ... ok
test_editorial_relation_never_in_standard_policies ... ok
test_lemma_fields_denied_via_mixed_lineage ... ok
test_manifest_lists_all_consumed_fields_and_classes ... ok
test_model_derived_denied_outside_discovery ... ok
test_mrp_denied_everywhere_including_discovery ... ok
test_policy_behavior_deterministic ... ok
test_registry_load_rejects_dangling_dependency ... ok
test_restoration_field_denied_under_strict_and_transcription ... ok
test_technical_ids_control_flow_vs_semantic ... ok
test_unknown_field_raises ... ok
test_unregistered_alias_raises ... ok

Ran 14 tests in 0.042s
OK
```

Covers all 10 cases from the original spec plus 2 corpus-specific cases
(`mrp_*` denial, `lemma_*` mixed-lineage denial) found while building
the registry.

`python scripts/evidence_policy_smoke.py` — ran clean against 3 real
dev-side fragments (`KUB 37.123`, `KBo 1.28`, `KUB 4.46+`), 72-field
registry loaded, all four fail-closed demonstrations behaved as
predicted (permitted request passes; same field rejected under a
stricter policy; `cu` rejected even under the most permissive standard
policy; a technical ID rejected specifically from the semantic-feature
path). One real manifest written to
`p4_out/evidence_policy_smoke_manifest.json`.

## Sample manifest (from the smoke run)

```json
{
  "task": "textual_affinity",
  "evidence_policy": "transcription_assisted",
  "features_requested": ["sign_attested"],
  "features_observed": ["sign_attested"],
  "evidence_classes_used": ["EDITORIAL_TRANSCRIPTION"],
  "prohibited_features_encountered": [],
  "editorial_content_fraction": 1.0,
  "restored_content_fraction": 0.0,
  "model_derived_content_fraction": 0.0,
  "dataset_manifest_hash": "39c7bfc703f24523",
  "split_manifest_hash": "309d917cd2aa39d4",
  "config_hash": "d0dd6b71872eaad1",
  "git_commit": "2e32d29cc5cc37f1f39b6e38a7c86aecdc345b80",
  "corpus_version": "TLHdig 0.2.0-beta",
  "seed": 20260722,
  "declared_statistics_universe": "full_non_test (per CLAUDE.md's corpus-statistics convention)",
  "created_utc": "2026-07-22T23:14:06.895860+00:00"
}
```

## Non-negotiable constraints — compliance check

- Frozen test side: not accessed. This pass touched no fragment
  content at all beyond the smoke script's 3 dev-side sample IDs, used
  only to prove `load_fragment_universe()` interop.
- Split assignments: unchanged.
- Historical reports: none rewritten or deleted.
- `cu`: never used as model input; explicitly denied in every policy,
  tested directly (test #2, smoke demo #3).
- Unknown fields: never silently classified — `validate_fields` and
  `load_registry` both raise (tests #1, #9, and the dangling-dependency
  test).
- IDs/labels/split fields/relation metadata into semantic feature
  matrices: blocked by `validate_semantic_features` (test #10, smoke
  demo #4) for `SYSTEM_TECHNICAL`; `EDITORIAL_RELATION` is never in any
  standard policy's `allow` list at all (extra test, checked directly).
- `artifact_strict` is not described anywhere as unmediated clay
  access — `specs/EVIDENCE_POLICY.md` states plainly that no field is
  currently registered as bare `OBSERVED_ARTIFACT` on this corpus.
- Model output was not turned into ground truth — this pass produced
  no model output at all.
- Commit is reversible and infrastructure-only: no historical script
  touched; one new dependency (PyYAML) disclosed above.

## Decision points raised, not improvised (per the implementation
request's own list — none decided here)

1. `line_lang`, `is_sum`/`is_akk`/`is_det`/`is_num`/`is_syllabic` —
   tentative `OBSERVED_DOCUMENT_STRUCTURE` classification, explicitly
   flagged uncertain in the registry itself.
2. Whether to permit any `EDITORIAL_RELATION` field as a model feature
   under a specialized diagnostic policy — not created in this pass.
3. Whether/when to retrofit `lib/eval_harness.py` and the historical
   Phase 1 scripts onto this policy system.
4. Whether/when to patch `02_parse.py`'s `line_lang` malformed-value
   bug found during registry verification.
5. When to promote the evidence-policy layer from "available
   infrastructure" to "mandatory for every new Phase 2 probe" — not
   yet applied to any actual probe (P2-A/P2-D remain unrun as of this
   pass).
