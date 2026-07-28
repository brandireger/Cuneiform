# Phase 4 P4-D / P4-E ratification record

**Decided by:** Ixca, 2026-07-27.
**Scope:** seven decisions arising from the P4-D language-aware API migration
and the P4-E Unresolved Evidence Workbench implementation.

This record does not widen any authorization boundary. Protected-test access
and GPU training remain unauthorized; Gate 3 is untouched.

## Why these had to be decided together

Occurrence identity is a hash of location **and** category set, and run
boundaries are cut wherever the category set changes. Adding
`MISSING_LANGUAGE_TAG` moved the occurrence count 238,642 → 238,652 and
changed the ids around the affected tokens; adding `RARE_FORM` moved it again
to 238,745. Expert annotations bind to occurrence hashes, so **any change to
the category vocabulary orphans existing annotations.** Decisions 1–3 were
therefore settled before any expert uses the workbench, while the cost is
zero.

---

## Decision 1 — Contract ratified as 1.1.0

**RATIFIED.** Four amendments to
`configs/unresolved_evidence_contract.schema.json`, all forced by real data
during implementation. Version 1.0.1 was an interim working state and was
never released; 1.1.0 is the first ratified version after 1.0.0.

| amendment | reason |
|---|---|
| `line_index_in_doc`, `token_start`, `token_end` nullable | The 9 Gate 1 parser anomalies are word-language attributes recorded outside the primary `<text>`. They have no enclosing line. 1.0.0 could not represent one of its own declared intake sources; the alternative was inventing a line index. |
| `MISSING_LANGUAGE_TAG` added | The vocabulary could name an *empty*, *malformed*, or *unrecognized* language attribute but not an *absent* one. 71 tokens fell through the first extraction pass. The alternative was collapsing "absent" into "empty", destroying a distinction Gate 0 drew deliberately. |
| `RARE_FORM` added | See decision 2. |
| `SYSTEM_PROPOSAL` cluster status added | See decision 3. |

## Decision 2 — `RARE_FORM` is separate from `LEXICAL_UNKNOWN`

**RATIFIED.** A governed frequency detector populates `RARE_FORM`;
`LEXICAL_UNKNOWN` is reserved for expert assertion and is **never** set by
extraction.

The distinction is the whole point. A frequency detector can establish that a
form is rare *in this corpus*. It cannot establish that a form is unknown *to
Hittitology* — that is a philological judgment only a trained specialist can
make. Collapsing the two would have let a Zipfian tail masquerade as lexical
discovery.

Ratified detector:

- **name:** `attested_frequency_at_most_1_in_governed_non_test_universe`
- **threshold:** attested count ≤ 1
- **declared universe:** non-structural tokens with damage state `attested` or
  `laes`, over the governed non-test universe (train + dev + discovery)
- **restored tokens excluded** — they are editorial proposals, and letting
  them inflate a count would hide genuinely rare attested forms behind
  scholarly reconstruction, the opposite of "let the artifacts speak"
- **illegible `x` excluded** — a placeholder is not a reading

Result: 4,283 distinct tokens in the frequency universe, 1,777 at or below
threshold, yielding **1,726 `RARE_FORM` occurrences**. `LEXICAL_UNKNOWN`
remains **0**, by design.

`validate_occurrence` refuses either category without a named detector in
`context`, so neither can be inferred from a tokenizer OOV or a bare count.

## Decision 3 — `SYSTEM_PROPOSAL` cluster status

**RATIFIED.** A deterministic, non-model grouping now enters as
`SYSTEM_PROPOSAL`; `MODEL_PROPOSAL` is reserved for groupings a model actually
produced. `build_cluster_proposal` derives the status from `model_derived`
rather than defaulting, and a `SYSTEM_PROPOSAL` carrying
`method.model_derived: true` is refused.

Previously every system-generated cluster was labeled `MODEL_PROPOSAL`, which
told an expert a model had been consulted when the channel was plain string
matching. All 5,844 current proposals are `SYSTEM_PROPOSAL`.

## Decision 4 — Annotation-event backup

**RATIFIED and implemented** as `scripts/phase4_workbench_backup.py`.

The event log is append-only and hash-chained, so a lost file is unrecoverable
*and* un-reconstructable: occurrences can be rebuilt from the pinned corpus at
any time, but a specialist's day of judgments cannot. The backup verifies the
chain **before** copying — archiving a corrupt log would preserve the
corruption and make it look safe — writes timestamped copies that never
overwrite, and appends to a ledger recording event count, chain head, and file
checksum.

**This must be run before and after any real expert session.** The workbench
has recorded no events yet.

## Decision 5 — Rerun scope: deferred, with a hard deadline

**RATIFIED: do not rerun now; rerun before any P7 paper drafting.**

P4-D changed what the active P2-E and real-gap scripts compute. Their
committed reports were not recomputed; ten carry a
`[PREDATES P4-D — numbers not recomputed]` header applied by
`scripts/p4d_stamp_stale_reports.py`.

The binding constraint: ~9.5% of the real-gap query denominator was
non-Hittite or unresolved, and the witness index loses ~6% of its tokens. Any
paper or mentorship pitch citing the current coverage figures would be citing
language-contaminated numbers on **both** sides. The rerun is P4-G work and
must precede P7.

## Decision 6 — Mixed-line policy stays `EXCLUDE_LINE`

**RATIFIED.** A line whose lexical tokens do not all resolve to the scope's
language is dropped whole (846 lines in the measured slice). Splicing out the
offending words would fabricate token adjacencies that never existed on the
tablet; segment-splitting is coherent but changes the per-line shape that
`line_position_in_fragment` depends on across the real-gap path.

`EXCLUDE_LINE` is fail-closed and the loss is bounded. Revisit only if witness
coverage proves to be the binding constraint on the real-gap results — which
the decision-5 rerun would reveal.

## Decision 7 — Expert interface is the next build

**RATIFIED as the next work item.** The workbench data layer is complete and
has no UI; a Hittitologist cannot currently use it. The existing Takšan
prototype covers missing-text decisions, not unresolved occurrences — a
different contract and record shape, though the two could share a shell.

---

## State after ratification

- Contract `unresolved_evidence_contract` **1.1.0**.
- **238,745 occurrences**; logical SHA-256
  `fd387b97a9aeb1cb9b7e9a89f3b20f8b015ef50af524695cec6567b64b191f47`.
- Cluster proposals: 4,566 same-language, 1,278 opt-in cross-language, all
  `SYSTEM_PROPOSAL`.
- 162 unit tests pass; Ruff clean; `git diff --check` clean.
- 4,000 sampled occurrences and all 5,844 cluster proposals validate against
  the ratified schema, with every `RARE_FORM` carrying a named detector and no
  extraction-set `LEXICAL_UNKNOWN`.
