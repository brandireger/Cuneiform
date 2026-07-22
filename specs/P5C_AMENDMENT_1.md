# P5C_AMENDMENT_1.md — Baseline reconciliation resolution (Option 1)

Authority: amends P5C_SPEC.md E1.3. Ratified jointly (Ixca +
architect session) 2026-07-22, on review of p5c_report.md. The
E1.3 stop was correct conduct: both pre-named candidate effects
measured bit-identical zero; 100% of the P4B->P5 baseline delta
traced to a third mechanism — 29_cascade.py fit BM25 IDF/avgdl
over a query-derived candidate-union reference (15,153 fragments)
instead of the full non-test universe (21,920) — confirmed by
reproducing D19's numbers to 4 decimals. OPTION 1 (full-universe
refit) is selected. Rationale on record: a corpus statistic must
be a property of the corpus, fixed independently of the
evaluation queries; a query-derived reference is evaluation-
dependent preprocessing, the same family of contamination this
project polices everywhere else. Two permanently non-matching
"BM25-alone" numbers in the record is not an acceptable
alternative for the price of one CPU refit.

## A1 — Refit (CPU only)

- Refit ALL P5 BM25 features — whole-fragment AND edge-window
  (N=3 per the D16b promotion) — with IDF/avgdl computed over
  the full non-test universe (21,920 fragments; the P4B B1
  reference). Candidate lists themselves (D16/D16b union
  top-200) are unchanged; only the scoring statistics refit.
- VERIFICATION GATE: the refit BM25-alone row on the 182 dev
  joins at full_distractor must reproduce P4B's B1 numbers
  exactly (0.676 / 0.808 at @1/@10, to 4 decimals). If it does
  not, STOP and flag — do not proceed on an unverified baseline.

## A2 — Gate-table re-emission (addendum, not rewrite)

- Re-run the D19 ablation grid and G1–G4 gate table over the
  corrected features (same frozen combiner protocol: refit the
  same logistic regression on TRAIN with the corrected feature
  values; no new features, no search). Emit as an ADDENDUM
  section appended to p5_report.md ("Corrected-baseline gate
  table"), leaving the original table in place above it,
  labeled with its now-understood reference-set caveat.
- Expected outcome, stated in advance: all gate VERDICTS
  unchanged (a ~1-point baseline shift is noise against a
  40-point cascade regression). If ANY verdict flips, STOP and
  flag before D17c — that would mean the failure geometry is
  more baseline-sensitive than anything yet measured, and the
  diagnosis plan itself would need rethinking.

## A3 — Convention codified (prevents recurrence)

Append to the project's standing conventions (CLAUDE.md
conventions section, one line, dated):

  "Corpus statistics (BM25 IDF/avgdl, calibration
  distributions, vocabulary counts, damage-rate profiles) are
  fit over the DECLARED universe for their phase (typically the
  full non-test universe), never over query-derived subsets.
  Any deviation is a documented decision, not a default.
  (Added 2026-07-22 after the E1.3 reconciliation; see
  p5c_report.md.)"

## A4 — Proceed to D17c

- With A1 verified and A2 emitted, D17c (P5C_SPEC.md) proceeds
  immediately and WITHOUT further check-in — the E1.3 stop
  condition is resolved by this amendment.
- D17c's M1 correlations use the CORRECTED BM25 scores
  (full-universe statistics) throughout, so every downstream
  diagnostic inherits the canonical baseline from the start.
- All other P5C_SPEC provisions unchanged: D17b conditioning,
  two-config ceiling, 12h budget, verbatim gates, automatic
  fallback, no third round.

## Paper note (no action; file with paper materials)

The E1.3 decomposition itself is a datum: a 30% reduction in
BM25's IDF reference corpus moved dev-join recall by only
~1 point (0.676->0.665 @1) — the lexical signal on this corpus
is stable under substantial reference perturbation. One
sentence in the robustness discussion; also a candidate
methods-section anecdote for why the project measures
attributions rather than narrating them (both pre-named
explanations for the delta measured to exactly zero).

## Acceptance (fold into p5c_report.md when the pass completes)

1. A1 verification gate: refit reproduces 0.676/0.808 to 4
   decimals (show the row).
2. A2 addendum emitted; verdict-stability statement (each of
   G1–G4: unchanged / FLIPPED) — any flip stops the line.
3. A3 convention line present in CLAUDE.md (quote it).
4. D17c report follows per P5C_SPEC.md unchanged.

Small artifacts back: updated p5c_report.md (A1/A2/A3 sections),
p5_report.md addendum, then d17c_report.md. No checkpoints, no
parquet.
