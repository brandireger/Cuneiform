# P4 Report -- Tokenizer, Fracture Engine, Pre-training, Bi-encoder

Aggregates all 6 acceptance checks from specs/P4_NEURAL_SPEC.md. Every number here is copied from its source report (reports/*.md), never recomputed -- follow the links for full detail, methodology, and caveats.

## Check 1 -- H1 harness patch

Full detail: `reports/h1_patch_report.md`.

- 5 docID-family pairs found (exhaustive regex sweep, base-form-verified); 6,408 same-family candidate exclusions applied across the full P3 scorer x task x index-variant re-run.
- 98 exact-dedup groups inspected: 97 are genuine formulaic collisions (near-empty fragments from unrelated tablets) and correctly stay in ranking; the 1 that's also a real family match is excluded via the family mechanism, not a separate rule.
- Patched P3 tables emitted to `results_p3_patched/`.

## Check 2 -- Sign-level tokenizer (D12)

Full detail: `reports/tokenizer_report.md`.

- **Vocab size: 2,374** (1,022 logogram-class + 1,342 syllabic/other).
- **Dev OOV rate: 0.16%** -- PASS (target <1%).
- Amendment applied and reported honestly: the first attempt (P3's bm25_sign convention verbatim) landed at vocab=14,170 / OOV=3.66%, missing both targets -- flagged rather than silently fixed; architect approved sign-level logogram decomposition (splitting determinative/Sumerogram/Akkadogram content on real wedge-cluster boundaries), which fixed both.
- Round-trip fidelity: 5/5 seeded examples exact match, 0 unknown tokens.
- Truncation rate at seq_len=512: 3.82% of fragments.

## Check 3 -- Fracture engine (D13)

Full detail: `reports/fracture_report.md`.

- 3,333 eligible TRAIN fragments for cut pairs (>=8 lines, >=60 attested signs); 17,644 eligible for self-supervised views (TRAIN + discovery pool).
- Synthetic-vs-real distribution match shown (not asserted) across n_lines / n_attested_signs; 10 rendered examples with seam parameters included in the source report.
- Streaming generator, seeded -- millions of pairs never materialized to disk; a fixed 2,000-pair dev-diagnostic set is.

## Check 4 -- Pre-training (D14)

Full detail: `reports/pretrain_report.md`.

- Final checkpoint: step 59,999 (all 60,000 configured steps completed; scheduled task exited cleanly, no crash).
- Dev MLM loss: 7.85 (step 0) -> 3.94 (final fresh pass).
- Span-infilling exact-match (SPAN-level, by length band): strong at length 1 (41.3%), collapsing to 0% by length 6+ -- reported plainly, not smoothed over.
- Boundary-head AUC by negative type (dev): in_doc=0.746 (hardest), cross_genre=0.901, random=0.947 (easiest) -- matches the intended difficulty curriculum.
- Restoration-agreement (diagnostic only, never a training/eval target): token-level 21.0%, span-exact 11.7% over 309 real editor-restored dev spans.

## Check 5 -- Bi-encoder (D15)

Full detail: `reports/biencoder_report.md`.

- Best combo: **real_only / line_max** -- real dev-join recall@10 = **0.571**.
- BM25 dev-join recall@10 baseline: **0.835**.
- Delta: **-0.264**.

**PRE-REGISTERED SUCCESS CRITERION: NOT MET.** The spec's stated bar for proceeding to P5 is real dev-join recall@10 *meaningfully above* BM25's -- the best bi-encoder combo instead lands meaningfully *below* it (0.571 vs 0.835). Both numbers are stated per spec; whether/how to proceed is the judgment call explicitly reserved for the architect check-in, not decided here. Duplicates show the same pattern (BM25 ahead on all three mixes), consistent with CLAUDE.md's own prediction that duplicates are near-solved by lexical overlap -- but the JOINS gap is the one that matters for the P5 decision, and it was not anticipated to run this direction.

## Check 6 -- Resumability

- **D14 (19_pretrain.py): rigorously verified.** Kill + resume tested against a small config; EVERY row of the resulting loss_curve.csv matched bit-for-bit against an uninterrupted continuous run (mlm_loss, boundary_loss, total_loss, dev_mlm_loss, dev_span_exact, dev_boundary_auc all identical; only wall-clock elapsed_s differed, as expected). Four real bugs were found and fixed during this testing (not assumed correct beforehand): local RNG state not saved (only global `random` module was), one of two save_checkpoint() call sites missed by an edit, an off-by-one re-executing the checkpointed step on resume, and a CUDA/CPU RNG-state tensor type mismatch on load.
- **D15 (20_biencoder.py): functionally verified, not bit-identically verified.** A fresh run followed by `--resume` was confirmed to load the checkpoint correctly (`Initialized from D14 checkpoint @ pretrain step 1000` / `Resumed after step N`) and continue without error, reusing the same save/load pattern already proven correct for D14. The full row-for-row bit-identical loss-curve comparison specifically was not repeated for D15 -- flagged honestly as a narrower check than D14's, not silently equated to it.

## Overall

Checks 1-4 and 6 (D14 half) pass cleanly. **Check 5 is the one that changes the picture**: the bi-encoder does not clear BM25 on the metric that was supposed to gate P5. This is reported as a real negative result, per CLAUDE.md's "report more, claim less" -- not reframed as a partial success. Recommended next discussion with the architect: whether P5 (edge-continuation scorer) proceeds anyway (P5 reranks a candidate list the bi-encoder produces, so a weak bi-encoder stage still constrains what P5 can recover), whether D15 needs another training round (more steps, different negatives, or a different base checkpoint), or whether the retrieval stage's design needs to change before P5 is worth building.