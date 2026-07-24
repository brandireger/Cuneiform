# Expert missing-text decision contract

Version 1.0.0, ratification candidate, 2026-07-23.

## Purpose

The interface serves a trained Hittite-language expert. It presents
evidence-bounded possibilities for one or more missing signs and records the
expert's response. It is not an automatic restoration system and it does not
translate a corpus frequency, witness share, rank, or confidence interval into
the probability that a reading is true.

The machine schema is
`configs/expert_decision_contract.schema.json`; executable cross-field
invariants and P2-E4/P2-E6 adapters live in
`lib/expert_decision_contract.py`.

## Two immutable record types

### Suggestion packet

`missing_text_suggestion_packet` is the evidence presented for one bounded
location. It contains:

- the exact query location and editorially transcribed left/right context;
- zero or more sign-sequence options;
- typed supporting and contradictory evidence, including source references;
- a complete option count and an explicit collapsed-tail count;
- assistance layers, evidence policy, editorial/model features, and
  limitations;
- group-level audit rates, only where Phase 2 established the named
  estimand;
- permitted expert actions and an explicit abstention reason.

The packet hash is the immutable object reviewed by the expert. Any later
change creates a new packet and invalidates an old decision's hash binding.

### Expert decision

`expert_decision_record` contains one of four actions:

1. `SELECT_OPTION`;
2. `REJECT_ALL`;
3. `OTHER_OR_UNSUPPORTED`;
4. `WITHHOLD_JUDGMENT`.

Abstention packets permit only the last two. `OTHER_OR_UNSUPPORTED` may carry
an expert-supplied sequence, but that sequence remains a quarantined proposal.
Every decision stores the reviewed packet's SHA-256, an opaque reviewer ID and
declared role, an optional rationale, and the assistance acknowledgment.

No decision becomes corpus ground truth automatically. Every decision is
`QUARANTINED_EXPERT_JUDGMENT` and requires a separate adjudication workflow
that is deliberately outside this contract.

## Uncertainty vocabulary

There are only two uncertainty kinds:

- `GROUP_AUDIT_RATE`: a named empirical frequency on held-out or
  composition-held-out audit contexts, with its estimand, scope, sample size,
  and 95% Wilson interval;
- `UNAVAILABLE`: no defensible transferable audit rate.

The scope is either `OPTION_RANK` (P2-E4 single-sign packets),
`CANDIDATE_SET` (P2-E6 multi-sign packets), or `NONE`. Every rate carries
`instance_truth_probability: false`. The UI label must say “historical group
audit rate,” never “probability,” “confidence this is correct,” or an
equivalent formulation.

Witness-family support count and share are evidence summaries. They do not
receive confidence intervals and are never probabilities that an option is
true.

## Candidate-set display

- Preserve stable option IDs and the evidence order.
- Never silently truncate. If the complete set is not expanded, show the
  exact collapsed-tail count and make it inspectable.
- P2-E6 equal-support boundary ties remain one evidence tier. The UI may
  collapse a large tier, but may not imply that an arbitrary first five are
  better supported.
- Always show `Other / unsupported` and `Withhold judgment`.
- Show `Reject all` only when options are presented.
- An empty sign sequence is a legitimate witnessed omission, not a rendering
  error.
- Witness alternatives may differ in length from the encoded gap estimate.

## Assistance and evidence

The packet names the active evidence-policy profile and all enabled assistance
layers. Editorial transcription must be labeled as such; “artifact-only” is
not an allowed shortcut. Model-derived content, if a future discovery profile
permits it, must be typed and visually separable from observed/editorial
evidence.

Supporting and contradictory arrays are both mandatory. An empty
contradictory array means “none encoded in this packet,” not “confirmed true.”
Restorations, `cu`, morphology, and model-generated text remain absent from
the P2-E4/P2-E6 adapters.

## Fail-closed invariants

The validator rejects:

- a hidden `dev_evaluation_only` payload;
- any group audit rate marked as an instance truth probability;
- silent truncation or inconsistent shown/total/tail counts;
- automatic completion or automatic ground-truth mutation;
- a selection of an option absent from the reviewed packet;
- a decision bound to the wrong packet hash;
- selection actions on an abstention packet;
- assistance flags that conceal model-derived content.

The JSON Schema defines the interchange shape. The Python validator is also
required because JSON Schema alone does not express every relational
invariant above.

## Versioning

Breaking field or semantic changes increment the major version. Additive
optional fields increment the minor version. Wording-only clarifications
increment the patch version. Stored decisions always retain the original
contract version and packet hash; migrations create new records rather than
rewriting the expert's historical action.
