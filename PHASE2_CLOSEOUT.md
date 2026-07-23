# Phase 2 closeout — evidence-bounded missing-text decisions

Closed 2026-07-23 on branch `codex/phase2-readiness`.

## Status

Phase 2 is complete as an exploratory characterization phase. It answered the
chartered question—what is recoverable from the encoded corpus, at what
horizon, under which assistance profile, and where abstention is required—
well enough to define an expert decision interface.

This closeout does not promote any Phase 2 probe to a citable measurement.
The frozen test side remains untouched. No publication, corpus migration, or
new ground-truth label has been authorized.

## What the encoded evidence supports

| target | Phase 2 finding | product boundary |
|---|---|---|
| physical fracture seam | TLHdig join markup supplies row membership but no member-specific within-line fracture column; decisive material modalities are absent | do not present textual seam scores as physical-fit probabilities |
| one missing sign | independent-witness evidence is sparse globally, but the strict selector found 5,486 dev audit contexts; its complete candidate set retained the intentionally hidden sign in 92.95% of those selected contexts, with composition-macro mean 83.11% | strongest starting path for an expert candidate UI; retain alternatives and group-audit labeling |
| two missing signs | tie-complete witness set effectively retained the audit span in 27.36% of all eligible contexts; composition-macro mean 16.18% | optional evidence, not default completion |
| three missing signs | effective inclusion 17.77% | optional evidence with strong abstention |
| four missing signs | effective inclusion 11.78% | optional evidence with strong abstention |
| five missing signs | effective inclusion 7.95%; composition-macro mean 5.32% | mostly an insufficiency signal |
| alignment rescue | only 6/387 exact-anchor absences were rescued at depth five | retain as an inspectable negative result; do not promote the scorer |

The single-sign figures describe selector-accepted audit contexts, not all
lacunae. The multi-sign figures include abstention in the eligible-context
denominator. Neither is a truth probability for a real damaged passage.

## Uncertainty decision

Phase 2 established historical group audit rates:

- option-rank rates for the P2-E4 single-sign path;
- whole-candidate-set rates for the P2-E6 multi-sign path.

It did not establish calibrated probabilities for individual options.
Composition transfer was heterogeneous; the P2-E6 weighted mean absolute
set-calibration gap was 8.17 percentage points. Witness-family counts and
shares therefore remain evidence summaries without probability semantics.

The interface must use the phrase “historical group audit rate” and show the
estimand, sample size, and 95% Wilson interval. It must not label these values
“probability this reading is correct.”

## Implemented decision boundary

Contract v1.0.0 is defined by:

- `specs/EXPERT_DECISION_CONTRACT.md`;
- `configs/expert_decision_contract.schema.json`;
- `lib/expert_decision_contract.py`;
- `phase2_out/p2e7_contract_examples.jsonl`.

The contract supports `SELECT_OPTION`, `REJECT_ALL`,
`OTHER_OR_UNSUPPORTED`, and `WITHHOLD_JUDGMENT`. It preserves typed evidence,
assistance layers, explicit abstention, and collapsed-tail counts. Decisions
are hash-bound to the reviewed packet and remain
`QUARANTINED_EXPERT_JUDGMENT` pending a separate adjudication process.

The validator fails closed on hidden evaluation answers, silent truncation,
instance-probability claims, stale packet hashes, unsafe selection during
abstention, and automatic ground-truth mutation.

## What Phase 2 did not establish

- automatic restoration;
- reliable per-option probabilities;
- physical join confirmation from text alone;
- a reason to train or scale another model now;
- authority to use restorations, `cu`, morphology, or model output as hidden
  truth;
- authority to touch the test set or convert expert UI actions directly into
  supervision.

## Next workstream

Build a small expert UI prototype against contract v1.0.0.

1. Start with the stronger single-sign path.
2. Show multi-sign evidence behind an optional expansion, grouping large
   equal-support tails without hiding their count.
3. Display supporting witnesses, limitations, assistance layers, and the
   correctly scoped group audit interval.
4. Offer all four expert actions and store hash-bound, quarantined decisions.
5. Use expert interaction to identify a concrete missing capability before
   authorizing another model or training run.

The first usability question is not “did the system guess correctly?” It is:
can a trained expert understand why each option is present, reject the entire
set, and withhold judgment without the interface overstating the evidence?

