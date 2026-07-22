# P2 Deliverable 3 -- Edges Report

- Fragments total: 22757 (20957 standalone docs + 1833 reconstructed composite members from 654 composite docs)
- Fragments with a detected top-edge loss (gap before first line, or first line has a prime mark): 83.7%
- Fragments with a detected bottom-edge loss (gap at/after last line, or last line has a prime mark): 98.8%
- Documents with at least one `<gap>` element: 21104

## P2.5 A5.2 addendum -- physical-edge-line coverage

- Fragments with a top edge CONFIRMED preserved (first line sits on the upper `Rand`, overriding the prime-mark heuristic): 0.4%
- Fragments with a bottom edge CONFIRMED preserved (last line sits on the lower `Rand`): 0.2%
- Fragments preserving a left/right physical edge somewhere in their line range: 1.0% / 0.2%

## Scope notes
- `cu` (▒ positions) is deliberately NOT used as a break signal here -- D1's damage-oracle investigation found cu renders the editor's full proposed reading (restored signs get real glyphs); the authoritative per-sign silhouette is `sign_damage_states` from transliteration markup, already used for left/right edge states.
- Top/bottom edge detection is a first-pass heuristic (gap adjacency + prime-mark presence), not definitive -- e.g. a prime mark persists across an entire broken side by convention, so `has_prime` on the first/last line is a weak corroborating signal, not proof by itself; `top_edge_gap_desc` / `bottom_edge_gap_desc` (the editor's own free-text gap description, e.g. 'Vs. bricht ab') is the stronger signal when present.
- Composite-member fragments' gap events are attributed by line-index adjacency in the shared document stream, not by member -- a gap physically belonging to a different member interleaved nearby could be mis-attributed in rare cases; not deeply validated at this stage, flagged for P5/P6 review.