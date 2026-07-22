# P5C_SPEC.md — Boundary-head diagnosis, one targeted retrain, pre-registered fallback

Authority: CLAUDE.md + P5_RERANK_SPEC.md + p5_report.md review.
Ratified jointly (Ixca + architect session) 2026-07-22. Standing
facts: P5 gates G1/G2/G4 FAILED (cascade regresses BM25-alone);
D19's combiner learned NEGATIVE weights on seam_score/n_agree/
d18_lift because the frozen D14 head scores BM25-mined
lexically-similar non-partners HIGHER and more consistently
(0.876 ± 0.024) than real join partners (0.690 ± 0.251). D17b was
correctly withheld pending this joint call. This spec authorizes:

> **Corrective note (2026-07-22, per P5C_AMENDMENT_2.md H6):** the
> 0.876/0.690 comparison above was an artifact of input degeneracy,
> not a measurement of the head's preferences. A per-script
> tokenization bug (E2, `flatten_lines`, fixed via
> `encode_fragment_window()`) fed ~83%-`<UNK>` windows to the frozen
> D14 head for every real-join positive and every hard negative in
> this comparison; only the 600 synthetic positives (a different,
> correctly-tokenized code path) carried real content. The 0.690±0.251
> figure exactly reconstructs as a two-population mixture (0.87-ish
> content-blind cluster + a widely-dispersed content-aware
> distribution) — see `reports/h2_audit_report.md`. This spec's D17c/
> D17b/fallback MACHINERY is unaffected; only the diagnosis this
> paragraph offers for WHY G1/G2/G4 failed is corrected — see
> `reports/p5c2_report.md` for the sighted re-measurement.
one zero-GPU discriminating diagnostic (D17c), ONE conditional
retraining round (D17b, <= 12h GPU), gates re-applied verbatim,
and an AUTOMATIC fallback if they fail again. No third round
exists. Splits frozen; dev for selection; test touched by nothing;
engineering law applies.

## E1 — Erratum & bookkeeping (do first, independent of the rest)

1. Regenerate the patched P3 tables with the corrected H1
   family-exclusion logic as `results_p3_patched_v2/`. Do NOT
   overwrite or delete `results_p3_patched/` (v1) — mark it
   SUPERSEDED in its directory (a one-line SUPERSEDED.md pointing
   to v2 and to the erratum).
2. Append an erratum paragraph to `h1_patch_report.md`: what the
   bug was (same-parent_doc siblings excluded as "same family,"
   deleting every join query's own true partner), which numbers
   it affected (v1 patched join tables — tier-A/B 0.0 artifacts),
   which it did NOT affect (original unpatched P3 numbers incl.
   the 0.059 number-to-beat; duplicates task), date, git hash of
   the fix.
3. Baseline reconciliation, one paragraph in p5c_report.md:
   derive BM25-alone 0.676/0.808 (P4B) -> 0.665/0.802 (P5)
   exactly — decompose into (a) H1-correction effect and (b)
   union-candidate-set effect, so the baseline's provenance is
   closed. If the decomposition does not fully explain the
   delta, STOP and flag before D17c.

## D17c — Discriminating diagnostic (zero GPU; from existing
## D17/D18 score artifacts + corpus parquets)

Two mechanisms on trial; each gets a named verdict
(LIVE / NOT LIVE / INDETERMINATE) with the numbers that decide it.

- M1 SIMILARITY-ATTRACTION (curriculum gap: "lexically-similar-
  but-wrong" never a negative type):
  a. Among NEGATIVE pairs only: Spearman correlation of
     seam_score with the candidate's BM25 score to the query
     (whole-fragment and edge-window variants). Strongly
     positive -> M1 LIVE.
  b. Bin negatives by BM25-score decile; plot mean seam_score
     per decile (table, not just a figure).
- M2 FLUENCY/DAMAGE CONFOUND (head scores intact formulaic text
  above damaged true seams):
  a. Compare seam-WINDOW damage statistics (x-rate,
     restored-share, edge-loss incidence, attested-sign density)
     between positive and negative pairs at the scored argmax
     placement. Report means ± std both classes.
  b. Across ALL pairs: correlation of seam_score with
     seam-window damage rate; and within POSITIVES only (holds
     truth constant, varies damage). Strongly negative,
     especially within-positives -> M2 LIVE.
  c. Sanity slice: the 10 highest-scored negatives and 10
     lowest-scored positives, rendered with damage states, one
     line of qualitative annotation each — do they LOOK like
     "pristine formula" vs "broken truth"?
- Emit `d17c_report.md` with both verdicts and a one-paragraph
  D17b curriculum prescription derived from them (which
  ingredients below activate).

## D17b — ONE conditional retraining round (<= 12h GPU;
## contents conditioned on D17c verdicts)

Base: D14 checkpoint; fine-tune the boundary-validity head (and,
config-flagged, the top encoder layers — default head-only first;
if head-only shows no dev-AUC movement in the first 2h, the
unfreeze-top-2-layers config MAY be swapped in within the same
12h budget, logged, no other architecture changes).

Curriculum ingredients (activated per D17c):
- IF M1 LIVE: add negative type 4 to the boundary curriculum:
  BM25-hard negatives — seam windows constructed from
  top-BM25-ranked non-partner candidates for TRAIN-side queries
  (mining depth config; never dev/test queries; never other
  witnesses of the same composition, per the D14 rule that
  protects duplicate signal).
- IF M2 LIVE: positives include fracture-engine seam-local pairs
  with the EROSION pass applied AT THE SEAM at calibrated rates
  (the engine's corrected use: damaged-but-true seams), so the
  head cannot learn damage == wrong. Additionally, apply matched
  erosion to a sampled share of negatives (config) so damage
  rate cannot serve as a class giveaway in EITHER direction.
- IF BOTH LIVE: both, jointly; ratios in config, defaults 1:1:1
  real:synthetic-damaged:prior-curriculum; no ratio search
  beyond the single default + one fallback (0.5 weight on the
  new types) — two configs maximum, both reported.
- IF NEITHER LIVE: do not train. STOP; architect check-in (the
  diagnosis failed, and spending the round anyway is exactly
  what this spec exists to prevent).
- Training mechanics: TRAIN side only; dev AUC (per negative
  type, INCLUDING the new type 4) for early stopping; seeds/git
  hash/corpus version logged; kill+resume verified to the D14
  bit-identical standard before the long run.

## D19 re-run — combiner + gates, verbatim

- Refit the same pre-committed logistic regression (same
  features, same TRAIN-side fit protocol — no new features, no
  combiner search) over D17b scores (+ existing D18 scores; D18
  is NOT retrained — if D17b's encoder layers were unfrozen,
  re-EMIT D18 lifts from the updated encoder, same H <= 5 cap,
  and say so).
- Re-apply gates G1–G4 from P5_RERANK_SPEC.md verbatim — same
  thresholds, same baseline rows restated (v2-corrected), same
  per-tier and hard-set tables, CIs throughout. Also report the
  D17b head's positive-vs-negative score table (the §5-style
  comparison) so the mechanism fix is verified at the
  representation level, not just the leaderboard level.

## Pre-registered fallback (automatic; no discussion round)

IF the re-applied gates fail (G1 or G4 fails; or G1/G4 pass but
regress vs BM25 in point estimate): OPTION 2 EXECUTES —
- BM25-retrieve-deep (union candidate set) ships as the final
  P5 retrieval+ranking stage, no learned reranker.
- D15, D17/D18/D19, and D17b are written up together as the
  paper's convergent negative finding: learned similarity/
  continuity signals collapse toward lexical similarity on this
  corpus across three components and two diagnostic routes, and
  a targeted curriculum intervention did not rescue it.
- P6 proceeds on BM25-alone with the paper reframed per
  P5_RERANK_SPEC's proceed clause (contribution = honest
  ranking + measurement + negative results; tier-A continuation
  stated as open).
No third training round. No new proposals inside this cycle.
(If G1/G4 PASS meaningfully: proceed-to-P6 recommendation with
the numbers; G2 status shapes the paper claim per the standing
clause.)

## Acceptance checks (`p5c_report.md`)

1. E1 complete: v2 tables emitted, v1 marked superseded, erratum
   paragraph appended, baseline delta fully decomposed.
2. D17c: M1 and M2 verdicts with deciding numbers; 20-case
   qualitative slice included; curriculum prescription stated
   BEFORE D17b launches (timestamped).
3. D17b (if launched): config(s) used, per-negative-type dev
   AUC curves incl. type 4, resumability verified, wall-clock
   <= 12h per config, two configs maximum.
4. D19 re-run: full gate table, per-tier + hard-set rows,
   positive-vs-negative score comparison for the new head.
5. Fallback clause: report states explicitly which branch
   executed and why, quoting the pre-registered rule.
6. No test-side contact anywhere (assert + statement).

Small artifacts back: p5c_report.md, d17c_report.md, updated
h1_patch_report.md, results_p3_patched_v2 summary tables (the
small .md tables, not parquet). No checkpoints.
