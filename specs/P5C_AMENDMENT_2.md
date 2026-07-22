# P5C_AMENDMENT_2.md — E2 resolution + pipeline hardening before the one-way door

Authority: amends P5C_SPEC.md (+ Amendment 1). Ratified jointly
(Ixca + architect session) 2026-07-22 on review of the E2 finding
in p5c_report.md. Two purposes: (1) resolve E2 (content-blind seam
scoring) via fix -> audit -> sighted re-score -> third gate table;
(2) install a HARDENING LAYER against the whole genus of bugs this
cycle has produced, BEFORE P6 — because P6's test runs happen once,
and a silent plumbing bug there is unfixable forever. No GPU is
authorized by this amendment; everything is CPU-only.

Diagnosis of the genus, on record: all three caught bugs (H1
family exclusion, IDF reference drift, flatten_lines tuples) share
one shape — a silent representation or bookkeeping mismatch at an
interface between components, absorbed without error by a
defaulting lookup, a permissive type, or a per-script
reimplementation. The remedy genus is likewise one shape:
canonical single implementations, hard contracts at interfaces,
and known-answer tracers that verify plumbing (not performance)
before every run.

## H1 of this amendment — E2 fix (canonicalize, don't patch)

- New library function `lib/hittite_tokenizer.py::
  encode_fragment_window(lines, *, include_restored=False)` —
  THE single path from (token, damage_state) line structures to
  model input ids, implementing the already-correct
  `render_tokens()` unpacking pattern. All five affected scripts
  (27, 27b, 28, 29, 29b) import it; every local `flatten_lines`
  is DELETED, not fixed in place. Convention line added to
  CLAUDE.md: "Model-input encoding goes through
  encode_fragment_window(); local re-implementations are
  forbidden."
- `Tokenizer.encode()` gains STRICT MODE (default ON): asserts
  every element is `str` before lookup; a tuple/list raises
  immediately with the offending element in the message. The
  defaulting `.get(t, unk)` silently absorbing tuples is the
  exact mechanism that hid E2 for an entire phase; strict mode
  makes that class of bug a crash at first token instead of a
  false paper section.

## H2 — Tokenization-path audit (D15/P4B first; Branch R depends on it)

- Table in `h2_audit_report.md`: EVERY call site in the repo that
  encodes fragment content into any model (training and scoring;
  D14 pretrain, D15 train, P4B re-embedding, D17/D18/D19, demo
  export where applicable), with columns: script, function,
  unpacks-correctly (verified by EXECUTING on one real fragment
  and inspecting the resulting ids, not by reading code), verdict
  CLEAN / BROKEN / UNCERTAIN.
- Priority rows: `20_biencoder.py` training featurization and the
  P4B embedding path. If EITHER is broken, STOP — Branch R's
  evidentiary base (p4b_report.md B1/B2) is compromised and the
  branch selection itself returns to the joint call before any
  re-scoring proceeds.
- Bug-account confirmation: histogram the §5 TRAIN positive
  seam_scores split by synthetic (correct path) vs real-join
  (broken path). Predicted signature: bimodal — synthetic
  positives dispersed, real-join positives clustered near the
  negatives' 0.876 attractor. Include the figure + one paragraph.
  (If the signature is absent, say so — the bug is still real and
  directly verified; the mixture story would just be wrong.)

## H3 — Contracts library (`lib/contracts.py`; small, used everywhere)

Each helper is a few lines; the value is that they run at EVERY
ingress, not once in a test file. All raise on violation except
the two marked WARN.

- C1 `assert_encoding_sane(ids, tokenizer, max_unk=0.05)`:
  window UNK-rate <= 5% (corpus OOV is 0.16%; E2 ran at 82.6%)
  AND at least one non-special token present; logs ONE decoded
  round-trip example per script invocation.
- C2 `assert_parallel(*seqs)`: equal lengths for parallel lists
  (tokens / damage_states / glyphs) at CONSTRUCTION time. Used in
  decompose, cu_alignment, fracture engine, encode path.
- C3 `assert_truth_reachable(query, gold, candidate_ids)`: for
  every eval query, the gold partner is IN the candidate universe
  (or is explicitly counted into a reported ceiling-exclusion
  line). H1's bug was truth silently excluded and 0.0 read as
  "hard task"; this makes that impossible to repeat silently.
- C4 `assert_stats_provenance(stats, expected_universe,
  expected_n)`: every fitted corpus statistic (BM25 IDF/avgdl,
  calibration distributions, vocab) is a stamped object carrying
  {universe_name, n, content_hash}; consumers assert the stamp
  matches their declared universe. Amendment 1's convention, now
  enforced in code rather than prose.
- C5 `assert_no_test(ids)` / `assert_dev_only_selection(...)`:
  the split-purity asserts, factored into one helper and called
  at every data ingress in every scoring/training/export script
  (several scripts already do this ad hoc; unify them).
- C6 `assert_unique_docids(frame)`: no doc_id appears twice after
  loading; the canonical fragment-universe loader (with the
  28-ambiguous exclusion) becomes the ONLY loader — decompose-
  derived artifacts consumed downstream get re-checked at load,
  closing the KUB 4.1 class.
- C7 `assert_seam_window_bilateral(window_meta)`: every
  constructed seam window contains >= 1 lexical (non-special)
  token from EACH side of the seam. A content-blind or one-sided
  window fails loudly. (E2 would also have tripped this.)
- C8 (WARN) `warn_degenerate_feature(name, values)`: any combiner
  feature with near-zero variance or NaN/inf across the training
  set emits a loud warning with the distribution summary. The
  negatives' 0.876 ± 0.024 was visible in the feature table all
  along; this makes it impossible to not-see.
- C9 (WARN) intent-tagged features: each combiner feature
  declares its DESIGNED sign (all current features: positive =
  more join-like). After fitting, any learned coefficient with
  sign opposite to intent triggers a prominent report section —
  the fit proceeds (the data may be right and the intent wrong),
  but silence is no longer an option. P5's negative seam_score
  weight sat in a coefficient list for a full report cycle;
  never again.
- C10 impossible-value tripwires in the reporting layer: any
  recall/AUC cell that is exactly 0.0 or exactly 1.0 with n >= 20
  gets a mandatory one-line explanation in the emitting report.
  Legitimate zeros exist — tier-A full-distractor was one — but
  each must be claimed, not passed over; v1's silent 0.0 tables
  are the motivating case.

## H4 — Tracer suite (`scripts/00_tracers.py`; runs in seconds;
## MANDATORY before every scoring/training run and at the top of P6)

A frozen canary set, committed to the repo: 5 easy dev joins
(high overlap), 5 random non-pairs, 3 known duplicates. Tracers
verify PLUMBING, not performance:

- T1 SCRAMBLE SENSITIVITY (the E2 killer): for each canary pair,
  score once normally and once with the candidate's lexical
  content randomly permuted (structure/damage layout preserved).
  ASSERT the score CHANGES (beyond float noise) for >= 4/5
  canaries, for EVERY content-consuming scorer (seam, D18, BM25,
  any future model). A scorer whose output is invariant to its
  input's content is blind, definitionally, whatever its metrics
  say.
- T2 SELF-SIMILARITY: BM25 and any embedding scorer must score
  fragment-with-itself above fragment-with-random for 5/5
  canaries.
- T3 EASY-CANARY RANKING: within a 50-candidate toy universe,
  each easy canary's true partner ranks top-10 for the full
  pipeline. Failure = plumbing, not difficulty, by construction
  of the canaries.
- T4 D18 CONTEXT SANITY: for canary joins, the true
  continuation's probability WITH query context exceeds the null
  for >= 4/5 — the lift D18 assumes exists must exist on gimmes.
- T5 DETERMINISM SMOKE: score 20 fixed pairs twice in-process;
  assert bit-identical.
- Tracer results (pass/fail per tracer, one line each) are
  embedded at the top of every downstream report. A report
  without a tracer block is an unaccepted report.

## H5 — Sighted re-score and the third gate table

Order: H2 audit verdict (STOP if D15/P4B broken) -> H1 fix ->
contracts installed -> tracers green -> re-score.

- Re-run D17 (27, 27b), D18 (28), and D19 featurization +
  combiner fit (29b path) through encode_fragment_window(),
  against the SAME frozen D14 checkpoint, corrected BM25 features
  from Amendment 1 throughout. CPU-only; comparable wall-clock to
  the prior pass.
- Emit the SIGHTED GATE TABLE — G1–G4 verbatim, per-tier and
  hard-set rows, CIs, plus the §5-style positive-vs-negative
  score comparison for the now-sighted head, plus C8/C9 output
  sections.
- Branch logic downstream (pre-registered):
  - Sighted gates PASS (G1+G4; G2 per the standing clause): D17b
    is UNNECESSARY — proceed-to-P6 recommendation with the frozen
    head; the prior failure is written up as an input-pipeline
    artifact, not a model finding.
  - Sighted gates FAIL: NOW run D17c's M1/M2 diagnostics on the
    sighted scores (they finally test what they were designed to
    test), then D17b per its existing conditioning, budget, and
    two-config ceiling, then the automatic fallback. Nothing
    about that machine changes except that its inputs are real.

## H6 — Errata & narrative corrections

- p5_report.md §5: annotate the curriculum-gap mechanism story
  SUPERSEDED (computed on content-blind inputs; see E2/H5), with
  a pointer to the sighted table. Original text stays in place.
- P5C_SPEC.md standing-facts paragraph: corrective note appended
  (the 0.876/0.690 comparison was an artifact of input
  degeneracy, not a measurement of the head's preferences).
- Paper notes: the "convergent negative finding" claim is
  DOWNGRADED to single-component (D15) pending H2's audit of
  D15's own path; if D15 audits clean, restate it as the sole
  verified leg. The E2 episode itself becomes a methods
  anecdote: the diagnostic's data requirements (per-token damage
  states) are what exposed the blind scorer — tooling honesty
  paid for itself.
- data_card_notes.md, one line: "Seam/continuation scores
  computed before 2026-07-22 used incorrectly encoded inputs,
  were caught by internal audit, and are superseded by re-scored
  values; see p5c_report.md E2." Also state: the demo never
  displayed these scores — 'Edge fit: pending P5' was literally
  true throughout.

## Acceptance checks (`p5c2_report.md`)

1. H2 audit table complete; D15/P4B rows verdicted BY EXECUTION;
   bimodality figure + paragraph included; STOP honored if
   triggered.
2. encode_fragment_window() exists; zero local flatten
   implementations remain (grep proof in the report); strict-mode
   encode demonstrated to raise on a tuple (show the traceback).
3. contracts.py: each of C1–C10 exercised once in a test showing
   it FIRES on a constructed violation (an assert that cannot
   fire protects nothing) and passes on clean input.
4. Tracer suite green; T1 additionally shown to FAIL against the
   pre-fix broken path (retro-validation: the tracer catches the
   actual historical bug) and PASS post-fix.
5. Sighted gate table emitted with tracer block, C8/C9 sections,
   per-tier + hard-set rows, and a branch recommendation (branch
   selection reserved for the joint call).
6. H6 errata all in place (quote each in the report).
7. No test-side contact (assert + statement); zero GPU hours.

Small artifacts back: p5c2_report.md, h2_audit_report.md, sighted
gate tables (md), tracer output block, updated errata files. No
checkpoints, no parquet.
