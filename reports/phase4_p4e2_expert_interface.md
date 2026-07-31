# Phase 4 P4-E2 — expert interface for the Unresolved Evidence Workbench

**Status:** implemented 2026-07-27; browser smoke-tested 2026-07-29. The
queue's two selection exclusions are still **awaiting ratification**. See
`reports/phase5_p4e2_browser_smoke.md` for the bounded browser result.

Ratification decision 7 made this the next build: the workbench data layer was
complete and had no UI, so a Hittitologist could not use it.

**On the label.** This is **P4-E2**, a continuation of P4-E, not P4-F. The
charter already assigns P4-F to language-conditioned pretraining — the Gate 3
item the handoff explicitly forbids beginning — and P4-G's "expose the
workbench in the expert interface" is gated behind the new dataset and model
passing their gates. The interface depends on neither. No protected-test
material is reachable, no annotation entered any training artifact, the frozen
D14 checkpoint is untouched, and Gate 3 remains closed.

## What was built

| component | file |
|---|---|
| Review-queue export | `scripts/phase4_workbench_review_export.py` |
| Interface | `demo/workbench_unresolved_prototype.html` |
| Expert-session ingest | `scripts/phase4_workbench_ingest_events.py` |
| Tests (19) | `tests/test_phase4_workbench_interface.py` |

The shape follows the Takšan prototype, which already works in this repo: a
Python export writes a data file, a static HTML page reads it, and judgments
leave the browser as a file that a CLI validates on the way in. The two pages
share `canonical_sha256` — `lib/unresolved_evidence.py`'s hashing is
byte-identical to the expert decision contract's, so both self-check against
the same vector, confirmed against the real Python function
(`3d2321f6…`).

## The finding that shaped the queue

Cluster proposals are Zipfian, and it only becomes a problem when you try to
put a person in front of them. Measured over all 4,566 same-language
proposals: median size **3**, but the largest has **95,530 members across
17,353 documents** and its entire shared sequence is `x`. A UI that listed
clusters would open on that.

The first fix — rank by distinct document count — inverted the queue for the
same underlying reason. The top became the single signs `a` (3,542 documents),
`i`, `e`, `an`: a damaged common sign appears everywhere. That is the second
Zipfian floor, one level up from `x`.

Shared-sequence evidence gets its force from **specificity**, not recurrence.
Ranking by sequence length first, document count second, surfaces material an
expert can actually adjudicate — `me na aḫ ḫa an da` across 3 documents,
`ninda gur₄ ra em ṣa` across 5 — where a judgment about one member informs the
others.

## Queue policy `contentful_sequence_length_v1`

> **SUPERSEDED 2026-07-31 by `contentful_sequence_length_v2`.** The two
> exclusions below were decided separately: contentless **RATIFIED** with a
> widened character set, minimum length **UNRATIFIED and DEFERRED**. The counts
> in this section are the v1 counts and are retained as the record of what was
> presented for ratification. Current status:
> `reports/phase5_p4e2_queue_policy_ratification.md`,
> `configs/p4e2_queue_policy.json`.

| channel | proposals | contentless | below min length | eligible | queued |
|---|---:|---:|---:|---:|---:|
| `SAME_LANGUAGE_AS_QUERY` | 4,566 | 125 | 1,544 | 2,897 | 60 |
| `CROSS_LANGUAGE_PARALLEL` | 1,278 | 38 | 542 | 698 | 60 |

**Contentless exclusion.** A cluster whose shared sequence is nothing but
placeholder characters (`x`, `_`, editorial parentheses and periods) groups
occurrences by the *absence* of a reading. A character test rather than a
token list, because the placeholders combine: `x`, `x x`, `)x`, `(_)`, and
`x x x x x( )x` are all the same nothing, and a token list caught only the
first. Removes 125 same-language clusters covering 131,963 occurrences.

**Minimum sequence length 2.** Removes 1,544 same-language clusters covering
75,018 occurrences — the single-sign floor described above.

**Both were display policies awaiting Ixca's ratification** at the time of
writing, not findings — see the superseding note above for how each was
decided.
Nothing excluded is deleted, altered, or judged uninteresting; illegible runs
and single signs remain in the extraction at their ratified hashes, and a
future queue keyed on *surrounding context* rather than shared surface form
would reach them. They need ratifying before real expert labor because they
decide what a specialist is shown.

Also policy, and reported on screen: at most 12 members rendered per cluster
beside the true `member_count`, at most 60 clusters per channel (a review
session, not a corpus — raise with `--max-clusters`), and ±2 lines of
surrounding context rebuilt from the Gate 2 dataset, since an occurrence
record carries only its own line.

## Integrity properties

**Nothing ratified is mutated.** Occurrences and cluster proposals are
read-only inputs; selection happens in the export. The accepted hashes travel
with the payload and are displayed in the page footer.

**Whole canonical records travel with the queue.** The event contract binds an
action to `canonical_sha256(reviewed_record)`. Had the payload carried trimmed
display objects, that hash would point at nothing on disk. The page therefore
ships whole records — 1.96 MB, in line with the existing Takšan payload — and
trims only for display.

**The queue has a content hash.** `channels_logical_sha256` is stable across
rebuilds; the file hash is not, because every record carries its own
provenance.

**Ingest verifies, then re-chains.** `phase4_workbench_ingest_events.py` is the
only supported path from a browser export into the log. It recomputes each
event's `reviewed_record_sha256` from the record currently on disk and refuses
on mismatch — a judgment about a record that has since changed is a judgment
about something else. It verifies the existing chain, refuses to append when
the current head appears in no backup ledger entry, and re-chains the session
onto the real head. Re-chaining changes an event's own hash but never the
reviewed-record binding, which is the one that matters. All three refusals
were exercised against the real artifacts (tampered hash, unknown target,
cross-version session), plus a clean dry run of a two-event session.

**Nothing is promoted.** Ingested events stay
`QUARANTINED_EXPERT_JUDGMENT` / `requires_adjudication: true`. Ingest is not
adjudication, and the adjudication gate deliberately does not exist yet.

## Spec compliance

| requirement | how |
|---|---|
| Filters by category, language, mixed-language, site, CTH, review state | sidebar; free-text matches sequence, document id, CTH |
| Occurrences with surrounding lines | ±2 lines from the Gate 2 dataset, damage state colored, the unresolved run highlighted |
| Observed / editorial / catalog evidence separated | evidence class shown per proposal; catalog fields carry `CATALOG_METADATA`; bin CTH flagged as *unlabeled, not negative* |
| Same-language default | opening channel; cross-language requires a confirmation and shows a standing banner |
| Cross-language visibly enabled | separate channel, separate button state, blue banner, never merged into same-language evidence |
| Cluster merge/split | `SPLIT_CLUSTER`, `MERGE_CLUSTERS`, `REMOVE_FROM_CLUSTER` |
| Competing hypotheses | multiple proposals per occurrence, listed side by side, never collapsed |
| Withhold judgment always available | on every occurrence |
| Full provenance per occurrence | archive member, payload SHA-256, occurrence id, split, CTH, site |
| No score called a probability | counts labeled "not a probability or a confidence score"; `scores_are_probabilities: false` carried through |
| Contradictory evidence never hidden | rendered unconditionally; when absent, the page says that is the absence of a recorded objection, not evidence of soundness |

## What is not verified

**No specialist usability review has occurred.** The 2026-07-29 in-app-browser
smoke test verified rendering, filtering, the separate cross-language opt-in,
reviewer/rationale entry, local event state, and clean discard on reload. It
found that the original native `window.prompt` path was unsupported in that
browser; the page now uses an accessible in-page dialog for prompts,
confirmations, and alerts. The test did not download an export file and did not
exercise ingest. The earlier field-contract, hash-vector, export/ingest, and
refusal-path checks remain the evidence for those paths.

**No expert has used it.** The event log is still empty, and
`Phase4/phase4_out/annotation_backups/` still does not exist. It is created on
first backup.

**Prototype dialog input.** Hypotheses are collected through one reusable
modal dialog. This is browser-compatible and keyboard-labelled, but it is
still a sequential prototype rather than a specialist-designed review form.

## Open decisions for Ixca

1. **Ratify or amend the two queue exclusions.** Contentless sequences and the
   minimum sequence length of 2 decide what a specialist sees. Both are
   defensible and both are reversible — `--min-sequence-length 1` admits the
   single-sign clusters today.
2. **Queue size.** 60 clusters per channel is a session, not a survey. If the
   intent is broad coverage rather than depth, this should rise and the
   payload with it.
3. **Ungrouped occurrences are out of scope for this queue.** Roughly 13,900
   occurrences are in no cluster at all because their sequence is unique —
   arguably the most interesting material, and unreachable through a
   cluster-first interface. A second queue keyed on context would be a
   separate build.
4. **Concurrent sessions.** Ingest re-chains onto the current head, so two
   reviewers working simultaneously is safe in the sense that neither is lost.
   Whether their judgments should be interleaved in one log or kept in
   separate logs per reviewer is a governance question, not an engineering
   one.
