# CONTEXT_HANDOFF.md — Read this first (new architect session)

Prepared 2026-07-22 for the Phase 2 opening conversation. Everything
here is verified against the project's own reports; where something is
opinion or open, it says so.

## 0. Read this warning before you read anything else

The previous architect session's most costly failures were not
technical. They were:

- **Narrating attributions instead of measuring them.** Twice, causes
  were asserted with confidence ("almost certainly X and Y") and
  measured to contribute *exactly zero*. Never write "almost
  certainly." Name the measurement.
- **Building a mechanism story before auditing the model's inputs.**
  An elaborate two-mechanism theory (with confidence percentages,
  which made it look rigorous) was constructed on scores computed
  over ~83% `<UNK>` — a model reading blank pages. Audit inputs
  first, always.
- **Frame lock.** For several rounds the session optimized a cascade
  inside an unexamined premise ("the model is the variable, the task
  is fixed"). The governance apparatus kept catching parameter-level
  errors, which *licensed* misplaced confidence. Governance cannot
  audit premises. Only deliberate stepping-back can, and Ixca had to
  request it.

Ixca will treat you as a colleague and will push back when you reach
for tidy conclusions. Take that seriously; it is the most valuable
part of this collaboration.

## 1. The project in one paragraph

**Takšan** (Hittite *takšan*, "jointly; the middle") suggests joins
and duplicates among Hittite tablet fragments. Corpus: TLHdig Beta
0.2.0, ~22k documents, CC BY 4.0, transliterations only (no
translations). Target: the ALP workshop, and a mentorship pitch to UT
Austin MSAI. Ixca does the research direction and ratification; an
architect session (you) does specification and analysis; a separate
Claude Code session builds and reports. Splits are FROZEN at git
7b010cde. The test side has never been touched.

## 2. What works, with numbers

BM25 over sign-level tokenization, dev joins (n=182), full-distractor:
**recall@1 = 0.6758, recall@10 = 0.8077, recall@200 = 0.896.** Task A
(composition assignment, test-side, n=793): recall@1 = 0.7831. Frozen
P3 test-side tier-A baseline: **0.0588 (test_only) / 0.0000
(full_distractor)**, n=34.

Tokenizer: vocab 2,374, dev OOV 0.16%, round-trip exact. Note the
corpus's most frequent token is `x` (illegible) at 19,624 documents —
the most common "sign" in Hittite is a hole.

## 3. What doesn't work, with numbers (Phase 1's real output)

1. **Dense bi-encoder loses to BM25 and degrades faster with scale.**
   recall@10: 0.835→0.808 (BM25) vs 0.571→0.396 (dense) from
   test_only to full_distractor. Dense-only hits at k=10: 1 of 182.
   RRF fusion (0.769) < BM25 alone (0.808). Encoding verified CLEAN.
2. **Frozen boundary head does not discriminate on real content.**
   Sighted seam_score: positives 0.4680 ±0.1597, negatives 0.4804
   ±0.1411 (negatives marginally *higher*). Cascade regresses BM25
   on every gate.
3. **Edge-continuation lift is negative.** H=5 mean −0.110 over
   206,551 pairs; tracer T4 failed independently. Span-infilling:
   0.413 exact at length 1, 0.002 at 5, 0.000 at 6+.
4. **Tier A is at zero.** Sighted cascade tier A recall@1 = @10 =
   0.0 (n=27). BM25 ceiling@200 for tier A = 0.519.

## 4. The finding that reframes everything

The fracture engine's calibration states plainly that tier A/B joins
have `n_shared_lines ≈ 0` — **"that IS the no-overlap seam
signature."** Phase 1 built lexical-similarity-adjacent methods for a
class of pairs *defined by the absence of shared text*. The aggregate
recall numbers are carried by tier C (ceiling 0.984); "join detection"
has been two different problems sharing a name.

Phase 2 therefore asks *what is recoverable from this corpus at all,
and under what formulation* — not *which model ranks pairs best*. See
`PHASE2_CHARTER.md` for Q1–Q5 and the probe menu (P2-A through P2-H).
Highest priority: **P2-A** (can the head localize a seam it has been
handed?) and **P2-D** (how reliable is the ground truth?).

## 5. Four bugs, and what they taught

- **H1 family exclusion** — composite-doc siblings shared a
  `parent_doc`, so every join query's true partner was silently
  excluded; tables read 0.0 and were nearly accepted as difficulty.
- **IDF reference drift** — corpus statistics fit over a
  query-derived subset (15,153) not the declared universe (21,920).
- **E2 content-blind scoring** — five local `flatten_lines`
  reimplementations pushed tuples into a defaulting `.get()`; 82.6%
  UNK for an entire phase.
- **B5 scheme mismatch (OPEN)** — `sign_attested` word-grain tokens
  fed to the decomposed per-sign vocabulary, 13.9% UNK. B5's ~0.56
  correlation is **provisionally withdrawn**; re-run or don't cite.
  B1/B2 are CLEAN, so Branch R stands.

All four share one shape: a silent representation mismatch at a
component interface, absorbed by permissive code. The hardening layer
(`encode_fragment_window`, contracts C1–C10, tracers T1–T5) exists to
kill that genus. **T1 is retro-validated**: 0/8 canaries changed under
scramble pre-fix, 8/8 post-fix.

## 6. Demo track (unchanged, do not destabilize)

`TAKSAN_DEMO_SPEC.md` is the single consolidated authority (it
supersedes DEMO_SPEC, DM_AMENDMENTS, DM_AMENDMENT_2,
DESIGN_ADDENDUM). Private, static, offline, BM25-backed. Glyph layer:
83.11% coverage via `cu_alignment.py`, hand-audited at 0 damage-state
misattributions in 44/45 samples. Design: fired-dark default, Green
Stone accent, seal-based status vocabulary (Proposed / Sealed / Set
aside), isometric cube mark, pedestal-line motif. Ixca has supplied
their own 2017 photograph of the Green Stone at Hattusa for the About
page. Ixca decided 2026-07-22: **demo continues on current rails.**

## 7. Working relationship and standing conventions

- Confidence percentages on factual claims; opinions labeled as
  opinions.
- Read attachments completely before responding.
- Judgment calls are joint; Code Claude recommends, never decides.
- Superseded numbers are annotated in place, never deleted.
- `CONTRIBUTION_LEDGER.md` records human/AI attribution per decision,
  including AI errors. It is awaiting Ixca's review signature.
- Phase 2 governance is `SANDBOX_RULES.md` — deliberately lighter
  than Phase 1's. No pre-registered gates on probes; time-boxed kill
  criteria; `[PROBE]` labels mandatory; a scheduled premise audit
  every third probe.

## 8. Open items inherited

- P2-A and P2-D unrun (highest priority probes).
- B5 re-run or permanent non-citation (cheap; decide early).
- P6 (test-side final runs) deferred until Phase 2 says what to
  measure.
- TLHdig Beta 0.3 exists (2025-11-01); pin stays at 0.2.0-beta.
  Corpus migration is a one-way door → joint call.
- TLHdig team outreach: after numbers exist. Agenda items are
  accumulating (0.3 access, translation-layer roadmap, Ullikummi
  font permission for any public build).
- Ledger signature pending.

## 9. If you read only one thing

The most defensible asset this project has is not a recall number. It
is the audit trail: four bugs caught before they could launder false
findings into a paper, every superseded number annotated rather than
erased, and a phase that ended by questioning its own premise instead
of chasing one more model. Protect that. It is what makes the negative
results worth publishing.
