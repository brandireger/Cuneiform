# Implementation Request for Claude Code

Please implement the provenance-first evidence-policy infrastructure described in `EXPERT_OPINION.md` and `EVIDENCE_POLICY_SPEC.md`.

## Required first commit

1. Add `EXPERT_OPINION.md` at repository root.
2. Adapt `EVIDENCE_POLICY_SPEC.md` into `specs/EVIDENCE_POLICY.md`.
3. Add the standing-rule text from `CLAUDE_MD_INSERT.md` to `CLAUDE.md` near the cleanroom/engineering standards sections, avoiding duplication.
4. Create `lib/evidence_policy.py` with:
   - evidence classes;
   - reviewed field registry loading;
   - named policy loading;
   - fail-closed validation;
   - derived-feature dependency validation;
   - manifest construction/writing.
5. Create `configs/evidence_policies.yaml` and a reviewed initial field registry, preferably `configs/evidence_registry.yaml`.
6. Create tests covering every fail-closed rule in the specification.
7. Integrate the policy and manifest into exactly one new Phase 2 probe or a tiny standalone smoke script. Do not refactor all historical phases in this commit.
8. Produce a short report stating:
   - files changed;
   - registry decisions and uncertainties;
   - tests run and results;
   - one sample manifest;
   - any conflicts with current parser schemas or governance.

## Non-negotiable constraints

- Do not access the frozen test side.
- Do not change split assignments.
- Do not rewrite or delete historical reports.
- Do not use `cu` as model input.
- Do not silently classify unknown fields.
- Do not permit IDs, labels, split fields, parent IDs, or relation metadata into semantic feature matrices.
- Do not treat transliteration as unmediated clay observation.
- Do not turn model output into ground truth.
- Keep the commit reversible and infrastructure-focused.

## Decision points to raise, not improvise

Ask Ixca before:

- reclassifying an existing corpus field when the origin is ambiguous;
- permitting an `EDITORIAL_RELATION` field as a model feature;
- changing the cleanroom definition;
- retrofitting all historical scripts;
- changing any frozen data artifact;
- promoting an exploratory result to a citable claim.
