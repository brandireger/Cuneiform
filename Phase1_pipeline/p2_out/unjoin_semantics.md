# P2 Deliverable 2 — Sigla Semantics Verification (gate, per P2_PARSER_SPEC.md)

Verified against 20 randomly sampled multi-member composite documents
(seed=20260720, drawn from 1,012 docs whose `AO:TxtPubl` contains at
least one `{€N}` tag) plus one corpus-wide cross-reference check.
Findings below, each with a confidence rating, BEFORE any
`03_unjoin.py` reconstruction logic was written.

## 1. Member declaration (`AO:TxtPubl`) — CONFIRMED, high confidence

`AO:TxtPubl` is a sequence of `<manuscript siglum> {€N}` groups
separated by a join-type marker. Example (`KBo 19.69+`):

    KBo 19.69 {€1} (+) KBo 19.66 {€2} (+) KBo 19.67 {€3} + UBT 158 {€4} (+) KUB 6.41 {€5}

- `€N` sigla are **integers, assigned in declaration order**, and are
  **scoped to the single document** — €2 in one composite has no
  relationship to €2 in another. Do not treat sigla as global IDs;
  key every downstream table on `(parent_doc_id, siglum)`.
- **Two distinct join-type markers appear between members and must be
  captured per-pair, not per-document**: plain `+` = direct physical
  join (fragments physically touch); `(+)` = indirect join (same
  tablet/object attributed on textual/content grounds, not a direct
  physical fit) — standard Hittitological notation. `KBo 19.69+`
  mixes both types across its 5 members in one document, so
  `join_pairs.jsonl` must record `join_type` (direct/indirect) per
  member-pair, parsed from the separator token immediately preceding
  each `{€N}` group, not assumed uniform for the whole doc.
- The existing `MEMBER_RE` regex in `02_parse.py`
  (`([^{}]+?)\{€(\d+)\}`) correctly extracts manuscript name + siglum
  but currently folds the `(+)`/`+` separator into leftover
  whitespace on the *manuscript* capture — it does not yet expose
  join_type. `03_unjoin.py` re-parses `AO:TxtPubl` itself with a
  separator-aware pass rather than relying on that field.

## 2. Per-line sigla tag in `lb@lnr` — CONFIRMED, high confidence

Format: optional leading `{€N}` (single member) or `{€N+M[+...]}`
(shared/overlap line), followed by the line label(s).

- **Single siglum** (e.g. `{€2} lk. Kol. 1′`): the line belongs to
  that member only; label is that member's own numbering.
- **Multi-siglum shared line** (e.g. `{€3+2} Vs. I 1′/lk. Kol. 5′`):
  the line is attested in both members. **The order of sigla in the
  brace tag matches the order of slash-separated labels,
  positionally** — verified via internal numbering continuity in 4
  independent samples, e.g. in `KBo 30.34+`: member €2's own
  numbering runs `{€2} lk. Kol. 1′..4′` immediately before the shared
  line `{€3+2} Vs. I 1′/lk. Kol. 5′` — the label `lk. Kol. 5′` (2nd
  slash position) is the natural continuation of €2's own sequence
  (4′→5′), and the sigla tag lists €2 in the 2nd position (`3+2`).
  Confirmed again in `KBo 31.182+` (€3's "Rs.? IV" numbering
  continues seamlessly, `IV 8`→`IV 9`, across two different shared
  lines paired with different partners) and `KUB 58.96+`.
- **When per-member labels happen to be identical**, only ONE label
  is written, no slash (e.g. `KBo 51.140+`: `{€1+4}Rs. IV 1`, no
  `label/label` duplication; `KUB 34.45++`: `{€1+2} Vs. 2′`). Parser
  must handle 1-label-N-sigla as "same label applies to all listed
  members," not as a format error.
- 3-way and 5-way shared lines exist (`KBo 12.66+`: `{€1+2+3}`;
  `KBo 19.69+`: up to 5 members), same rule generalizes N-way.

## 3. Manuscript redundancy across files — CHECKED, negligible

Cross-referenced all 1,844 distinct member-manuscript names (from
multi-member composites) against all 21,611 standalone docIDs
corpus-wide: only 6 overlaps (0.3%), several of which are
self-naming artifacts (a composite's own docID equals its lead
member's siglum, e.g. `KBo 30.20` as both the composite's docID and
its `{€1}` member name — not two separate files). Real redundancy
risk is low; `03_unjoin.py` should still log any true duplicates it
finds (both files present, same manuscript, different docIDs) as a
data-hygiene note rather than silently double-counting them in
join_pairs.jsonl.

## 4. Not yet verified — flag for `03_unjoin.py` implementation

- Whether `lg` (per-line language) or `cu` can differ between the two
  halves of a slash-separated shared line (each member's own
  transliteration of the *same* physical text could show minor
  editorial differences) — not observed in the 20-doc sample but not
  ruled out; if it occurs, treat as two aligned-but-distinct
  attestations of the same line, not an error.
- Column (`Vs. I` vs `lk. Kol.` etc.) does not have to match between
  paired members on a shared line — this is *expected*, not an
  anomaly: it reflects each manuscript's own physical layout (e.g.
  one witness numbers by column, another by continuous line count).
  Junction-geometry classification (horizontal vs vertical join, per
  P2 spec Deliverable 2) must be derived from each member's own
  side/column trend across the whole document, not from a single
  shared line's label mismatch.

## Conclusion

Hypothesis in the P2 spec is confirmed with high confidence for (1)
and (2), the load-bearing mechanics for reconstruction. Proceeding to
implement `03_unjoin.py` on this basis, with join_type captured
per-pair and the two open items above logged (not silently assumed)
during reconstruction.
