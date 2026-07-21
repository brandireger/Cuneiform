# P2 Deliverable 2 -- Unjoin Report

- Composite-doc candidates (TxtPubl parses to >=2 members): 659
- Successfully reconstructed: 655
- Quarantined (documented reason, not counted as positives): 4
- Errors (exceptions during reconstruction): 0
- **Acceptance check #3 (>=90% unjoined or explicitly quarantined): 100.0%** (PASS)

Note: P1 inventory's *authoritative* join-notation scan (docID/TxtPubl/lb@txtid text containing a well-formed embedded '+') found 866 docs. This deliverable's population (659 docs) is defined more precisely as 'TxtPubl parses to >=2 {€N}-tagged members' and differs from 866 because (a) some P1 866-matches have a *dangling* trailing '+' with the second member's name never given in TxtPubl at all (an incomplete-metadata case, e.g. `KUB 7.19 {€1} +`), which this stricter parse cannot resolve to >=2 named members and therefore excludes; (b) some single-member docs carry a non-1 {€N} tag (e.g. `KBo 45.18 {€2}`) referencing a join family not fully represented in that file. Both are corpus data-quality artifacts, not parser bugs -- consistent with CLAUDE.md's 'quality filtering must be explicit, never silent' standard.

## Members-per-doc histogram

- 2 members: 420 docs
- 3 members: 123 docs
- 4 members: 50 docs
- 5 members: 28 docs
- 6 members: 15 docs
- 7 members: 11 docs
- 8 members: 1 docs
- 10 members: 5 docs
- 11 members: 3 docs
- 12 members: 1 docs
- 13 members: 2 docs

## Pair-level stats

- Total member-pairs emitted: 1581

### join_type
- direct: 968
- inferred_from_shared_lines: 399
- indirect: 213
- None: 1

### junction_geometry (heuristic -- see script docstring; treat as noisy first-pass metadata, not ground truth)
- extended_overlap_duplicate_like: 704
- no_overlap_seam: 478
- unclear: 214
- seam_single_line_transition: 185

- n_shared_lines: min=0, median=4, max=61

## Quarantine reasons (top 10)

- (4) no per-line {€N} sigla found despite 2-member TxtPubl (likely incomplete line-level tagging in source data)

*Full detail in join_pairs.jsonl / unjoin_quarantine.jsonl / unjoin_reconstructed.jsonl.*