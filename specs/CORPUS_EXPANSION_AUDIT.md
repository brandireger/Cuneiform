# Corpus expansion audit — TLHdig 0.3 and external transfer

Status: authorized feasibility audit, not corpus migration.

## Immediate question

Does TLHdig Beta 0.3 contain enough additional or corrected, safely
processable Hittite material to justify opening a separately governed corpus
migration—and what evidence would still be needed before testing
cross-language cuneiform pretraining?

## Non-negotiable boundary

- TLHdig 0.2 remains the pinned baseline.
- The 0.3 archive lives under the gitignored `external_corpora/` quarantine.
- Frozen splits are not changed.
- Training is not authorized.
- Test-side XML is never opened, decompressed, parsed, hashed, sampled, or
  compared. Its archive entries are counted only after filename-stem gating.
- Candidate entries whose filename stem is absent or ambiguous in the frozen
  split map are not opened. “Unmatched” means possibly new or renamed, not
  proven new.
- Duplicate filename stems inside either archive are quarantined because the
  split decision is not entry-unique.
- Only small aggregate inventories, manifests, and reports enter git.

## Audit layers

### A. Central-directory inventory

Without reading payloads, compare archive size, entry count, XML count,
macOS-junk count, filename-stem overlap, duplicate stems, CTH-folder coverage,
and unmatched-entry counts.

### B. Split-gated non-test delta

For filename stems that map uniquely to `train`, `dev`, or `discovery` in the
frozen split:

- parse XML separately in 0.2 and 0.3;
- record parse failures;
- compare raw SHA-256 only within the same non-test stem;
- inventory tag/attribute names and `<lb>` counts;
- count language-code and damage-marker usage;
- detect CTH-folder moves;
- report changed versus byte-identical documents.

No changed content is treated as better merely because it changed.

### C. Migration recommendation

A migration may be proposed, not performed, if 0.3:

- verifies against the official checksum;
- materially reduces parse failures or adds quarantined candidate documents;
- does not introduce an unhandled schema break;
- admits a defensible identifier/split migration plan;
- preserves evidence-policy and cleanroom enforcement.

## External-corpus follow-on

Only after the 0.3 audit, inventory selected ORACC, SumTablets, eBL, and CDLI
sources for:

- per-project license and redistribution terms;
- language, period, genre, and provenance;
- sign-token and transliteration normalization compatibility;
- damage/restoration encoding;
- identifier overlap with every TLHdig version;
- source-aware deduplication;
- sign-vocabulary and bounded-context overlap.

Foreign-language corpora may support auxiliary pretraining or hard-negative
construction. They may not supply Hittite candidate truth, evaluation labels,
or direct expert-facing restoration evidence.

## Falsifier

The expansion hypothesis is not worth pursuing if 0.3 adds little usable
non-test material and a source-aware external inventory shows negligible
Hittite sign/context overlap after licensing, deduplication, and markup
normalization.
