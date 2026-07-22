# DM0_RULING.md — Architect ruling on the cu verification gate

Authority: amends TAKSAN_DEMO_SPEC.md §4. Ratified jointly
(Ixca + architect session) 2026-07-22, on review of
dm0_cu_report.md.

## Ruling 1 — Conditional GO ratified; §4 bar amended

The original "<1% of lines" bar conflated coverage with error and
is REPLACED. New bar, binding:

- RENDERED lines (cu_alignment tiers exact / edge_trim /
  skeleton_only) must show **< 1% damage-state misattribution**
  (a glyph styled with the wrong damage state — above all, any
  restored/laes sign styled as attested, which is a demo-rule-4
  violation).
- UNRENDERED lines (tier unresolved, currently 16.89%) fall back
  to transliteration-only via the existing §3.2 mechanism. A safe
  fallback is NOT an error. The footer reports the glyph-coverage
  percentage at all times; demo_data_report.md records it.

DM1/DM2 proceed immediately on `cu_alignment.py::align_line()`.

## Ruling 2 — Spot-audit required (parallel, does not block build)

- Hand-audit **30 random `edge_trim` lines and 15 random
  `skeleton_only` lines** against the source XML. Count
  damage-state misattributions per line and per glyph; report
  the rate with the sample sizes in `dm0_audit_report.md`.
  Seeded sampling; list the sampled (doc_id, line) pairs.
- Decision rule, pre-registered: if `skeleton_only` shows ANY
  restored-as-attested misattribution, or > 1 total
  misattribution across its 15 samples, DEMOTE the
  `skeleton_only` tier (1.51% of lines) to the unresolved
  fallback — cheap insurance, negligible coverage cost. If
  `edge_trim` shows restored-as-attested misattribution, stop
  and flag to the architect session before DM2 renders that
  tier (do not silently demote 23.7% of coverage — that is a
  joint call).
- If the audit is clean, the glyph layer ships with a measured
  honesty bound; cite the audit in the model/data card.

## Ruling 3 — Orphan-marker limitation goes on record

The decompose_corpus.py orphan-marker gap (damage markers outside
<w> spans silently dropped) is accepted as-is for this cycle. P4
results stand: internally consistent, not invalidated. But "not
invalidated" is not "unaffected" — record in the DATA CARD under
known limitations, one entry, plain language:

  "Damage markers positioned outside word boundaries in the
  source XML are not captured; edge-damage rates are therefore
  slightly undercounted, which biases the fracture engine's
  edge-damage calibration marginally toward under-damage and
  undercounts the illegible-sign rate. Direction known, magnitude
  small; a parser extension is a candidate for the next corpus
  rebuild cycle (not this one — splits are frozen)."

No pipeline change this cycle. A proper fix rides the next
corpus-version migration (see TLHdig 0.3 note in
TAKSAN_DEMO_SPEC.md §8).

Small artifacts back: dm0_audit_report.md (sampled pairs,
per-tier misattribution rates, decision-rule outcome).
