# Data Card Notes (staging)

Content to be included verbatim in DM1's `cards.data` JSON payload
(TAKSAN_DEMO_SPEC.md §5.4) once that export script is built. Staged
here now so the ruling's exact wording isn't lost before DM1 exists.

## Known limitations

### Orphan damage-marker gap (per DM0_RULING.md Ruling 3, 2026-07-22)

> Damage markers positioned outside word boundaries in the source XML
> are not captured; edge-damage rates are therefore slightly
> undercounted, which biases the fracture engine's edge-damage
> calibration marginally toward under-damage and undercounts the
> illegible-sign rate. Direction known, magnitude small; a parser
> extension is a candidate for the next corpus rebuild cycle (not this
> one — splits are frozen).

Accepted as-is for this cycle per the ruling. P4 results stand
(internally consistent, not invalidated) — this note exists so the
limitation is on record, not because anything needs to be redone.

### Ambiguous duplicate doc_ids not yet excluded from demo rendering

Found during the DM0 Ruling 2 spot-audit (`reports/dm0_audit_report.md`):
`decompose_corpus.py` and `damage_oracle.parquet` are built directly from
the raw corpus zip, upstream of `eval_harness.load_fragment_universe()`'s
28-doc_id ambiguous-duplicate exclusion (documented in P3/P2.5) — so a
demo export drawing on those artifacts directly could show duplicated
token content for those 28 doc_ids (confirmed in one sampled line, KUB
4.1). DM1's export script should apply the same exclusion list before
rendering.

### Ambiguous-duplicate documents in the training corpus (per P5_RERANK_SPEC.md, 2026-07-22 review)

> The training corpus included 28 ambiguous-duplicate documents with
> merged token content; evaluation excluded them; effect on trained
> models negligible but nonzero.

(Third known-limitations line, added on the 2026-07-22 P5 review. The
demo-export-time exclusion of these same 28 doc_ids is the item
already tracked above from `dm0_audit_report.md` — this entry is the
model/data-card-facing statement of the same fact, distinct from the
DM1 implementation action item.)

## Score columns (per P5_RERANK_SPEC.md "Consequential edits", 2026-07-22)

- **"Learned similarity" (neural bi-encoder) is RETIRED.** D15's
  bi-encoder was dropped from the cascade after P4B's diagnostics
  (Branch R, ratified `specs/P5_RERANK_SPEC.md`) — it must not appear
  as a demo score column at all going forward. D15 is written up as a
  clean negative result in the paper and model card instead (see
  `reports/p4b_report.md`, `reports/p5_report.md`).
- **"Edge fit" (tooltip: continuation lift — pending P5)** becomes
  D17/D18-backed *if and only if* P5's gate G1 passes (see
  `reports/p5_report.md` for the gate outcome once P5 finishes) — the
  copy should read "Edge fit" (active) on a G1 pass, and stay
  "Edge fit — pending P5" (or an honest equivalent) if G1 fails.
  Do not flip this copy before the gate result is in hand.
- "Text overlap" (BM25 over sign n-grams) is unaffected.

### Seam/continuation scores pre-2026-07-22 superseded (E2, per p5c_report.md/p5c2_report.md)

Seam/continuation scores (D17 boundary-head, D18 edge-continuation
lift) computed before 2026-07-22 used incorrectly encoded inputs (a
per-script tokenization bug that silently reduced ~83% of every
scored window to `<UNK>`), were caught by internal audit, and are
superseded by re-scored values — see `reports/p5c_report.md` (E2) and
`reports/p5c2_report.md` (H5's sighted re-score). **The demo never
displayed these scores**: per the "Score columns" section above,
"Edge fit" stayed "pending P5" throughout (P5's gate G1 never passed
on the pre-fix numbers), so no user-facing artifact was ever built on
the corrupted values — this line is a data-lineage record, not a
correction to anything shown.

## Glyph-layer coverage (per DM0_RULING.md Ruling 1)

- Rendered lines (exact/edge_trim/skeleton_only tiers via
  `cu_alignment.py::align_line()`): 83.11% of corpus lines.
- Unrendered lines fall back to transliteration-only (safe, not an
  error) — footer must report this coverage percentage at all times
  per the ruling.
- Audited misattribution rate: 0 in 44/45 hand-checked samples (1
  sample unverifiable due to an XML-lookup failure in the audit
  tooling) — see `reports/dm0_audit_report.md` for the full method and
  sampled (doc_id, line) pairs.
